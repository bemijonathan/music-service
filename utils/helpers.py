"""
Helper utility functions for Dhive AI Music Generator.
Contains various utility functions for text processing, file handling, and API interactions.
"""

import re
import logging
import cloudinary
import cloudinary.uploader
from urllib.request import urlopen
from tempfile import NamedTemporaryFile
from typing import Any


def sanitize_for_logging(text):
    """
    Function to sanitize text for logging.
    This function ensures that any non-ASCII characters are removed from the text.
    """
    if isinstance(text, str):
        return text.encode('ascii', errors='ignore').decode('ascii')
    return str(text)


def normalize_content(content: Any) -> str:
    """
    Function to normalize content from Gemini/LLM responses.
    This function ensures that the content is always returned as a string, handling different formats gracefully.
    """
    if isinstance(content, list):
        return " ".join(
            item if isinstance(item, str) else item.get("text", "")
            for item in content
        )
    return str(content)


def extract_task_id(item: dict):
    """
    Try to normalize and extract a Suno task ID
    from different possible shapes Suno's API might return.
    """
    if not item or not isinstance(item, dict):
        return None

    # Common top-level keys
    for key in ("id", "task_id", "taskId", "taskID"):
        if key in item and item.get(key):
            return item[key]

    # Sometimes wrapped in a `data` field
    data_field = item.get("data")
    if isinstance(data_field, dict):
        for key in ("id", "task_id", "taskId", "taskID"):
            if key in data_field and data_field.get(key):
                return data_field[key]

    # Sometimes wrapped in a list of dicts under `data`
    if isinstance(data_field, list) and data_field:
        for candidate in data_field:
            if isinstance(candidate, dict):
                for key in ("id", "task_id", "taskId", "taskID"):
                    if candidate.get(key):
                        return candidate[key]

    # Sometimes APIs sneak the taskId under "metadata"
    meta = item.get("metadata")
    if isinstance(meta, dict):
        for key in ("id", "task_id", "taskId", "taskID"):
            if meta.get(key):
                return meta[key]

    # If all fails, return None
    return None


def make_safe_public_id(title: str, task_id: str):
    """
    Helper: sanitize public id for Cloudinary (keep letters, numbers, -, _)
    """
    if not title:
        base = "dhive_song"
    else:
        base = title
    base = base.strip()
    # replace whitespace with underscore, remove problematic chars
    base = re.sub(r"\s+", "_", base)
    base = re.sub(r"[^A-Za-z0-9_\-]", "", base)
    # limit length (Cloudinary allows long names but keep it reasonable)
    base = base[:120]
    return f"{base}_{task_id}"


def upload_to_cloudinary(remote_url: str) -> str:
    """
    Upload helper function for Cloudinary.
    Downloads a file from a remote URL and uploads it to Cloudinary.
    """
    try:
        # Download file temporarily
        with urlopen(remote_url) as response, NamedTemporaryFile(delete=True) as tmp_file:
            tmp_file.write(response.read())
            tmp_file.flush()

            # Upload to Cloudinary
            result = cloudinary.uploader.upload(
                tmp_file.name,
                resource_type="video"
            )
            return result.get("secure_url", "")  # Return empty string if secure_url missing

    except Exception as e:
        logging.error(f"❌ Cloudinary upload failed: {str(e)}", exc_info=True)
        return ""  # always returns string


def try_notify(song, cloudinary_url, task_id):
    """
    Optional: notification helper (placeholder)
    """
    import requests
    
    # Example: if your Song model has an email or webhook_url attribute
    try:
        if getattr(song, "webhook_url", None):
            # send a POST to user's webhook (non-blocking in production, but here synchronous)
            payload = {"task_id": task_id, "audio_url": cloudinary_url}
            try:
                requests.post(song.webhook_url, json=payload, timeout=5)
                logging.info(f"🔔 Notified webhook for task {task_id}")
            except Exception as e:
                logging.warning(f"🔕 Failed to notify webhook for task {task_id}: {e}")
        # Optionally email - adapt this to your mailer
        # if getattr(song, "user_email", None):
        #     send_email(song.user_email, ...)
    except Exception as e:
        logging.warning(f"⚠️ Notification helper error for task {task_id}: {e}")
