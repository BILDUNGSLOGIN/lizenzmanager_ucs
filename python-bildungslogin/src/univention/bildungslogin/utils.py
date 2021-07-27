from enum import Enum
from ucsschool.lib.models import UdmObject


class Status(Enum):
    ASSIGNED = "ASSIGNED"
    PROVISIONED = "PROVISIONED"
    AVAILABLE = "AVAILABLE"
    EXPIRED = "EXPIRED"


class Assignment:
    def __init__(self, username, licence, time_of_assignment, status):  # type: (str, str, str, Status) -> None
        self.assignee = username
        self.time_of_assignment = time_of_assignment
        self.status = status
        self.licence = licence

    @staticmethod
    def from_udm_obj(udm_obj):  # type: (UdmObject) -> Assignment
        # todo here i actually need to find the parent and get it's license_code, right?
        licence = "something"
        return Assignment(
            username=udm_obj.props.vbmAssignmentAssignee,
            licence=licence,
            time_of_assignment=udm_obj.props.vbmAssignmentTimeOfAssignment,
            status=udm_obj.props.vbmAssignmentStatus,
        )
