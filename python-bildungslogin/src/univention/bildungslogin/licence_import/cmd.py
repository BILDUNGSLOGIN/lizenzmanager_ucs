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

import argparse

from univention.bildungslogin.licence_import import import_licences


def parse_args():  # type: () -> argparse.Namespace
    parser = argparse.ArgumentParser(description='Import media licences')
    parser.add_argument('--licence-file', help='Path to the licence file which should be imported')
    parser.add_argument('--school', help='School abbreviation for which the licence should be imported')
    args = parser.parse_args()
    return args


def main():  # type: () -> None
    args = parse_args()
    import_licences(args.licence_file, args.school)


if __name__ == '__main__':
    main()
