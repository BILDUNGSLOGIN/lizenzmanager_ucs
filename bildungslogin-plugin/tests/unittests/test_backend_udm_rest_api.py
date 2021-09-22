# -*- coding: utf-8 -*-

import copy
import os
from unittest.mock import patch

import faker
import nest_asyncio
import pytest

from bildungslogin_plugin.backend import ConfigurationError, DbConnectionError
from bildungslogin_plugin.backend_udm_rest_api import UdmRestApiBackend
from bildungslogin_plugin.models import SchoolContext
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
        ["school_admin", "staff"],
        ["staff"],
        ["student"],
        ["teacher"],
        ["teacher_and_staff"],
        ["teacher_and_staff", "school_admin"],
    ),
    ids=roles_id,
)
@pytest.mark.asyncio
async def test_get_school_context(fake_udm_user, roles):
    user = fake_udm_user(roles)
    backend = UdmRestApiBackend(
        username=fake.user_name(),
        password=fake.password(),
        url="http://127.0.0.1/univention/udm",
    )
    result = await backend.get_school_context(user)
    expected = {ou: SchoolContext(classes=set(), roles=set(roles)) for ou in user.props.school}
    for dn in [dn for dn in user.props.groups if "cn=klassen,cn=schueler" in dn]:
        ou, kls = dn.split(",")[0].split("=")[1].split("-")
        expected[ou].classes.add(kls)

    assert result == expected


@pytest.mark.asyncio
async def test_get_school_context_ignore_bad_class(fake_udm_user):
    user = fake_udm_user(["student"])
    base_dn = os.environ["LDAP_BASE"]
    bad_ou = fake.word()
    user.props.groups.append(
        f"cn={bad_ou}-{fake.word()},cn=klassen,cn=schueler,cn=groups,ou={bad_ou},{base_dn}"
    )
    backend = UdmRestApiBackend(
        username=fake.user_name(),
        password=fake.password(),
        url="http://127.0.0.1/univention/udm",
    )
    result = await backend.get_school_context(user)
    expected = {
        ou: SchoolContext(classes=set(), roles={"student"}) for ou in user.props.school if ou != bad_ou
    }
    for dn in [dn for dn in user.props.groups if "cn=klassen,cn=schueler" in dn]:
        ou, kls = dn.split(",")[0].split("=")[1].split("-")
        if ou == bad_ou:
            continue
        expected[ou].classes.add(kls)

    assert result == expected


@pytest.mark.asyncio
async def test_get_school_context_uses_get_roles_oc_fallback(fake_udm_user):
    user = fake_udm_user(["teacher"])
    user.props.ucsschoolRole = []
    backend = UdmRestApiBackend(
        username=fake.user_name(),
        password=fake.password(),
        url="http://127.0.0.1/univention/udm",
    )
    result = await backend.get_school_context(user)
    expected = {ou: SchoolContext(classes=set(), roles={"teacher"}) for ou in user.props.school}
    for dn in [dn for dn in user.props.groups if "cn=klassen,cn=schueler" in dn]:
        ou, kls = dn.split(",")[0].split("=")[1].split("-")
        expected[ou].classes.add(kls)

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
    assert expected == UdmRestApiBackend.get_roles_for_school(roles, school)


def test_get_roles_for_school_invalid_role():
    with pytest.raises(ValueError):
        UdmRestApiBackend.get_roles_for_school([":school:bar"], "bar")


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
            UdmRestApiBackend.get_roles_oc_fallback(options)
    else:
        assert expected == UdmRestApiBackend.get_roles_oc_fallback(options)
