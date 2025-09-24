"""
JWT Authentication utilities for multi-tenant chatbot platform
"""

import jwt
from datetime import datetime, timedelta
from typing import Dict, Optional, Union
from jose import JWTError
from app.utils.password import verify_password, get_password_hash
from app.core.config import settings

# JWT Configuration from centralized settings
SECRET_KEY = settings.jwt_secret_key
ALGORITHM = settings.jwt_algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes
REFRESH_TOKEN_EXPIRE_DAYS = settings.refresh_token_expire_days

def create_access_token(data: Dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.
    
    Args:
        data: Dictionary containing the claims to encode in the token
        expires_delta: Optional expiration time delta
        
    Returns:
        str: Encoded JWT token
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: Dict) -> str:
    """
    Create a JWT refresh token.
    
    Args:
        data: Dictionary containing the claims to encode in the token
        
    Returns:
        str: Encoded JWT refresh token
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> Optional[Dict]:
    """
    Verify and decode a JWT token.
    
    Args:
        token: JWT token string
        
    Returns:
        Dict: Decoded token payload if valid, None otherwise
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except (JWTError, ValueError, TypeError, Exception):
        # Handles malformed tokens like "invalid_token_12345" that cause DecodeError: Not enough segments        # Catch all possible exceptions from malformed tokens
        return None

def create_company_tokens(company_id: str, email: str) -> Dict[str, str]:
    """
    Create both access and refresh tokens for a company.
    
    Args:
        company_id: Company identifier
        email: Company email
        
    Returns:
        Dict containing access_token and refresh_token
    """
    token_data = {
        "sub": company_id,
        "email": email,
        "user_type": "company"
    }
    
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

def create_user_tokens(user_id: str, company_id: str, email: Optional[str] = None) -> Dict[str, str]:
    """
    Create both access and refresh tokens for a user.
    
    Args:
        user_id: User identifier
        company_id: Company identifier
        email: User email (optional)
        
    Returns:
        Dict containing access_token and refresh_token
    """
    token_data = {
        "sub": user_id,
        "company_id": company_id,
        "email": email,
        "user_type": "user"
    }
    
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

def create_guest_tokens(session_id: str, company_id: str) -> Dict[str, str]:
    """
    Create tokens for a guest session.
    
    Args:
        session_id: Guest session identifier
        company_id: Company identifier
        
    Returns:
        Dict containing access_token and refresh_token
    """
    token_data = {
        "sub": session_id,
        "company_id": company_id,
        "user_type": "guest"
    }
    
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

def refresh_access_token(refresh_token: str) -> Optional[str]:
    """
    Create a new access token from a refresh token.
    
    Args:
        refresh_token: Valid refresh token
        
    Returns:
        str: New access token if refresh token is valid, None otherwise
    """
    payload = verify_token(refresh_token)
    if not payload or payload.get("type") != "refresh":
        return None
    
    # Create new access token with same claims (except exp and type)
    user_type = payload.get("user_type")
    
    if user_type == "company":
        # For company tokens, sub contains the company_id
        new_token_data = {
            "sub": payload.get("sub"),
            "email": payload.get("email"),
            "user_type": user_type
        }
    else:
        # For user/guest tokens, preserve both sub and company_id
        new_token_data = {
            "sub": payload.get("sub"),
            "company_id": payload.get("company_id"),
            "email": payload.get("email"),
            "user_type": user_type
        }
    
    return create_access_token(new_token_data)

def decode_token(token: str) -> Optional[Dict]:
    """
    Decode a JWT token and return its payload.
    
    Args:
        token: JWT token string
        
    Returns:
        Dict: Token payload if valid, None otherwise
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # Check if token is expired
        exp = payload.get("exp")
        if exp and datetime.utcnow().timestamp() > exp:
            return None
            
        return payload
    except (JWTError, ValueError, TypeError, Exception):
        # Handles malformed tokens like "invalid_token_12345" that cause DecodeError: Not enough segments        # Catch all possible exceptions from malformed or invalid tokens
        return None

def get_current_user_info(token: str) -> Optional[Dict]:
    """
    Extract user information from a JWT token.
    
    Args:
        token: JWT token string
        
    Returns:
        Dict: User information if token is valid, None otherwise
    """
    payload = decode_token(token)
    if not payload:
        return None
    
    user_type = payload.get("user_type")
    
    if user_type == "company":
        # For company tokens, sub contains the company_id
        return {
            "company_id": payload.get("sub"),
            "email": payload.get("email"),
            "user_type": user_type
        }
    elif user_type in ["user", "guest"]:
        # For user/guest tokens, sub contains user_id/session_id
        return {
            "user_id": payload.get("sub"),
            "company_id": payload.get("company_id"),
            "email": payload.get("email"),
            "user_type": user_type
        }
    else:
        # Unknown user type
        return None

# Token validation helpers
def is_company_token(token: str) -> bool:
    """Check if token belongs to a company."""
    payload = decode_token(token)
    return payload is not None and payload.get("user_type") == "company"

def is_user_token(token: str) -> bool:
    """Check if token belongs to a registered user."""
    payload = decode_token(token)
    return payload is not None and payload.get("user_type") == "user"

def is_guest_token(token: str) -> bool:
    """Check if token belongs to a guest session."""
    payload = decode_token(token)
    return payload is not None and payload.get("user_type") == "guest" 