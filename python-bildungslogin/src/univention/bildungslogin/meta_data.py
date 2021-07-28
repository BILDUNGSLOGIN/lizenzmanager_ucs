# WIP, not tests (!)


import hashlib

from ldap.filter import filter_format
from typing import List, Optional
from ucsschool.lib.models import UdmObject

from utils import Assignment, Status
from univention.udm import UDM, CreateError, NoObject as UdmNoObject


class MetaData:
    def __init__(
        self,
        product_id,
        title=None,
        description=None,
        author=None,
        publisher=None,
        cover=None,
        cover_small=None,
        modified=None,
    ):  # type: (str, str, str, str, str, str, str, str) -> None
        self.product_id = product_id
        self.title = title
        self.description = description
        self.author = author
        self.publisher = publisher
        self.cover = cover
        self.cover_small = cover_small
        self.modified = modified


class MetaDataHandler:
    def __init__(self, lo):
        self.lo = lo
        udm = UDM(lo).version(1)
        self._licenses_mod = udm.get("vbm/licenses")
        self._assignments_mod = udm.get("vbm/assignments")
        self._meta_data_mod = udm.get("vbm/metadata")

    @staticmethod
    def from_udm_obj(udm_obj):  # type: (UdmObject) -> MetaData
        return MetaData(
            product_id=udm_obj.props.vbmProductId,
            title=udm_obj.props.vbmMetaDataTitle,
            description=udm_obj.props.vbmMetaDataDescription,
            author=udm_obj.props.vbmMetaDataAuthor,
            publisher=udm_obj.props.vbmMetaDataPublisher,
            cover=udm_obj.props.vbmMetaDataCover,
            cover_small=udm_obj.props.vbmMetaDataCoverSmall,
            modified=udm_obj.props.vbmMetaDataModified,
        )

    def get_all(self, filter_s=None):  # type: (str) -> List[MetaData]
        assignments = self._meta_data_mod.search(filter_s=filter_s)
        return [MetaDataHandler.from_udm_obj(a) for a in assignments]

    def fetch_meta_data(self, meta_data):  # type: (MetaData) -> None
        """call meta-data api
        todo"""
        pass

    def _get_assignments(self, meta_data):  # type: (MetaData) -> List[Assignment]
        """assignments of license with productID"""
        # get licenses objects from udm with the given product id.
        filter_s = filter_format("(&(vbmProductId=%s))", [meta_data.product_id])
        licenses_of_product = [o for o in self._licenses_mod.search(filter_s)]
        assignments = []
        for udm_license in licenses_of_product:
            # the assignments are placed below the licenses.
            assignments_to_license = self._assignments_mod.search(base=udm_license.dn)
            assignments.extend(
                [
                    Assignment.from_udm_obj(assignment)
                    for assignment in assignments_to_license
                ]
            )
        return assignments

    def number_of_available_licenses(self, meta_data):  # type: (MetaData) -> int
        """count the number of assignments with status available"""
        return len(
            [
                a
                for a in self._get_assignments(meta_data)
                if a.status == Status.AVAILABLE
            ]
        )

    def number_of_provisioned_and_assigned_licenses(
        self, meta_data
    ):  # type: (MetaData) -> int
        """count the number of assignments with status provisioned or assigned"""
        return len(
            [
                a
                for a in self._get_assignments(meta_data)
                if a.status in [Status.PROVISIONED, Status.ASSIGNED]
            ]
        )

    def number_of_expired_licenses(self, meta_data):  # type: (MetaData) -> int
        """count the number of assignments with status expired"""
        return len(
            [
                a
                for a in self._get_assignments(meta_data)
                if a.status in [Status.EXPIRED]
            ]
        )

    def number_of_licenses(self, meta_data):  # type: (MetaData) -> int
        """count the number of assignments"""
        return len(self._get_assignments(meta_data))

    def create(self, meta_data):  # type: (MetaData) -> None
        try:
            udm_obj = self._meta_data_mod.new()
            udm_obj.props.cn = hashlib.sha256(meta_data.product_id).hexdigest()
            udm_obj.props.vbmProductId = meta_data.product_id
            udm_obj.props.vbmMetaDataTitle = meta_data.title
            udm_obj.props.vbmMetaDataDescription = meta_data.description
            udm_obj.props.vbmMetaDataAuthor = meta_data.author
            udm_obj.props.vbmMetaDataPublisher = meta_data.publisher
            udm_obj.props.vbmMetaDataCover = meta_data.cover
            udm_obj.props.vbmMetaDataCoverSmall = meta_data.cover_small
            udm_obj.props.vbmMetaDataModified = meta_data.modified
            udm_obj.save()
        except CreateError as e:
            print(
                "Error creating meta datum for product id {}: {}".format(
                    meta_data.product_id, e
                )
            )

    def save(self, meta_data):  # type: (MetaData) -> None
        # this can be called by fetch_meta_data to update meta-data
        # todo
        pass
