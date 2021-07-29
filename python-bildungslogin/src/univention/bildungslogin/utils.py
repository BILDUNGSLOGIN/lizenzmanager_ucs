import logging

from enum import Enum


class Status(Enum):
    ASSIGNED = "ASSIGNED"
    PROVISIONED = "PROVISIONED"
    AVAILABLE = "AVAILABLE"
    EXPIRED = "EXPIRED"


class LicenseType(Enum):
    VOLUME = "Volumenlizenz"
    SINGLE = "Einzellizenz"


class Assignment:
    def __init__(self, username, license, time_of_assignment, status):  # type: (str, str, str, Status) -> None
        self.assignee = username
        self.time_of_assignment = time_of_assignment
        self.status = status
        self.license = license


def get_logger():  # type: () -> logging.Logger
    return logging.getLogger(__name__)