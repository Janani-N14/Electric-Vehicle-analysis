import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict
from fastapi import Request
from ev_fleet_management.config.settings import JWT_SECRET_KEY, JWT_ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
from ev_fleet_management.exception.custom_exception import AuthenticationError

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.PyJWTError:
        raise AuthenticationError("Could not validate credentials, token is invalid or expired")

def get_current_user_from_cookie(request: Request) -> Dict:
    token = request.cookies.get("access_token")
    if not token:
        # Check Authorization header as backup
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            
    if not token:
        raise AuthenticationError("Missing authentication token. Please sign in.")
        
    return decode_access_token(token)

def get_optional_current_user(request: Request) -> Optional[Dict]:
    try:
        return get_current_user_from_cookie(request)
    except Exception:
        return None
