from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from app.models.admin import AdminUser
from app.core.security import verify_password, create_access_token
from app.schemas.auth import TokenResponse
from app.core.config import settings
from app.core.limiter import limiter

from loguru import logger

router = APIRouter()


@router.post("/login", summary="Admin Login", response_model=TokenResponse)
@limiter.limit(settings.rate_limit_admin)
async def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
    # 1. Find the user in the database
    user = await AdminUser.find_one(AdminUser.username == form_data.username)
    if not user:
        logger.warning(f"Login failed: unknown user '{form_data.username}'.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 2. Verify the password hash
    if not verify_password(form_data.password, user.hashed_password):
        logger.warning(f"Login failed: wrong password for '{form_data.username}'.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 3. Generate and return the JWT token
    logger.info(f"Login successful for '{user.username}'.")
    access_token = create_access_token(data={"sub": user.username})
    return TokenResponse(access_token=access_token, token_type="bearer")