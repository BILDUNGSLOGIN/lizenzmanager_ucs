from typing import Dict, List

from pydantic import BaseModel, Field, conlist, constr

sample_user = {
    "id": "sample_user_id",
    "context": {
        "schoolA": {"classes": ["class1", "class2"], "roles": ["student"]},
        "schoolB": {"classes": [], "roles": ["staff", "teacher"]},
    },
    "licenses": ["COR-123", "COR-456"],
}

user_id_description = "The unique id of the user. Could be generated from a hash."


class Context(BaseModel):
    classes: List[str] = Field(..., description="List of names of classes. Can be empty.")
    roles: conlist(min_items=1, item_type=str) = Field(
        ..., description="List of roles at the school. Can be more then one."
    )


class User(BaseModel):
    """A user describing with context and license information"""

    id: str = Field(..., description=user_id_description)
    licenses: List[constr(max_length=255)] = Field(
        ..., description="A list of license strings a user owns."
    )
    context: Dict[str, Context] = Field(
        ...,
        description="""Extra information about the user, e.g. schools and classes
                       attended, or roles within a school. Keys of this dictionary are
                       the names of schools""",
    )

    class Config:
        schema_extra = dict(example=sample_user)
