# -*- coding: utf-8 -*-
from __future__ import annotations

import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Path, status
from pydantic import constr

from bildungslogin_plugin.backend import DbBackend, DbConnectionError, UserNotFound
from bildungslogin_plugin.models import User
from ucsschool.apis.opa import OPAClient, opa_instance
from ucsschool.apis.utils import auth_manager
from ucsschool.apis.models import AuthenticatedUser

NonEmptyStr = constr(min_length=1)
NoStarStr = constr(regex=r"^[^*]+$")

router = APIRouter()

_backend: Optional[DbBackend] = None
logger = logging.getLogger(__name__)


def set_backend(obj: DbBackend) -> None:
    global _backend
    _backend = obj


def get_backend() -> DbBackend:
    if not _backend:
        raise RuntimeError("The DB backend connection has not been setup.")
    return _backend


@router.get("/user/{id}", response_model=User, response_model_exclude_none=True)
async def get(
        user_id: NonEmptyStr = Path(..., alias="id", description="User ID", title="User ID"),
        backend: DbBackend = Depends(get_backend),
        policy_instance: OPAClient = Depends(opa_instance),
        user: AuthenticatedUser = Depends(auth_manager("bildungslogin", AuthenticatedUser)),
) -> User:
    """Retrieve a users name, license, role, class and school information."""
    await policy_instance.check_policy_true_or_raise("bildungslogin_plugin/user", user.dict())
    logger.debug(
        "Retrieving user with user_id=%r and backend=%r...", user_id, backend.__class__.__name__
    )
    try:
        return await backend.get_user(user_id)
    except DbConnectionError as exc:
        error_id = uuid.uuid4()
        logger.exception("[%s] Error connecting to database: %s", error_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error. Error ID: {error_id!s}.",
        ) from exc
    except UserNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No user with id {user_id!r} found.",
        )
    except Exception as exc:  # pragma: no cover
        error_id = uuid.uuid4()
        logger.exception("[%s] Error looking for user with id %r: %s", error_id, user_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error. Error ID: {error_id!s}.",
        ) from exc
