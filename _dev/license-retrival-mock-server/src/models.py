import enum
from typing import List, Optional

from pydantic import AnyHttpUrl, BaseModel, Field, conint


class CR1LicenseSpecialType(str, enum.Enum):
    """ CR1 License special type (sonderlizenz) """
    EMPTY = ""
    DEMO = "Demo"


class CR2LicenseSpecialType(str, enum.Enum):
    """ CR2 License special type (sonderlizenz) """
    DEMO = "Demo"
    TEACHER = "Lehrkraft"


class CR2LicenseType(str, enum.Enum):
    """ License type (lizenztyp), new to CR2 """
    SCHOOL = "Schullizenz"
    GROUP = "Lerngruppenlizenz"
    VOLUME = "Volumenlizenz"
    SINGLE = "Einzellizenz"


class BaseLicense(BaseModel):
    """ Base License model common to every version"""
    lizenzcode: str
    product_id: str
    lizenzgeber: str
    kaufreferenz: Optional[str]
    nutzungssysteme: Optional[str]
    gueltigkeitsbeginn: Optional[str]  # should be date, but licenses can provide empty string
    gueltigkeitsende: Optional[str]  # should be date, but licenses can provide empty string
    gueltigkeitsdauer: Optional[str]


class CR1License(BaseLicense):
    """ License model for the CR1 version """
    lizenzanzahl: conint(gt=0)
    sonderlizenz: Optional[CR1LicenseSpecialType]


class CR1LicensePackageResponse(BaseModel):
    """ License package response for CR1 version """
    licenses: List[CR1License]
    package_id: str


class CR2License(BaseLicense):
    """ License model for the CR2 version """
    school_id: Optional[str] = Field(..., alias="school_ID")
    lizenzanzahl: conint(ge=0)
    sonderlizenz: Optional[CR2LicenseSpecialType]
    lizenztyp: CR2LicenseType


class CR2LicensePackageResponse(BaseModel):
    """ License package response for CR2 version """
    licenses: List[CR2License]
    package_id: str


class Query(BaseModel):
    """ Query for the request """
    id: str


class Cover(BaseModel):
    """ Info about a cover """
    rel: str
    href: AnyHttpUrl


class Metadata(BaseModel):
    """ Metadata of the product """
    id: str
    title: str
    publisher: str
    cover_small: Cover = Field(..., alias="coverSmall")
    cover: Cover
    modified: int
    author: str
    description: str


class MetadataInfo(BaseModel):
    """ Metadata response for a single product """
    query: Query
    status: int
    data: Metadata
