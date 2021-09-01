# -*- coding: utf-8 -*-
import pytest

from bildungslogin_plugin.models import User


def test_user_with_valid_attributes(valid_user_kwargs):
    kwargs = valid_user_kwargs()
    user = User(**kwargs)
    assert user.dict() == kwargs


@pytest.mark.parametrize(
    "test_data", (
        ("id", ""),
        ("first_name", ""),
        ("last_name", ""),
        ("licenses", {""}),
        ("context", {}),
    )
)
def test_user_attribute_validation(test_data, valid_user_kwargs):
    attr, bad_value = test_data
    kwargs = valid_user_kwargs()
    kwargs[attr] = bad_value
    with pytest.raises(ValueError):
        User(**kwargs)
