# -*- coding: utf-8 -*-
#
# Copyright 2022 Univention GmbH
#
# http://www.univention.de/
#
# All rights reserved.
#
# The source code of this program is made available
# under the terms of the GNU Affero General Public License version 3
# (GNU AGPL V3) as published by the Free Software Foundation.
#
# Binary versions of this program provided by Univention to you as
# well as other copyrighted, protected or trademarked materials like
# Logos, graphics, fonts, specific documentations and configurations,
# cryptographic keys etc. are subject to a license agreement between
# you and Univention and not subject to the GNU AGPL V3.
#
# In the case you use this program under the terms of the GNU AGPL V3,
# the program is provided in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public
# License with the Debian GNU/Linux or Univention distribution in file
# /usr/share/common-licenses/AGPL-3; if not, see
# <http://www.gnu.org/licenses/>.

from __future__ import print_function

import argparse
import sys

import configparser
from typing import Any, Dict, List, Optional

from . import (confirm_licenses_package, get_access_token, retrieve_licenses_package,
               save_license_package_to_json)
from ..exceptions import AuthError, BiloServerError, LicenseSaveError, ScriptError
from ..utils import get_proxies


def parse_args(args=None):  # type: (Optional[List[str]]) -> argparse.Namespace
    parser = argparse.ArgumentParser(description="Retrieve license package")
    parser.add_argument(
        "--pickup-number", required=True, help="Pickup Number given when ordering license"
    )
    parser.add_argument(
        "--school", required=True, help="School abbreviation for which the license should be retrieved"
    )
    parser.add_argument(
        "--config-file", required=False, help="A path to a file which contains all config options for this command."
    )

    return parser.parse_args(args)


def retrieve_licenses(config, pickup_number):
    """
    Retrieve, save and confirm the retrieval of the license package

    During the workflow, the retrieval and confirmation
    endpoints can return the following status codes:
    Retrieval: 200 / 208
    Confirmation: 200 / 409
    The following scenarios are considered to be viable:
        - 200 -> 200 - The license package was retrieved, saved and confirmed for the first time
        - 208 -> 200 - The license package was already retrieved,
                       but has failed to be saved last time
        - 208 -> 409 - The license package was already retrieved
                       and was successfully confirmed

    The scenario where the license was newly acquired (200),
    but the confirmation has already happened (409) is considered
    to be erroneous and will raise an exception
    """
    if config is None:
        config = get_config_from_file('/etc/bildungslogin/config.ini')
    client_id = config["client_id"]
    client_secret = config["client_secret"]
    scope = config["scope"]
    auth_server = config["auth_server"]
    resource_server = config["resource_server"]
    proxies = get_proxies()

    try:
        access_token = get_access_token(client_id, client_secret, scope, auth_server, proxies)
    except Exception as exc:
        raise AuthError(
            "Unable to get access: {}".format(exc.message)
        )
    retrieve_response_code, license_response = \
        retrieve_licenses_package(access_token, resource_server, pickup_number, proxies)
    try:
        license_path = save_license_package_to_json(license_response, pickup_number)
    except Exception as exc:
        raise LicenseSaveError(
            "Unable to save license as a json: {}".format(exc.message)
        )

    confirm_response_code = confirm_licenses_package(access_token, resource_server, pickup_number, proxies)
    if (retrieve_response_code, confirm_response_code) == (200, 409):
        raise BiloServerError("Server error: New license was already confirmed")
    return license_path, license_response['licenses']


def get_config(args):  # type: (argparse.Namespace) -> Dict[str, Any]
    config = get_config_from_file(args.config_file)

    has_missing_args = False
    for required_field in ["client_id", "client_secret", "scope"]:
        if not config.get(required_field):
            has_missing_args = True
            print(
                "'%s' is missing. Add it via --config-file or --%s"
                % (required_field, required_field.replace("_", "-"))
            )
    if has_missing_args:
        sys.exit(1)
    return config


def get_config_from_file(filename):  # type: (str) -> Dict[str, Any]
    config = {}
    cp = configparser.ConfigParser()
    try:
        with open(filename, "r") as fd:
            cp.read_file(fd)
    except EnvironmentError as exc:
        raise ScriptError("Failed to load config from {!r}: {!s}".format(filename, exc))
    else:
        if cp.has_option("Auth", "ClientId"):
            config["client_id"] = cp["Auth"]["ClientId"]
        if cp.has_option("Auth", "ClientSecret"):
            config["client_secret"] = cp["Auth"]["ClientSecret"]
        if cp.has_option("Auth", "Scope"):
            config["scope"] = cp["Auth"]["Scope"]
        if cp.has_option("APIEndpoint", "AuthServer"):
            config["auth_server"] = cp["APIEndpoint"]["AuthServer"]
        if cp.has_option("APIEndpoint", "ResourceServer"):
            config["resource_server"] = cp["APIEndpoint"]["ResourceServer"]
    return config


def main():  # type: () -> None
    try:
        args = parse_args()
        retrieve_licenses(get_config(args), args.pickup_number)
    except ScriptError as err:
        print("Script Error: %s" % (err,), file=sys.stderr)
