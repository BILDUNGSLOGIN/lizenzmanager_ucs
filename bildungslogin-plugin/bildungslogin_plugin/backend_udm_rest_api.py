# -*- coding: utf-8 -*-
from __future__ import annotations

import enum

from hashlib import sha256

import logging
import os
import zlib
from typing import Dict, List, Optional, Set

# TODO: UDM REST client should raise application specific exception:
from aiohttp.client_exceptions import ClientConnectorError

from udm_rest_client.udm import UDM, UdmObject

from .backend import ConfigurationError, DbBackend, DbConnectionError, UserNotFound
from .models import AssignmentStatus, Class, SchoolContext, User, Workgroup

UCR_CONTAINER_CLASS = ("ucsschool_ldap_default_container_class", "klassen")
UCR_CONTAINER_PUPILS = ("ucsschool_ldap_default_container_pupils", "schueler")

logger = logging.getLogger(__name__)


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


class UdmRestApiBackend(DbBackend):
    """LDAP Database access  using the UDM REST API."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for kwarg in ("username", "password", "url"):  # check only required parameters
            if kwarg not in kwargs:
                raise ConfigurationError(f"Missing UDM REST API client configuration option {kwarg!r}.")
        self.udm = UDM(**kwargs)
        self.udm.session.open()
        self.assignment_mod = self.udm.get("bildungslogin/assignment")
        self.license_mod = self.udm.get("bildungslogin/license")
        self.user_mod = self.udm.get("users/user")
        self.group_mod = self.udm.get("groups/group")
        self.school_mod = self.udm.get("container/ou")
        self.ldap_base = os.environ["LDAP_BASE"]

    async def connection_test(self) -> None:
        """
        Test DB connection.

        :return: nothing if successful or raises an error
        :raises DbConnectionError: if connecting failed
        """
        logger.debug("Starting connection test for UDM REST API...")
        try:
            ldap_base = await self.udm.session.base_dn
        except ClientConnectorError as exc:
            raise DbConnectionError(str(exc)) from exc
        if ldap_base != self.ldap_base:  # pragma: no cover
            raise ConfigurationError(
                f"LDAP base in environment ({self.ldap_base!r}) and UDM REST API ({ldap_base!r}) differ."
            )

    async def get_user(self, username: str) -> User:
        """
        Load a user object and its school, class and license information from LDAP.

        :param str username: the `uid` LDAP attribute
        :return: User object
        :rtype: User
        :raises ConnectionError: when a problem with the connection happens
        :raises UserNotFound: when a user could not be found in the DB
        """
        try:
            user = await self._get_object_by_name(ObjectType.USER, username)
        except ValueError:
            raise UserNotFound
        user_id = user.props.username
        # in the first iteration (MVP) given names and family names are not allowed to be exposed:
        first_name = None
        if user.props.firstname:
            first_name = user.props.firstname
        last_name = None
        if user.props.lastname:
            last_name = user.props.lastname
        licenses = await self.get_licenses_and_set_assignment_status(ObjectType.USER, user)
        return_obj = User(id=user_id,
                          first_name=first_name,
                          last_name=last_name,
                          context=await self.get_school_context(user),
                          licenses=self._get_licenses_codes(licenses))
        remove_empty_values(return_obj)
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
        string = school_uuid + object_uuid
        return sha256(string.encode("utf-8")).hexdigest()

    @staticmethod
    def _get_licenses_codes(licenses: List[UdmObject]) -> List[str]:
        """ Extract a list of unique licenses codes """
        return sorted(set(l.props.code for l in licenses))

    async def _get_groups_with_role(self, user: UdmObject, role: str) -> List[UdmObject]:
        """ Obtain user groups, that have specific role """
        groups = []
        for group_dn in user.props.groups:
            group = await self.udm.obj_by_dn(group_dn)
            if any(r == role for r in group.props.ucsschoolRole):
                groups.append(group)
        return groups

    @staticmethod
    def extract_group_name(school: UdmObject, group: UdmObject) -> str:
        """
        In LDAP classes/workgroups are prepended with the school name:
        Example: DEMOSCHOOL-Group

        This function is meant to extract the name of the group
        """
        _, group_name = group.props.name.split(f"{school.props.name}-", 1)
        return group_name

    async def get_classes(self, user: UdmObject, school: UdmObject) -> List[UdmObject]:
        """
        Get a list of classes that user is assigned to,
        and they belong to the given school
        """
        class_school_role = f"school_class:school:{school.props.name}"
        classes = await self._get_groups_with_role(user, class_school_role)
        return classes

    async def get_class_info(self, school: UdmObject, class_obj: UdmObject) -> Class:
        """ Obtain relevant information about the class and initialize Class instance """
        licenses = await self.get_licenses_and_set_assignment_status(ObjectType.GROUP, class_obj)
        return Class(id=self._get_object_id(school.uuid, class_obj.uuid),
                     name=self.extract_group_name(school, class_obj),
                     licenses=self._get_licenses_codes(licenses))

    async def get_workgroups(self, user: UdmObject, school: UdmObject) -> List[UdmObject]:
        """
        Get a list of workgroups that user is assigned to,
        and they belong to the given school
        """
        class_school_role = f"workgroup:school:{school.props.name}"
        return await self._get_groups_with_role(user, class_school_role)

    async def get_workgroup_info(self, school: UdmObject, workgroup: UdmObject) -> Workgroup:
        """ Obtain relevant information about the workgroup and initialize Workgroup instance """
        licenses = await self.get_licenses_and_set_assignment_status(ObjectType.GROUP, workgroup)
        return Workgroup(id=self._get_object_id(school.uuid, workgroup.uuid),
                         name=self.extract_group_name(school, workgroup),
                         licenses=self._get_licenses_codes(licenses))

    async def get_school_context(self, user: UdmObject) -> Dict[str, SchoolContext]:
        output = {}
        for school_ou in user.props.school:
            school = await self._get_object_by_name(ObjectType.SCHOOL, school_ou)
            school_id = self._get_object_id(school.uuid, school.uuid)

            # Get all licenses, but filter out those with special type "Lehrkraft"
            # in case the user doesn't have a "teacher" role
            user_roles = self.get_roles(user, school_ou)
            all_licenses = \
                await self.get_licenses_and_set_assignment_status(ObjectType.SCHOOL, school)
            applicable_licenses = []
            for lic in all_licenses:
                if lic.props.special_type == "Lehrkraft" and "teacher" not in user_roles:
                    continue
                applicable_licenses.append(lic)
            # Create school context object
            school_context = SchoolContext(
                school_authority=None,  # the value is not present in LDAP schema yet
                # school_code=school.props.name,
                school_identifier=None,
                school_name=school.props.name,
                roles=user_roles,
                # <greif@univention.de> Temporarily deactivated for performance reasons
                classes=[],
                workgroups=[],
                #classes=[await self.get_class_info(school, c)
                #         for c in await self.get_classes(user, school)],
                #workgroups=[await self.get_workgroup_info(school, w)
                #            for w in await self.get_workgroups(user, school)],
                licenses=self._get_licenses_codes(applicable_licenses))
            remove_empty_values(school_context)
            output[school_id] = school_context
        return output

    async def get_licenses_and_set_assignment_status(self, object_type: ObjectType,
                                                     obj: UdmObject) -> List[UdmObject]:
        license_dns = set()
        obj_name = getattr(obj.props, "username", None)
        if not obj_name:
            obj_name =getattr(obj.props, "name", None)

        async for assignment in self.assignment_mod.search(
                f"(bildungsloginAssignmentAssignee={obj.uuid})"):
            if assignment.props.status == AssignmentStatus.AVAILABLE.name:
                logger.error(
                    "License assignment for %s %r has invalid status 'AVAILABLE', setting to "
                    "'ASSIGNED' (and then to 'PROVISIONED'): %r.",
                    object_type.value,
                    obj_name,
                    assignment.dn)
                assignment.props.status = AssignmentStatus.ASSIGNED.name
                await assignment.save()
            if assignment.props.status != AssignmentStatus.PROVISIONED.name:
                logger.debug("Setting assignment status to 'PROVISIONED': %r.", assignment.dn)
                assignment.props.status = AssignmentStatus.PROVISIONED.name
                await assignment.save()
            license_dns.add(assignment.position)

        return [(await self.license_mod.get(license_dn)) for license_dn in license_dns]

    def get_roles(self, user: UdmObject, school_ou: str) -> List[str]:
        """
        Returns a list of unique roles the user is assigned to in the given school
        First, tries to obtain the roles via user's ucsschoolRole property
        If this doesn't work out, falls back to general user's roles (defined via options)
        """
        roles = self._get_roles_for_school(user.props.ucsschoolRole, school_ou)
        if not roles:
            logger.warning(
                "Cannot get roles of user %r at OU %r from 'ucsschool_roles' %r. Using "
                "objectClass fallback, options: %r.",
                user.dn,
                school_ou,
                user.props.ucsschoolRole,
                user.options,
            )
            roles = self._get_roles_oc_fallback(user.options)
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
    def _get_roles_oc_fallback(options: Dict[str, bool]) -> Set[str]:
        ocs = set(key for key, val in options.items() if val is True)
        if ocs >= {"ucsschoolTeacher", "ucsschoolStaff"}:
            return {"staff", "teacher"}
        if "ucsschoolTeacher" in ocs:
            return {"teacher"}
        if "ucsschoolStaff" in ocs:
            return {"staff"}
        if "ucsschoolStudent" in ocs:
            return {"student"}
        if "ucsschoolAdministrator" in ocs:
            return {"school_admin"}
        raise RuntimeError(f"Cannot determine role of user from options: {options!r}")
