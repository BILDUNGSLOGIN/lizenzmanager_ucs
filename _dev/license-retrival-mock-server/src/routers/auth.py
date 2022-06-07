from fastapi import APIRouter, Form
from pydantic import BaseModel

router = APIRouter(prefix="/auth", tags=["Auth"])


class AuthResponse(BaseModel):
    """ Response model for get_license_package """
    access_token: str
    token_type: str
    expires_in: int
    scope: str


@router.post("", response_model=AuthResponse)
def auth(scope: str = Form(...)):
    """ Mock auth endpoint """
    return AuthResponse(access_token="dummy_token",
                        token_type="bearer",
                        expires_in=28800,
                        scope=scope)
