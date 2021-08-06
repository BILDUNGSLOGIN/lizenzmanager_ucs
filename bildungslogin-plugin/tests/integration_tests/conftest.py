import asyncio
import datetime
from pathlib import Path
import os
import random
from typing import Any, Dict, List, Tuple
import uuid
from hashlib import sha256

import factory
import faker
import pytest

from bildungslogin_plugin.models import AssignmentStatus
from ucsschool.kelvin.client import Session, User, UserResource
from udm_rest_client import UDM, UdmObject, NoObject as UdmNoObject
from ucsschool.apis.plugins.auth import ldap_auth


fake = faker.Faker()

APP_ID = "ucsschool-apis"
APP_BASE_PATH = Path("/var/lib/univention-appcenter/apps", APP_ID)
APP_CONFIG_BASE_PATH = APP_BASE_PATH / "conf"
CN_ADMIN_PASSWORD_FILE = APP_CONFIG_BASE_PATH / "cn_admin.secret"


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop()
    yield loop
    loop.close()


class KelvinUserFactory(factory.Factory):
    class Meta:
        model = User

    name = factory.Faker("user_name")
    school = ""
    schools = factory.List([])
    firstname = factory.Faker("first_name")
    lastname = factory.Faker("last_name")
    birthday = factory.LazyFunction(
        lambda: fake.date_of_birth(minimum_age=6, maximum_age=65).strftime("%Y-%m-%d")
    )
    disabled = False
    email = None
    password = factory.Faker("password", length=20)
    record_uid = factory.LazyAttribute(lambda o: o.name)
    roles = factory.List([])
    school_classes = factory.Dict({})
    source_uid = "TESTID"
    udm_properties = factory.Dict({})
    ucsschool_roles = factory.List([])
    dn = ""
    url = ""
    kelvin_password_hashes = None


@pytest.fixture  # noqa: C901
def test_user_obj():  # noqa: C901
    # copied from kelvin-rest-api-client/tests/conftest.py::new_user_test_obj
    role_choices = ("staff", "student", "teacher", "teacher_and_staff")

    def _func(**kwargs) -> User:
        if "roles" not in kwargs:
            try:
                role = kwargs.pop("role")
            except KeyError:
                role = random.choice(role_choices)
            if role in ("staff", "student", "teacher"):
                kwargs["roles"] = [role]
            elif role == "teacher_and_staff":
                kwargs["roles"] = ["staff", "teacher"]
            else:
                raise ValueError(  # pragma: no cover
                    f"Argument 'role' to new_user_test_obj() must be one of "
                    f"{', '.join(role_choices)}."
                )
        if "school" not in kwargs and "schools" not in kwargs:
            test_school = "DEMOSCHOOL"  # TODO: create random OU?
            kwargs["school"] = test_school
            kwargs["schools"] = [kwargs["school"]]
        if "school" not in kwargs:
            kwargs["school"] = sorted(kwargs["schools"])[0]  # pragma: no cover
        if "schools" not in kwargs:
            kwargs["schools"] = [kwargs["school"]]
        if "school_classes" not in kwargs:
            kwargs["school_classes"] = {kwargs["school"]: fake.words(nb=2, unique=True)}
        if "ucsschool_roles" not in kwargs:
            kwargs["ucsschool_roles"] = [
                f"{role}:school:{school}" for role in kwargs["roles"] for school in kwargs["schools"]
            ]
        user: User = KelvinUserFactory(**kwargs)
        user.name = user.name[:15]
        return user

    return _func


@pytest.fixture(scope="session")
def udm_kwargs() -> Dict[str, Any]:
    return {
        "username": ldap_auth.credentials.cn_admin,
        "password": ldap_auth.credentials.cn_admin_password,
        "url": f"https://{os.environ['LDAP_MASTER']}/univention/udm/",
    }


@pytest.fixture(scope="session")
def kelvin_session_kwargs() -> Dict[str, str]:
    return {
            "username": "Administrator",
            "password": "univention",
            "host": os.environ["LDAP_MASTER"],
            "verify": False,
        }


@pytest.fixture
async def schedule_delete_udm_obj(udm_kwargs):
    objs: List[Tuple[str, str]] = []

    def _func(dn: str, udm_mod: str) -> None:
        objs.append((dn, udm_mod))

    yield _func

    async with UDM(**udm_kwargs) as udm:
        for dn, udm_mod_name in objs:
            mod = udm.get(udm_mod_name)
            try:
                udm_obj = await mod.get(dn)
            except UdmNoObject:
                print(f"UDM {udm_mod_name!r} object {dn!r} does not exist (anymore).")
                continue
            await udm_obj.delete()
            print(f"Deleted UDM {udm_mod_name!r} object {dn!r} through UDM.")


@pytest.fixture
async def schedule_delete_user_dn(schedule_delete_udm_obj):
    def _func(dn: str) -> None:
        schedule_delete_udm_obj(dn, "users/user")

    yield _func


@pytest.fixture
def create_test_user(kelvin_session_kwargs, test_user_obj, schedule_delete_user_dn):
    async def _func(**kwargs) -> User:
        async with Session(**kelvin_session_kwargs) as session:
            user: User = test_user_obj(session=session, **kwargs)
            new_user: User = await user.save()
        schedule_delete_user_dn(new_user.dn)
        return new_user

    return _func


@pytest.fixture
def random_license_data():
    yesterday = datetime.datetime.now() - datetime.timedelta(days=1)
    next_year = datetime.datetime.now() + datetime.timedelta(days=365)

    def _func() -> Dict[str, Any]:
        code = f"VHT-{uuid.uuid4()!s}"
        return {
            "cn": sha256(code.encode()).hexdigest(),
            "code": code,
            "delivery_date": datetime.datetime.now().strftime("%Y-%m-%d"),
            # "expired": None,
            # "ignored": None,
            # "num_assigned": None,
            # "num_available": None,
            # "num_expired": None,
            "product_id": f"urn:bilo:medium:A00{random.randint(10, 99)}#{random.randint(10, 99)}-"
                          f"{random.randint(10, 99)}-TZ",
            "provider": "VHT",
            "purchasing_reference": f"{yesterday.isoformat()} -02:00 4572022",
            "quantity": random.randint(2, 5),
            "school": "DEMOSCHOOL",
            # "special_type": None,
            "utilization_systems": random.choice(("Antolin", "Alfons", "BiBox")),
            "validity_duration": random.choice(("Schuljahreslizenz", "Dauerlizenz")),
            "validity_end_date": next_year.strftime("%Y-%m-%d"),
            "validity_start_date": yesterday.strftime("%Y-%m-%d"),
        }

    return _func


@pytest.fixture
def new_assignment_data():
    def _func() -> Dict[str, Any]:
        return {
            "assignee": None,
            "cn": str(uuid.uuid4()),
            "status": AssignmentStatus.AVAILABLE.name,
            "time_of_assignment": None,
        }

    return _func


@pytest.fixture
def create_license_and_assignments(
        new_assignment_data, random_license_data, schedule_delete_udm_obj, udm_kwargs
):
    """Create a license and its associated assignments in LDAP."""
    async def _func() -> Tuple[UdmObject, List[UdmObject]]:
        async with UDM(**udm_kwargs) as udm:
            license_mod = udm.get("vbm/license")
            license_obj = await license_mod.new()
            license_obj.position = f"cn=vbm,cn=univention,{ldap_auth.settings.ldap_base}"
            license_data = random_license_data()
            license_obj.props.update(license_data)
            await license_obj.save()
            schedule_delete_udm_obj(license_obj.dn, "vbm/license")

            assignments = []
            for _ in range(license_obj.props.quantity):
                assignment_mod = udm.get("vbm/assignment")
                assignment_obj = await assignment_mod.new()
                assignment_obj.position = license_obj.dn
                assignment_data = new_assignment_data()
                assignment_obj.props.update(assignment_data)
                await assignment_obj.save()
                schedule_delete_udm_obj(assignment_obj.dn, "vbm/assignment")
                assignments.append(assignment_obj)
            license_obj.props.assignments = [assignment.dn for assignment in assignments]
            await license_obj.save()

        return license_obj, assignments

    return _func
