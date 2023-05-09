from __future__ import print_function

import argparse
import sys
from datetime import datetime

import requests
from json import dumps

from typing import List, Optional
from ldap.filter import filter_format

from univention.admin.uldap import getAdminConnection
from univention.udm import UDM

from ..license_retrieval.cmd_license_retrieval import get_config, get_access_token
from ..exceptions import ScriptError


def parse_args(args=None):  # type: (Optional[List[str]]) -> argparse.Namespace
    parser = argparse.ArgumentParser(description="Retrieve license statuses")
    parser.add_argument(
        "--config-file", required=False, help="A path to a file which contains all config options for this command."
    )

    return parser.parse_args(args)


def register_licenses(access_token, resource_server):
    lo, _ = getAdminConnection()
    udm = UDM(lo).version(2).get('bildungslogin/license')
    licenses = udm.search('(!(registered=1))')
    licenses = [license for license in licenses]

    codes = []
    for license in licenses:
        codes.append(str(license.props.code))

    codes = dumps(codes)
    if len(codes) > 0:
        request = requests.get(
            url=resource_server + "/demand",
            data=codes,
            headers={"Authorization": "Bearer " + access_token,
                     "Content-Type": "application/vnd.de.bildungslogin.licensestatus-demand+json"},
        )
        if request.status_code != 200:
            print("License registration failed.")
        else:
            for license in licenses:
                license.props.registered = True
                license.save()


def update_licenses_status(access_token, resource_server):
    lo, _ = getAdminConnection()
    udm = UDM(lo).version(2).get('bildungslogin/license')

    request = requests.get(
        url=resource_server + "/data",
        headers={"Authorization": "Bearer " + access_token},
    )
    for update in request.json():
        if 'code' in update:
            filter_s = filter_format("(code=%s)", [update['code']])
            licenses = udm.search(filter_s)
            for license in licenses:
                if 'activation' in update:
                    if update['activation'] == 'ACTIVATED':
                        license.props.usage_status = True
                    elif update['activation'] == 'NOT_ACTIVATED':
                        license.props.usage_status = False
                if 'validity' in update:
                    if update['validity'] == 'VALID':
                        license.props.validity_status = True
                    elif update['validity'] == 'INVALID':
                        license.props.validity_status = False
                if 'expireDate' in update:
                    license.props.expiry_date = datetime.utcfromtimestamp(update['expireDate'] / 1000).date()
                license.save()


def update_licenses(config):
    access_token = get_access_token(config['client_id'],
                                    config['client_secret'],
                                    config['scope'],
                                    config['auth_server'])
    register_licenses(access_token, config['resource_server'])
    update_licenses_status(access_token, config['resource_server'])


def main():  # type: () -> None
    try:
        args = parse_args()
        update_licenses(get_config(args))
    except ScriptError as err:
        print("Script Error: %s" % (err,), file=sys.stderr)
