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
import pytest

from univention.udm import UDM


@pytest.fixture(scope="session")
def udm():
    return UDM.admin().version(1)


@pytest.fixture()
def create_metadata(udm):

    created_metadata = []

    def _create_metadata(
        product_id,
        modified="2000-01-01",
        title="",
        description="",
        author="",
        publisher="",
        cover="",
        cover_small="",
    ):
        metadata = udm.get("vbm/metadata").new()
        metadata.props.product_id = product_id
        metadata.props.modified = modified
        metadata.props.title = title
        metadata.props.description = description
        metadata.props.author = author
        metadata.props.publisher = publisher
        metadata.props.cover = cover
        metadata.props.cover_small = cover_small
        metadata.save()
        created_metadata.append(metadata)
        return metadata

    yield _create_metadata

    for metadata_obj in created_metadata:
        metadata_obj.delete()


@pytest.fixture()
def create_license(udm):

    created_licenses = []

    def _create_license(
        code,
        product_id,
        quantity,
        school,
        validity_start_date="2000-01-01",
        validity_end_date="2000-01-01",
        delivery_date="2000-01-01",
        ignored="0",
        provider="univention",
        purchasing_reference="",
        utilization_systems="",
        validity_duration="",
        special_type="",
    ):
        license_obj = udm.get("vbm/license").new()
        license_obj.props.code = code
        license_obj.props.product_id = product_id
        license_obj.props.quantity = quantity
        license_obj.props.school = school
        license_obj.props.validity_start_date = validity_start_date
        license_obj.props.validity_end_date = validity_end_date
        license_obj.props.delivery_date = delivery_date
        license_obj.props.ignored = ignored
        license_obj.props.provider = provider
        license_obj.props.purchasing_reference = purchasing_reference
        license_obj.props.utilization_systems = utilization_systems
        license_obj.props.validity_duration = validity_duration
        license_obj.props.special_type = special_type
        license_obj.save()
        created_licenses.append(license_obj)
        return license_obj

    yield _create_license

    for license_obj in created_licenses:
        # TODO: Change if https://forge.univention.org/bugzilla/show_bug.cgi?id=53620 is CLOSED
        license_obj._orig_udm_object.remove(True)
