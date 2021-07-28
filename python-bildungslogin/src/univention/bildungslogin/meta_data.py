# WIP, not tests (!)


from ldap.filter import filter_format
from typing import List
from ucsschool.lib.models import UdmObject
from ucsschool.lib.models.base import LoType

from utils import Assignment, Status
from univention.udm import UDM, CreateError
from assignment_handler import AssignmentHandler


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
    def __init__(self, lo):  # type: (LoType) -> None
        self.lo = lo
        udm = UDM(lo).version(1)
        self._licenses_mod = udm.get("vbm/license")
        self._assignments_mod = udm.get("vbm/assignment")
        self._meta_data_mod = udm.get("vbm/metadatum")
        self.ah = AssignmentHandler(self.lo)

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

    def from_dn(self, dn):  # type: (str) -> MetaData
        udm_license = self._meta_data_mod.get(dn)
        return self.from_udm_obj(udm_license)

    def get_all(self, filter_s=None):  # type: (str) -> List[MetaData]
        assignments = self._meta_data_mod.search(filter_s=filter_s)
        return [MetaDataHandler.from_udm_obj(a) for a in assignments]

    def fetch_meta_data(self, meta_data):  # type: (MetaData) -> None
        """call meta-data api
        todo"""
        # something like
        # res = self.meta_data_api_client.get([
        #     {
        #         "id": meta_data.product_id
        #     }
        # ])
        # ... update or create udm object
        pass

    def get_assignments_for_license(self, dn):  # type: (str) -> List[Assignment]
        """Get all assignments which are placed as leaves under the license."""
        assignments_from_license = self._assignments_mod.search(base=dn)
        return [
                self.ah.from_udm_obj(assignment)
                for assignment in assignments_from_license
            ]

    def get_licenses_udm_object_by_product_id(self, product_id):  # type: (str) -> UdmObject
        filter_s = filter_format("(&(vbmProductId=%s))", [product_id])
        return [o for o in self._licenses_mod.search(filter_s)]

    def get_assignments_for_meta_data(self, meta_data):  # type: (MetaData) -> List[Assignment]
        """assignments of license with productID"""
        # get licenses objects from udm with the given product id.
        licenses_of_product = self.get_licenses_udm_object_by_product_id(meta_data.product_id)
        assignments = []
        for udm_license in licenses_of_product:
            # get the assignments placed below the licenses.
            assignments.extend(self.get_assignments_for_license(udm_license.dn))

        return assignments

    def get_number_of_available_licenses(self, meta_data):  # type: (MetaData) -> int
        """count the number of assignments with status available"""
        return len(
            [
                a
                for a in self.get_assignments_for_meta_data(meta_data)
                if a.status == Status.AVAILABLE
            ]
        )

    def get_number_of_provisioned_and_assigned_licenses(
        self, meta_data
    ):  # type: (MetaData) -> int
        """count the number of assignments with status provisioned or assigned"""
        return len(
            [
                a
                for a in self.get_assignments_for_meta_data(meta_data)
                if a.status in [Status.PROVISIONED, Status.ASSIGNED]
            ]
        )

    def get_number_of_expired_licenses(self, meta_data):  # type: (MetaData) -> int
        """count the number of assignments with status expired"""
        return len(
            [
                a
                for a in self.get_assignments_for_meta_data(meta_data)
                if a.status in [Status.EXPIRED]
            ]
        )

    def get_number_of_licenses(self, meta_data):  # type: (MetaData) -> int
        """count the number of assignments"""
        return len(self.get_assignments_for_meta_data(meta_data))

    def create(self, meta_data):  # type: (MetaData) -> None
        try:
            udm_obj = self._meta_data_mod.new()
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

    def get_meta_data_by_product_id(self, product_id):  # type: (str) -> UdmObject
        filter_s = filter_format("(&(vbmProductId=%s))", [product_id])
        try:
            return [o for o in self._meta_data_mod.search(filter_s)][0]
        except KeyError:
            print("Meta data object with product id {} does not exist!".format(product_id))

    def save(self, meta_data):  # type: (MetaData) -> None
        udm_meta_data = self.get_meta_data_by_product_id(meta_data.product_id)
        # todo update udm_meta_data
        udm_meta_data.save()
