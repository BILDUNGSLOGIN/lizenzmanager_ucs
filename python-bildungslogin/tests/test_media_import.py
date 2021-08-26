# -*- coding: utf-8 -*-

import datetime

import attr
import pytest
from jsonschema import ValidationError, validate

from univention.bildungslogin.media_import import MEDIA_SCHEMA, load_media
from univention.bildungslogin.models import MetaData

test_metadata_raw = {
    "status": 200,
    "query": {"id": "urn:bilo:medium:COR-9783060658336"},
    "data": {
        "publisher": "Cornelsen",
        "coverSmall": {
            "href": "https://static.cornelsen.de/media/9783060658336/9783060658336_COVER_STD_B110_X2.png",
            "rel": "src",
        },
        "description": "Entdecken und verstehen - Sch\xfclerbuch als E-Book - 7. Schuljahr",
        "title": "Entdecken und verstehen",
        "author": "",
        "cover": {
            "href": "/media/9783060658336/9783060658336_COVER_STD_B160_X2.png",
            "rel": "src",
        },
        "modified": 1628258416000,
        "id": "urn:bilo:medium:COR-9783060658336",
    },
}

test_metadata = MetaData(
    product_id="urn:bilo:medium:COR-9783060658336",
    title="Entdecken und verstehen",
    description="Entdecken und verstehen - Sch\xfclerbuch als E-Book - 7. Schuljahr",
    author="",
    publisher="Cornelsen",
    cover="",
    cover_small="https://static.cornelsen.de/media/9783060658336/9783060658336_COVER_STD_B110_X2.png",
    modified=datetime.date(2021, 8, 6),
)


def test_load_media():
    """Test that meta data loaded from dict are the same as a corresponding python object."""
    metadata = load_media(test_metadata_raw)
    assert metadata.__dict__ == attr.asdict(test_metadata)


def test_media_schema():
    """Test that the schema works with our sample test_metadata_raw. We assume the test_metadata_raw to be valid"""
    validate(instance=test_metadata_raw["data"], schema=MEDIA_SCHEMA)


@pytest.mark.parametrize("field_name", ["id", "title", "publisher", "cover", "coverSmall", "modified"])
def test_media_schema_validation_required_fails(field_name):
    """A missing value in the media should raise a ValidationError"""
    test_media_broken = test_metadata_raw["data"].copy()
    del test_media_broken[field_name]
    with pytest.raises(ValidationError):
        validate(instance=test_media_broken, schema=MEDIA_SCHEMA)


@pytest.mark.parametrize(
    "field_name",
    ["author", "description"],
)
def test_media_schema_validation_optionals(field_name):
    """An optional value can be left out from the media"""
    test_license_broken = test_metadata_raw["data"].copy()
    del test_license_broken[field_name]
    validate(instance=test_license_broken, schema=MEDIA_SCHEMA)


@pytest.mark.parametrize(
    "definition_name,property_name",
    zip(
        ["Publisher", "Description", "Author", "Title", "MediumIdentifier"],
        ["publisher", "description", "author", "title", "id"],
    ),
)
def test_media_schema_validation_fails_for_incorrect_length(definition_name, property_name):
    """Test a violation of string length raises a ValidationError."""
    media_definition_value = MEDIA_SCHEMA["definitions"][definition_name]
    test_media_broken = test_metadata_raw["data"].copy()
    if "maxLength" in media_definition_value:
        while len(test_media_broken[property_name]) < media_definition_value["maxLength"] + 1:
            test_media_broken[property_name] += "t"
        with pytest.raises(ValidationError):
            validate(instance=test_media_broken, schema=MEDIA_SCHEMA)
    if "minLength" in media_definition_value:
        test_media_broken[property_name] = test_media_broken[property_name][
            : min(media_definition_value["minLength"] - 1, 0)
        ]
        with pytest.raises(ValidationError):
            validate(instance=test_media_broken, schema=MEDIA_SCHEMA)
