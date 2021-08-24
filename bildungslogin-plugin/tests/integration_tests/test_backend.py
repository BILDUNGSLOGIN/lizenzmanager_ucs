# -*- coding: utf-8 -*-
import datetime
import itertools
import zlib

import pytest

from bildungslogin_plugin.backend_udm_rest_api import UdmRestApiBackend
from bildungslogin_plugin.models import AssignmentStatus, User as ProvUser
from ucsschool.kelvin.client import User as KelvinUser
from udm_rest_client import UdmObject


def compare_kelvin_user_and_prov_user(kelvin_user: KelvinUser, prov_user: ProvUser) -> None:
    assert f"Vorname ({zlib.crc32(kelvin_user.firstname.encode('UTF-8'))})" == prov_user.first_name
    assert f"Nachname ({zlib.crc32(kelvin_user.lastname.encode('UTF-8'))})" == prov_user.last_name
    assert set(kelvin_user.schools) == set(prov_user.context.keys())
    prov_user_roles = set(itertools.chain(*(c.roles for c in prov_user.context.values())))
    kelvin_user_roles = {r.rsplit("/", 1)[-1] for r in kelvin_user.roles}
    assert prov_user_roles == kelvin_user_roles
    for ou, context in prov_user.context.items():
        if kelvin_user_roles != {"staff"}:
            assert set(kelvin_user.school_classes[ou]) == context.classes


@pytest.mark.asyncio
async def test_connection_test(backend: UdmRestApiBackend):
    await backend.connection_test()


@pytest.mark.asyncio
async def test_get_user_no_licenses(backend: UdmRestApiBackend, create_test_user):
    """Test that a newly created user has no assigned licenses in the backend."""
    kelvin_user: KelvinUser = await create_test_user()
    prov_user: ProvUser = await backend.get_user(kelvin_user.name)
    compare_kelvin_user_and_prov_user(kelvin_user, prov_user)
    assert prov_user.licenses == set()


@pytest.mark.asyncio
async def test_get_user_with_licenses(
    backend: UdmRestApiBackend, create_test_user, create_license_and_assignments, udm
):
    """
    Test that license assignments are created with AVAILABLE status, can be assigned to a user and the
    license is in the ASSIGNED status, and after provisioning the status is PROVISIONED.
    """
    kelvin_user: KelvinUser = await create_test_user()
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
    assert prov_user.licenses == {license_obj1.props.code, license_obj2.props.code}
