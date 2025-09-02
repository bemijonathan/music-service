"""
Flask routes for Dhive AI Music Generator.
Contains all the API endpoint definitions.
"""

import logging
from flask import request, jsonify, send_file, render_template
from io import BytesIO
import requests

from conf.config import app, db
from models.song import Song, SongStatus
from utils.music_generator import SunoMusicGenerator
from utils.helpers import sanitize_for_logging, extract_task_id, upload_to_cloudinary, try_notify
import cloudinary.uploader

# Initialize the SunoMusicGenerator instance
generator = SunoMusicGenerator()


# Route to create a full song (lyrics + music)
# This route handles POST requests to create a new song
@app.route("/create_song", methods=["POST"])
def create_song():
    try:
        data = request.get_json(force=True)

        # Extract parameters from request
        title = data.get("title", "Untitled")
        genre = data.get("genre", "pop")
        mood = data.get("mood", "")
        theme = data.get("theme", "")
        style = data.get("style", genre)  # Default style = genre
        instrumental = False

        # Special handling: if style == "instrumental", force instrumental mode
        if style.lower() == "instrumental":
            instrumental = True
            style = genre  # fallback style for instrumental tracks

        logging.info(f"🎵 Creating song with title='{title}', genre='{genre}', mood='{mood}', theme='{theme}', style='{style}', instrumental={instrumental}")

        # Call generator
        result, status = generator.generate_song(
            title=title,
            genre=genre,
            mood=mood,
            theme=theme,
            style=style,               # FIX: respect user's style
            instrumental=instrumental  # handle instrumental mode
        )

        # Normalize task_id using helper
        task_id = extract_task_id(result)

        return jsonify({
            "message": "Song generation started",
            "task_id": task_id,
            "result": result
        }), status

    except Exception as e:
        logging.error(f"❌ Error in /create_song: {str(e)}")
        return jsonify({"error": str(e)}), 500


# Route to check the status of a music generation task
@app.route("/check_status/<task_id>", methods=["GET"])
def check_status_route(task_id):
    try:
        data, status = generator.check_status(task_id)

        # Handle Suno "Not Found" case
        if status == 404 or (isinstance(data, dict) and data.get("error") == "Not Found"):
            logging.warning(f"⚠️ Suno returned 404 for task_id={task_id}")
            return jsonify({"error": "Task not found on Suno", "task_id": task_id}), 404

        # Handle any other error
        if status != 200 or not isinstance(data, dict):
            return jsonify(data), status

        # Normalize task_id in case Suno responds differently
        normalized_id = extract_task_id(data) or task_id

        # Extract Suno audio URL (supports multiple response shapes)
        suno_audio_url = (
            data.get("audio_url")
            or data.get("suno_url")
            or (data.get("data", {}) if isinstance(data.get("data"), dict) else {}).get("audio_url")
            or (data.get("data", {}) if isinstance(data.get("data"), dict) else {}).get("suno_url")
        )

        # Fetch song from DB
        song = Song.query.filter_by(task_id=normalized_id).first()
        if not song:
            return jsonify({"error": "Song not found"}), 404

        # If Suno audio exists and Cloudinary URL not yet saved, upload to Cloudinary
        if suno_audio_url and not song.cloudinary_url:
            cloudinary_url = upload_to_cloudinary(suno_audio_url)
            song.suno_url = suno_audio_url       # keep Suno link
            song.cloudinary_url = cloudinary_url # permanent link
            song.audio_url = cloudinary_url      # alias for clients
            song.status = SongStatus.completed
            db.session.commit()
            logging.info(f"🎵 Updated Cloudinary URL for task_id {normalized_id}")

        # Return only permanent Cloudinary URL and metadata
        return jsonify({
            "status": song.status.value,
            "task_id": normalized_id,
            "audio_url": song.cloudinary_url,  # permanent URL for client
            "lyrics": song.lyrics
        }), 200 if song.cloudinary_url else 202

    except Exception as e:
        logging.error(f"❌ Error checking task status: {sanitize_for_logging(str(e))}", exc_info=True)
        return jsonify({"error": str(e)}), 500


# Route to handle the callback from Suno API
# This route receives the audio URL from Suno and uploads it to Cloudinary
@app.route("/receive_song", methods=["POST"])
def receive_song():
    try:
        data = request.get_json(force=True)
        task_id = data.get("task_id")
        audio_url = data.get("audio_url")

        # Validate required fields
        if not task_id or not audio_url:
            logging.warning("❌ Missing task_id or audio_url in callback")
            return jsonify({"error": "Missing task_id or audio_url"}), 400

        # Verify task exists in database
        song = Song.query.filter_by(task_id=task_id).first()
        if not song:
            logging.warning(
                f"❌ Song with task_id {task_id} not found in database")
            return jsonify({"error": "Song not found"}), 404

        logging.info(f"📞 Received callback for task_id: {task_id}")

        # Step 1: Download audio from Suno
        try:
            audio_resp = requests.get(audio_url, stream=True, timeout=30)
            audio_resp.raise_for_status()
            audio_file = audio_resp.content
            logging.info(
                f"✅ Downloaded audio from Suno: {len(audio_file)} bytes")
        except requests.exceptions.RequestException as e:
            logging.error(f"❌ Failed to fetch audio from Suno: {e}")
            return jsonify({"error": "Failed to download audio"}), 500

        # Step 2: Upload to Cloudinary using helper function
        try:
            cloudinary_url = upload_to_cloudinary(audio_url)
            if not cloudinary_url:
                raise Exception("Cloudinary upload returned empty URL")
            logging.info(f"✅ Uploaded to Cloudinary: {cloudinary_url}")
        except Exception as e:
            logging.error(f"❌ Cloudinary upload failed: {e}")
            return jsonify({"error": "Cloudinary upload failed"}), 500

        # Step 3: Update DB
        try:
            song.status = SongStatus.completed
            song.suno_url = audio_url       # Suno's temp link
            song.cloudinary_url = cloudinary_url  # Permanent Cloudinary link
            song.audio_url = cloudinary_url      # alias for clients
            db.session.commit()
            logging.info(f"✅ Updated database for task_id {task_id}")
        except Exception as e:
            logging.error(
                f"❌ Database update failed for task_id {task_id}: {e}")
            db.session.rollback()
            return jsonify({"error": "Database update failed"}), 500

        # Optional: Send notification if configured
        try_notify(song, cloudinary_url, task_id)

        logging.info(f"🎉 Song {task_id} processing completed successfully")
        return jsonify({
            "message": "Song stored successfully",
            "task_id": task_id,
            "cloudinary_url": cloudinary_url
        })

    except Exception as e:
        logging.error(
            f"❌ Unexpected error in receive_song callback: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500


# Route to download the generated audio file
# This route takes an audio URL as input and returns the audio file for download
@app.route("/download", methods=["POST"])
def download():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing JSON payload"}), 400

    url = data.get("audio_url")
    if not url:
        return jsonify({"error": "audio_url required"}), 400

    try:
        response = requests.get(url, stream=True)
        if response.status_code == 200:
            return send_file(
                BytesIO(response.content),
                as_attachment=True,
                download_name=f"song_{url.split('/')[-1]}",
                mimetype="audio/mpeg"
            )
        return jsonify({"error": "Failed to download file"}), 500
    except Exception as e:
        logging.error(f"❌ Download failed: {e}")
        return jsonify({"error": "Download failed", "details": str(e)}), 500


# Route to handle the root endpoint
# This route returns a comprehensive API documentation and testing page
@app.route("/", methods=["GET"])
def index():
    return render_template('index.html')


# Health check route
# This route can be used to check if the server is healthy
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy"}), 200
