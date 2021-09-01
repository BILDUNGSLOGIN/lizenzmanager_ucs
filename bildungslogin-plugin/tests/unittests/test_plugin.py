# -*- coding: utf-8 -*-

from unittest.mock import patch

import pytest

import bildungslogin_plugin.plugin
from bildungslogin_plugin.backend_udm_rest_api import UdmRestApiBackend
from bildungslogin_plugin.routes.v1.users import get_backend


@patch("bildungslogin_plugin.plugin.ldap_auth")
@pytest.mark.asyncio
async def test_setup(ldap_auth_mock):
    bildungslogin_plugin.plugin.setup()
    backend = get_backend()
    assert isinstance(backend, UdmRestApiBackend)
