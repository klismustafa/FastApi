import os
import json
import shutil
from datetime import datetime
from typing import Dict, List, Optional, Any
import uuid
from dotenv import load_dotenv

# Create directories if they don't exist
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
DATA_DIR = os.path.join(os.path.dirname(__file__), "local_data")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

# Data storage files
USERS_FILE = os.path.join(DATA_DIR, "users.json")
RESTAURANTS_FILE = os.path.join(DATA_DIR, "restaurants.json")
REVIEWS_FILE = os.path.join(DATA_DIR, "reviews.json")

# Initialize data files if they don't exist
def init_data_files():
    for file_path in [USERS_FILE, RESTAURANTS_FILE, REVIEWS_FILE]:
        if not os.path.exists(file_path):
            with open(file_path, 'w') as f:
                json.dump([], f)

init_data_files()

# Helper functions to read and write JSON data
def read_json(file_path: str) -> List[Dict]:
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return []

def write_json(file_path: str, data: List[Dict]):
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=2)

# File upload handler
async def save_file(file_data: bytes, file_name: str, content_type: str) -> str:
    """Save a file locally and return its URL path"""
    # Generate a unique filename to prevent collisions
    file_ext = os.path.splitext(file_name)[1]
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)
    
    # Save the file
    with open(file_path, 'wb') as f:
        f.write(file_data)
    
    # Return a relative URL to the file
    return f"/uploads/{unique_filename}"

# User management
def get_user_by_username(username: str) -> Optional[Dict]:
    users = read_json(USERS_FILE)
    for user in users:
        if user.get("username") == username:
            return user
    return None

def get_user_by_email(email: str) -> Optional[Dict]:
    users = read_json(USERS_FILE)
    for user in users:
        if user.get("email") == email:
            return user
    return None

def get_user_by_id(user_id: int) -> Optional[Dict]:
    users = read_json(USERS_FILE)
    for user in users:
        if user.get("id") == user_id:
            return user
    return None

def create_user(user_data: Dict) -> Dict:
    users = read_json(USERS_FILE)
    
    # Generate a new ID
    new_id = 1
    if users:
        new_id = max(user.get("id", 0) for user in users) + 1
    
    user_data["id"] = new_id
    users.append(user_data)
    write_json(USERS_FILE, users)
    return user_data

def update_user(user_id: int, updated_data: Dict) -> Optional[Dict]:
    users = read_json(USERS_FILE)
    for i, user in enumerate(users):
        if user.get("id") == user_id:
            users[i].update(updated_data)
            write_json(USERS_FILE, users)
            return users[i]
    return None

# Restaurant management
def get_restaurants(skip: int = 0, limit: int = 10) -> List[Dict]:
    restaurants = read_json(RESTAURANTS_FILE)
    return restaurants[skip:skip+limit]

def get_restaurant_by_id(restaurant_id: int) -> Optional[Dict]:
    restaurants = read_json(RESTAURANTS_FILE)
    for restaurant in restaurants:
        if restaurant.get("id") == restaurant_id:
            return restaurant
    return None

def create_restaurant(restaurant_data: Dict) -> Dict:
    restaurants = read_json(RESTAURANTS_FILE)
    
    # Generate a new ID
    new_id = 1
    if restaurants:
        new_id = max(restaurant.get("id", 0) for restaurant in restaurants) + 1
    
    restaurant_data["id"] = new_id
    restaurants.append(restaurant_data)
    write_json(RESTAURANTS_FILE, restaurants)
    return restaurant_data

# Review management
def get_reviews_by_restaurant(restaurant_id: int, skip: int = 0, limit: int = 10) -> List[Dict]:
    reviews = read_json(REVIEWS_FILE)
    restaurant_reviews = [r for r in reviews if r.get("restaurant_id") == restaurant_id]
    return restaurant_reviews[skip:skip+limit]

def create_review(review_data: Dict) -> Dict:
    reviews = read_json(REVIEWS_FILE)
    
    # Generate a new ID
    new_id = 1
    if reviews:
        new_id = max(review.get("id", 0) for review in reviews) + 1
    
    review_data["id"] = new_id
    review_data["created_at"] = datetime.now().isoformat()
    reviews.append(review_data)
    write_json(REVIEWS_FILE, reviews)
    return review_data

# Add these functions to local_storage.py

# Admin data file
ADMINS_FILE = os.path.join(DATA_DIR, "admins.json")

# Initialize admin data file
def init_admin_file():
    if not os.path.exists(ADMINS_FILE):
        with open(ADMINS_FILE, 'w') as f:
            json.dump([], f)

init_admin_file()

# Admin management
def is_admin(email: str) -> bool:
    """Check if a user has admin access"""
    admins = read_json(ADMINS_FILE)
    return any(admin.get("email") == email for admin in admins)

def add_admin(email: str) -> bool:
    """Add admin access for a user"""
    if is_admin(email):
        return False
    
    admins = read_json(ADMINS_FILE)
    admins.append({"email": email})
    write_json(ADMINS_FILE, admins)
    return True

def remove_admin(email: str) -> bool:
    """Remove admin access for a user"""
    admins = read_json(ADMINS_FILE)
    initial_count = len(admins)
    admins = [admin for admin in admins if admin.get("email") != email]
    
    if len(admins) < initial_count:
        write_json(ADMINS_FILE, admins)
        return True
    return False

def get_all_admins() -> List[Dict]:
    """Get all users with admin access"""
    return read_json(ADMINS_FILE)

def get_all_users() -> List[Dict]:
    """Get all users"""
    return read_json(USERS_FILE)

def get_all_reviews() -> List[Dict]:
    """Get all reviews with user and restaurant info"""
    reviews = read_json(REVIEWS_FILE)
    users = {user["id"]: user for user in read_json(USERS_FILE)}
    restaurants = {restaurant["id"]: restaurant for restaurant in read_json(RESTAURANTS_FILE)}
    
    for review in reviews:
        user_id = review.get("user_id")
        restaurant_id = review.get("restaurant_id")
        
        if user_id in users:
            review["username"] = users[user_id].get("username", "Unknown")
        else:
            review["username"] = "Unknown"
            
        if restaurant_id in restaurants:
            review["restaurant_name"] = restaurants[restaurant_id].get("name", "Unknown")
        else:
            review["restaurant_name"] = "Unknown"
    
    return reviews

# Initialize the first admin (your email)
# Update the imports at the top of the file
import os
import json
import shutil
from datetime import datetime
from typing import Dict, List, Optional, Any
import uuid
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Update the init_first_admin function
def init_first_admin():
    """Initialize admin users from .env file"""
    admins = read_json(ADMINS_FILE)
    
    # Get admin emails from .env file
    admin_emails = os.getenv("ADMINS", "")
    if admin_emails:
        # Split by comma and strip whitespace
        email_list = [email.strip() for email in admin_emails.split(",")]
        
        # Add each email as admin if not already present
        for email in email_list:
            if email and not any(admin.get("email") == email for admin in admins):
                admins.append({"email": email})
                print(f"Added admin: {email}")
    
    # If no admins in .env and no existing admins, add a default admin
    if not admins:
        default_email = "admin@example.com"
        admins.append({"email": default_email})
        print(f"No admins specified in .env, initialized default admin: {default_email}")
    
    # Save the updated admin list
    write_json(ADMINS_FILE, admins)

# Call this function to ensure admins are initialized
init_first_admin()