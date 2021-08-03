import datetime


class Status:
    ASSIGNED = "ASSIGNED"
    PROVISIONED = "PROVISIONED"
    AVAILABLE = "AVAILABLE"


class LicenseType:
    VOLUME = "Volumenlizenz"
    SINGLE = "Einzellizenz"


# todo move me
class Assignment(object):
    def __init__(self, username, license, time_of_assignment, status):
        # type: (str, str, str, Status) -> None
        self.assignee = username
        self.time_of_assignment = time_of_assignment
        self.status = status
        self.license = license


def parse_raw_license_date(date_str):  # type: (str) -> datetime.datetime
    return datetime.datetime.strptime(date_str, "%d-%m-%Y")
