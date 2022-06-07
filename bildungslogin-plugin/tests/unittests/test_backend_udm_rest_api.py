# -*- coding: utf-8 -*-

import copy
from unittest.mock import patch, Mock

import faker
import nest_asyncio
import pytest

from bildungslogin_plugin.backend import ConfigurationError, DbConnectionError
from bildungslogin_plugin.backend_udm_rest_api import UdmRestApiBackend
from bildungslogin_plugin.models import Class, SchoolContext, Workgroup
from bildungslogin_plugin.routes.v1.users import get_backend, set_backend

fake = faker.Faker()
# pytest event loop is already running: https://github.com/encode/starlette/issues/440
nest_asyncio.apply()  # patches asyncio to allow nested use of asyncio.run and loop.run_until_complete


@pytest.fixture(scope="session")
def init_kwargs():
    return lambda: {"username": fake.user_name(), "password": fake.first_name(), "url": fake.url()}


@patch("bildungslogin_plugin.backend_udm_rest_api.UDM")
def test_init_kwargs_ok(udm_mock, init_kwargs):
    UdmRestApiBackend(**init_kwargs())


@patch("bildungslogin_plugin.backend_udm_rest_api.UDM")
def test_init_kwargs_missing(udm_mock, init_kwargs):
    complete_kwargs = init_kwargs()
    for k in complete_kwargs.keys():
        kwargs = copy.deepcopy(complete_kwargs)
        del kwargs[k]
        with pytest.raises(ConfigurationError):
            UdmRestApiBackend(**kwargs)


@pytest.mark.asyncio
@patch("bildungslogin_plugin.backend_udm_rest_api.UDM")
async def test_user_not_found(udm_mock, client):
    backend = UdmRestApiBackend(
        username=fake.user_name(),
        password=fake.password(),
        url="http://127.0.0.1/univention/udm",
    )
    try:
        ori_backend = get_backend()
    except RuntimeError:
        ori_backend = None
    try:
        set_backend(backend)
        resp = client.get(f"/v1/user/{fake.uuid4()}")
        assert resp.status_code == 404
    finally:
        set_backend(ori_backend)


@pytest.mark.asyncio
async def test_connection_test_udm_connect():
    backend = UdmRestApiBackend(
        username=fake.user_name(),
        password=fake.password(),
        url="http://127.0.0.1/univention/udm",
    )
    with pytest.raises(DbConnectionError):
        await backend.connection_test()


def test_intermittent_udm_rest_api_not_reachable(client):
    backend = UdmRestApiBackend(
        username=fake.user_name(),
        password=fake.password(),
        url="http://127.0.0.1/univention/udm",
    )
    try:
        ori_backend = get_backend()
    except RuntimeError:
        ori_backend = None
    try:
        set_backend(backend)
        resp = client.get(f"/v1/user/{fake.uuid4()}")
        assert resp.status_code == 500
    finally:
        set_backend(ori_backend)


def roles_id(roles) -> str:
    return "+".join(roles)


@pytest.mark.parametrize(
    "roles",
    (
        ["staff"],
        ["student"],
        ["teacher"],
        ["school_admin"],
        ["teacher", "staff"],
        ["student", "staff"],
    ),
    ids=roles_id,
)
@pytest.mark.asyncio
async def test_get_school_context(fake_udm_user, roles):
    school_ou = "test_school"
    user = fake_udm_user(roles, [school_ou])
    backend = UdmRestApiBackend(
        username=fake.user_name(),
        password=fake.password(),
        url="http://127.0.0.1/univention/udm",
    )
    with patch.object(backend, "_get_object_by_name") as gobn_mock, \
            patch.object(backend, "get_licenses_and_set_assignment_status") as glasas_mock, \
            patch.object(backend, "get_classes") as gc_mock, \
            patch.object(backend, "get_workgroups") as gw_mock:
        # Prepare mocks
        gobn_mock.return_value = Mock(**{"uuid": "1",
                                         "props.name": school_ou,
                                         "props.displayName": "Test School"})
        glasas_mock.side_effect = [{Mock(**{"props.code": "1", "props.special_type": "Lehrkraft"})},
                                   {Mock(**{"props.code": "2"})},
                                   {Mock(**{"props.code": "3"})}]
        gc_mock.return_value = [Mock(**{"uuid": "2", "props.name": f"{school_ou}-class"})]
        gw_mock.return_value = [Mock(**{"uuid": "3", "props.name": f"{school_ou}-workgroup"})]
        result = await backend.get_school_context(user)
    # create expectation
    expected_school_licenses = ["1"] if "teacher" in roles else []
    expected_context = SchoolContext(
        school_authority=None,  # the value is not present in LDAP schema yet
        school_code=school_ou,
        school_identifier="4fc82b26aecb47d2868c4efbe3581732a3e7cbcc6c2efb32062c08170a05eeb8",
        school_name="Test School",
        roles=sorted(roles),
        classes=[Class(
            id="6b51d431df5d7f141cbececcf79edf3dd861c3b4069f0b11661a3eefacbba918",
            name="class",
            licenses=["2"],
        )],
        workgroups=[Workgroup(
            id="3fdba35f04dc8c462986c992bcf875546257113072a909c162f7e470e581e278",
            name="workgroup",
            licenses=["3"],
        )],
        licenses=expected_school_licenses)
    # check
    expected_result = {expected_context.school_identifier: expected_context}
    assert expected_result == result


@pytest.mark.asyncio
async def test_get_school_context_uses_get_roles_oc_fallback(fake_udm_user):
    school_ou = "test_ou"
    user = fake_udm_user(["teacher"], school_ou)
    user.props.ucsschoolRole = []  # clean roles
    backend = UdmRestApiBackend(
        username=fake.user_name(),
        password=fake.password(),
        url="http://127.0.0.1/univention/udm",
    )
    result = backend.get_roles(user, school_ou)
    expected = ["teacher"]  # expect teacher role from the options
    assert result == expected


def data_id(data) -> str:
    roles, school, expected = data
    return f"{'+'.join(roles)}/{school}->{'+'.join(expected)}"


@pytest.mark.parametrize(
    "data",
    (
        (["teacher:school:School1", "student:school:School2"], "School1", {"teacher"}),
        (["staff:school:School1", "staff:school:School2"], "School1", {"staff"}),
        (["staff:school:School1", "staff:school:School2"], "School3", set()),
        (["teacher:school:School1", "student:school:School1"], "School1", {"student", "teacher"}),
    ),
    ids=data_id,
)
def test_get_roles_for_school(data):
    roles, school, expected = data
    assert expected == UdmRestApiBackend._get_roles_for_school(roles, school)


def test_get_roles_for_school_invalid_role():
    with pytest.raises(ValueError):
        UdmRestApiBackend._get_roles_for_school([":school:bar"], "bar")


def roles2_id(data) -> str:
    options, expected = data
    roles = "+".join(k for k, v in options.items() if v)
    return f"{roles}->{'+'.join(expected)}"


@pytest.mark.parametrize(
    "data",
    (
        ({"ucsschoolAdministrator": False, "ucsschoolStaff": True, "foo": True}, {"staff"}),
        ({"ucsschoolAdministrator": True, "ucsschoolStaff": False, "foo": True}, {"school_admin"}),
        ({"ucsschoolStaff": True, "ucsschoolTeacher": True, "foo": True}, {"staff", "teacher"}),
        ({"ucsschoolStudent": True, "ucsschoolStaff": False, "foo": True}, {"student"}),
        ({"ucsschoolStaff": True, "ucsschoolTeacher": False, "foo": True}, {"staff"}),
        ({"ucsschoolTeacher": True, "ucsschoolStaff": False, "foo": True}, {"teacher"}),
        ({"foo": True}, {"RuntimeError"}),
    ),
    ids=roles2_id,
)
def test_get_roles_oc_fallback(data):
    options, expected = data
    if expected == {"RuntimeError"}:
        with pytest.raises(RuntimeError):
            UdmRestApiBackend._get_roles_oc_fallback(options)
    else:
        assert expected == UdmRestApiBackend._get_roles_oc_fallback(options)
