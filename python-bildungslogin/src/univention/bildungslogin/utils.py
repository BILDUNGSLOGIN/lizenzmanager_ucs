from enum import Enum


class Status(Enum):
    ASSIGNED = "ASSIGNED"
    PROVISIONED = "PROVISIONED"
    AVAILABLE = "AVAILABLE"
    EXPIRED = "EXPIRED"


class Assignment:
    def __init__(self, username, license, time_of_assignment, status):  # type: (str, str, str, Status) -> None
        self.assignee = username
        self.time_of_assignment = time_of_assignment
        self.status = status
        self.license = license
