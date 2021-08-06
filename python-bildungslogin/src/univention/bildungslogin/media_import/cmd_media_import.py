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
import sys
from datetime import datetime
from typing import List, NoReturn, Optional

import requests

from univention.admin.uldap import getAdminConnection
from univention.bildungslogin.handlers import BiloCreateError, MetaDataHandler
from univention.bildungslogin.models import MetaData

AUTHENTICATION_SERVER = "https://global.telekom.com/gcp-web-api/oauth"
RESOURCE_SERVER = "https://www.bildungslogin-test.de/api"


class ScriptError(Exception):
    pass


def error(msg):
    # type: (str) -> NoReturn
    raise ScriptError(msg)


def get_access_token(user, password, scope):
    response = requests.post(
        AUTHENTICATION_SERVER,
        data={"grant_type": "client_credentials", "scope": scope},
        auth=(
            user,
            password,
        ),
    )
    if response.status_code != 200:
        try:
            json = response.json()
            msg = json.get("error_description", "")
        except ValueError:
            msg = ""
        error("Authorization failed: %s" % (msg,))
    # TODO do we have to check that the api returns what we expect here?
    return response.json()["access_token"]


def get_media_data(product_ids, user, password, scope):
    at = get_access_token(user, password, scope)

    response = requests.post(
        RESOURCE_SERVER + "/external/univention/media/query",
        json=[{"id": pid} for pid in product_ids],
        headers={
            "Authorization": "Bearer " + at,
            "Content-Type": "application/vnd.de.bildungslogin.mediaquery+json",
        },
    )
    #  if response.status_code != 200:
    #  msg = response.json().get('error_description', '')
    #  error("Getting media data failed: %s" % (msg,))
    lo, po = getAdminConnection()
    mh = MetaDataHandler(lo)

    not_found = []
    import_errors = []
    for ro in response.json():
        print(ro)
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
                    modified=datetime.utcfromtimestamp(data["modified"]).strftime(
                        "%Y-%m-%d"
                    ),  # TODO this can fail, e.g. with the data from minimal.py
                )
            except Exception as exc:
                print(data)
                print(exc)
                import_errors.append("%s")
            else:
                try:
                    mh.create(md)
                except BiloCreateError as exc:
                    import_errors.append(
                        "%s: %s"
                        % (
                            data.get("id"),
                            str(exc),
                        )
                    )
        else:
            not_found.append(ro["query"]["id"])

    if not_found:
        print("The following product ids did not yield metadata:")
        for e in not_found:
            print(e)
        print(" ")
    if import_errors:
        print("The media data for the following product ids could not be imported:")
        for e in import_errors:
            print(e)


def main(args):
    # type: (argparse.Namespace) -> None
    print(args)
    get_media_data(args.product_ids, args.user, args.password, args.scope)


def parse_args(args=None):
    # type: (Optional[List[str]]) -> argparse.Namespace
    parser = argparse.ArgumentParser(description="Import media data for given product ids")
    parser.add_argument("--user", required=True, help="TODO")
    parser.add_argument("--password", required=True, help="TODO")
    parser.add_argument("--scope", required=True, help="TODO")
    parser.add_argument("product_ids", nargs="+", help="One or multiple product ids")
    return parser.parse_args(args)


if __name__ == "__main__":
    try:
        main(parse_args())
    except ScriptError as err:
        print("Error: %s" % (err,), file=sys.stderr)
