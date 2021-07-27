from time import time
from typing import List
from licence import Licence
from utils import Status, Assignment


class LicenceManager:


    @staticmethod
    def get_all_assignments_for_user(username):  # type: (str) -> List[Assignment]
        """&(vbmAssignmentAssignee=uid)(vbmAssignmentStatus!=...)"""
        pass

    @staticmethod
    def get_assignments_for_product_id_for_user(username):  # type: (str) -> List[Assignment]
        """&(vbmAssignmentAssignee=uid)(vbmAssignmentStatus!=...) below sub"""
        # do we need this?
        pass

    @staticmethod
    def assign_to_licence(licence, username):  # type: (str, str) -> bool
        # licence is still valid, status is ok
        # check if school is ok
        # create assignment in layer below
        assignment = Assignment(
            username=username,
            licence=licence,
            time_of_assignment=str(time()),
            status=Status.ASSIGNED,
        )
        return True

    @staticmethod
    def assign_users_to_licences(licences, usernames):  # type: (List[Licence], List[str]) -> None
        """Eine Lizenz kann nur zugewiesen werden,
        wenn die Menge an Lizenzen ausreicht, um allen Benutzern eine Lizenz zuzuweisen.
        -> this is more like"""
        user_counter = 0
        # this will raise an exception in udm
        assert len(licences) >= len(usernames)
        for username, licence in zip(usernames, licences):
            assigned = LicenceManager.assign_to_licence(licence.licence_code, username)
            if assigned:
                print(
                    "log something about assigning {} to {}".format(licence.meta_data.title, username)
                )
                user_counter += 1

    @staticmethod
    def change_licence_status(licence_id, username, status):  # type: (str, str, str) -> bool
        # can change from available to assigned if a username is provided
        # or from available to provisioned
        # todo matrix
        # username has to be present except if licence expired (or valid-date)

        """search for licence with licence id and user with username and change the status
        -> if a user has more than one licence, do we simply change the first? what if that's
        not possible?
        -> we take any licence
        """
