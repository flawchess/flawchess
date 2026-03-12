"""Auth router: register and JWT login/logout endpoints via FastAPI-Users."""

from fastapi import APIRouter
from fastapi_users import schemas as fapi_schemas

from app.users import auth_backend, fastapi_users

router = APIRouter()

# JWT login / logout
router.include_router(
    fastapi_users.get_auth_router(auth_backend),
    prefix="/auth/jwt",
    tags=["auth"],
)

# Registration
router.include_router(
    fastapi_users.get_register_router(fapi_schemas.BaseUser[int], fapi_schemas.BaseUserCreate),
    prefix="/auth",
    tags=["auth"],
)
