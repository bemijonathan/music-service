# Importing necessary libraries
from flask import request, jsonify, send_file
import requests
import json
import logging
from io import BytesIO
import cloudinary
import cloudinary.uploader

# Import from our modular structure
from conf.config import app, db
from models.song import Song, SongStatus
from utils.music_generator import SunoMusicGenerator, upload_audio_to_cloudinary_from_buffer, poll_for_audio
from utils.helpers import sanitize_for_logging, extract_task_id, upload_to_cloudinary

# Import routes (this will register all the routes with the app)
import utils.routes


# Main block
# This block initializes the Flask app and creates the database tables
# It also starts the Flask server and prints a welcome message
if __name__ == '__main__':
    print("🚀 Welcome to Dhive AI - Your AI Music Generator!")
    print("🌟 Initializing SunoMusicGenerator...")
    with app.app_context():
        db.create_all()
    print("✅ SunoMusicGenerator initialized successfully!")
    print("🌐 Flask running at: http://127.0.0.1:5000")
    app.run(debug=True)
