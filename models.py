from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(db.Model, UserMixin):
    """
    User model for authentication and authorization.
    Inherits from UserMixin to provide Flask-Login integration.
    """
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default='user')
    name = db.Column(db.String(100), nullable=False)
    gender = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    address = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    documents = db.relationship('Document', backref='author', lazy=True, cascade='all, delete-orphan')
    quote_entries = db.relationship('QuoteEntry', backref='user', lazy=True, cascade='all, delete-orphan')

class Document(db.Model):
    """
    Document model for storing user-created documents.
    Tracks content, word count, and modification timestamps.
    """
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    word_count = db.Column(db.Integer, default=0)
    last_modified = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class QuoteEntry(db.Model):
    """
    Stores a canonical quote with its normalized form for fast lookup.
    Optionally linked to a user who added it (NULL for system-seeded quotes).
    """
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    quote_text = db.Column(db.Text, nullable=False)
    quote_normalized = db.Column(db.String(500), nullable=False, index=True, unique=True)
    source_label = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship to analysis chunks
    analysis_chunks = db.relationship('AnalysisChunk', backref='quote_entry', lazy=True, cascade='all, delete-orphan')


class AnalysisChunk(db.Model):
    """
    Stores a single analysis paragraph linked to a QuoteEntry.
    quality_score allows ranking when multiple chunks exist for one quote.
    """
    id = db.Column(db.Integer, primary_key=True)
    quote_id = db.Column(db.Integer, db.ForeignKey('quote_entry.id'), nullable=False)
    chunk_text = db.Column(db.Text, nullable=False)
    quality_score = db.Column(db.Float, default=1.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

