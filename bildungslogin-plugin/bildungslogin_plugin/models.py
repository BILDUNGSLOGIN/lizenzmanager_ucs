# -*- coding: utf-8 -*-
from __future__ import annotations

from enum import Enum
from typing import Dict, Set

from pydantic import BaseModel, Field, conset, constr, validator

NonEmptyStr = constr(min_length=1)


_sample_user = {
    "id": "sample_user_id",
    "context": {
        "SchoolA": {"classes": ["Class1", "Class2"], "roles": ["student"]},
        "SchoolB": {"classes": [], "roles": ["staff", "teacher"]},
    },
    "licenses": ["COR-123", "COR-456"],
}


class AssignmentStatus(str, Enum):
    # keep this in sync with python-bildungslogin/src/univention/bildungslogin/utils.py
    ASSIGNED = "ASSIGNED"
    PROVISIONED = "PROVISIONED"
    AVAILABLE = "AVAILABLE"


class SchoolContext(BaseModel):
    """Extra information about a user, e.g. schools and classes attended, roles within each school."""

    classes: Set[NonEmptyStr] = Field(..., description="Class names. Can be none.")
    roles: conset(min_items=1, item_type=NonEmptyStr) = Field(
        ..., description="Roles at the school. Can be more than one."
    )


class User(BaseModel):
    """A user describing with context and license information"""

    id: NonEmptyStr
    first_name: NonEmptyStr
    last_name: NonEmptyStr
    licenses: Set[constr(min_length=1, max_length=255)] = Field(
        ..., description="Licenses assigned to user."
    )
    context: Dict[str, SchoolContext] = Field(
        ...,
        description="School related information: classes and roles within each school. Keys of this "
        "dictionary are the names of schools.",
    )

    class Config:
        schema_extra = dict(example=_sample_user)

    @validator("context")
    def context_not_empty(cls, value: Dict[str, SchoolContext]):
        if not value:
            raise ValueError("The context must not be empty!")
        return value
