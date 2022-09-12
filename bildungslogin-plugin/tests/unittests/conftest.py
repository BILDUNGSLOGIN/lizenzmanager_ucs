# -*- coding: utf-8 -*-

import os
from typing import Any, Callable, Dict, List, Mapping, Optional

import faker
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from bildungslogin_plugin.backend import UserNotFound
from bildungslogin_plugin.models import Class, SchoolContext, User, Workgroup
from bildungslogin_plugin.plugin import router
from bildungslogin_plugin.routes.v1.users import DbBackend, get_backend, set_backend
from ucsschool.apis.opa import opa_instance
from ucsschool.apis.utils import auth_manager
from udm_rest_client.base import BaseObject, BaseObjectProperties

_ori_backend = None
fake = faker.Faker()


class FakeDbBackend(DbBackend):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, kwargs)
        self._user: Optional[User] = None

    async def connection_test(self) -> None:
        pass

    async def get_user(self, username: str) -> User:
        if self._user:
            return self._user
        else:
            raise UserNotFound


@pytest.fixture(scope="session")
def fake_db_backend():
    def _func() -> FakeDbBackend:
        return FakeDbBackend()

    return _func


@pytest.fixture(scope="session")
def app():
    return FastAPI()


class FakeOPA:
    @classmethod
    async def check_policy_true_or_raise(cls, *_args, **_kwargs):
        return True


@pytest.fixture(scope="session")
def fake_opa():
    """Returns a class with a method check_policy_true -> True"""
    return FakeOPA


@pytest.fixture(scope="session")
def dependency_overrides(app):
    """Override app dependencies temporarily"""

    def _standard_overrides(overrides: Mapping[Callable, Callable]):
        # let's override the dependencies, so that we don't test more than we want
        for original, override in overrides.items():
            print(f"overriding {original} with {override}")
            app.dependency_overrides[original] = override  # todo typehints?

    yield _standard_overrides
    app.dependency_overrides = {}


async def _async_dict():
    return {}


@pytest.fixture(scope="session")
def client(app, dependency_overrides, fake_opa):
    # FastAPI Depends() overrides for complete session
    overrides = {
        opa_instance: fake_opa,
        auth_manager: _async_dict,
    }
    dependency_overrides(overrides)
    app.include_router(router)
    return TestClient(app)


@pytest.fixture(scope="session")
def set_the_backend():
    global _ori_backend

    async def _func(backend, connection_test=True):
        global _ori_backend
        try:
            _ori_backend = get_backend()
        except RuntimeError:
            _ori_backend = None

        if backend and connection_test:
            await backend.connection_test()
        set_backend(backend)

    yield _func

    set_backend(_ori_backend)


@pytest.fixture(scope="session")
def valid_user_kwargs():
    def _func() -> Dict[str, Any]:
        def _get_licenses():
            return fake.words(nb=3, unique=True)

        return User(
            id=fake.uuid4(),
            first_name=fake.first_name(),
            last_name=fake.last_name(),
            licenses=_get_licenses(),
            context={
                ou: SchoolContext(
                    school_authority=None,
                    school_code=fake.unique.word(),
                    school_identifier=fake.unique.word(),
                    school_name=fake.unique.word(),
                    licenses=_get_licenses(),
                    classes=[Class(name=n,
                                   id="".join(reversed(n)),
                                   licenses=_get_licenses())
                             for n in fake.words(nb=3, unique=True)],
                    workgroups=[Workgroup(name=n,
                                          id="".join(reversed(n)),
                                          licenses=_get_licenses())
                                for n in fake.words(nb=3, unique=True)],
                    roles=["staff", "student", "teacher"],
                )
                for ou in fake.words(nb=3, unique=True)
            },
        ).dict()

    return _func


@pytest.fixture(scope="session")
def empty_udm_obj():
    def _func() -> BaseObject:
        obj = BaseObject()
        obj.props = BaseObjectProperties(obj)
        return obj

    return _func


@pytest.fixture(scope="session")
def fake_udm_user(empty_udm_obj):
    def _func(roles: List[str], ous: List[str] = None) -> BaseObject:
        """
        First role will be used to determine LDAP container. Alph. 1st OU will be used for LDAP position.
        """
        base_dn = os.environ["LDAP_BASE"]
        container = {
            "school_admin": "admins",
            "staff": "mitarbeiter",
            "student": "schueler",
            "teacher": "lehrer",
            "teacher_and_staff": "lehrer und mitarbeiter",
        }[roles[0]]
        if "teacher_and_staff" in roles:
            roles.remove("teacher_and_staff")
            roles.extend(["staff", "teacher"])
        if not ous:
            ous = [f"ou{fake.word()}", f"ou{fake.word()}"]

        obj = empty_udm_obj()
        obj.props.first_name = fake.first_name()
        obj.props.last_name = fake.last_name()
        obj.props.user_name = fake.user_name()
        obj.props.school = ous
        obj.props.groups = [f"cn=Domain Users {ou},cn=groups,ou={ou},{base_dn}" for ou in ous]
        obj.props.groups.extend(
            [f"cn={ou}-{fake.word()},cn=klassen,cn=schueler,cn=groups,ou={ou},{base_dn}" for ou in ous]
        )
        obj.props.ucsschoolRole = [f"{role}:school:{ou}" for ou in ous for role in roles]

        obj.position = f"cn={container},ou={sorted(obj.props.school)[0]},{base_dn}"
        obj.dn = f"uid={obj.props.user_name},{obj.position}"
        obj.options = {
            "ucsschoolAdministrator": "school_admin" in roles,
            "ucsschoolExam": False,
            "ucsschoolTeacher": "teacher" in roles,
            "ucsschoolStudent": "student" in roles,
            "ucsschoolStaff": "staff" in roles,
            "pki": False,
        }
        return obj

    return _func
