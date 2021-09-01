# -*- coding: utf-8 -*-
from __future__ import annotations

import logging
import os
import re
import zlib
from typing import Dict, List, Pattern, Set

# TODO: UDM REST client should raise application specific exception:
from aiohttp.client_exceptions import ClientConnectorError
from ldap3.utils.conv import escape_filter_chars

from udm_rest_client.udm import UDM, UdmObject

from .backend import ConfigurationError, DbBackend, DbConnectionError, UserNotFound
from .models import AssignmentStatus, SchoolContext, User

UCR_CONTAINER_CLASS = ("ucsschool_ldap_default_container_class", "klassen")
UCR_CONTAINER_PUPILS = ("ucsschool_ldap_default_container_pupils", "schueler")

logger = logging.getLogger(__name__)


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
        self.ldap_base = os.environ["LDAP_BASE"]
        self.school_class_dn_regex = self._school_class_dn_regex()

    @staticmethod
    def _school_class_dn_regex() -> Pattern:
        """Regex to match 'cn=DEMOSCHOOL-1a,cn=klassen,cn=schueler,cn=groups,ou=DEMOSCHOOL,...'."""
        # copied from ucsschool-id-connector/src/ucsschool_id_connector/utils.py
        base_dn = os.environ["LDAP_BASE"]
        c_class = os.environ.get(UCR_CONTAINER_CLASS[0]) or UCR_CONTAINER_CLASS[1]
        c_student = os.environ.get(UCR_CONTAINER_PUPILS[0]) or UCR_CONTAINER_PUPILS[1]
        return re.compile(
            f"cn=(?P<ou>[^,]+?)-(?P<name>[^,]+?),"
            f"cn={c_class},cn={c_student},cn=groups,"
            f"ou=(?P=ou),"
            f"{base_dn}",
            flags=re.IGNORECASE,
        )

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
            async for user in self.user_mod.search(f"(uid={escape_filter_chars(username)})"):
                break
            else:
                raise UserNotFound
        except ClientConnectorError as exc:
            raise DbConnectionError(str(exc)) from exc
        # UDM REST API exposes the entryUUID attribut only when fetching the object by DN, not in the
        # results of the search operation. Getting the DN first directly by LDAP saves very little time.
        # So we fetch the user again using the UDM REST API:
        try:
            udm_user = await self.user_mod.get(user.dn)
        except ClientConnectorError as exc:  # pragma: no cover
            raise DbConnectionError(str(exc)) from exc
        user_id = udm_user.props.username
        # in the first iteration (MVP) given names and family names are not allowed to be exposed:
        first_name = f"Vorname ({zlib.crc32(udm_user.props.firstname.encode('UTF-8'))})"
        last_name = f"Nachname ({zlib.crc32(udm_user.props.lastname.encode('UTF-8'))})"
        context = await self.get_school_context(udm_user)
        licenses = await self.get_licenses_and_set_assignment_status(udm_user)

        return User(
            id=user_id,
            first_name=first_name,
            last_name=last_name,
            context=context,
            licenses=licenses,
        )

    async def get_school_context(self, user: UdmObject) -> Dict[str, SchoolContext]:
        school_classes = {ou: [] for ou in user.props.school}
        for group_dn in user.props.groups:
            match = self.school_class_dn_regex.match(group_dn)
            if match:
                ou = match.groupdict()["ou"]
                name = match.groupdict()["name"]
                school_classes[ou].append(name)
        context = {}
        for ou, classes in school_classes.items():
            if ou not in user.props.school:
                logger.warning(
                    "User %r is in school class group(s) of school %r, which is missing in 'schools'. "
                    "Ignoring classes for that OU. Users groups: %r.",
                    user.dn,
                    ou,
                    user.props.groups,
                )
            else:
                roles = self.get_roles_for_school(user.props.ucsschoolRole, ou)
                if not roles:
                    logger.warning(
                        "Cannot get roles of user %r at OU %r from 'ucsschool_roles' %r. Using "
                        "objectClass fallback, options: %r.",
                        user.dn,
                        ou,
                        user.props.ucsschoolRole,
                        user.options,
                    )
                    roles = self.get_roles_oc_fallback(user.options)
                context[ou] = SchoolContext(classes=classes, roles=roles)
        return context

    async def get_licenses_and_set_assignment_status(self, user: UdmObject) -> Set[str]:
        license_dns = set()
        async for assignment in self.assignment_mod.search(
            f"(bildungsloginAssignmentAssignee={user.uuid})"
        ):
            if assignment.props.status == AssignmentStatus.AVAILABLE.name:
                logger.error(
                    "License assignment for user %r has invalid status 'AVAILABLE', setting to "
                    "'ASSIGNED' (and then to 'PROVISIONED'): %r.",
                    user.props.username,
                    assignment.dn,
                )
                assignment.props.status = AssignmentStatus.ASSIGNED.name
                await assignment.save()
            if assignment.props.status != AssignmentStatus.PROVISIONED.name:
                logger.debug("Setting assignment status to 'PROVISIONED': %r.", assignment.dn)
                assignment.props.status = AssignmentStatus.PROVISIONED.name
                await assignment.save()
            license_dns.add(assignment.position)

        return {(await self.license_mod.get(license_dn)).props.code for license_dn in license_dns}

    @staticmethod
    def get_roles_for_school(roles: List[str], school: str) -> Set[str]:
        """
        Takes a list of ucsschool_roles and returns a list of user roles for the given school.

        >>> UdmRestApiBackend.get_roles_for_school(
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
    def get_roles_oc_fallback(options: Dict[str, bool]) -> Set[str]:
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
