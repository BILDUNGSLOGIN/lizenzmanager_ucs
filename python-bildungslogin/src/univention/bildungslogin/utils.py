from enum import Enum


class Status(Enum):
    ASSIGNED = 1
    PROVISIONED = 2
    AVAILABLE = 3
    EXPIRED = 4


class Assignment:
    def __init__(self, username, licence, time_of_assignment, status):  # type: (str, str, str, Status) -> None
        self.assignee = username
        self.time_of_assignment = time_of_assignment
        self.status = status
        self.licence = licence
