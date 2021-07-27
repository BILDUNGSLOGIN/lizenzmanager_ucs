from enum import Enum


class Status(Enum):
    ASSIGNED = 1
    PROVISIONED = 2
    AVAILABLE = 3
    EXPIRED = 4


class Assignment:
    def __init__(
        self, username: str, licence: str, time_of_assignment: str, status: Status
    ):
        self.assignee = username
        self.time_of_assignment = time_of_assignment
        self.status = status
        self.licence = licence
