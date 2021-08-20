# -*- coding: utf-8 -*-

import datetime

import attr

from univention.bildungslogin.media_import import load_media
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
