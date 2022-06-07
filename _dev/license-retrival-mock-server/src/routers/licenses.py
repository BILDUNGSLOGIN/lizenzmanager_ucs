""" Endpoints common to both CR1 and CR2 versions """
import json
from pathlib import Path
from typing import Callable, List, Type

from fastapi import APIRouter, Form, HTTPException, Response

from models import (CR1LicensePackageResponse, CR2LicensePackageResponse,
                    Cover, Metadata, MetadataInfo, Query)

router = APIRouter()

VERSIONS_INFO = {
    "CR1": {
        "license_folder": Path("licenses", "cr1"),
        "license_response_model": CR1LicensePackageResponse,
    },
    "CR2": {
        "license_folder": Path("licenses", "cr2"),
        "license_response_model": CR2LicensePackageResponse,
    }
}


def confirm_license(response: Response, package_id: str = Form(...)):
    """
    Mocked endpoint for license confirmation
    Based on the input parameters should be able to return different response codes:
    - 20
    - 208
    - 404
    if package_id ends with "208" or "404" would return the respective code,
    otherwise will return "200"
    """
    if package_id.endswith("208"):
        response.status_code = 208
    elif package_id.endswith("404"):
        response.status_code = 404


def create_get_license_package_endpoint(licenses_folder: Path, response_cls: Type) -> Callable:
    """ Create get_license_package function for the given version """

    def get_license_package(package_id: str = Form(...)):
        """ Mocked endpoint for obtaining licenses """
        package_path = licenses_folder / f"{package_id}.json"
        try:
            with package_path.open(encoding="utf-8") as file:
                licenses = json.load(file)
        except FileNotFoundError:
            raise HTTPException(status_code=404)
        return response_cls(licenses=licenses, package_id=package_id)

    return get_license_package


def acquire_metadata(queries: List[Query]) -> List[MetadataInfo]:
    """ Returns metadata information about the requested products """
    output = []
    for query in queries:
        metadata = Metadata(
            id=query.id,
            title=f"Title of {query.id}",
            publisher="WES",
            coverSmall=Cover(rel="src", href="https://c.wgr.de/i/artikel/60x/WEB-14-124227.jpg"),
            cover=Cover(rel="src", href="https://c.wgr.de/i/artikel/60x/WEB-14-124227.jpg"),
            modified=1630490602000,
            author="Mock Server",
            description="Automatically generated metadata")
        output.append(MetadataInfo(query=query, status=200, data=metadata))
    return output


for version in VERSIONS_INFO.keys():
    # Add metadata acquisition endpoint
    router.add_api_route(f"/{version.lower()}/external/univention/media/query",
                         acquire_metadata, methods=["POST"], tags=[version],
                         response_model=List[MetadataInfo])
    # Add confirmation endpoint to version
    router.add_api_route(f"/{version.lower()}/external/publisher/v2/licensepackage/confirm",
                         confirm_license, methods=["POST"], tags=[version])
    # Add license retrieval endpoint to version
    cls = VERSIONS_INFO[version]["license_response_model"]
    func = create_get_license_package_endpoint(VERSIONS_INFO[version]["license_folder"], cls)
    router.add_api_route(f"/{version.lower()}/external/publisher/v2/licensepackage",
                         func, methods=["GET"], tags=[version], response_model=cls,
                         response_model_exclude_unset=True)
