from univention.bildungslogin.license_import.cmd_license_import import main as cmd_license_import
from univention.bildungslogin.license_retrieval.cmd_license_retrieval import main as cmd_license_retrieval
from univention.bildungslogin.media_import.cmd_media_import import main as cmd_media_import
from univention.bildungslogin.media_import.cmd_media_update import main as cmd_media_update


def license_import():
    cmd_license_import()


def license_retrieval():
    cmd_license_retrieval()


def media_import():
    cmd_media_import()


def media_update():
    cmd_media_update()
