#!/usr/bin/env python
#
# Copyright 2023 Univention GmbH
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
#

from __future__ import print_function
import subprocess
import sys
import logging
import getopt
from univention.udm import UDM
from univention.config_registry.backend import ConfigRegistry

ucr = ConfigRegistry()
ucr.load()

udm_licenses = UDM.admin().version(1).get('bildungslogin/license')
udm_metadata = UDM.admin().version(1).get('bildungslogin/metadata')

# CSV file location
csv_file_name = '/tmp/users.csv'
# Log file location
logfile = '/tmp/get_userlicenses.log'
# Define the log format
log_format = "%(levelname)s %(message)s"

# Define basic configuration
logging.basicConfig(
    # Define logging level
    level=logging.INFO,
    # Declare the object we created to format the log messages
    format=log_format,
    # Declare handlers
    handlers=[
        # logging.FileHandler(logfile),
        logging.StreamHandler(sys.stdout),
    ]
)
logger = logging.getLogger("get_missing_metadata")


def usage():
    helptext = '''
Usage:
    bildungslogin_get_missing_metadata.py [-h|--help] [-f|--fix]
    -h | --help         print this help
    -f | --fix          fix missing metadata
'''
    print(helptext)


def which(program):
    import os
    def is_exe(fpath):
        return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

    fpath, fname = os.path.split(program)
    if fpath:
        if is_exe(program):
            return program
    else:
        for path in os.environ["PATH"].split(os.pathsep):
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return exe_file
    return None


######################################
# Main function
######################################
def main():
    fix_missing = False
    # Argument handling
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hf", ["help", "fix"])
    except getopt.GetoptError as err:
        # print help information and exit:
        print(err)  # will print something like "option -a not recognized"
        usage()
        sys.exit(2)
    for o, a in opts:
        if o in ("-h", "--help"):
            usage()
            sys.exit()
        elif o in ("-f", "--fix"):
            fix_missing = True
            print("Will download missing metadata...")
        else:
            assert False, "unhandled option"
            sys.exit(2)

    logger.info("Loading current licenses and product data...")

    current_license_products = []
    license_data = udm_licenses.search()
    for license_details in license_data:
        if license_details.props.product_id not in current_license_products:
            current_license_products.append(license_details.props.product_id)

    for current_license_product in current_license_products:
        metadata_details = list(udm_metadata.search("bildungsloginProductId={}".format(current_license_product)))
        metadata_available = len(metadata_details) > 0
        if metadata_available:
            logger.debug("Metadata available for " + current_license_product)
        else:
            logger.warn("No Metadata available for " + current_license_product)
            if fix_missing:
                ProcessOutput = subprocess.Popen(
                    ['sudo', 'bildungslogin-media-import', '--config-file', '/etc/bildungslogin/config.ini',
                     current_license_product],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT)
                stdout, stderr = ProcessOutput.communicate()
                if stderr is None:
                    if stdout.startswith("Error"):
                        logger.error(stdout.strip())
                    else:
                        logger.info(stdout.strip())


# Starting to run the code here...
###########################################
if __name__ == "__main__":
    main()
    logger.info("Finished")
