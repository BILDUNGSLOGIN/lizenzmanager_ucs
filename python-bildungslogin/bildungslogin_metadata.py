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

import subprocess

from ldap.filter import filter_format

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

        if hasattr(code, 'decode'):
            code = code.decode("utf-8")

        if hasattr(product_id, 'decode'):
            product_id = product_id.decode("utf-8")

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

        process_output = subprocess.Popen(
            ['sudo', 'bildungslogin-media-import', '--config-file', '/etc/bildungslogin/config.ini',
             product_id],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT)
        stdout, stderr = process_output.communicate()
        if hasattr(stdout, 'decode'):
            stdout = stdout.decode("utf-8")
        if stderr is None:
            if stdout.startswith("Error"):
                self.logger.error(stdout.strip())
            else:
                self.logger.info(stdout.strip())
