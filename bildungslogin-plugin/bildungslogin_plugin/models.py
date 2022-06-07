# -*- coding: utf-8 -*-
from __future__ import annotations

from enum import Enum
from pydantic import BaseModel, Field, conlist, constr, validator
from typing import Dict, List, Optional

NonEmptyMaxLenStr = constr(min_length=1, max_length=255)


class AssignmentStatus(str, Enum):
    # keep this in sync with python-bildungslogin/src/univention/bildungslogin/utils.py
    ASSIGNED = "ASSIGNED"
    PROVISIONED = "PROVISIONED"
    AVAILABLE = "AVAILABLE"


class UserRole(str, Enum):
    """ User roles """
    STUDENT = "student"
    TEACHER = "teacher"
    STAFF = "staff"


class Workgroup(BaseModel):
    """ User workgroup """
    name: NonEmptyMaxLenStr = Field(..., description="Name of the workgroup")
    id: NonEmptyMaxLenStr = Field(..., description="School-unique ID of the workgroup")
    licenses: Optional[List[NonEmptyMaxLenStr]] = \
        Field(None, description="License-Codes attached to the workgroup")


class Class(BaseModel):
    """ User class """
    name: NonEmptyMaxLenStr = Field(..., description="Name of the class")
    id: NonEmptyMaxLenStr = Field(..., description="School-unique ID of the class")
    licenses: Optional[List[NonEmptyMaxLenStr]] = \
        Field(None, description="License-Codes attached to the class")


class SchoolContext(BaseModel):
    """
    Extra information about a user,
    e.g. schools and classes attended, roles within each school.
    """
    school_authority: Optional[NonEmptyMaxLenStr] = \
        Field(None, description="School authority")
    school_code: NonEmptyMaxLenStr = \
        Field(..., description="A school abbreviation that the publisher can assign freely")
    school_identifier: Optional[NonEmptyMaxLenStr] = \
        Field(None, description="A school abbreviation that is officially assigned (state/federal)")
    school_name: Optional[NonEmptyMaxLenStr] = \
        Field(None, description="A self-assigned name for the school")
    classes: List[Class] = \
        Field(..., description="Classes of the school, the user is related to")
    roles: conlist(min_items=1, item_type=UserRole) = \
        Field(..., description="Roles in the school, the user is related to")
    workgroups: List[Workgroup] = \
        Field(..., description="Workgroups of the school, the user is related to")
    licenses: Optional[List[NonEmptyMaxLenStr]] = \
        Field(None, description="Licenses attached to the school")


class User(BaseModel):
    """ A user describing with context and license information """
    id: NonEmptyMaxLenStr = Field(..., description="User-ID")
    first_name: Optional[NonEmptyMaxLenStr] = Field(None, description="First Name")
    last_name: Optional[NonEmptyMaxLenStr] = Field(None, description="Last Name")
    licenses: Optional[List[NonEmptyMaxLenStr]] = \
        Field(None, description="Licenses assigned to user")
    context: Dict[NonEmptyMaxLenStr, SchoolContext] = \
        Field(..., description=("School related information: classes and roles within "
                                "each school. Keys of this dictionary is the unique school ID. "
                                "Must contain at least one element"))

    @validator("context")
    def context_not_empty(cls, value: Dict[NonEmptyMaxLenStr, SchoolContext]):
        """
        Validate the context:
        - Check that there's at least one school context attached
        """
        if not value:
            raise ValueError("The context must not be empty!")
        return value
