# -*- coding: utf-8 -*-
from typing import Callable, Mapping, Optional

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from bildungslogin_plugin.plugin import router
from bildungslogin_plugin.routes.v1.users import DbBackend, User
from ucsschool.apis.opa import opa_instance
from ucsschool.apis.plugins.auth import get_token


class FakeDbBackend(DbBackend):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, kwargs)
        self._user: Optional[User] = None

    async def connection_test(self) -> None:
        pass

    async def get_user(self, username: str) -> User:
        return self._user


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
        get_token: _async_dict,
    }
    dependency_overrides(overrides)
    app.include_router(router)
    return TestClient(app)
