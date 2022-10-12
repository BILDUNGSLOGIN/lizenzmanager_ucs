# -*- coding: utf-8 -*-
from __future__ import annotations

import asyncio
import enum
import logging
import os
from hashlib import sha256
from typing import Dict, List, Optional, Set

# TODO: UDM REST client should raise application specific exception:
from aiohttp.client_exceptions import ClientConnectorError
from ldap3 import Entry, ALL_ATTRIBUTES, \
    ALL_OPERATIONAL_ATTRIBUTES
from udm_rest_client.udm import UDM, UdmObject

from ucsschool.apis.utils import LDAPAccess
from .backend import DbBackend, DbConnectionError
from .models import AssignmentStatus, Class, SchoolContext, User, Workgroup

UCR_CONTAINER_CLASS = ("ucsschool_ldap_default_container_class", "klassen")
UCR_CONTAINER_PUPILS = ("ucsschool_ldap_default_container_pupils", "schueler")

logger = logging.getLogger()


def _return_none_if_empty(input_string: str) -> Optional[str]:
    """ Returns None is string is empty """
    if input_string == "":
        return None
    return input_string


def remove_empty_values(input_object):
    fields = [i for i in input_object.__dict__.keys() if i[:1] != '_']
    for field in fields:
        if not getattr(input_object, field):
            delattr(input_object, field)
    return


class ObjectType(enum.Enum):
    GROUP = "group"
    SCHOOL = "school"
    USER = "user"


class LdapRepository:

    def __init__(self, ldap_auth: LDAPAccess):
        self._ldap_auth = ldap_auth
        self._user: Entry | None = None
        self._licenses: List[Entry] = []
        self._assignments: List[Entry] = []
        self._schools: List[Entry] = []
        self._workgroups: List[Entry] = []
        self._classes: List[Entry] = []

    async def load(self, userid: str):
        search_filter = f"(|(userid={userid})(&(objectClass=bildungsloginAssignment)(bildungsloginAssignmentAssignee=*))" \
                        f"(objectClass=bildungsloginLicense)" \
                        f"(objectClass=ucsschoolOrganizationalUnit)(objectClass=ucsschoolGroup))"

        entries = await self._ldap_auth.search(
            search_filter=search_filter,
            attributes=[ALL_ATTRIBUTES, ALL_OPERATIONAL_ATTRIBUTES]
        )

        self._process_entries(entries)

    def _process_entries(self, entries: List[Entry]):
        for entry in entries:
            if 'person' in entry.entry_attributes_as_dict['objectClass']:
                self._user = entry
            elif 'bildungsloginLicense' in entry.entry_attributes_as_dict['objectClass']:
                self._licenses.append(entry)
            elif 'bildungsloginAssignment' in entry.entry_attributes_as_dict['objectClass']:
                if 'bildungsloginAssignmentAssignee' in entry.entry_attributes_as_dict:
                    self._assignments.append(entry)
            elif 'ucsschoolOrganizationalUnit' in entry.entry_attributes_as_dict['objectClass']:
                self._schools.append(entry)
            elif 'ucsschoolGroup' in entry.entry_attributes_as_dict['objectClass']:
                if 'workgroup' in str(entry.ucsschoolRole):
                    self._workgroups.append(entry)
                elif 'school_class' in str(entry.ucsschoolRole):
                    self._classes.append(entry)

    def get_user(self) -> Entry:
        return self._user

    def get_assignments_by_assignee(self, assignee: Entry) -> List[Entry]:
        assignments = []
        for assignment in self._assignments:
            if assignment.bildungsloginAssignmentAssignee \
                    == assignee.entryUUID:
                assignments.append(assignment)

        return assignments

    def get_license_by_assignment(self, assignment: Entry) -> Entry | None:
        for license in self._licenses:
            if license.entry_dn in assignment.entry_dn:
                return license
        return None

    def get_school(self, name: str) -> Entry | None:
        for school in self._schools:
            if name == school.ou:
                return school
        return None

    def get_classes(self, school: Entry, user: Entry) -> List[Entry]:
        classes = []
        for _class in self._classes:
            if _class.ucsschoolRole == f"school_class:school:{school.ou}" and hasattr(_class,
                                                                                      'memberUid') and user.uid in _class.memberUid:
                classes.append(_class)
        return classes

    def get_workgroups(self, school: Entry, user: Entry) -> List[Entry]:
        workgroups = []
        for workgroup in self._workgroups:
            if workgroup.ucsschoolRole == f"workgroup:school:{school.ou}" and hasattr(workgroup,
                                                                                      'memberUid') and user.uid in workgroup.memberUid:
                workgroups.append(workgroup)
        return workgroups

    @staticmethod
    def get_school_roles(user):
        school_roles = []
        for school_role in user.ucsschoolRole:
            school_roles.append(str(school_role))
        return school_roles

    @staticmethod
    def get_object_classes(obj):
        _list = set()
        for object_class in obj.objectClass:
            _list.add(object_class)

        return _list


class UdmRestApiBackend(DbBackend):
    """LDAP Database access  using the UDM REST API."""

    def __init__(self, ldap_auth: LDAPAccess, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ldap_auth = ldap_auth
        self.ldap_base = os.environ["LDAP_BASE"]
        self.repository: LdapRepository | None = None
        self.udm = UDM(**kwargs)
        self.udm.session.open()
        self.assignment_mod = self.udm.get("bildungslogin/assignment")

    async def connection_test(self) -> None:
        """
        Test DB connection.

        :return: nothing if successful or raises an error
        :raises DbConnectionError: if connecting failed
        """

    async def get_user(self, username: str) -> User:
        """
        Load a user object and its school, class and license information from LDAP.

        :param str username: the `uid` LDAP attribute
        :return: User object
        :rtype: User
        :raises ConnectionError: when a problem with the connection happens
        :raises UserNotFound: when a user could not be found in the DB
        """
        self.repository = LdapRepository(self.ldap_auth)
        await self.repository.load(userid=username)

        user = self.repository.get_user()
        licenses = self.get_licenses_and_set_assignment_status(ObjectType.USER, user)
        return_obj = User(
            id=str(user.userId),
            first_name=str(user.givenName),
            last_name=str(user.sn),
            context=self.get_school_context(user),
            licenses=self._get_licenses_codes(licenses)
        )

        return return_obj

    async def _get_object_by_name(self, object_type: ObjectType, name: str) -> UdmObject:
        """
        Get group/user/school based on its name
        1. Search the object
        2. Obtain the object by its DN, as UDM REST API provides certain information
            (e.g. entryUUID) only in this case
        """
        if object_type is ObjectType.GROUP:
            mod = self.group_mod
            filter_string = f"(name={name})"
        elif object_type is ObjectType.USER:
            mod = self.user_mod
            filter_string = f"(username={name})"
        elif object_type is ObjectType.SCHOOL:
            mod = self.school_mod
            filter_string = f"(&(name={name})(objectClass=ucsschoolOrganizationalUnit))"
        else:
            raise RuntimeError("Cannot handle object type: {}".format(object_type))

        try:
            objects = [o async for o in mod.search(filter_string)]
        except ClientConnectorError as exc:
            raise DbConnectionError(str(exc)) from exc

        if len(objects) == 0:
            raise ValueError(f"No {object_type.value}-object found with the name '{name}'")
        try:
            [obj] = objects
        except ValueError:
            raise ValueError(f"More than one {object_type.value} found with the name '{name}'")
        return await mod.get(obj.dn)

    @staticmethod
    def _get_object_id(school_uuid: str, object_uuid: str) -> str:
        """ Create an ID for the object """
        string = str(school_uuid) + str(object_uuid)
        return sha256(string.encode("utf-8")).hexdigest()

    @staticmethod
    def _get_licenses_codes(licenses: List[Entry]) -> List[str]:
        """ Extract a list of unique licenses codes """
        return sorted(set(str(_license.bildungsloginLicenseCode) for _license in licenses))

    @staticmethod
    def extract_group_name(school: Entry, group: Entry) -> str:
        """
        In LDAP classes/workgroups are prepended with the school name:
        Example: DEMOSCHOOL-Group

        This function is meant to extract the name of the group
        """
        _, group_name = str(group.cn).split(f"{school.ou}-", 1)
        return group_name

    def get_class_info(self, school: Entry, class_obj: Entry) -> Class:
        """ Obtain relevant information about the class and initialize Class instance """
        licenses = self.get_licenses_and_set_assignment_status(ObjectType.GROUP, class_obj)
        return Class(id=self._get_object_id(school.entryUUID, class_obj.entryUUID),
                     name=self.extract_group_name(school, class_obj),
                     licenses=self._get_licenses_codes(licenses))

    def get_workgroup_info(self, school: Entry, workgroup: Entry) -> Workgroup:
        """ Obtain relevant information about the workgroup and initialize Workgroup instance """
        licenses = self.get_licenses_and_set_assignment_status(ObjectType.GROUP, workgroup)
        return Workgroup(id=self._get_object_id(school.entryUUID, workgroup.entryUUID),
                         name=self.extract_group_name(school, workgroup),
                         licenses=self._get_licenses_codes(licenses))

    def get_school_context(self, user: Entry) -> Dict[str, SchoolContext]:
        output = {}
        for school_ou in user.ucsschoolSchool:
            school = self.repository.get_school(school_ou)
            school_id = self._get_object_id(str(school.entryUUID), str(school.entryUUID))

            # Get all licenses, but filter out those with special type "Lehrkraft"
            # in case the user doesn't have a "teacher" role
            user_roles = self.get_roles(user, school_ou)
            all_licenses = self.get_licenses_and_set_assignment_status(ObjectType.SCHOOL, school)
            applicable_licenses = []
            for lic in all_licenses:
                if hasattr(lic,
                           'bildungsloginLicenseSpecialType') and lic.bildungsloginLicenseSpecialType == "Lehrkraft" and "teacher" not in user_roles:
                    continue
                applicable_licenses.append(lic)

            # Create school context object
            school_context = SchoolContext(
                school_authority=None,  # the value is not present in LDAP schema yet
                school_identifier=None,
                school_name=school_ou,
                roles=user_roles,
                classes=[self.get_class_info(school, c)
                         for c in self.repository.get_classes(school, user)],
                workgroups=[self.get_workgroup_info(school, w)
                            for w in self.repository.get_workgroups(school, user)],
                licenses=self._get_licenses_codes(applicable_licenses))
            remove_empty_values(school_context)
            output[school_id] = school_context
        return output

    def get_licenses_and_set_assignment_status(self, object_type: ObjectType,
                                               obj: Entry) -> List[Entry]:
        licenses = []
        assignments = self.repository.get_assignments_by_assignee(obj)
        for assignment in assignments:
            licenses.append(self.repository.get_license_by_assignment(assignment))
            if str(assignment.bildungsloginAssignmentStatus) != AssignmentStatus.PROVISIONED.name:
                if str(assignment.bildungsloginAssignmentStatus) == AssignmentStatus.AVAILABLE.name:
                    logger.error(
                        "License assignment for %s %r has invalid status 'AVAILABLE', setting to "
                        "'ASSIGNED' (and then to 'PROVISIONED'): %r.",
                        object_type.value,
                        obj.entry_dn,
                        assignment.entry_dn)
                    asyncio.create_task(self.correct_assignment_status(assignment))
                else:
                    asyncio.create_task(self.set_assignment_status_provisioned(assignment))

        return licenses

    async def correct_assignment_status(self, assignment: Entry):
        udm_assignment = await self.assignment_mod.get(assignment.entry_dn)
        udm_assignment.props.status = AssignmentStatus.ASSIGNED.name
        await udm_assignment.save()
        await self.set_assignment_status_provisioned(udm_assignment)

    async def set_assignment_status_provisioned(self, assignment: Entry | UdmObject):
        if isinstance(assignment, Entry):
            assignment = await self.assignment_mod.get(assignment.entry_dn)
        assignment.props.status = AssignmentStatus.PROVISIONED.name
        await assignment.save()

    def get_roles(self, user: Entry, school_ou: str) -> List[str]:
        """
        Returns a list of unique roles the user is assigned to in the given school
        First, tries to obtain the roles via user's ucsschoolRole property
        If this doesn't work out, falls back to general user's roles (defined via options)
        """
        roles = self._get_roles_for_school(self.repository.get_school_roles(user), school_ou)
        if not roles:
            logger.warning(
                "Cannot get roles of user %r at OU %r from 'ucsschool_roles' %r. Using "
                "objectClass fallback.",
                user.entry_dn,
                school_ou,
                user.ucsschoolRole,
            )
            roles = self._get_roles_oc_fallback(self.repository.get_object_classes(user))
        return sorted(roles)

    @staticmethod
    def _get_roles_for_school(roles: List[str], school: str) -> Set[str]:
        """
        Takes a list of ucsschool_roles and returns a list of user roles for the given school.

        >>> UdmRestApiBackend._get_roles_for_school(
        ... ["teacher:school:School1", "student:school:School2"],
        ... "school1"
        ... )
        {'teacher'}

        :param roles: The list of ucsschool_roles to filter
        :param school: The school to filter the roles for
        :return: The list of user roles for the given school
        :raises ValueError: If any of the role strings is malformed
        """
        # copied from id-broker-plugin/provisioning_plugin/utils.py
        filtered_roles = set()
        for role in roles:
            role_parts = role.split(":")
            if len(role_parts) != 3 or not all(role_parts):
                raise ValueError(f"The role {role} is malformed!")
            if (
                    role_parts[1] == "school"
                    and role_parts[2] == school
                    and role_parts[0] in ("staff", "student", "school_admin", "teacher")
            ):
                filtered_roles.add(role_parts[0])
        return filtered_roles

    @staticmethod
    def _get_roles_oc_fallback(options: Set[str]) -> Set[str]:
        if options >= {"ucsschoolTeacher", "ucsschoolStaff"}:
            return {"staff", "teacher"}
        if "ucsschoolTeacher" in options:
            return {"teacher"}
        if "ucsschoolStaff" in options:
            return {"staff"}
        if "ucsschoolStudent" in options:
            return {"student"}
        if "ucsschoolAdministrator" in options:
            return {"school_admin"}
        raise RuntimeError(f"Cannot determine role of user from options: {options!r}")
