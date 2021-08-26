# -*- coding: utf-8 -*-
#
# Copyright 2021 Univention GmbH
#
# https://www.univention.de/
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
# you and Univention.
#
# This program is provided in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public
# License with the Debian GNU/Linux or Univention distribution in file
# /usr/share/common-licenses/AGPL-3; if not, see
# <https://www.gnu.org/licenses/>.
#

from __future__ import absolute_import

from ldap.filter import filter_format

from univention.bildungslogin.media_import.cmd_media_import import (
    ScriptError,
    get_config_from_file,
    import_all_media_data,
)
from univention.listener import ListenerModuleHandler

CONFIG_FILE = "/etc/bildungslogin/config.ini"


class BildungsloginMetaDataDownloader(ListenerModuleHandler):
    class Configuration(object):
        name = "bildungslogin_meta_data_downloader"
        description = "Bildungslogin Metadata retrieval"
        ldap_filter = "(objectClass=bildungsloginLicense)"
        attributes = []

    def create(self, dn, new):
        code = new.get("bildungsloginLicenseCode", [None])[0]
        product_id = new.get("bildungsloginProductId", [None])[0]
        self.logger.info(
            "New Bildungslogin license. Code: %r Product ID: %r DN: %r", code, product_id, dn
        )

        meta_data_filter = filter_format(
            "(&(objectClass=bildungsloginMetaData)(bildungsloginProductId=%s))", (product_id,)
        )
        if self.lo.searchDn(meta_data_filter):
            self.logger.info("Meta data for product %r already exist in LDAP.", product_id)
            return

        self.logger.info("Fetching metadata for product %r...", product_id)

        config = get_config_from_file(CONFIG_FILE)
        if not all(
            (
                config.get("client_id"),
                config.get("client_secret"),
                config.get("scope"),
                config.get("auth_server"),
                config.get("resource_server"),
            )
        ):
            raise ValueError("Incomplete configuration in %r.", CONFIG_FILE)

        try:
            import_all_media_data(
                self.lo,
                config["client_id"],
                config["client_secret"],
                config["scope"],
                config["auth_server"],
                config["resource_server"],
                [product_id],
            )
        except ScriptError as exc:
            self.logger.error("Error retrieving meta data for product %r: %s", product_id, exc)
