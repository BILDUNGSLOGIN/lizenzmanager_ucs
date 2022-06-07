import subprocess

import univention.testing.ucsschool.ucs_test_school as utu
from univention.bildungslogin.license_retrieval import (
    cmd_license_retrieval,
    retrieve_licenses_package
)

TEST_PICKUP = "WES-flW-v2S-jqr"


def test_cli_retrieve_license(license_handler, lo, hostname):
    """Test that a license can be retrieved by the CLI tool bildungslogin-license-retrieval"""
    with utu.UCSTestSchool() as schoolenv:
        ou, _ = schoolenv.create_ou(name_edudc=hostname)
        try:
            subprocess.check_call(
                [
                    "bildungslogin-license-retrieval",
                    "--pickup-number",
                    TEST_PICKUP,
                    "--school",
                    ou,
                    "--config-file",
                    "etc/bildungslogin/config.ini"
                ]
            )
        finally:
            print('test retrieve licenses cli')


def get_config_mock(*args, **kwargs):  # type: (*Any, **Any) -> Dict[str, Any]
    return {
        "client_id": None,
        "client_secret": None,
        "scope": None,
        "auth_server": None,
        "resource_server": None,
    }


def license_retrieval_rest_api_mock():
    return [
        {
            "licenses": [
                {
                    "lizenzcode": "f5sdfsdf-345c-4237-a451-4444736eb011",
                    "product_id": "918-3-16-062213-4",
                    "lizenzanzahl": 14,
                    "lizenzgeber": "VHT",
                    "kaufreferenz": "2014-05-11T01:28:16 -02:00 4572022",
                    "nutzungssysteme": "Antolin",
                    "gueltigkeitsbeginn": "11-05-2021",
                    "gueltigkeitsende": "14-12-2022",
                    "gueltigkeitsdauer": "365 Tage",
                    "sonderlizenz": "Lehrkraft"
                },
                {
                    "lizenzcode": "7bd46a45-345c-4237-a451-4444736eb011",
                    "product_id": "918-3-22-062023-4",
                    "lizenzanzahl": 25,
                    "lizenzgeber": "VHT"
                }
            ],
            "package_id": "VHT-9MV-EYD-iz5"
        }
    ]


def retrieve_license_retrieval_mock(*args, **kwargs):  # type: (*Any, **Any) -> List[Dict[str, Any]]
    return license_retrieval_rest_api_mock()


def parse_args_mock(*args, **kwargs):
    return [TEST_PICKUP, "DEMOSCHOOL"]


def test_cli_import(lo, mocker):
    """Test that a meta data import is possible."""
    mocker.patch.object(cmd_license_retrieval, "get_config", get_config_mock)
    mocker.patch.object(cmd_license_retrieval, "parse_args", parse_args_mock)
    mocker.patch(
        "univention.bildungslogin.license_retrieval.cmd_license_retrieval.retrieve_licenses_package",
        retrieve_license_retrieval_mock,
    )
    mocker.patch("univention.bildungslogin.license_retrieval.get_access_token")
# mh = MetaDataHandler(lo)
# delete_metadata_after_test(TEST_PRODUCT_ID_1)
# delete_metadata_after_test(TEST_PRODUCT_ID_2)
# cmd_license_retrieval.main()
# udm_metadata = mh.get_meta_data_by_product_id(TEST_PRODUCT_ID_1)
# metadata = mh.from_udm_obj(udm_metadata)
# assert metadata.__dict__ == TEST_META_DATA[0]
