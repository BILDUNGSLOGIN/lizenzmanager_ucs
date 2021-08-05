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

from univention.bildungslogin.handlers import BiloCreateError
from univention.bildungslogin.license_import import import_license, load_license_file


def parse_args():  # type: () -> argparse.Namespace
    parser = argparse.ArgumentParser(description="Import media licenses")
    parser.add_argument(
        "--license-file", required=True, help="Path to the license file which should be imported"
    )
    parser.add_argument(
        "--school", required=True, help="School abbreviation for which the license should be imported"
    )
    args = parser.parse_args()
    return args


def import_licenses(license_file, school):
    licenses = load_license_file(license_file, school)
    errors = False
    for license in licenses:
        try:
            import_license(license)
        except BiloCreateError as exc:
            errors = True
            print(
                'Warning: License "{}" could not be imported due to the following error \n{}'.format(
                    license.license_code, exc
                ),
                file=sys.stderr,
            )
    if errors:
        print("Error: Not all licenses were imported successful", file=sys.stderr)
        sys.exit(1)


def main():  # type: () -> None
    args = parse_args()
    import_licenses(args.license_file, args.school)


if __name__ == "__main__":
    main()
