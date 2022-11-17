# -*- coding: utf-8 -*-
from __future__ import annotations

import asyncio
import enum
import json
import logging
import os
from hashlib import sha256
from os.path import exists
from typing import Dict, List, Optional, Set

from fastapi import HTTPException
from ldap3 import Entry
from udm_rest_client.udm import UDM, UdmObject
from ucsschool.apis.utils import LDAPAccess
from .backend import DbBackend
from .models import AssignmentStatus, Class, SchoolContext, User, UserRole, Workgroup

UCR_CONTAINER_CLASS = ("ucsschool_ldap_default_container_class", "klassen")
UCR_CONTAINER_PUPILS = ("ucsschool_ldap_default_container_pupils", "schueler")

logger = logging.getLogger()

JSON_PATH = '/var/lib/univention-appcenter/apps/ucsschool-apis/data/bildungslogin.json'

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


class LdapUser:
    def __init__(self,
                 entry_uuid: str,
                 entry_dn,
                 object_class: List[str],
                 user_id: str,
                 given_name: str,
                 sn: str,
                 ucsschool_school: List[str],
                 ucsschool_role: List[str]):
        self.objectClass = object_class
        self.entry_dn = entry_dn
        self.ucsschoolRole = ucsschool_role
        self.entryUUID = entry_uuid
        self.uid = user_id
        self.userId = user_id
        self.givenName = given_name
        self.sn = sn
        self.ucsschoolSchool = ucsschool_school


class LdapLicense:
    def __init__(self, entry_uuid, entry_dn, object_class: List[str], bildungslogin_license_code,
                 bildungslogin_license_special_type):
        self.bildungsloginLicenseSpecialType = bildungslogin_license_special_type
        self.objectClass = object_class
        self.entry_dn = entry_dn
        self.entryUUID = entry_uuid
        self.bildungsloginLicenseCode = bildungslogin_license_code


class LdapAssignment:
    def __init__(self, entry_uuid, entry_dn, object_class: List[str], bildungslogin_assignment_status,
                 bildungslogin_assignment_assignee):
        self.objectClass = object_class
        self.bildungsloginAssignmentStatus = bildungslogin_assignment_status
        self.entry_dn = entry_dn
        self.entryUUID = entry_uuid
        self.bildungsloginAssignmentAssignee = bildungslogin_assignment_assignee


class LdapSchool:
    def __init__(self, entry_uuid, entry_dn, object_class: List[str], ou):
        self.objectClass = object_class
        self.entry_dn = entry_dn
        self.entryUUID = entry_uuid
        self.ou = ou


class LdapGroup:
    def __init__(self, entry_uuid, entry_dn, cn, ucsschool_role, member_uid: List[str]):
        self.memberUid = member_uid
        self.entry_dn = entry_dn
        self.entryUUID = entry_uuid
        self.cn = cn
        self.ucsschoolRole = ucsschool_role


class LdapRepository:

    def __init__(self, ldap_auth: LDAPAccess):
        self._ldap_auth = ldap_auth
        self._timestamp: float | None = None
        self._clear()

    def update(self, start_up=False):
        if not exists(JSON_PATH):
            logger.error('JSON file not found at %r. Please check if it is updating.', JSON_PATH)
            if not start_up:
                raise FileNotFoundError(f"JSON file not found at {JSON_PATH}. Please check if it is updating.")
            return

        stat = os.stat(JSON_PATH)
        file_time = stat.st_mtime

        if self._timestamp is not None and file_time <= self._timestamp:
            return

        self._clear()
        f = open(JSON_PATH, 'r')
        json_string = f.read()
        f.close()
        json_dictionary = json.loads(json_string)
        self._process_entries(json_dictionary)
        self._timestamp = file_time

    def count_objects(self):
        return len(self._users) + len(self._workgroups) + len(self._licenses) + len(self._assignments) + len(
            self._schools) + len(self._classes)

    def _clear(self):
        self._users: List[LdapUser] = []
        self._licenses: List[LdapLicense] = []
        self._assignments: List[LdapAssignment] = []
        self._schools: List[LdapSchool] = []
        self._workgroups: List[LdapGroup] = []
        self._classes: List[LdapGroup] = []

    def _process_entries(self, entries: Dict):
        for entry in entries['users']:
            self._users.append(
                LdapUser(entry['entryUUID'], entry['entry_dn'], entry['objectClass'], entry['uid'], entry['givenName'],
                         entry['sn'], entry['ucsschoolSchool'], entry['ucsschoolRole']))
        for entry in entries['licenses']:
            self._licenses.append(LdapLicense(entry['entryUUID'], entry['entry_dn'], entry['objectClass'],
                                              entry['bildungsloginLicenseCode'],
                                              entry['bildungsloginLicenseSpecialType']))
        for entry in entries['assignments']:
            self._assignments.append(
                LdapAssignment(entry['entryUUID'], entry['entry_dn'], entry['objectClass'],
                               entry['bildungsloginAssignmentStatus'], entry['bildungsloginAssignmentAssignee']))
        for entry in entries['schools']:
            self._schools.append(LdapSchool(entry['entryUUID'], entry['entry_dn'], entry['objectClass'], entry['ou']))
        for entry in entries['workgroups']:
            self._workgroups.append(
                LdapGroup(entry['entryUUID'], entry['entry_dn'], entry['cn'], entry['ucsschoolRole'],
                          entry['memberUid']))
        for entry in entries['classes']:
            self._classes.append(LdapGroup(entry['entryUUID'], entry['entry_dn'], entry['cn'], entry['ucsschoolRole'],
                                           entry['memberUid']))

    def get_user(self, userid: str) -> LdapUser | None:
        for user in self._users:
            if hasattr(user, 'uid') and user.uid == userid:
                return user
        return None

    def get_assignments_by_assignee(self, assignee: Entry) -> List[LdapAssignment]:
        assignments = []
        for assignment in self._assignments:
            if assignment.bildungsloginAssignmentAssignee \
                    == assignee.entryUUID:
                assignments.append(assignment)

        return assignments

    def get_license_by_assignment(self, assignment: LdapAssignment) -> LdapLicense | None:
        for _license in self._licenses:
            if _license.entry_dn in assignment.entry_dn:
                return _license
        return None

    def get_school(self, name: str) -> LdapSchool | None:
        for school in self._schools:
            if name == school.ou:
                return school
        return None

    def get_classes(self, school: LdapSchool, user: LdapUser) -> List[LdapGroup]:
        classes = []
        for _class in self._classes:
            if _class.ucsschoolRole == f"school_class:school:{school.ou}" and user.uid in _class.memberUid:
                classes.append(_class)
        return classes

    def get_workgroups(self, school: LdapSchool, user: LdapUser) -> List[LdapGroup]:
        workgroups = []
        for workgroup in self._workgroups:
            if workgroup.ucsschoolRole == f"workgroup:school:{school.ou}" and user.uid in workgroup.memberUid:
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
        self.ldap_base = os.environ["LDAP_BASE"]
        self.repository: LdapRepository | None = None
        self.udm = UDM(**kwargs)
        self.udm.session.open()
        self.assignment_mod = self.udm.get("bildungslogin/assignment")
        self.repository = LdapRepository(ldap_auth)
        self.repository.update(start_up=True)

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
        self.repository.update()
        user = self.repository.get_user(username)

        if user is None:
            raise HTTPException(status_code=404, detail="User not found.")

        licenses = self.get_licenses_and_set_assignment_status(ObjectType.USER, user)
        return_obj = User(
            id=str(user.userId),
            first_name=str(user.givenName),
            last_name=str(user.sn),
            context=self.get_school_context(user),
            licenses=self._get_licenses_codes(licenses)
        )

        return return_obj

    @staticmethod
    def _get_object_id(school_uuid: str, object_uuid: str) -> str:
        """ Create an ID for the object """
        string = str(school_uuid) + str(object_uuid)
        return sha256(string.encode("utf-8")).hexdigest()

    @staticmethod
    def _get_licenses_codes(licenses: List[LdapLicense]) -> List[str]:
        """ Extract a list of unique licenses codes """
        return sorted(set(str(_license.bildungsloginLicenseCode) for _license in licenses))

    @staticmethod
    def extract_group_name(school: LdapSchool, group: LdapGroup) -> str:
        """
        In LDAP classes/workgroups are prepended with the school name:
        Example: DEMOSCHOOL-Group

        This function is meant to extract the name of the group
        """
        _, group_name = str(group.cn).split(f"{school.ou}-", 1)
        return group_name

    def get_class_info(self, school: LdapSchool, class_obj: LdapGroup) -> Class:
        """ Obtain relevant information about the class and initialize Class instance """
        licenses = self.get_licenses_and_set_assignment_status(ObjectType.GROUP, class_obj)
        return Class(id=self._get_object_id(school.entryUUID, class_obj.entryUUID),
                     name=self.extract_group_name(school, class_obj),
                     licenses=self._get_licenses_codes(licenses))

    def get_workgroup_info(self, school: LdapSchool, workgroup: LdapGroup) -> Workgroup:
        """ Obtain relevant information about the workgroup and initialize Workgroup instance """
        licenses = self.get_licenses_and_set_assignment_status(ObjectType.GROUP, workgroup)
        return Workgroup(id=self._get_object_id(school.entryUUID, workgroup.entryUUID),
                         name=self.extract_group_name(school, workgroup),
                         licenses=self._get_licenses_codes(licenses))

    def get_school_context(self, user: LdapUser) -> Dict[str, SchoolContext]:
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
                if lic.bildungsloginLicenseSpecialType == "Lehrkraft" and "teacher" not in user_roles:
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
                                               obj) -> List[LdapLicense]:
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

    async def correct_assignment_status(self, assignment: LdapAssignment):
        udm_assignment = await self.assignment_mod.get(assignment.entry_dn)
        udm_assignment.props.status = AssignmentStatus.ASSIGNED.name
        await udm_assignment.save()
        await self.set_assignment_status_provisioned(udm_assignment)

    async def set_assignment_status_provisioned(self, assignment: LdapAssignment | UdmObject):
        if isinstance(assignment, LdapAssignment):
            assignment = await self.assignment_mod.get(assignment.entry_dn)
        assignment.props.status = AssignmentStatus.PROVISIONED.name
        await assignment.save()

    def get_roles(self, user: LdapUser, school_ou: str) -> List[str]:
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
        Note that this function IGNORES any roles which aren't relevant for the purpose of this module.

        >>> UdmRestApiBackend._get_roles_for_school(
        ... ["teacher:school:School1", "student:school:School2"],
        ... "school1"
        ... )
        {'teacher'}

        :param roles: The list of ucsschool_roles to filter
        :param school: The school to filter the roles for
        :return: The list of user roles for the given school
        """
        valid_roles = set([x.value for x in UserRole])
        # copied from id-broker-plugin/provisioning_plugin/utils.py
        filtered_roles = set()
        for role in roles:
            role_parts = role.split(":")
            if len(role_parts) == 3 and all(role_parts):
                if (
                    role_parts[1] == "school"
                    and role_parts[2] == school
                    and role_parts[0] in valid_roles
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
        # 'school_admin' is not valid in models.UserRole: ignore it!
        #if "ucsschoolAdministrator" in options:
        #    return {"school_admin"}
        raise RuntimeError(f"Cannot determine role of user from options: {options!r}")
