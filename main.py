from datetime import timedelta
from typing import List, Dict, Optional
from fastapi import FastAPI, Depends, HTTPException, status, Request, Form, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import os
import aiofiles
from PIL import Image
import uuid
import json
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import local storage instead of database
import local_storage
from auth import (
    create_access_token,
    verify_password,
    get_password_hash,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    generate_verification_token,
    send_verification_email,
    decode_token
)

app = FastAPI()

# Mount the uploads directory to serve files
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

templates = Jinja2Templates(directory="templates")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# OAuth2 setup
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Pydantic models (simplified versions of schemas.py)
class UserCreate(BaseModel):
    username: str
    email: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    is_verified: int

class RestaurantCreate(BaseModel):
    name: str

class Restaurant(BaseModel):
    id: int
    name: str

class ReviewCreate(BaseModel):
    text: str
    rating: int
    restaurant_id: int
    image_url: Optional[str] = None

class Review(BaseModel):
    id: int
    text: str
    rating: int
    image_url: Optional[str] = None
    user_id: int
    restaurant_id: int

class AdminEmail(BaseModel):
    email: str

# Authentication functions
def authenticate_user(username: str, password: str) -> Optional[Dict]:
    user = local_storage.get_user_by_username(username)
    if not user:
        return None
    if not verify_password(password, user.get("hashed_password")):
        return None
    return user

async def get_current_user(token: str = Depends(oauth2_scheme)) -> Dict:
    try:
        payload = decode_token(token)
        username = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        user = local_storage.get_user_by_username(username)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def get_verified_user(current_user: Dict = Depends(get_current_user)) -> Dict:
    if not current_user.get("is_verified"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not verified"
        )
    return current_user

# Routes
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/register")
async def register_user(username: str = Form(...), email: str = Form(...), password: str = Form(...)):
    # Check if user already exists
    if local_storage.get_user_by_username(username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    if local_storage.get_user_by_email(email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create user
    hashed_password = get_password_hash(password)
    verification_token = generate_verification_token()
    
    user_data = {
        "username": username,
        "email": email,
        "hashed_password": hashed_password,
        "is_verified": 0,
        "verification_token": verification_token
    }
    
    user = local_storage.create_user(user_data)
    
    # Send verification email
    await send_verification_email(email, verification_token)
    
    return {
        "message": "User registered successfully. Please check your email to verify your account.",
        "user_id": user["id"]
    }

@app.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["username"]}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/verify/{token}")
async def verify_email(token: str):
    users = local_storage.get_all_users()
    for user in users:
        if user.get("verification_token") == token:
            # Update user verification status
            local_storage.update_user(user["id"], {"is_verified": 1, "verification_token": None})
            return {"message": "Email verified successfully"}
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Invalid verification token"
    )

@app.get("/users/me", response_model=UserResponse)
async def read_users_me(current_user: Dict = Depends(get_current_user)):
    return current_user

@app.post("/restaurants/", response_model=Restaurant)
async def create_restaurant(
    restaurant: RestaurantCreate,
    current_user: Dict = Depends(get_current_user)
):
    restaurant_data = {"name": restaurant.name}
    created_restaurant = local_storage.create_restaurant(restaurant_data)
    
    # Ensure the id is an integer
    created_restaurant["id"] = int(created_restaurant["id"])
    
    return created_restaurant

@app.get("/restaurants/", response_model=List[Restaurant])
async def list_restaurants(
    skip: int = 0,
    limit: int = 10
):
    return local_storage.get_restaurants(skip, limit)

@app.post("/reviews/")
async def create_review(
    text: str = Form(...),
    rating: int = Form(...),
    restaurant_id: int = Form(...),
    image: UploadFile = File(None),
    current_user: Dict = Depends(get_verified_user)
):
    # Validate rating
    if rating < 1 or rating > 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rating must be between 1 and 5"
        )
    
    # Check if restaurant exists
    restaurant = local_storage.get_restaurant_by_id(restaurant_id)
    if not restaurant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Restaurant not found"
        )
    
    image_url = None
    if image and image.filename:
        # Validate image
        if image.size > 5 * 1024 * 1024:  # 5MB limit
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Image size must be less than 5MB"
            )
        
        if not image.content_type.startswith('image/'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File must be an image"
            )
        
        # Save image locally
        try:
            image_data = await image.read()
            image_url = await local_storage.save_file(image_data, image.filename, image.content_type)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to save image: {str(e)}"
            )
    
    # Create review
    review_data = {
        "text": text,
        "rating": rating,
        "restaurant_id": restaurant_id,
        "user_id": current_user["id"],
        "image_url": image_url
    }
    
    created_review = local_storage.create_review(review_data)
    
    return {
        "message": "Review created successfully",
        "review_id": created_review["id"],
        "image_url": image_url
    }

@app.get("/restaurants/{restaurant_id}/reviews/", response_model=List[Review])
async def list_restaurant_reviews(
    restaurant_id: int,
    skip: int = 0,
    limit: int = 10
):
    return local_storage.get_reviews_by_restaurant(restaurant_id, skip, limit)

# Admin endpoints
@app.get("/admin")
async def admin_page(request: Request):
    return templates.TemplateResponse("admin.html", {"request": request})

@app.get("/admin/check-access")
async def check_admin_access(current_user: Dict = Depends(get_current_user)):
    # Reload admin list to ensure it's up to date with .env
    local_storage.init_first_admin()
    
    if not local_storage.is_admin(current_user.get("email")):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have admin access"
        )
    return {"admin": True}

@app.get("/admin/users")
async def get_admin_users(current_user: Dict = Depends(get_current_user)):
    if not local_storage.is_admin(current_user.get("email")):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have admin access"
        )
    return local_storage.get_all_users()

@app.get("/admin/reviews")
async def get_admin_reviews(current_user: Dict = Depends(get_current_user)):
    if not local_storage.is_admin(current_user.get("email")):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have admin access"
        )
    return local_storage.get_all_reviews()

@app.get("/admin/admins")
async def get_admin_list(current_user: Dict = Depends(get_current_user)):
    if not local_storage.is_admin(current_user.get("email")):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have admin access"
        )
    return local_storage.get_all_admins()

@app.post("/admin/add-admin")
async def add_admin_access(
    admin_email: AdminEmail,
    current_user: Dict = Depends(get_current_user)
):
    # Check if current user is admin
    if not local_storage.is_admin(current_user.get("email")):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have admin access"
        )
    
    # Check if user exists
    user = local_storage.get_user_by_email(admin_email.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Add admin access
    success = local_storage.add_admin(admin_email.email)
    if not success:
        return {"message": "User already has admin access"}
    
    return {"message": "Admin access granted successfully"}

@app.post("/admin/remove-admin")
async def remove_admin_access(
    admin_email: AdminEmail,
    current_user: Dict = Depends(get_current_user)
):
    # Check if current user is admin
    if not local_storage.is_admin(current_user.get("email")):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have admin access"
        )
    
    # Prevent removing your own admin access
    if admin_email.email == current_user.get("email"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot remove your own admin access"
        )
    
    # Remove admin access
    success = local_storage.remove_admin(admin_email.email)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User does not have admin access"
        )
    
    return {"message": "Admin access removed successfully"}