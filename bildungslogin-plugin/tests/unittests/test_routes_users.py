# -*- coding: utf-8 -*-

import random

import faker
import nest_asyncio
import pytest

from bildungslogin_plugin.models import SchoolContext
from bildungslogin_plugin.routes.v1.users import DbBackend, User

fake = faker.Faker()
# pytest event loop is already running: https://github.com/encode/starlette/issues/440
nest_asyncio.apply()  # patches asyncio to allow nested use of asyncio.run and loop.run_until_complete


@pytest.mark.asyncio
async def test_routes_v1_users_get(client, fake_db_backend, set_the_backend):
    """Test that the REST API returns for a User-ID a JSON-Object."""
    user = User(
        id=fake.uuid4(),
        first_name=fake.first_name(),
        last_name=fake.last_name(),
        licenses=set(fake.words(nb=3, unique=True)),
        context={
            ou: SchoolContext(
                classes=set(fake.words(nb=2, unique=True)),
                roles={random.choice(("staff", "student", "teacher"))},
            )
            for ou in fake.words(nb=3, unique=True)
        },
    )
    backend: DbBackend = fake_db_backend()
    backend._user = user
    await set_the_backend(backend)
    response = client.get(f"/v1/user/{user.id}")
    assert response.status_code == 200
    assert User(**response.json()) == user


@pytest.mark.asyncio
async def test_missing_plugin_initialization(client, set_the_backend):
    await set_the_backend(None)
    with pytest.raises(RuntimeError):
        client.get(f"/v1/user/{fake.uuid4()}")
