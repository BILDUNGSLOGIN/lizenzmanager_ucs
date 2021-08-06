import datetime
import itertools
import zlib

import pytest
from bildungslogin_plugin.backend import UdmRestApiBackend
from bildungslogin_plugin.models import AssignmentStatus, User as ProvUser
from ucsschool.kelvin.client import User as KelvinUser
from ucsschool.apis.plugins.auth import ldap_auth
from udm_rest_client import UDM, UdmObject


@pytest.fixture(scope="session")
def backend() -> UdmRestApiBackend:
    return UdmRestApiBackend(
        username=ldap_auth.credentials.cn_admin,
        password=ldap_auth.credentials.cn_admin_password,
        url=f"https://{ldap_auth.settings.master_fqdn}/univention/udm",
    )


def compare_kelvin_user_and_prov_user(kelvin_user: KelvinUser, prov_user: ProvUser) -> None:
    assert f"Vorname ({zlib.crc32(kelvin_user.firstname.encode('UTF-8'))})" == prov_user.first_name
    assert f"Nachname ({zlib.crc32(kelvin_user.lastname.encode('UTF-8'))})" == prov_user.last_name
    assert set(kelvin_user.schools) == set(prov_user.context.keys())
    for ou, context in prov_user.context.items():
        assert set(kelvin_user.school_classes[ou]) == context.classes
    prov_user_roles = set(itertools.chain(*(c.roles for c in prov_user.context.values())))
    kelvin_user_roles = {r.rsplit("/", 1)[-1] for r in kelvin_user.roles}
    assert prov_user_roles == kelvin_user_roles


@pytest.mark.asyncio
async def test_connection_test(backend: UdmRestApiBackend):
    await backend.connection_test()


@pytest.mark.asyncio
async def test_get_user_no_licenses(backend: UdmRestApiBackend, create_test_user):
    kelvin_user: KelvinUser = await create_test_user()
    prov_user: ProvUser = await backend.get_user(kelvin_user.name)
    compare_kelvin_user_and_prov_user(kelvin_user, prov_user)
    assert prov_user.licenses == set()


@pytest.mark.asyncio
async def test_get_user_with_licenses(
        backend: UdmRestApiBackend, create_test_user, create_license_and_assignments, udm_kwargs
):
    kelvin_user: KelvinUser = await create_test_user()
    license_obj1, assignment_objs1 = await create_license_and_assignments()
    license_obj2, assignment_objs2 = await create_license_and_assignments()
    _, _ = await create_license_and_assignments()  # will not be assigned

    # assign licenses 1+2 to user, but not 3
    async with UDM(**udm_kwargs) as udm:
        udm_user = await udm.get("users/user").get(kelvin_user.dn)
        assignment_obj1: UdmObject = assignment_objs1[0]
        assignment_obj1.props.assignee = udm_user.uuid
        assignment_obj1.props.status = AssignmentStatus.ASSIGNED.name  # see below why ASSIGNED
        assignment_obj1.props.time_of_assignment = datetime.datetime.now().strftime("%Y-%m-%d")
        await assignment_obj1.save()
        # allowed status changes are controlled by UDM module,
        # cannot change from AVAILABLE directly to PROVISIONED
        assignment_obj1.props.status = AssignmentStatus.PROVISIONED.name
        await assignment_obj1.save()
        assignment_obj2: UdmObject = assignment_objs2[0]
        assignment_obj2.props.assignee = udm_user.uuid
        assignment_obj2.props.status = AssignmentStatus.ASSIGNED.name
        assignment_obj2.props.time_of_assignment = datetime.datetime.now().strftime("%Y-%m-%d")
        await assignment_obj2.save()
        assignment_obj2.props.status = AssignmentStatus.PROVISIONED.name
        await assignment_obj2.save()

    prov_user: ProvUser = await backend.get_user(kelvin_user.name)
    compare_kelvin_user_and_prov_user(kelvin_user, prov_user)
    assert prov_user.licenses == {license_obj1.props.code, license_obj2.props.code}
