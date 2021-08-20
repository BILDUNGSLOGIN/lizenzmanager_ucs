# -*- coding: utf-8 -*-
import random

import faker

from bildungslogin_plugin.models import SchoolContext
from bildungslogin_plugin.routes.v1.users import DbBackend, User, set_backend

fake = faker.Faker()


def test_routes_v1_users_get(client, fake_db_backend):
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
    set_backend(backend)
    response = client.get(f"/v1/user/{user.id}")
    assert response.status_code == 200
    assert User(**response.json()) == user
