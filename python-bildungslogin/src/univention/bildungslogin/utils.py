#!/usr/share/ucs-test/runner /usr/bin/py.test -s
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
# <https://www.gnu.org/licenses/>.

from ldap.filter import escape_filter_chars

from univention.lib.i18n import Translation
from univention.config_registry import ucr_factory

_ = Translation("python-bildungslogin").translate


def get_entry_uuid(lo, dn):
    """UDM doesn't expose the `entryUUID` attribute, so we have to use ldap here."""
    return lo.get(dn, attr=["entryUUID"])["entryUUID"][0]


def ldap_escape(value, allow_asterisks=True):
    escaped_wildcard = escape_filter_chars("*")
    value = escape_filter_chars(value)
    if allow_asterisks:
        value = value.replace(escaped_wildcard, "*")
    return value


def get_proxies():
    ucr = ucr_factory()
    http_proxy = ucr.get('proxy/http')
    https_proxy = ucr.get('proxy/https')
    if http_proxy is None and https_proxy is None:
        return None

    proxies = {}
    if http_proxy:
        proxies.update({'http': http_proxy})

    if https_proxy:
        proxies.update({'https': https_proxy})

    return proxies
