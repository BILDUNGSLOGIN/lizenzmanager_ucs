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
    parser.add_argument(
        "--get-all", required=False, help="Get all status information, not just the new.", action="store_true",
    )

    return parser.parse_args(args)


def register_licenses(client_id, client_secret, scope, auth_server, resource_server, licenses):
    while len(licenses) > 0:
        tmp_licenses = []
        for _ in range(0, 101):
            if len(licenses) > 0:
                tmp_licenses.append(licenses.pop(0))

        codes = []
        for license in tmp_licenses:
            codes.append(str(license.props.code))

        codes = dumps(codes)
        if len(codes) > 0:
            access_token = get_access_token(client_id, client_secret, scope, auth_server)
            request = requests.post(
                url=resource_server + "/licensestatus/v1/demand",
                data=codes,
                headers={"Authorization": "Bearer " + access_token,
                         "Content-Type": "application/vnd.de.bildungslogin.licensestatus-demand+json"},
            )
            if request.status_code != 200:
                print("License registration failed.")
                print("Status code: {0}".format(str(request.status_code)))
                print("Error: " + request.content)
            else:
                for license in tmp_licenses:
                    license.props.registered = True
                    license.save()


def update_licenses_status(access_token, resource_server, get_all):
    lo, _ = getAdminConnection()
    udm = UDM(lo).version(2).get('bildungslogin/license')

    request = requests.get(
        url=resource_server + "/licensestatus/v1/data" + ('?filter=all' if get_all else ''),
        headers={"Authorization": "Bearer " + access_token},
    )
    if request.status_code != 200:
        print("Update Status code: " + str(request.status_code))
        print("Body: " + request.content)
    else:
        for update in request.json():
            if 'code' in update:
                print('License code: ' + update['code'])
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


def get_licenses():
    lo, _ = getAdminConnection()
    udm = UDM(lo).version(2).get('bildungslogin/license')
    licenses = udm.search('(!(registered=1))')
    licenses = [license for license in licenses]

    return licenses


def update_licenses(config, args):
    licenses = get_licenses()
    register_licenses(config['client_id'],
                      config['client_secret'],
                      config['scope'],
                      config['auth_server'], config['resource_server'], licenses)
    access_token = get_access_token(config['client_id'],
                                    config['client_secret'],
                                    config['scope'],
                                    config['auth_server'])
    update_licenses_status(access_token, config['resource_server'], args.get_all)


def main():  # type: () -> None
    try:
        args = parse_args()
        update_licenses(get_config(args), args)
    except ScriptError as err:
        print("Script Error: %s" % (err,), file=sys.stderr)
