# -*- coding: utf-8 -*-
#
# UCS test
#
# Copyright 2013-2021 Univention GmbH
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

import random

import pytest

##########################################################
# copied from ucs-test to reduce build time dependencies #
# ~/git/ucs/test/ucs-test/univention/testing/strings.py  #
##########################################################

STR_NUMERIC = "0123456789"
STR_ALPHA = "abcdefghijklmnopqrstuvwxyz"
STR_ALPHANUM = STR_ALPHA + STR_NUMERIC
STR_ALPHANUMDOTDASH = STR_ALPHANUM + ".-"

STR_SPECIAL_CHARACTER = "!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~ ´€Ω®½"
STR_UMLAUT = "äöüßâêôûŵẑŝĝĵŷĉ"
STR_UMLAUTNUM = STR_UMLAUT + STR_NUMERIC


@pytest.fixture
def random_string():
    def _random_string(length=10, alpha=True, numeric=True, charset=None, encoding="utf-8"):
        """
        Get specified number of random characters (ALPHA, NUMERIC or ALPHANUMERIC).
        Default is an alphanumeric string of 10 characters length. A custom character set
        may be defined via "charset" as string. The default encoding is UTF-8.
        If length is 0 or negative, an empty string is returned.
        """
        result = ""
        for _ in range(length):
            if charset:
                result += random.choice(charset)
            elif alpha and numeric:
                result += random.choice(STR_ALPHANUM)
            elif alpha:
                result += random.choice(STR_ALPHA)
            elif numeric:
                result += random.choice(STR_NUMERIC)
        return result.encode(encoding)

    return _random_string


@pytest.fixture
def random_name(random_string):
    def _random_name(length=10):
        """
        create random name (1 ALPHA, 8 ALPHANUM, 1 ALPHA)
        """
        return (
            random_string(length=1, alpha=True, numeric=False)
            + random_string(length=(length - 2), alpha=True, numeric=True)
            + random_string(length=1, alpha=True, numeric=False)
        )

    return _random_name


@pytest.fixture
def random_username(random_name):
    def _random_username(length=10):
        return random_name(length)

    return _random_username
