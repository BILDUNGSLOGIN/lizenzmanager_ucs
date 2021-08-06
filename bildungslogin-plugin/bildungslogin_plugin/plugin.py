# -*- coding: utf-8 -*-
import asyncio
import logging
from pathlib import Path
from typing import List

from fastapi import APIRouter

from ucsschool.apis.models import Plugin
from ucsschool.apis.plugins.auth import ldap_auth

from .backend import UdmRestApiBackend
from .routes.v1 import users as users_routes_v1

# the name of the plugin which will also determine the name of the resource
PLUGIN_NAME: str = "bildungslogin"
# the plugins current version. Not used for anything in the ucsschool-apis app
PLUGIN_VERSION: str = "1.0.0"
# the plugins tags:
PLUGIN_TAGS: List[str] = [PLUGIN_NAME]
# the router that will be mounted as the resource under the plugins name:
router: APIRouter = APIRouter()

SETTINGS_FILE = Path(f"/etc/ucsschool/apis/{PLUGIN_NAME}/settings.json")

logger = logging.getLogger(__name__)


def setup():
    logger.info(f"Setup of {PLUGIN_NAME!r} with version {PLUGIN_VERSION!r}...")
    # load config now to raise exception about errors as early as possible
    setup_db_backend(
        username=ldap_auth.credentials.cn_admin,
        password=ldap_auth.credentials.cn_admin_password,
        url=f"https://{ldap_auth.settings.master_fqdn}/univention/udm",
    )


def setup_db_backend(**plugin_settings) -> None:
    backend = UdmRestApiBackend(**plugin_settings)
    # setup() is not async, so setup_db_backend() isn't either.
    # We use the event loop created by FastAPI.
    loop = asyncio.get_running_loop()
    loop.create_task(backend.connection_test())
    logger.info("UDM REST API connection successfully tested.")
    users_routes_v1.set_backend(backend)


router.include_router(users_routes_v1.router, prefix="/v1")

# This is the object that is referenced in the pyproject.toml as the plugin object:
BildungsloginPlugin = Plugin(PLUGIN_NAME, PLUGIN_VERSION, PLUGIN_TAGS, router, setup)
