# -*- coding: utf-8 -*-
from typing import Callable, Mapping
from unittest.mock import AsyncMock, MagicMock

import pytest
from bildungslogin_plugin import bildungslogin_plugin
from bildungslogin_plugin.bildungslogin_plugin import kelvin_session, router
from bildungslogin_plugin.models import sample_user
from fastapi import FastAPI
from fastapi.testclient import TestClient

from ucsschool.apis.plugins.auth import oauth2_scheme


# TODO how do we get this from id_broker_plugin.tests.conftest?
# or generally: refactor, we have too much copy and paste in the
# plugins
@pytest.fixture(scope="session")
def app():
    return FastAPI()


async def _async_dict():
    return {}


@pytest.fixture(scope="session")
def async_dict():
    """Returns an async method that returns an empty dict"""
    return _async_dict


async def mock_kelvin_session():
    return MagicMock()


@pytest.fixture(scope="session")
def client(app, dependency_overrides, async_dict):
    # FastAPI Depends() overrides for complete session
    app.include_router(router)
    overrides = {
        oauth2_scheme: async_dict,
        kelvin_session: mock_kelvin_session,
    }
    dependency_overrides(overrides)
    return TestClient(app)


@pytest.fixture(scope="session")
def dependency_overrides(app):
    """Override app dependencies temporarily"""

    def _standard_overrides(overrides: Mapping[Callable, Callable]):
        app.include_router(router)
        # let's override the dependencies, so that we don't test more than we want
        for original, override in overrides.items():
            print(f"overriding {original} with {override}")
            app.dependency_overrides[original] = override  # todo typehints?

    yield _standard_overrides
    app.dependency_overrides = {}


class DictObject(dict):
    def __getattr__(self, item):
        return self[item]

    def __setattr__(self, key, value):
        self[key] = value

    def as_dict(self):
        return self


# This is the kelvin equivalent of the sample user from the models
kelvin_sample_user = DictObject(
    __licenses__=["COR-123", "COR-456"],
    name="sample_user_id",
    roles=["student"],
    firstname="stu1",
    lastname="dent",
    school_classes=dict(schoolA=["class1", "class2"], schoolB=[]),
    school="schoolA",
    ucsschool_roles=["student:school:schoolA", "staff:school:schoolB", "teacher:school:schoolB"],
)


def test_userdata_correct(client, monkeypatch):
    user_id = "sample_user_id"
    expected_user = dict(sample_user)
    expected_user["id"] = user_id

    monkeypatch.setattr(
        bildungslogin_plugin, "get_single_user_by_name", AsyncMock(return_value=kelvin_sample_user)
    )
    response = client.get(f"/user/{user_id}")
    assert response.status_code == 200
    assert response.json() == expected_user
