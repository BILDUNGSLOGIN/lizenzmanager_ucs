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

from univention.listener import ListenerModuleHandler

CONFIG_FILE = "/etc/bildungslogin/config.ini"


class BildungsloginUserListener(ListenerModuleHandler):
    class Configuration(object):
        name = "bildungslogin_user_listener"
        description = "Set unused licenses free after user deletion."
        ldap_filter = "(&(objectClass=ucsschoolType)(univentionObjectType=users/user))"
        attributes = []

    def remove(self, dn, old):
        self.logger.info("Release assignment for user %r...", old.get('uid'))
        process_output = subprocess.Popen(
            ['sudo', 'bildungslogin-assignment-release', '--entry-uuid', old['entryUUID'][0]],
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
