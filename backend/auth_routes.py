"""
El Comparativo - Authentication Endpoints
Complete auth API: register, login, logout, profile, etc.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from typing import Dict, Any
from uuid import UUID

from .auth import (
    UserService,
    TokenManager,
    get_current_user,
    get_current_active_user,
    require_premium
)
from .auth_models import (
    UserRegister,
    UserLogin,
    UserUpdate,
    PasswordChange,
    LoginResponse,
    UserResponse,
    TokenResponse,
    MessageResponse,
    UserStatsResponse,
    SubscriptionUpgrade,
    SubscriptionResponse
)
from .database import get_db_pool


router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/register", response_model=LoginResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserRegister):
    """
    Register a new user
    
    Creates new user account and returns access tokens
    
    - **email**: Valid email address (unique)
    - **password**: Minimum 8 characters, must contain letter and number
    - **full_name**: Optional full name
    - **phone**: Optional phone number
    """
    try:
        # Create user
        user = await UserService.create_user(
            email=user_data.email,
            password=user_data.password,
            full_name=user_data.full_name,
            phone=user_data.phone
        )
        
        # Generate tokens
        access_token = TokenManager.create_access_token(
            data={"sub": str(user["id"]), "email": user["email"]}
        )
        refresh_token = TokenManager.create_refresh_token(
            data={"sub": str(user["id"])}
        )
        
        return {
            "user": user,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )


@router.post("/login", response_model=LoginResponse)
async def login(credentials: UserLogin):
    """
    Login with email and password
    
    Returns user data and access tokens
    
    - **email**: User email
    - **password**: User password
    """
    user = await UserService.authenticate_user(
        email=credentials.email,
        password=credentials.password
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Generate tokens
    access_token = TokenManager.create_access_token(
        data={"sub": str(user["id"]), "email": user["email"]}
    )
    refresh_token = TokenManager.create_refresh_token(
        data={"sub": str(user["id"])}
    )
    
    return {
        "user": user,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


@router.post("/login/oauth2", response_model=TokenResponse)
async def login_oauth2(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    OAuth2 compatible login endpoint
    
    Used by Swagger UI and OAuth2 clients
    """
    user = await UserService.authenticate_user(
        email=form_data.username,  # OAuth2 uses "username" field
        password=form_data.password
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Generate tokens
    access_token = TokenManager.create_access_token(
        data={"sub": str(user["id"]), "email": user["email"]}
    )
    refresh_token = TokenManager.create_refresh_token(
        data={"sub": str(user["id"])}
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(refresh_token: str):
    """
    Refresh access token using refresh token
    
    - **refresh_token**: Valid refresh token
    """
    try:
        payload = TokenManager.verify_token(refresh_token)
        
        # Check token type
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )
        
        user_id = payload.get("sub")
        
        # Verify user still exists and is active
        user = await UserService.get_user_by_id(UUID(user_id))
        if not user or not user.get("is_active"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )
        
        # Generate new tokens
        new_access_token = TokenManager.create_access_token(
            data={"sub": user_id, "email": user["email"]}
        )
        new_refresh_token = TokenManager.create_refresh_token(
            data={"sub": user_id}
        )
        
        return {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer"
        }
        
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: Dict = Depends(get_current_active_user)):
    """
    Get current authenticated user information
    
    Requires valid access token in Authorization header
    """
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_data: UserUpdate,
    current_user: Dict = Depends(get_current_active_user)
):
    """
    Update current user profile
    
    - **full_name**: New full name
    - **phone**: New phone number
    """
    updated_user = await UserService.update_user(
        user_id=current_user["id"],
        full_name=user_data.full_name,
        phone=user_data.phone
    )
    
    return updated_user


@router.post("/me/change-password", response_model=MessageResponse)
async def change_user_password(
    password_data: PasswordChange,
    current_user: Dict = Depends(get_current_active_user)
):
    """
    Change user password
    
    - **old_password**: Current password
    - **new_password**: New password (min 8 chars, must contain letter and number)
    """
    await UserService.change_password(
        user_id=current_user["id"],
        old_password=password_data.old_password,
        new_password=password_data.new_password
    )
    
    return {"message": "Password changed successfully"}


@router.get("/me/stats", response_model=UserStatsResponse)
async def get_user_stats(current_user: Dict = Depends(get_current_active_user)):
    """
    Get current user statistics
    
    Returns:
    - Total searches performed
    - Saved searches count
    - Saved vehicles count
    - Active price alerts
    - Searches today
    - Searches remaining (free tier only)
    """
    pool = get_db_pool()
    
    async with pool.acquire() as conn:
        # Get total searches
        total_searches = await conn.fetchval("""
            SELECT COUNT(*) FROM search_history
            WHERE user_id = $1
        """, current_user["id"])
        
        # Get saved searches
        saved_searches = await conn.fetchval("""
            SELECT COUNT(*) FROM saved_searches
            WHERE user_id = $1
        """, current_user["id"])
        
        # Get saved vehicles
        saved_vehicles = await conn.fetchval("""
            SELECT COUNT(*) FROM saved_vehicles
            WHERE user_id = $1
        """, current_user["id"])
        
        # Get active alerts
        active_alerts = await conn.fetchval("""
            SELECT COUNT(*) FROM price_alerts
            WHERE user_id = $1 AND is_active = true
        """, current_user["id"])
    
    # Calculate searches remaining
    searches_remaining = None
    if current_user["subscription_tier"] == "free":
        FREE_TIER_LIMIT = 5
        searches_remaining = max(0, FREE_TIER_LIMIT - current_user["daily_searches_count"])
    
    # Calculate subscription days remaining
    subscription_days_remaining = None
    if current_user["subscription_tier"] == "premium" and current_user["subscription_ends_at"]:
        from datetime import datetime
        days_left = (current_user["subscription_ends_at"] - datetime.utcnow()).days
        subscription_days_remaining = max(0, days_left)
    
    return {
        "total_searches": total_searches or 0,
        "saved_searches": saved_searches or 0,
        "saved_vehicles": saved_vehicles or 0,
        "active_alerts": active_alerts or 0,
        "searches_today": current_user["daily_searches_count"],
        "searches_remaining": searches_remaining
    }


@router.get("/me/subscription", response_model=SubscriptionResponse)
async def get_subscription_status(current_user: Dict = Depends(get_current_active_user)):
    """
    Get current subscription status
    """
    days_remaining = None
    
    if current_user["subscription_tier"] == "premium" and current_user["subscription_ends_at"]:
        from datetime import datetime
        days_left = (current_user["subscription_ends_at"] - datetime.utcnow()).days
        days_remaining = max(0, days_left)
    
    return {
        "tier": current_user["subscription_tier"],
        "status": current_user["subscription_status"],
        "starts_at": current_user.get("subscription_starts_at"),
        "ends_at": current_user.get("subscription_ends_at"),
        "auto_renew": False,  # TODO: Implement auto-renew logic
        "days_remaining": days_remaining
    }


@router.post("/me/upgrade", response_model=MessageResponse)
async def upgrade_subscription(
    upgrade_data: SubscriptionUpgrade,
    current_user: Dict = Depends(get_current_active_user)
):
    """
    Upgrade to premium subscription
    
    - **payment_method**: Payment method (stripe, zinli, paypal)
    - **payment_token**: Payment processor token
    
    TODO: Integrate with actual payment processors
    """
    # TODO: Process payment with Stripe/Zinli/PayPal
    # For now, just upgrade (MVP)
    
    await UserService.upgrade_to_premium(
        user_id=current_user["id"],
        payment_id=upgrade_data.payment_token
    )
    
    return {"message": "Successfully upgraded to Premium"}


@router.post("/logout", response_model=MessageResponse)
async def logout(current_user: Dict = Depends(get_current_active_user)):
    """
    Logout current user
    
    Note: Since we're using stateless JWT, actual logout is handled client-side
    by removing the token. This endpoint is for future session management.
    """
    # TODO: Implement token blacklist if needed
    # For now, just return success
    
    return {"message": "Successfully logged out"}


# Admin endpoints (require premium or admin role)

@router.get("/users/premium", response_model=MessageResponse)
async def premium_only_endpoint(current_user: Dict = Depends(require_premium)):
    """
    Example premium-only endpoint
    
    Requires premium subscription
    """
    return {"message": f"Welcome premium user: {current_user['email']}"}
