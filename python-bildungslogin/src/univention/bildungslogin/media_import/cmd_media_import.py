# -*- coding: utf-8 -*-
#
# Copyright 2021 Univention GmbH
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
import configparser
import sys
from datetime import datetime
from typing import List, Optional

import requests

from univention.admin.uldap import getAdminConnection
from univention.bildungslogin.handlers import BiloCreateError, MetaDataHandler
from univention.bildungslogin.models import MetaData


class ScriptError(Exception):
    pass


def get_access_token(client_id, client_secret, scope, auth_server):
    response = requests.post(
        auth_server,
        data={"grant_type": "client_credentials", "scope": scope},
        auth=(
            client_id,
            client_secret,
        ),
    )
    if response.status_code != 200:
        raise ScriptError("Authorization failed: %s" % (response.json()["error_description"],))
    return response.json()["access_token"]


def get_media_data(client_id, client_secret, scope, auth_server, resource_server, product_ids):
    access_token = get_access_token(client_id, client_secret, scope, auth_server)

    response = requests.post(
        resource_server + "/external/univention/media/query",
        json=[{"id": product_id} for product_id in product_ids],
        headers={
            "Authorization": "Bearer " + access_token,
            "Content-Type": "application/vnd.de.bildungslogin.mediaquery+json",
        },
    )

    lo, po = getAdminConnection()
    mh = MetaDataHandler(lo)

    not_found = []
    import_errors = []
    for ro in response.json():
        if ro["status"] == 200:
            data = ro["data"]
            try:
                md = MetaData(
                    product_id=data["id"],
                    title=data["title"],
                    description=data["description"],
                    author=data["author"],
                    publisher=data["publisher"],
                    cover=data["cover"][
                        "href"
                    ],  # TODO what does data['cover'] look like if there is no cover
                    cover_small=data["coverSmall"]["href"],
                    modified=datetime.utcfromtimestamp(data["modified"] // 1).strftime("%Y-%m-%d"),
                )
            except (KeyError, ValueError) as exc:
                import_errors.append(
                    "%s -- %s"
                    % (
                        data["id"],
                        exc,
                    )
                )
            else:
                try:
                    mh.create(md)
                except BiloCreateError as exc:
                    import_errors.append(
                        "%s -- %s"
                        % (
                            data.get("id"),
                            str(exc),
                        )
                    )
        else:
            not_found.append(ro["query"]["id"])

    err = ""
    if not_found or import_errors:
        err += "Not all media data could be downloadeda:\n"
    if not_found:
        err += "  The following product ids did not yield metadata:\n"
        for e in not_found:
            err += "    %s\n" % (e,)
        err += "\n"
    if import_errors:
        err += "  The media data for the following product ids could not be imported:\n"
        for e in import_errors:
            err += "    %s\n" % (e,)
    if err:
        raise ScriptError(err)


def main(args):
    # type: (argparse.Namespace) -> None
    config = {
        "auth_server": "https://global.telekom.com/gcp-web-api/oauth",
        "resource_server": "https://www.bildungslogin-test.de/api",
    }

    if args.config_file:
        cp = configparser.ConfigParser()
        try:
            with open(args.config_file, "r") as fd:
                cp.read_file(fd)
        except EnvironmentError as exc:
            raise ScriptError(
                "Failed to load config from --config-file (%s): %s"
                % (
                    args.config_file,
                    exc,
                )
            )

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

    if args.client_id:
        config["client_id"] = args.client_id
    if args.client_secret:
        config["client_secret"] = args.client_secret
    if args.scope:
        config["scope"] = args.scope
    if args.auth_server:
        config["auth_server"] = args.auth_server
    if args.resource_server:
        config["resource_server"] = args.resource_server
    for required_field in ["client_id", "client_secret", "scope"]:
        if not config.get(required_field):
            print(
                "'%s' is missing. Add it via --config-file or --%s"
                % (required_field, required_field.replace("_", "-"))
            )
    get_media_data(
        config["client_id"],
        config["client_secret"],
        config["scope"],
        config["auth_server"],
        config["resource_server"],
        args.product_ids,
    )


def parse_args(args=None):
    # type: (Optional[List[str]]) -> argparse.Namespace
    parser = argparse.ArgumentParser(description="Import media data for given product ids")
    parser.add_argument(
        "--config-file",
        help="A path to a file which contains all config options for this command. See TODO for example.",
    )
    parser.add_argument("--client-id", help="client id used for authentication against --auth-server")
    parser.add_argument(
        "--client-secret", help="client secret used for authentication against --auth-server"
    )
    parser.add_argument("--scope", help="TODO")
    parser.add_argument("--auth-server", help="")
    parser.add_argument(
        "--resource-server", help="The server from which the media data should be downloaded"
    )
    parser.add_argument(
        "product_ids",
        nargs="+",
        help="One or multiple product ids whose media data should be downloaded",
    )
    return parser.parse_args(args)


if __name__ == "__main__":
    try:
        main(parse_args())
    except ScriptError as err:
        print("Error: %s" % (err,), file=sys.stderr)
