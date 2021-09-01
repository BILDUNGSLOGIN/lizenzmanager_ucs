# -*- coding: utf-8 -*-
from __future__ import annotations

import abc

from .models import User


class ConfigurationError(ConnectionError):
    ...


class DbConnectionError(ConnectionError):
    ...


class UserNotFound(Exception):
    ...


class DbBackend(abc.ABC):
    """Base class for LDAP database access."""

    def __init__(self, *args, **kwargs):
        """
        :raises ConfigurationError: when the data passed in `args` or `kwargs` is not as expected
        """
        ...

    async def connection_test(self) -> None:
        """
        Test DB connection.

        :return: nothing if successful or raises an error
        :raises DbConnectionError: if connecting failed
        """
        raise NotImplementedError  # pragma: no cover

    async def get_user(self, username: str) -> User:
        """
        Load a user object and its school, class and license information from LDAP.

        :param str username: the `uid` LDAP attribute
        :return: User object
        :rtype: User
        :raises ConnectionError: when a problem with the connection happens
        :raises UserNotFound: when a user could not be found in the DB
        """
        raise NotImplementedError  # pragma: no cover
