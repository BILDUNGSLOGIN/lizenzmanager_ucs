# -*- coding: utf-8 -*-
from unittest import mock

import datetime
import itertools
import zlib
from typing import Any, Dict, List

import pytest
from ldap3 import AUTO_BIND_TLS_BEFORE_BIND, MODIFY_REPLACE, SIMPLE, Connection
from ldap3.core.exceptions import LDAPBindError, LDAPExceptionError

from bildungslogin_plugin.backend_udm_rest_api import ObjectType, UdmRestApiBackend
from bildungslogin_plugin.models import AssignmentStatus, Class, SchoolContext, User as ProvUser, \
    User, Workgroup
from ucsschool.apis.plugins.auth import ldap_auth
from ucsschool.kelvin.client import User as KelvinUser
from udm_rest_client import UdmObject


def compare_kelvin_user_and_prov_user(kelvin_user: KelvinUser, prov_user: ProvUser) -> None:
    assert f"Vorname ({zlib.crc32(kelvin_user.firstname.encode('UTF-8'))})" == prov_user.first_name
    assert f"Nachname ({zlib.crc32(kelvin_user.lastname.encode('UTF-8'))})" == prov_user.last_name
    assert len(kelvin_user.schools) == len(prov_user.context.keys())
    prov_user_roles = set(itertools.chain(*(c.roles for c in prov_user.context.values())))
    kelvin_user_roles = {r.rsplit("/", 1)[-1] for r in kelvin_user.roles}
    assert prov_user_roles == kelvin_user_roles
    for context in prov_user.context.values():
        ou = context.school_code
        # check school
        assert ou in kelvin_user.schools
        # check classes
        assert sorted(kelvin_user.school_classes[ou]) == sorted(c.name for c in context.classes)
        assert [] == context.workgroups


@pytest.mark.asyncio
async def test_connection_test(backend: UdmRestApiBackend):
    await backend.connection_test()


@pytest.mark.asyncio
async def test_get_user_no_licenses(backend: UdmRestApiBackend, create_test_user):
    """Test that a newly created user has no assigned licenses in the backend."""
    kelvin_user: KelvinUser = await create_test_user()
    # NOTE: create_test_user sometimes creates a user with no school classes
    assert kelvin_user.school_classes
    prov_user: ProvUser = await backend.get_user(kelvin_user.name)
    compare_kelvin_user_and_prov_user(kelvin_user, prov_user)
    assert prov_user.licenses == []


@pytest.mark.asyncio
async def test_get_user_with_licenses(
    backend: UdmRestApiBackend, create_test_user, create_license_and_assignments, udm
):
    """
    Test that license assignments are created with AVAILABLE status, can be assigned to a user and the
    license is in the ASSIGNED status, and after provisioning the status is PROVISIONED.
    """
    kelvin_user: KelvinUser = await create_test_user()
    # NOTE: create_test_user sometimes creates a user with no school classes
    assert kelvin_user.school_classes
    license_obj1, assignment_objs1 = await create_license_and_assignments(quantity=1)
    license_obj2, assignment_objs2 = await create_license_and_assignments(quantity=1)
    _, _ = await create_license_and_assignments(quantity=1)  # will not be assigned

    # assign licenses 1+2 to user, but not 3
    udm_user = await udm.get("users/user").get(kelvin_user.dn)
    assignment_obj1: UdmObject = assignment_objs1[0]
    assert assignment_obj1.position == license_obj1.dn
    assert assignment_obj1.props.status == AssignmentStatus.AVAILABLE.name
    assert not assignment_obj1.props.assignee
    assert not assignment_obj1.props.time_of_assignment
    assignment_obj1.props.assignee = udm_user.uuid
    # allowed status changes are controlled by UDM module,
    # cannot change from AVAILABLE directly to PROVISIONED, so setting to ASSIGNED first
    assignment_obj1.props.status = AssignmentStatus.ASSIGNED.name
    assignment_obj1.props.time_of_assignment = datetime.date.today().strftime("%Y-%m-%d")
    await assignment_obj1.save()
    # now set it to PROVISIONED
    assignment_obj1.props.status = AssignmentStatus.PROVISIONED.name
    await assignment_obj1.save()
    assignment_obj2: UdmObject = assignment_objs2[0]
    assignment_obj2.props.assignee = udm_user.uuid
    assignment_obj2.props.status = AssignmentStatus.ASSIGNED.name
    assignment_obj2.props.time_of_assignment = datetime.date.today().strftime("%Y-%m-%d")
    await assignment_obj2.save()
    assignment_obj2.props.status = AssignmentStatus.PROVISIONED.name
    await assignment_obj2.save()

    prov_user: ProvUser = await backend.get_user(kelvin_user.name)
    compare_kelvin_user_and_prov_user(kelvin_user, prov_user)
    assert sorted(prov_user.licenses) == sorted([license_obj1.props.code, license_obj2.props.code])


@pytest.mark.asyncio
async def test_get_user(backend: UdmRestApiBackend, create_test_user, create_workgroup,
                        create_license_and_assignments, udm):
    """
    Test get_user endpoint in case when user, their school
    and their group have an assigned license
    """
    kelvin_user: KelvinUser = await create_test_user(role="student")
    udm_user = await udm.get("users/user").get(kelvin_user.dn)
    [school_ou] = udm_user.props.school
    class_dn = next(g for g in udm_user.props.groups if "cn=klassen" in g)
    udm_class = await udm.get("groups/group").get(class_dn)
    [school_prefix, class_name] = udm_class.props.name.split("-", 1)
    assert school_prefix == school_ou

    async for school in udm.get("container/ou").search(f"name={school_ou}"):
        if f"ou={school_ou},dc=" in school.dn:
            udm_school = await udm.get("container/ou").get(school.dn)  # to obtain uuid
            break
    else:
        raise RuntimeError("School not found")

    # create workgroup
    udm_workgroup = await create_workgroup(school_ou, "test-workgroup")
    udm_user.props.groups = [udm_class.dn, udm_workgroup.dn]
    await udm_user.save()
    # create licenses
    user_license, [user_assignment] = \
        await create_license_and_assignments(quantity=1, license_type="SINGLE")
    school_license, [school_assignment] = \
        await create_license_and_assignments(quantity=1, license_type="SCHOOL")
    workgroup_license, [workgroup_assignment] = \
        await create_license_and_assignments(quantity=1, license_type="WORKGROUP")
    class_license, [class_assignment] = \
        await create_license_and_assignments(quantity=1, license_type="WORKGROUP")

    # assign licenses
    async def _assign(assignment, udm_object):
        assignment.props.assignee = udm_object.uuid
        assignment.props.status = AssignmentStatus.ASSIGNED.name
        assignment.props.time_of_assignment = datetime.date.today().strftime("%Y-%m-%d")
        await assignment.save()

    await _assign(user_assignment, udm_user)
    await _assign(school_assignment, udm_school)
    await _assign(workgroup_assignment, udm_workgroup)
    await _assign(class_assignment, udm_class)

    # send request and check expected results, mocking the id generation
    with mock.patch.object(backend, "_get_object_id", lambda x, y: y):
        response = await backend.get_user(udm_user.props.username)
    # avoid checking hashes
    assert "Vorname" in response.first_name
    assert udm_user.props.firstname not in response.first_name
    assert "Nachname" in response.last_name
    assert udm_user.props.lastname not in response.last_name
    response.first_name = None
    response.last_name = None

    expected_response = User(
        id=udm_user.props.username,
        first_name=None,
        last_name=None,
        licenses=[user_license.props.code],
        context={
            udm_school.uuid:
                SchoolContext(school_authority=None,
                              school_code=udm_school.props.name,
                              school_identifier=udm_school.uuid,
                              school_name=udm_school.props.displayName,
                              licenses=[school_license.props.code],
                              classes=[Class(name=class_name,
                                             id=udm_class.uuid,
                                             licenses=[class_license.props.code])],
                              workgroups=[Workgroup(name="test-workgroup",
                                                    id=udm_workgroup.uuid,
                                                    licenses=[workgroup_license.props.code])],
                              roles=["student"])
        },
    )

    assert response == expected_response


#
# TODO: this must be fixed in the ucsschool-apis app
#
async def ldap_auth_modify(
    dn: str,
    changes: Dict[str, List[Any]],
    raise_on_bind_error: bool = True,
) -> bool:
    """
    Modify attributes, *replaces* value(s).

    `changes` should be: {'sn': ['foo'], 'uid': ['bar']}

    (Change usage of MODIFY_REPLACE to change behavior.)

    :param dn: The dn of the object to modify
    :param changes: The changes that should be applied to the object
    :param raise_on_bind_error: If True an exceptions is raised on an bind failure, else nothing happens
    :return: True if modification was successful, else False
    """
    change_arg = dict((k, [(MODIFY_REPLACE, v)]) for k, v in changes.items())
    print(ldap_auth)

    try:
        with Connection(
            ldap_auth.server_master,
            user=f"{ldap_auth.credentials.cn_admin},{ldap_auth.settings.ldap_base}",
            password=ldap_auth.credentials.cn_admin_password,
            auto_bind=AUTO_BIND_TLS_BEFORE_BIND,
            authentication=SIMPLE,
            read_only=False,
        ) as conn:
            return conn.modify(dn, change_arg)
    except LDAPExceptionError as exc:
        if isinstance(exc, LDAPBindError) and not raise_on_bind_error:
            return False
        ldap_auth.logger.exception(
            "When connecting to %r with bind_dn %r: %s",
            ldap_auth.settings.master_fqdn,
            ldap_auth.credentials.cn_admin,
            exc,
        )
        raise


@pytest.mark.asyncio
async def test_get_licenses_and_set_assignment_status_fixes_bad_assignment_status(
    backend: UdmRestApiBackend, create_test_user, create_license_and_assignments, udm
):
    """
    Test that the function `get_licenses_and_set_assignment_status()` fixes the status of assignments
    that are in use but have status = `AVAILABLE`, when it should be `ASSIGNED`.
    """
    kelvin_user: KelvinUser = await create_test_user()
    license_obj1, assignment_objs1 = await create_license_and_assignments(quantity=1)
    udm_user = await udm.get("users/user").get(kelvin_user.dn)
    assignment_obj1: UdmObject = assignment_objs1[0]
    assert assignment_obj1.position == license_obj1.dn
    assert assignment_obj1.props.status == AssignmentStatus.AVAILABLE.name
    assert not assignment_obj1.props.assignee
    assert not assignment_obj1.props.time_of_assignment
    assignment_obj1.props.assignee = udm_user.uuid
    assignment_obj1.props.status = AssignmentStatus.ASSIGNED.name
    assignment_obj1.props.time_of_assignment = datetime.date.today().strftime("%Y-%m-%d")
    await assignment_obj1.save()

    # Set the assignments status to illegal value 'AVAILABLE' via LDAP, as the UDM module prevents it.
    await ldap_auth_modify(assignment_obj1.dn, {"bildungsloginAssignmentStatus": ["AVAILABLE"]})
    await assignment_obj1.reload()
    assignment_obj1.props.status = AssignmentStatus.AVAILABLE.name

    # Status cannot be set directly to 'PROVISIONED', so get_licenses_and_set_assignment_status() will
    # set it to 'ASSIGNED' first. Otherwise the UDM module will raise an exception here.
    licenses = await backend.get_licenses_and_set_assignment_status(ObjectType.USER, udm_user)
    license_codes = set(l.props.code for l in licenses)
    assert license_codes == {license_obj1.props.code}
    await assignment_obj1.reload()
    assignment_obj1.props.status = AssignmentStatus.PROVISIONED.name
