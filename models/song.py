"""
Database models for Dhive AI Music Generator.
Contains SQLAlchemy models for storing song metadata and status.
"""

import enum
from datetime import datetime
from conf.config import db

# Song status enum
class SongStatus(enum.Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"

# Define the SQLAlchemy model for storing generated song metadata
class Song(db.Model):
    __tablename__ = "song"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    task_id = db.Column(db.String(255), unique=True, nullable=False)

    # Song Metadata
    title = db.Column(db.String(255), nullable=False, default="Untitled")
    lyrics = db.Column(db.Text, nullable=False, default="")
    style = db.Column(db.String(100), nullable=False, default="unknown")
    mood = db.Column(db.String(100), nullable=False, default="neutral")
    theme = db.Column(db.String(100), nullable=False, default="general")
    artist_name = db.Column(db.String(100), nullable=True, default="")
    audio_url = db.Column(db.String(500), nullable=True)  # alias for cloudinary_url

    # URLs
    suno_url = db.Column(db.Text, nullable=True)          # temporary Suno audio link
    cloudinary_url = db.Column(db.Text, nullable=True)    # permanent Cloudinary URL

    # Status + Tracking
    status = db.Column(db.Enum(SongStatus), default=SongStatus.pending, nullable=False)
    retry_count = db.Column(db.Integer, default=0, nullable=False)
    error_message = db.Column(db.Text, nullable=True)

    # Extra Metadata
    duration = db.Column(db.Integer, nullable=True)       # duration in seconds

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Constructor
    def __init__(self, title, lyrics, style, mood, theme, task_id,
                 suno_url=None, cloudinary_url=None, status=SongStatus.pending,
                 artist_name="", duration=None):
        self.title = title
        self.lyrics = lyrics
        self.style = style
        self.mood = mood
        self.theme = theme
        self.task_id = task_id
        self.suno_url = suno_url
        self.cloudinary_url = cloudinary_url
        self.status = status
        self.artist_name = artist_name
        self.duration = duration

    def __repr__(self):
        return f"<Song id={self.id} task_id={self.task_id} status={self.status.value}>"

    def to_dict(self):
        """Return model data as JSON-serializable dict (for API responses)."""
        return {
            "id": self.id,
            "task_id": self.task_id,
            "title": self.title,
            "lyrics": self.lyrics,
            "style": self.style,
            "mood": self.mood,
            "theme": self.theme,
            "artist_name": self.artist_name,
            "suno_url": self.suno_url,        # temporary URL
            "cloudinary_url": self.cloudinary_url,    # permanent URL
            "audio_url": self.cloudinary_url,          # alias for clients expecting audio_url
            "status": self.status.value,
            "retry_count": self.retry_count,
            "error_message": self.error_message,
            "duration": self.duration,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
