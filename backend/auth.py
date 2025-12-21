"""
El Comparativo - Authentication System
Complete JWT-based authentication with user management
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from passlib.context import CryptContext
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import os
from uuid import UUID, uuid4

from .database import get_db_pool


# Security configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production-must-be-32-chars-minimum")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours
REFRESH_TOKEN_EXPIRE_DAYS = 30

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


class PasswordHasher:
    """Handle password hashing and verification"""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password"""
        return pwd_context.hash(password)
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against a hash"""
        return pwd_context.verify(plain_password, hashed_password)


class TokenManager:
    """Manage JWT tokens"""
    
    @staticmethod
    def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """
        Create JWT access token
        
        Args:
            data: Payload to encode (usually user_id, email)
            expires_delta: Custom expiration time
            
        Returns:
            Encoded JWT token
        """
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access"
        })
        
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def create_refresh_token(data: Dict[str, Any]) -> str:
        """Create JWT refresh token"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "refresh"
        })
        
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def verify_token(token: str) -> Dict[str, Any]:
        """
        Verify and decode JWT token
        
        Returns:
            Decoded token payload
            
        Raises:
            HTTPException if token invalid
        """
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return payload
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )


class UserService:
    """User management service"""
    
    @staticmethod
    async def create_user(
        email: str,
        password: str,
        full_name: Optional[str] = None,
        phone: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new user
        
        Args:
            email: User email (unique)
            password: Plain text password (will be hashed)
            full_name: Optional full name
            phone: Optional phone number
            
        Returns:
            Created user dict
            
        Raises:
            HTTPException if email already exists
        """
        pool = get_db_pool()
        
        # Check if user exists
        async with pool.acquire() as conn:
            existing = await conn.fetchrow(
                "SELECT id FROM users WHERE email = $1",
                email.lower()
            )
            
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered"
                )
            
            # Hash password
            password_hash = PasswordHasher.hash_password(password)
            
            # Create user
            user = await conn.fetchrow("""
                INSERT INTO users (
                    email, password_hash, full_name, phone,
                    subscription_tier, subscription_status,
                    created_at, updated_at
                )
                VALUES ($1, $2, $3, $4, 'free', 'active', NOW(), NOW())
                RETURNING 
                    id, email, full_name, phone,
                    subscription_tier, subscription_status,
                    created_at, is_active
            """, email.lower(), password_hash, full_name, phone)
            
            return dict(user)
    
    @staticmethod
    async def authenticate_user(email: str, password: str) -> Optional[Dict[str, Any]]:
        """
        Authenticate user with email and password
        
        Returns:
            User dict if authenticated, None otherwise
        """
        pool = get_db_pool()
        
        async with pool.acquire() as conn:
            user = await conn.fetchrow("""
                SELECT 
                    id, email, password_hash, full_name, phone,
                    subscription_tier, subscription_status,
                    is_active, created_at
                FROM users
                WHERE email = $1
            """, email.lower())
            
            if not user:
                return None
            
            # Verify password
            if not PasswordHasher.verify_password(password, user["password_hash"]):
                return None
            
            # Check if user is active
            if not user["is_active"]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Account is inactive"
                )
            
            # Update last login
            await conn.execute(
                "UPDATE users SET last_login_at = NOW() WHERE id = $1",
                user["id"]
            )
            
            # Return user without password hash
            user_dict = dict(user)
            user_dict.pop("password_hash")
            return user_dict
    
    @staticmethod
    async def get_user_by_id(user_id: UUID) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        pool = get_db_pool()
        
        async with pool.acquire() as conn:
            user = await conn.fetchrow("""
                SELECT 
                    id, email, full_name, phone,
                    subscription_tier, subscription_status,
                    subscription_starts_at, subscription_ends_at,
                    daily_searches_count, daily_searches_reset_at,
                    is_active, created_at, last_login_at
                FROM users
                WHERE id = $1
            """, user_id)
            
            return dict(user) if user else None
    
    @staticmethod
    async def update_user(
        user_id: UUID,
        full_name: Optional[str] = None,
        phone: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update user profile"""
        pool = get_db_pool()
        
        updates = []
        params = []
        param_count = 1
        
        if full_name is not None:
            updates.append(f"full_name = ${param_count}")
            params.append(full_name)
            param_count += 1
        
        if phone is not None:
            updates.append(f"phone = ${param_count}")
            params.append(phone)
            param_count += 1
        
        if not updates:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update"
            )
        
        updates.append("updated_at = NOW()")
        params.append(user_id)
        
        query = f"""
            UPDATE users
            SET {', '.join(updates)}
            WHERE id = ${param_count}
            RETURNING 
                id, email, full_name, phone,
                subscription_tier, subscription_status,
                updated_at
        """
        
        async with pool.acquire() as conn:
            user = await conn.fetchrow(query, *params)
            return dict(user)
    
    @staticmethod
    async def change_password(user_id: UUID, old_password: str, new_password: str):
        """Change user password"""
        pool = get_db_pool()
        
        async with pool.acquire() as conn:
            # Get current password hash
            user = await conn.fetchrow(
                "SELECT password_hash FROM users WHERE id = $1",
                user_id
            )
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            
            # Verify old password
            if not PasswordHasher.verify_password(old_password, user["password_hash"]):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Incorrect password"
                )
            
            # Hash new password
            new_hash = PasswordHasher.hash_password(new_password)
            
            # Update password
            await conn.execute(
                "UPDATE users SET password_hash = $1, updated_at = NOW() WHERE id = $2",
                new_hash, user_id
            )
    
    @staticmethod
    async def check_search_limit(user_id: UUID) -> bool:
        """
        Check if user can perform another search
        
        Returns:
            True if user can search, False if limit reached
        """
        pool = get_db_pool()
        
        async with pool.acquire() as conn:
            user = await conn.fetchrow("""
                SELECT 
                    subscription_tier,
                    daily_searches_count,
                    daily_searches_reset_at
                FROM users
                WHERE id = $1
            """, user_id)
            
            if not user:
                return False
            
            # Premium users have unlimited searches
            if user["subscription_tier"] == "premium":
                return True
            
            # Reset counter if new day
            if user["daily_searches_reset_at"].date() < datetime.utcnow().date():
                await conn.execute("""
                    UPDATE users
                    SET daily_searches_count = 0,
                        daily_searches_reset_at = NOW()
                    WHERE id = $1
                """, user_id)
                return True
            
            # Check free tier limit (5 searches/day)
            FREE_TIER_LIMIT = 5
            return user["daily_searches_count"] < FREE_TIER_LIMIT
    
    @staticmethod
    async def increment_search_count(user_id: UUID):
        """Increment user's daily search count"""
        pool = get_db_pool()
        
        async with pool.acquire() as conn:
            await conn.execute("""
                UPDATE users
                SET daily_searches_count = daily_searches_count + 1
                WHERE id = $1
            """, user_id)
    
    @staticmethod
    async def upgrade_to_premium(user_id: UUID, payment_id: Optional[str] = None):
        """Upgrade user to premium tier"""
        pool = get_db_pool()
        
        starts_at = datetime.utcnow()
        ends_at = starts_at + timedelta(days=30)  # 30 days subscription
        
        async with pool.acquire() as conn:
            await conn.execute("""
                UPDATE users
                SET 
                    subscription_tier = 'premium',
                    subscription_status = 'active',
                    subscription_starts_at = $1,
                    subscription_ends_at = $2,
                    updated_at = NOW()
                WHERE id = $3
            """, starts_at, ends_at, user_id)


async def get_current_user(token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
    """
    Dependency to get current authenticated user
    
    Usage in endpoints:
        @app.get("/api/me")
        async def get_me(current_user: dict = Depends(get_current_user)):
            return current_user
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = TokenManager.verify_token(token)
        user_id: str = payload.get("sub")
        
        if user_id is None:
            raise credentials_exception
        
        # Get user from database
        user = await UserService.get_user_by_id(UUID(user_id))
        
        if user is None:
            raise credentials_exception
        
        return user
        
    except Exception as e:
        raise credentials_exception


async def get_current_active_user(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Dependency to get current active user
    Checks if user account is active
    """
    if not current_user.get("is_active"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    return current_user


async def require_premium(
    current_user: Dict[str, Any] = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    Dependency to require premium subscription
    
    Usage:
        @app.get("/api/premium-feature")
        async def premium_only(user: dict = Depends(require_premium)):
            return {"message": "Premium feature"}
    """
    if current_user.get("subscription_tier") != "premium":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Premium subscription required"
        )
    return current_user
