"""
Music generation utilities for Dhive AI Music Generator.
Contains the SunoMusicGenerator class and related music generation functions.
"""

import os
import json
import uuid
import logging
import requests
from datetime import datetime
from typing import List, Dict, Any, Tuple
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
from tenacity import retry, stop_after_attempt, wait_fixed
import cloudinary.uploader

from conf.config import db, SUNO_API_KEY, GEMINI_API_KEY, SUNO_BASE_URL, APP_BASE_URL
from models.song import Song, SongStatus
from utils.helpers import sanitize_for_logging, normalize_content, extract_task_id, upload_to_cloudinary


class SunoMusicGenerator:
    """
    This class handles the music generation process using Suno API and Google Gemini LLM.
    It includes methods for generating lyrics, music, checking status, and handling callbacks.
    """
    
    def __init__(self):
        self.suno_api_key = SUNO_API_KEY
        self.gemini_api_key = GEMINI_API_KEY
        self.base_url = SUNO_BASE_URL
        self.app_base_url = APP_BASE_URL

        # Gemini LLM model init
        self.gemini_model = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            temperature=0.1,
            api_key=self.gemini_api_key
        )

    def _unique_title(self, title: str | None) -> str:
        """
        Helper method to make titles unique.
        Append timestamp + short UUID to a title so it is always distinct.
        Avoids duplicate DB entries.
        """
        base_title = title.strip() if title else "Untitled"
        unique_suffix = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        return f"{base_title}_{unique_suffix}"
    
    def generate_lyrics(self, theme: str, genre: str, mood: str, verse_count: int = 2) -> str:
        """
        Method to generate lyrics using Google Gemini LLM.
        This method takes a theme, genre, mood, and verse count as input and returns the generated lyrics.
        It constructs a prompt for the LLM and processes the response to ensure it is in the correct format.
        """
        prompt = (
            f"Write a {verse_count}-verse song on the theme of '{theme}' in the style of '{genre}', "
            f"with a '{mood}' mood. Format it as proper lyrics with line breaks."
        )
        messages = [HumanMessage(content=prompt)]

        try:
            response = self.gemini_model.invoke(messages)

            # Use the helper to normalize into a string
            lyrics = normalize_content(response.content)

            logging.info(f"🎤 Lyrics generated successfully: {sanitize_for_logging(lyrics)}")
            return lyrics

        except Exception as e:
            logging.error(f"🛑 Error from Gemini model: {sanitize_for_logging(str(e))}", exc_info=True)
            raise Exception(f"Gemini generation failed: {str(e)}")

    def generate_music(
            self,
            lyrics: str,
            style: str,
            title: str | None = None,
            mood: str | None = None,
            theme: str | None = None,
            callback_url: str | None = None,
            custom_mode: bool = True,
            instrumental: bool = False,
            task_id: str | None = None  # ignored on purpose; Suno will assign
        ) -> Tuple[Dict[str, Any], int]:
        """
        Method to generate music using Suno API.
        This method takes lyrics, style, title, mood, theme, and other parameters to generate music.
        It constructs a payload for the Suno API and handles the response, including checking for existing songs in the database.
        It also generates a unique task ID based on the content to avoid duplicates.
        """
        title = title or "Untitled"
        mood = mood or ""
        theme = theme or ""
        logging.info("🎵 Starting music generation process...")

        # Build callback_url automatically if not provided
        if not callback_url:
            callback_url = f"{self.app_base_url.rstrip('/')}/receive_song"
            logging.info(f"🔄 Auto-generated callback_url: {callback_url}")

        headers = {
            "Authorization": f"Bearer {self.suno_api_key}",
            "Content-Type": "application/json",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/115.0 Safari/537.36"
            )
        }

        # Build payload for Suno API
        payload: Dict[str, Any] = {
            "customMode": custom_mode,
            "instrumental": instrumental,
            "prompt": lyrics,
            "title": title,
            "mood": mood,
            "theme": theme,
            "model": "V4_5",
            "callbackUrl": callback_url
        }

        # Only include style if it's not "instrumental"
        if style and style.strip().lower() != "instrumental":
            payload["style"] = style

        logging.info("🎼 Payload to Suno:\n%s", json.dumps(payload, indent=2))
        try:
            resp = requests.post(f"{self.base_url}/api/v1/generate", headers=headers, json=payload, timeout=30)
            logging.info(f"Suno raw response status: {resp.status_code}")
            logging.info(f"Suno raw response text: {resp.text}")

            # Parse
            try:
                resp_json = resp.json()
            except Exception as e:
                logging.error(f"Failed to parse Suno response as JSON: {e}")
                return {"error": "Invalid response from Suno", "raw_response": resp.text}, 502

            # Handle non-200 HTTP or Suno code
            if resp.status_code != 200 or resp_json.get("code") != 200:
                msg = resp_json.get("msg") or "Suno error"
                return {
                    "error": msg,
                    "raw_response": resp_json
                }, 502

            # Normalize Suno task id from multiple possible shapes/keys
            data_field = resp_json.get("data")
            suno_task_id = None
            if isinstance(data_field, dict):
                suno_task_id = (
                    data_field.get("taskId") or
                    data_field.get("task_id") or
                    resp_json.get("taskId") or
                    resp_json.get("task_id")
                )
            elif isinstance(data_field, list) and data_field:
                first = data_field[0] or {}
                suno_task_id = (
                    first.get("taskId") or
                    first.get("task_id") or
                    first.get("id") or
                    resp_json.get("taskId") or
                    resp_json.get("task_id")
                )

            if not suno_task_id:
                return {
                    "error": "Suno did not return a recognizable task id",
                    "raw_response": resp_json
                }, 502

            # Persist (audio_url=None for now)
            try:
                existing = Song.query.filter_by(task_id=suno_task_id).first()
                if not existing:
                    song = Song(
                        task_id=suno_task_id,
                        title=title,
                        lyrics=lyrics,
                        style=style,
                        mood=mood,
                        theme=theme,
                        status=SongStatus.processing
                    )
                    db.session.add(song)
                    db.session.commit()
                    logging.info(f"📝 Created Song row with task_id={suno_task_id}")
            except Exception as db_err:
                logging.error(f"DB insert failed for task_id={suno_task_id}: {db_err}", exc_info=True)

            # Inform caller that generation started (no audio yet)
            out = {
                "message": "Generation started",
                "task_id": suno_task_id,
                # Keep shape compatible with your generate_song checks:
                "data": {"taskId": suno_task_id},
                "audio_url": None
            }
            return out, 202

        except Exception as e:
            logging.error(f"Unexpected error in generate_music: {e}", exc_info=True)
            return {"error": "Unexpected error", "details": str(e)}, 500

    def generate_song(
        self,
        title: str,
        theme: str,
        genre: str,
        mood: str,
        style: str,
        instrumental: bool = False
    ) -> Tuple[Dict[str, Any], int]:
        """
        Method to generate a song with lyrics and music.
        This method combines the lyrics generation and music generation processes.
        It takes title, theme, genre, mood, style, callback URL, and instrumental flag as input.
        It returns the generated song metadata, including lyrics and audio URL if available.
        """
        logging.info(f"Creating song: title={sanitize_for_logging(title)}, theme={theme}, genre={genre}, mood={mood}")

        try:
            # Make title unique
            title = self._unique_title(title)

            # Generate lyrics
            lyrics = self.generate_lyrics(theme=theme, genre=genre, mood=mood)
            logging.info("📝 Lyrics generated successfully")

            # Call generate_music and let it handle task_id creation
            response_data, status = self.generate_music(
                lyrics=lyrics,
                style=style,
                title=title,
                mood=mood,
                theme=theme,
                custom_mode=True,
                instrumental=instrumental
            )

            # Handle Suno API returning None
            if not response_data or response_data.get("data") is None:
                logging.error(f"❌ Suno API returned no data. Response: {response_data}")
                return {"error": "Suno API returned no data", "raw_response": response_data}, 500

            # get task id returned by generate_music
            task_id = response_data.get("task_id") or response_data.get("data", {}).get("taskId")

            # --- Handle 202 Processing ---
            if status == 202:
                logging.info(f"ℹ️ Song is still processing for task_id: {task_id}")
                return {
                    "message": "Song is still processing.",
                    "task_id": task_id,
                    "lyrics": lyrics
                }, 202

            # If successful, save new song to DB (if not already exists)
            if status == 200:
                task_id = task_id or response_data.get("data", {}).get("taskId")
                existing_song = Song.query.filter_by(task_id=task_id).first()

                if not existing_song:
                    try:
                        # Use constructor signature that exists: do not pass audio_url keyword
                        song = Song(
                            title=title,
                            lyrics=lyrics,
                            style=style,
                            mood=mood,
                            theme=theme,
                            task_id=task_id,
                            status=SongStatus.processing
                        )
                        db.session.add(song)
                        db.session.commit()
                        logging.info(f"🎵 Saved new song to DB with task_id: {task_id}")
                    except Exception as db_error:
                        logging.error(f"❌ DB insert failed: {sanitize_for_logging(str(db_error))}", exc_info=True)

                # Enrich response to client
                response_data["lyrics"] = lyrics
                response_data["code"] = 200
                response_data["msg"] = "success"
                response_data["data"] = {"taskId": task_id}

            return response_data, status

        except Exception as e:
            logging.error(f"❌ Failed to create song: {sanitize_for_logging(str(e))}", exc_info=True)
            return {"error": f"Lyrics or music generation failed: {str(e)}"}, 500

    def check_status(self, task_id: str) -> Tuple[Dict[str, Any], int]:
        """
        Method to check the status of a music generation task.
        This method polls the Suno API for the status of a task using its task ID.
        """
        headers = {"Authorization": f"Bearer {self.suno_api_key}"}
        try:
            # https://api.sunoapi.org/api/v1/generate/record-info
            url = f"{self.base_url}/api/v1/generate/record-info/?taskId={task_id}"
            resp = requests.get(url, headers=headers, timeout=30)
            text = resp.text
            logging.info(f"🔎 Suno status HTTP {resp.status_code}: {text}")

            # Handle Suno returning 404 or non-JSON
            try:
                js = resp.json()
            except Exception:
                return {"error": "Invalid JSON from Suno", "raw_response": text}, resp.status_code

            # If Suno explicitly says task not found, return gracefully
            if resp.status_code == 404 or js.get("status") == 404:
                return {
                    "task_id": task_id,
                    "status": "not_found",
                    "message": js.get("message", "Task not found")
                }, 404

            # If Suno returns a general error
            if resp.status_code != 200 or js.get("code") not in (200, None):
                return {
                    "task_id": task_id,
                    "status": "error",
                    "message": js.get("msg") or js.get("error") or "Unknown error",
                    "raw_response": js
                }, resp.status_code

            # Suno sometimes wraps data differently
            data_field = js.get("data")
            audio_url = None

            if isinstance(data_field, list) and data_field:
                audio_url = data_field[0].get("audio_url") or data_field[0].get("audioUrl")
            elif isinstance(data_field, dict):
                audio_url = data_field.get("audio_url") or data_field.get("audioUrl")

            if audio_url:
                return {
                    "task_id": task_id,
                    "status": "completed",
                    "audio_url": audio_url
                }, 200

            # Still pending
            return {
                "task_id": task_id,
                "status": "pending"
            }, 202

        except requests.exceptions.RequestException as e:
            return {"error": str(e)}, 500


@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
def upload_audio_to_cloudinary_from_buffer(audio_buffer, public_id: str) -> str:
    """
    Function to upload audio to Cloudinary with retry logic.
    Uploads audio to Cloudinary with retry logic.
    Accepts a BytesIO buffer or a local file path.
    Returns the secure Cloudinary URL.
    """
    try:
        result = cloudinary.uploader.upload(
            audio_buffer,
            resource_type="video",  # Cloudinary treats audio as video
            folder="Dhive_ai_songs",
            public_id=public_id,
            overwrite=True
        )
        cloudinary_url = result.get("secure_url")
        logging.info(f"✅ Uploaded to Cloudinary successfully: {cloudinary_url}")
        return cloudinary_url
    except Exception as e:
        logging.error(f"❌ Cloudinary upload attempt failed: {e}", exc_info=True)
        raise  # retry decorator will handle retries


def poll_for_audio(task_id, interval=5, retries=12):
    """
    Function to poll for audio availability.
    This function receives the audio URL from Suno and uploads it to Cloudinary.
    """
    import time
    from requests.exceptions import RequestException
    
    base_url = os.getenv("APP_BASE_URL", "http://127.0.0.1:5000")
    status_url = f"{base_url}/check_status/{task_id}"
    
    for attempt in range(retries):
        try:
            response = requests.get(status_url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get("audio_url"):
                    logging.info(f"✅ Song ready for task {task_id}: {data['audio_url']}")
                    print(f"✅ Song ready: {data['audio_url']}")
                    return data["audio_url"]
                else:
                    print(f"⏳ Attempt {attempt + 1}/{retries}: Not ready yet, retrying...")
            else:
                print(f"⚠️ Attempt {attempt + 1}/{retries}: Error polling, status code: {response.status_code}")
        except RequestException as e:
            logging.error(f"❌ Network error during polling for task {task_id}, attempt {attempt + 1}/{retries}: {e}")
            print(f"⚠️ Attempt {attempt + 1}/{retries}: Network error during polling: {e}")
        time.sleep(interval)
    
    logging.warning(f"🛑 Max retries ({retries}) reached for task {task_id}. Song not ready.")
    print(f"❌ Max retries ({retries}) reached. Song still not ready.")
    return None
