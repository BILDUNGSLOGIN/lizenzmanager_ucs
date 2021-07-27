from typing import List

from utils import Assignment


class MetaData:
    def __init__(
        self,
        product_id,
        title,
        description,
        author,
        publisher,
        cover,
        cover_small,
    ):  # type: (str, str, str, str, str, str, str) -> None
        self.product_id = product_id
        self.title = title
        self.description = description
        self.author = author
        self.publisher = publisher
        self.cover = cover
        self.cover_small = cover_small

        self._get_assignments()

    def _get_assignments(self):  # type: () -> List[Assignment]
        """assignments of licence with productID"""
        return []

    @property
    def number_of_available_licences(self):  # type: () -> int
        """count the number of assignments with status available"""
        return 0

    @property
    def number_of_provisioned_and_assigned_licences(self):  # type: () -> int
        """count the number of assignments with status provisioned or assigned"""
        return 0

    @property
    def number_of_expired_licences(self):  # type: () -> int
        """count the number of assignments with status expired"""
        return 0

    @property
    def number_of_licences(self):  # type: () -> int
        """count the number of assignments"""
        return 0
