"""
El Comparativo - Authentication Models
Pydantic models for auth requests and responses
"""

from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional
from datetime import datetime
from uuid import UUID


# Request Models

class UserRegister(BaseModel):
    """User registration request"""
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    full_name: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=50)
    
    @validator('password')
    def password_strength(cls, v):
        """Validate password strength"""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        
        # Check for at least one number
        if not any(char.isdigit() for char in v):
            raise ValueError('Password must contain at least one number')
        
        # Check for at least one letter
        if not any(char.isalpha() for char in v):
            raise ValueError('Password must contain at least one letter')
        
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "usuario@ejemplo.com",
                "password": "MiPassword123",
                "full_name": "Juan Pérez",
                "phone": "+58 412 1234567"
            }
        }


class UserLogin(BaseModel):
    """User login request"""
    email: EmailStr
    password: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "usuario@ejemplo.com",
                "password": "MiPassword123"
            }
        }


class UserUpdate(BaseModel):
    """User profile update request"""
    full_name: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=50)
    
    class Config:
        json_schema_extra = {
            "example": {
                "full_name": "Juan Carlos Pérez",
                "phone": "+58 424 9876543"
            }
        }


class PasswordChange(BaseModel):
    """Password change request"""
    old_password: str
    new_password: str = Field(..., min_length=8, max_length=100)
    
    @validator('new_password')
    def password_strength(cls, v):
        """Validate new password strength"""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        
        if not any(char.isdigit() for char in v):
            raise ValueError('Password must contain at least one number')
        
        if not any(char.isalpha() for char in v):
            raise ValueError('Password must contain at least one letter')
        
        return v


class PasswordReset(BaseModel):
    """Password reset request (forgot password)"""
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Password reset confirmation"""
    token: str
    new_password: str = Field(..., min_length=8, max_length=100)


class TokenRefresh(BaseModel):
    """Token refresh request"""
    refresh_token: str


# Response Models

class UserResponse(BaseModel):
    """User data response"""
    id: UUID
    email: str
    full_name: Optional[str]
    phone: Optional[str]
    subscription_tier: str
    subscription_status: str
    subscription_starts_at: Optional[datetime]
    subscription_ends_at: Optional[datetime]
    daily_searches_count: int
    is_active: bool
    created_at: datetime
    last_login_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """Token response"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 86400  # 24 hours in seconds


class LoginResponse(BaseModel):
    """Login response with user data and tokens"""
    user: UserResponse
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class MessageResponse(BaseModel):
    """Generic message response"""
    message: str


class UserStatsResponse(BaseModel):
    """User statistics response"""
    total_searches: int
    saved_searches: int
    saved_vehicles: int
    active_alerts: int
    searches_today: int
    searches_remaining: Optional[int]  # None for premium users
    subscription_days_remaining: Optional[int]  # None for free users


# Subscription Models

class SubscriptionUpgrade(BaseModel):
    """Subscription upgrade request"""
    payment_method: str = Field(..., description="stripe, zinli, paypal")
    payment_token: Optional[str] = Field(None, description="Payment processor token")


class SubscriptionResponse(BaseModel):
    """Subscription status response"""
    tier: str
    status: str
    starts_at: Optional[datetime]
    ends_at: Optional[datetime]
    auto_renew: bool = False
    days_remaining: Optional[int]
