#!/usr/share/ucs-test/runner /usr/bin/py.test -slv
# -*- coding: utf-8 -*-

## desc: Execute unittests
## exposure: safe
## tags: [bildungslogin]
## roles: [domaincontroller_master, domaincontroller_backup, domaincontroller_slave]
## packages: [python-bildungslogin]

import pytest


def test_unittests():
    """Execute unittests"""
    retcode = pytest.main(["-lvvx", "unittests"])
    assert retcode == 0
