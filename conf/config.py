"""
Configuration module for Dhive AI Music Generator.
Contains all configuration settings, environment variables, and app setup.
"""

import os
import logging
import io
import sys
import cloudinary
from dotenv import load_dotenv
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

# Load environment variables
load_dotenv()

# Ensure UTF-8 encoding for stdout
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("Dhive.log", encoding='utf-8'),  # Logs to file
        logging.StreamHandler()                              # Logs to terminal
    ]
)

# Initialize Flask app
app = Flask(__name__,
    static_folder='../views/static',
    template_folder='../views/templates'
)

# SQLAlchemy DB config
# This configuration uses environment variables to securely store database credentials
# Make sure to set these variables in your environment or .env file
app.config['SQLALCHEMY_DATABASE_URI'] = f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@{os.getenv('POSTGRES_HOST')}/{os.getenv('POSTGRES_DB')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize SQLAlchemy
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Cloudinary config
# This configuration uses environment variables to securely store Cloudinary credentials
# Make sure to set these variables in your environment or .env file
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True
)

# API Configuration
SUNO_API_KEY = os.environ.get('SUNO_API_KEY')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
SUNO_BASE_URL = "https://api.sunoapi.org"
APP_BASE_URL = os.environ.get("APP_BASE_URL", "http://localhost:5000")
