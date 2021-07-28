# WIP, not tests (!)


from time import time
from uuid import uuid4

from ldap.filter import filter_format
from typing import List
from univention.udm import UDM
from univention.udm.exceptions import CreateError

from licence import Licence
from utils import Status, Assignment


class LicenceAssignmentHandler:
    def __init__(self, lo):
        self.lo = lo
        udm = UDM(lo).version(1)
        self._licences_mod = udm.get("vbm/licences")
        self._assignments_mod = udm.get("vbm/assignments")
        self._users_mod = udm.get("users/user")

    def get_all(self, filter_s=None):  # type: (str) -> List[Assignment]
        assignments = self._assignments_mod.search(filter_s=filter_s)
        return [Assignment.from_udm_obj(a) for a in assignments]

    def get_all_assignments_for_user(self, username):  # type: (str) -> List[Assignment]
        filter_s = filter_format("(vbmAssignmentAssignee=%s)", [username])
        assignments = self._assignments_mod.search(filter_s)
        return [Assignment.from_udm_obj(a) for a in assignments]

    def get_assignments_for_product_id_for_user(
        self, username, product_id
    ):  # type: (str, str) -> List[Assignment]
        # do we need this?
        filter_s = filter_format("(vbmProductId=%s)", [product_id])
        udm_licences = self._licences_mod.search(filter_s)
        assignments = []
        for udm_licence in udm_licences:
            filter_s = filter_format("(vbmAssignmentAssignee=%s)", [username])
            udm_assignment = self._assignments_mod.search(
                base=udm_licence.dn, filter_s=filter_s
            )
            assignments.append(Assignment.from_udm_obj(udm_assignment))
        return [Assignment.from_udm_obj(a) for a in assignments]

    def assign_to_licence(self, licence, username):  # type: (Licence, str) -> bool
        filter_s = filter_format("(vbmLicenceCode=%s)", [licence])
        udm_licence = [o for o in self._licences_mod.search(filter_s)][0]
        # can i do this better? i only have the uid...
        filter_s = filter_format("(uid=%s)", [username])
        users = [u for u in self._users_mod.search(filter_s)]
        if not users:
            raise ValueError("Not user with username {}".format(username))
        if udm_licence.props.vbmLicenceSchool not in users[0].props.school:
            raise ValueError(
                "Licence can't be assigned to user in school {}".format(
                    users[0].props.school
                )
            )

        try:
            assignment = self._assignments_mod.new()
            assignment.props.cn = uuid4()
            assignment.position = udm_licence.dn
            assignment.props.vbmAssignmentAssignee = username
            assignment.props.vbmAssignmentTimeOfAssignment = time()  # todo
            assignment.props.vbmAssignmentStatus = Status.ASSIGNED
            assignment.save()
        except CreateError as e:
            print(
                "Error while assigning {} to {}: {}".format(
                    licence.licence_code, username, e
                )
            )
            return False
        return True

    def assign_users_to_licences(
        self, licences, usernames
    ):  # type: (List[str], List[str]) -> None
        """Eine Lizenz kann nur zugewiesen werden,
        wenn die Menge an Lizenzen ausreicht, um allen Benutzern eine Lizenz zuzuweisen.
        """
        if len(licences) >= len(usernames):
            raise ValueError(
                "The number of licences must be >= the users the licence codes!"
            )
        for username, licence in zip(usernames, licences):
            # todo ...
            self.assign_to_licence(licence, username)

    def change_licence_status(
        self, licence, username, status
    ):  # type: (str, str, str) -> bool
        # can change from available to assigned if a username is provided
        # or from available to provisioned
        # todo matrix
        # username has to be present except if licence expired (or valid-date)
        """search for licence with licence id and user with username and change the status
        -> if a user has more than one licence, do we simply change the first? what if that's
        not possible?
        -> we take any licence
        """
        if status not in [s.value for s in Status]:
            raise ValueError("Invalid status {}:".format(status))
        filter_s = filter_format("(vbmLicenceCode)", [licence])
        try:
            licence = [o for o in self._licences_mod.search(filter_s)][0]
        except KeyError:
            print("No licence with code {} was found!".format(licence))
            return False
        filter_s = filter_format("(vbmAssignmentAssignee)", [username])
        try:
            assignment = [
                a
                for a in self._assignments_mod.search(
                    base=licence.dn, filter_s=filter_s
                )
            ][0]
        except KeyError:
            print("No assignment {} -> {} was found!".format(licence, username))
            return False
        assignment.props.vbmAssignmentStatus = status
        assignment.save()
        return True
