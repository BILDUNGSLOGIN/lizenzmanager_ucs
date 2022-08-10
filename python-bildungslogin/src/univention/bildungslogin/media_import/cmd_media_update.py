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

import datetime
import sys
from typing import Any, Optional

from univention.admin.uldap import getAdminConnection
from univention.bildungslogin.handlers import MetaDataHandler

from . import get_access_token, retrieve_media_data, retrieve_media_feed
from .cmd_media_import import get_config_from_file, import_multiple_raw_media_data

CONFIG_FILE = "/etc/bildungslogin/config.ini"
UPDATE_TIMESTAMP_FILE = "/var/lib/bildungslogin/last_update"


def load_last_update_timestamp(path=UPDATE_TIMESTAMP_FILE):  # type: (Optional[str]) -> int
    try:
        with open(path, "r") as fp:
            return int(fp.read().strip())
    except EnvironmentError:
        return 0  # start with 1970-01-01


def save_last_update_timestamp(ts, path=UPDATE_TIMESTAMP_FILE):  # type: (int, Optional[str]) -> None
    with open(path, "w") as fp:
        fp.write(str(ts))


def update_ldap_meta_data(lo):  # type: (Any) -> bool
    last_update_ts = load_last_update_timestamp()
    print(
        "Updating meta data changed since {:%Y-%m-%d %H:%M} UTC...".format(
            datetime.datetime.utcfromtimestamp(last_update_ts // 1000).date()
        )
    )
    config = get_config_from_file(CONFIG_FILE)
    access_token = get_access_token(
        config["client_id"], config["client_secret"], config["scope"], config["auth_server"]
    )
    updated_product_ids = retrieve_media_feed(access_token, config["resource_server"], round(last_update_ts/1000))
    print("Meta data of {} products changed on the media server.".format(len(updated_product_ids)))
    if not updated_product_ids:
        return True
    mh = MetaDataHandler(lo)
    product_ids_in_ldap = {o.product_id for o in mh.get_all()}
    print("A total of {} product IDs was found in LDAP.".format(len(product_ids_in_ldap)))
    product_ids_to_update = set(updated_product_ids).intersection(product_ids_in_ldap)
    # No products in LDAP -> fall through -> ERROR
    # Some products in LDAP but nothing to update -> regular flow and nothing to do -> NO ERROR
    if len(product_ids_in_ldap) and not len(product_ids_to_update):
        print("No updates available to the products known to this system.")
        return True
    print(
        "Going to retrieve {} meta data entries from the media server...".format(
            len(product_ids_to_update)
        )
    )
    raw_media_data = retrieve_media_data(
        access_token, config["resource_server"], sorted(product_ids_to_update)
    )
    error_message = import_multiple_raw_media_data(mh, raw_media_data)
    # store earliest update timestamp from a successful item download
    all_dates_unique = {data["data"]["modified"] for data in raw_media_data if data["status"] == 200}
    if all_dates_unique:
        save_last_update_timestamp(min(all_dates_unique))
    if error_message:
        print(error_message)
        print("-" * 80)
        print("The next update will nevertheless look for updates from 'now' on.")
        print("To manually update products meta data, run:")
        print(
            "bildungslogin-media-import --config-file /etc/bildungslogin/config.ini product_id "
            "[product_id ...]"
        )
        print("Or delete {!r} to redownload all previous updates.".format(UPDATE_TIMESTAMP_FILE))
        return False
    print("No errors happened downloading the meta data.")
    return True


def main():  # type: () -> None
    lo, _ = getAdminConnection()
    success = update_ldap_meta_data(lo)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
