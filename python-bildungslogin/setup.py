#!/usr/bin/python3
# -*- coding: utf-8 -*-
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
# Sample debian/rules that uses debhelper.
# GNU copyright 1997 to 1999 by Joey Hess.


import io
from email.utils import parseaddr

from debian.changelog import Changelog
from debian.deb822 import Deb822
from setuptools import setup

dch = Changelog(io.open("debian/changelog", "r", encoding="utf-8"))
dsc = Deb822(io.open("debian/control", "r", encoding="utf-8"))
realname, email_address = parseaddr(dsc["Maintainer"])

setup(
    packages=[
        "univention",
        "univention.bildungslogin",
        "univention.bildungslogin.license_import",
        "univention.bildungslogin.media_import",
        "univention.bildungslogin.license_retrieval",
        "univention.bildungslogin.license_status_update"
    ],
    package_dir={"": "src"},
    entry_points={
        "console_scripts": [
            "bildungslogin-license-import=univention.bildungslogin.license_import.cmd_license_import:main",
            "bildungslogin-media-import=univention.bildungslogin.media_import.cmd_media_import:main",
            "bildungslogin-media-update=univention.bildungslogin.media_import.cmd_media_update:main",
            "bildungslogin-license-retrieval=univention.bildungslogin.license_retrieval.cmd_license_retrieval:main",
        ]
    },
    url="https://www.univention.de/",
    license="GNU Affero General Public License v3",
    name=dch.package,
    description='Python libs for the "Bildungslogin"',
    version=dch.version.full_version,
    maintainer=realname,
    maintainer_email=email_address,
)
