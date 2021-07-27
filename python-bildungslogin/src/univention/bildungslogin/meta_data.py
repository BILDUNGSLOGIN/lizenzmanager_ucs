import hashlib

from ldap.filter import filter_format
from typing import List, Optional

from utils import Assignment, Status
from univention.udm import UDM, CreateError, NoObject as UdmNoObject
from univention.management.console.ldap import get_machine_connection


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
    ):  # type: (str, Optional[str], Optional[str], Optional[str], Optional[str], Optional[str], Optional[str]) -> None
        """in the beginning only have the product_id"""
        self.product_id = product_id
        self.title = title
        self.description = description
        self.author = author
        self.publisher = publisher
        self.cover = cover
        self.cover_small = cover_small

        # todo das ist eher unguenstig.
        lo, po = get_machine_connection(write=True)
        udm = UDM(lo).version(1)
        self._licences_mod = udm.get("vbm/licences")
        self._meta_data_mod = udm.get("vbm/metadata")
        self._assignments_mod = udm.get("vbm/assignments")
        self.udm_obj = self._get_udm_object()

    def _get_udm_object(self):
        filter_s = filter_format("(vbmProductId=%s)", [self.product_id])
        return [o for o in self._licences_mod.search(filter_s)][0]

    def fetch_meta_data(self):
        """call meta-data api"""
        pass

    def _get_assignments(self):  # type: () -> List[Assignment]
        """assignments of licence with productID"""
        # 1) get all licences with productid
        filter_s = filter_format("(&(vbmProductId=%s))", [self.product_id])
        licences_of_product = [o for o in self._licences_mod.search(filter_s)]
        # 2) count get the leaves
        # todo check can i do this in one step? -> this looks expensive
        # this would be easy if vbmassignment would have the vbmlicence
        assignments = []
        for udm_licence in licences_of_product:
            assignments_to_licence = self._assignments_mod.search(base=udm_licence.dn)
            for assignment in assignments_to_licence:
                assignments.append(Assignment(status=assignment.props.vbmAssignmentStatus,
                 time_of_assignment=assignment.props.vbmAssignmentTimeOfAssignment,
                  username=assignment.props.vbmAssignmentAssignee,
                  licence=udm_licence.props.vbmLicenceCode))
        return assignments

    @property
    def number_of_available_licences(self):  # type: () -> int
        """count the number of assignments with status available"""
        return len([a for a in self._get_assignments() if a.status == Status.AVAILABLE])

    @property
    def number_of_provisioned_and_assigned_licences(self):  # type: () -> int
        """count the number of assignments with status provisioned or assigned"""
        return len([a for a in self._get_assignments() if a.status in [Status.PROVISIONED, Status.ASSIGNED]])

    @property
    def number_of_expired_licences(self):  # type: () -> int
        """count the number of assignments with status expired"""
        return len([a for a in self._get_assignments() if a.status in [Status.EXPIRED]])

    @property
    def number_of_licences(self):  # type: () -> int
        """count the number of assignments"""
        return len(self._get_assignments())

    def save(self):
        # The cn of vbmMetaDatum will be a hash of the vbmProductId.
        cn = hashlib.sha256(self.product_id)
