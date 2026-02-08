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
    role = db.Column(db.String(20), default='user')  # 'user' or 'admin'

    # Relationships
    style_models = db.relationship('StyleModel', backref='user', lazy=True, cascade='all, delete-orphan')
    documents = db.relationship('Document', backref='author', lazy=True, cascade='all, delete-orphan')

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

class StyleModel(db.Model):
    """
    StyleModel for storing trained n-gram models.
    Each user can have multiple style models trained from different text sources.
    """
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    model_data = db.Column(db.Text, nullable=False)  # JSON-encoded n-gram data
    name = db.Column(db.String(100), nullable=False)
    trained_at = db.Column(db.DateTime, default=datetime.utcnow)  # Timestamp for when model was trained
