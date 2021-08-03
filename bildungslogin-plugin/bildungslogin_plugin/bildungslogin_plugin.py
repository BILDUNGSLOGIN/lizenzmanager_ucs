from typing import Any, Dict, List

from bildungslogin_plugin.models import User, user_id_description
from fastapi import APIRouter, Depends, HTTPException, Path
from id_broker_plugin.id_broker_plugin import load_kelvin_session_kwargs
from starlette import status

import ucsschool.kelvin.client.exceptions
from ucsschool.apis.models import Plugin
from ucsschool.apis.plugins.auth import oauth2_scheme
from ucsschool.apis.utils import get_logger
from ucsschool.kelvin.client import Session, User as KelvinUser, UserResource

# the name of the plugin which will also determine the name of the resource
PLUGIN_NAME: str = "bildungslogin"
# the plugins current version. Not used for anything in the ucsschool-apis app
PLUGIN_VERSION: str = "1.0.0"
# the plugins tags:
PLUGIN_TAGS: List[str] = ["bildungslogin"]
# the router that will be mounted as the resource under the plugins name:
router: APIRouter = APIRouter()
PLUGIN_SETTINGS_FILE = Path("/etc/ucsschool/apis/id_broker/settings.json")
_kelvin_session_kwargs: Dict[str, Any] = {}
_kelvin_session: Session = None


async def kelvin_session() -> Session:
    # this function must be async, or Session.__init__() will fail because there is not yet an event loop
    global _kelvin_session
    if not _kelvin_session:
        _kelvin_session = Session(**_kelvin_session_kwargs)
        _kelvin_session.open()
    return _kelvin_session


def setup():
    logger = get_logger()
    logger.info(f"Setup of {PLUGIN_NAME} with version {PLUGIN_VERSION}")
    kwargs = load_kelvin_session_kwargs()
    logger.info(f"Setup of {PLUGIN_NAME} with kwargs {kwargs}")
    _kelvin_session_kwargs.update(kwargs)


# TODO this is copied from bettermarks_plugin. Refactor!
async def get_single_user_by_name(name: str, session: Session) -> User:
    """Search for a single user by name."""
    return await UserResource(session=session).get(name=name)


@router.get("/user/{user_id}", response_model=User)
async def get_user(
    user_id: str = Path(..., description=user_id_description),
    _token: str = Depends(oauth2_scheme),
    # policy_instance: OPAClient = Depends(opa_instance),
    session: Session = Depends(kelvin_session),
):
    """Return a user with context information about schools, roles, classes and license information. WARNING: this
    route is protected for now by an 'OAuth2 Resource Owner Password Credentials Grant'. This is subject to change
    to another type of grant in the future."""

    # TODO we don't know anything about the user_id yet. For now I use it directly
    # as an internal user_id. Please replace by something more meaningful
    try:
        kelvinuser: KelvinUser = await get_single_user_by_name(user_id, session)
    except ucsschool.kelvin.client.exceptions.NoObject:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No user was found for '{user_id}.'",
        )

    # TODO licenses. This here is only good for tests
    licenses = getattr(kelvinuser, "__licenses__", ["foo-123", "bar-456"])

    context = {}
    for schoolname, classes in kelvinuser.school_classes.items():
        context.setdefault(schoolname, dict(classes=classes, roles=[]))

    for role in kelvinuser.ucsschool_roles:
        r, c, s = role.split(":")
        if c != "school":
            continue
        if s not in context:
            context[s] = dict(classes=[], roles=[])
        roles = context[s]["roles"]
        if r not in roles:
            roles.append(r)

    return User(id=user_id, licenses=licenses, context=context)


# This is the object that is referenced in the pyproject.toml as the plugin object:
BildungsloginPlugin = Plugin(PLUGIN_NAME, PLUGIN_VERSION, PLUGIN_TAGS, router, setup)
