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

import re
from typing import List

from ldap.filter import escape_filter_chars


class Status(object):
    ASSIGNED = "ASSIGNED"
    PROVISIONED = "PROVISIONED"
    AVAILABLE = "AVAILABLE"


class LicenseType:
    VOLUME = "Volumenlizenz"
    SINGLE = "Einzellizenz"


def my_string_to_int(num):  # type: (str) -> int
    return int(num) if num else 0


def get_entry_uuid(lo, dn):
    """entryUUID can't be used in simple udm so we have to use ldap here."""
    return lo.get(dn, attr=["entryUUID"])["entryUUID"][0]


def get_special_filter(pattern, attribute_names):  # type: (str, List[str]) -> str
    """this is bluntly copied from school_umc_base but only uses the submatch part.
    todo use this in search"""
    expressions = []
    reg_white_spaces = re.compile(r"\s+")
    for iword in reg_white_spaces.split(pattern or ""):
        # evaluate the subexpression (search word over different attributes)
        sub_expr = []
        # all expressions for a full string match
        iword = escape_filter_chars(iword)
        # all expressions for a substring match
        if not iword:
            iword = "*"
        elif "*" not in iword:
            iword = "*%s*" % iword
        sub_expr += ["(%s=%s)" % (attr, iword) for attr in attribute_names]
        # append to list of all search expressions
        expressions.append("(|%s)" % "".join(sub_expr))
    if not expressions:
        return ""
    return "(&%s)" % "".join(expressions)
