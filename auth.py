from datetime import datetime, timedelta
from typing import Optional, Dict
import hashlib
import secrets
import base64
import json
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import os

# Secret key for token generation
SECRET_KEY = "your-secret-key"  # In production, use a secure environment variable
ALGORITHM = "HS256"  # We'll keep this for compatibility but won't use it
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# OAuth2 setup
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def verify_password(plain_password, hashed_password):
    """Verify a password against a hash"""
    salt = hashed_password[:32]  # First 32 chars are the salt
    stored_hash = hashed_password[32:]
    new_hash = hashlib.pbkdf2_hmac(
        'sha256', 
        plain_password.encode('utf-8'), 
        salt.encode('utf-8'), 
        100000
    ).hex()
    return new_hash == stored_hash

def get_password_hash(password):
    """Generate a salted hash for a password"""
    salt = secrets.token_hex(16)
    hash = hashlib.pbkdf2_hmac(
        'sha256', 
        password.encode('utf-8'), 
        salt.encode('utf-8'), 
        100000
    ).hex()
    return salt + hash

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create a simple token without JWT dependency"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire.timestamp()})
    
    # Convert to JSON and encode in base64
    json_str = json.dumps(to_encode)
    token = base64.urlsafe_b64encode(json_str.encode()).decode()
    
    # Add a simple signature
    signature = hashlib.sha256((token + SECRET_KEY).encode()).hexdigest()
    return f"{token}.{signature}"

def decode_token(token: str):
    """Decode a token without JWT dependency"""
    try:
        # Split token and signature
        token_part, signature = token.split('.')
        
        # Verify signature
        expected_signature = hashlib.sha256((token_part + SECRET_KEY).encode()).hexdigest()
        if signature != expected_signature:
            raise ValueError("Invalid signature")
        
        # Decode token
        decoded = base64.urlsafe_b64decode(token_part).decode()
        payload = json.loads(decoded)
        
        # Check expiration
        if datetime.utcnow().timestamp() > payload.get("exp", 0):
            raise ValueError("Token expired")
            
        return payload
    except Exception as e:
        raise ValueError(f"Invalid token: {str(e)}")

def generate_verification_token():
    """Generate a random token for email verification"""
    return secrets.token_urlsafe(32)

async def send_verification_email(email: str, token: str):
    """Send a verification email (simplified for local testing)"""
    verification_url = f"http://localhost:8000/verify/{token}"
    print(f"Verification URL for {email}: {verification_url}")