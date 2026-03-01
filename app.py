"""
Glint - Quote Analysis Retrieval Application

Routes:
    /                        - Home page (redirects based on auth status)
    /signup                  - User registration
    /login                   - User authentication
    /logout                  - User logout
    /dashboard               - User document management (CRUD)
    /document/new            - Create a new document
    /document/<id>/update    - Save document content
    /document/delete/<id>    - Delete a document
    /document/upload         - Upload a .txt file as a document
    /admin                   - Administrator panel (admin only)
    /admin/delete_user/<id>  - Delete a user account (admin only)
    /admin/quotes/add        - Add/merge quote-analysis entries (admin only)
    /api/quotes/search?q=    - Keyword search and ranking of quotes (JSON API)

Author: Steve
Date: February 2025
"""

import re
from pathlib import Path
from functools import wraps

from flask import Flask, jsonify, render_template, request, redirect, url_for, flash, abort
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

from models import db, User, Document, QuoteEntry, AnalysisChunk, Tag, quote_tags
from quote_engine import search_quotes

app = Flask(__name__)

# Configure SQLite database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///glint.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your-secret-key-here'  # Required for sessions and CSRF protection

# Initialize extensions
db.init_app(app)
login_manager = LoginManager(app)  # Initialize Flask-Login
login_manager.login_view = 'login'

# User loader callback for Flask-Login
# This tells Flask-Login how to reload the user object from the user ID stored in the session
@login_manager.user_loader
def load_user(user_id):
    """
    Load user by ID for Flask-Login.
    Called on each request to retrieve the current user from the session.
    """
    return User.query.get(int(user_id))


def admin_required(f):
    """
    Decorator to require admin role for route access.
    Must be used after @login_required so current_user is guaranteed loaded.
    Returns 403 Forbidden if the authenticated user is not an admin.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('login'))
        if current_user.role != 'admin':
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


@app.errorhandler(403)
def forbidden(e):
    """Custom 403 Forbidden error page for unauthorized admin access attempts."""
    return render_template('403.html'), 403


# ============================================
# Authentication Routes
# ============================================

@app.route('/')
def home():
    """
    Home route - redirects authenticated users to their appropriate dashboard.
    Unauthenticated users see the landing page.
    """
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('admin'))
        return redirect(url_for('dashboard'))
    return redirect(url_for('landing'))


@app.route('/home')
def landing():
    """
    Landing page route - displays marketing page for unauthenticated users.
    Authenticated users are redirected to their dashboard.
    """
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('admin'))
        return redirect(url_for('dashboard'))
    return render_template('landing.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    """
    User registration route.
    - GET: Display signup form
    - POST: Create new user account with hashed password
    Security: Uses Werkzeug password hashing with automatic salting
    """
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        name = request.form.get('name')
        gender = request.form.get('gender')
        email = request.form.get('email')
        address = request.form.get('address')

        # Validate input
        if not username or not password or not name or not email:
            flash('All required fields must be filled.', 'error')
            return redirect(url_for('signup'))

        # Check if username already exists
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists. Please choose another.', 'error')
            return redirect(url_for('signup'))

        # Check if email already exists
        existing_email = User.query.filter_by(email=email).first()
        if existing_email:
            flash('Email already registered. Please use another.', 'error')
            return redirect(url_for('signup'))

        # Get role from the signup form dropdown
        role = request.form.get('role', 'user')
        if role not in ('user', 'admin'):
            role = 'user'

        # Hash password for secure database storage
        hashed_password = generate_password_hash(password)

        # Create new user
        new_user = User(username=username, password_hash=hashed_password, role=role, 
                        name=name, gender=gender, email=email, address=address)
        db.session.add(new_user)
        db.session.commit()

        flash('Account created successfully! Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    User login route.
    - GET: Display login form
    - POST: Authenticate user and create session
    Security: Verifies password hashes using Werkzeug
    """
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = request.form.get('remember', False)

        # Find user by username
        user = User.query.filter_by(username=username).first()

        # Verify password hash against submitted password
        if user and check_password_hash(user.password_hash, password or ''):
            # Log the user in and create a session
            login_user(user, remember=remember)
            flash('Logged in successfully!', 'success')

            # Redirect admin to admin panel, regular users to dashboard
            if user.role == 'admin':
                return redirect(url_for('admin'))
            return redirect(url_for('dashboard'))
        else:
            # Authentication failed
            flash('Invalid username or password.', 'error')

    return render_template('login.html')

@app.route('/logout')
@login_required  # Only authenticated users can logout
def logout():
    """
    User logout route.
    Destroys the user session and redirects to landing page.
    """
    logout_user()
    flash('Logged out successfully.', 'success')
    return redirect(url_for('landing'))

# ============================================
# Placeholder Routes (to be implemented later)
# ============================================

@app.route('/dashboard')
@login_required  # Requires user to be logged in
def dashboard():
    """
    User dashboard with document list and selected document editor.
    """
    selected_doc_id = request.args.get('doc_id', type=int)
    documents = (
        Document.query
        .filter_by(user_id=current_user.id)
        .order_by(Document.last_modified.desc())
        .all()
    )

    selected_document = None
    if selected_doc_id is not None and documents:
        selected_document = next((doc for doc in documents if doc.id == selected_doc_id), None)
        if selected_document is None:
            flash('Requested document was not found.', 'error')
    elif documents and selected_doc_id is None:
        selected_document = documents[0]

    total_quotes = QuoteEntry.query.count()
    total_chunks = AnalysisChunk.query.count()

    # Fetch all quotes with their analysis chunks for the quote bank panel
    quotes = QuoteEntry.query.order_by(QuoteEntry.created_at.desc()).all()

    return render_template(
        'dashboard.html',
        documents=documents,
        selected_document=selected_document,
        total_quotes=total_quotes,
        total_chunks=total_chunks,
        quotes=quotes
    )


@app.route('/document/new', methods=['POST'])
@login_required
def new_document():
    """Create a new empty document for the current user."""
    title = request.form.get('title', '').strip() or 'Untitled Document'
    document = Document(user_id=current_user.id, title=title, content='', word_count=0)
    db.session.add(document)
    db.session.commit()
    flash(f'Document "{title}" created.', 'success')
    return redirect(url_for('dashboard', doc_id=document.id))


@app.route('/document/<int:doc_id>/update', methods=['POST'])
@login_required
def update_document(doc_id):
    """Update title/content for a document the current user owns."""
    document = Document.query.get_or_404(doc_id)
    if document.user_id != current_user.id:
        flash('Unauthorized document access.', 'error')
        return redirect(url_for('dashboard'))

    title = request.form.get('title', '').strip() or 'Untitled Document'
    content = request.form.get('content')
    if content is None or content == '':
        content = document.content
    content = content or ''
    plain_text = re.sub(r'<[^>]+>', ' ', content)
    word_count = len(plain_text.split())

    document.title = title
    document.content = content
    document.word_count = word_count
    db.session.commit()

    flash('Document saved.', 'success')
    return redirect(url_for('dashboard', doc_id=document.id))


@app.route('/document/delete/<int:doc_id>', methods=['POST'])
@login_required
def delete_document(doc_id):
    """Delete a document if it belongs to the current user."""
    document = Document.query.get_or_404(doc_id)
    if document.user_id != current_user.id:
        flash('Unauthorized document access.', 'error')
        return redirect(url_for('dashboard'))

    title = document.title
    db.session.delete(document)
    db.session.commit()
    flash(f'Document "{title}" deleted.', 'success')
    return redirect(url_for('dashboard'))


@app.route('/document/upload', methods=['POST'])
@login_required
def upload_document():
    """
    Upload a .txt file and create a document from its contents.
    """
    file = request.files.get('file')
    if file is None or file.filename is None or file.filename.strip() == '':
        flash('Please choose a text file to upload.', 'error')
        return redirect(url_for('dashboard'))

    filename = secure_filename(file.filename)
    if not filename.lower().endswith('.txt'):
        flash('Only .txt files are allowed.', 'error')
        return redirect(url_for('dashboard'))

    raw_bytes = file.read()
    content = raw_bytes.decode('utf-8', errors='ignore').strip()
    if not content:
        flash('Uploaded file is empty.', 'error')
        return redirect(url_for('dashboard'))

    title = Path(filename).stem or 'Uploaded Document'
    document = Document(
        user_id=current_user.id,
        title=title,
        content=content,
        word_count=len(content.split())
    )
    db.session.add(document)
    db.session.commit()

    flash(f'Uploaded "{filename}" as a new document.', 'success')
    return redirect(url_for('dashboard', doc_id=document.id))

@app.route('/admin/create_user', methods=['POST'])
@login_required
@admin_required
def create_user():
    """
    Create a new user from the admin panel.
    Accepts username and password, hashes the password before storing.
    """
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')
    role = request.form.get('role', 'user')

    if not username or not password:
        flash('Username and password are required.', 'error')
        return redirect(url_for('admin'))

    if len(password) < 6:
        flash('Password must be at least 6 characters.', 'error')
        return redirect(url_for('admin'))

    existing_user = User.query.filter_by(username=username).first()
    if existing_user:
        flash('Username already exists.', 'error')
        return redirect(url_for('admin'))

    hashed_password = generate_password_hash(password)
    new_user = User(
        username=username,
        password_hash=hashed_password,
        role=role,
        name=username,
        gender='prefer_not_to_say',
        email=f'{username}@local',
        address='Not provided'
    )
    db.session.add(new_user)
    db.session.commit()

    flash(f'User "{username}" created successfully!', 'success')
    return redirect(url_for('admin'))


@app.route('/admin')
@login_required
@admin_required
def admin():
    """
    Admin dashboard showing system statistics and user management table.
    Protected by both @login_required and @admin_required decorators.
    Non-admin users receive a 403 Forbidden response.
    """
    search_query = request.args.get('q', '').strip()

    # Get all users ordered by ID for the management table
    # Apply search filter if query provided
    if search_query:
        all_users = User.query.filter(
            User.username.ilike(f'%{search_query}%')
        ).order_by(User.id).all()
    else:
        all_users = User.query.order_by(User.id).all()

    # Get recent documents for overview (limit 50)
    recent_documents = Document.query.order_by(Document.created_at.desc()).limit(50).all()

    # Aggregate system-wide statistics for the dashboard overview
    total_users = User.query.filter_by(role='user').count()
    total_documents = Document.query.count()
    total_quotes = QuoteEntry.query.count()
    total_chunks = AnalysisChunk.query.count()
    total_words = db.session.query(db.func.sum(Document.word_count)).scalar() or 0

    stats = {
        'total_users': total_users,
        'total_documents': total_documents,
        'total_quotes': total_quotes,
        'total_chunks': total_chunks,
        'total_words': total_words,
    }

    return render_template('admin.html', users=all_users, stats=stats, search_query=search_query, documents=recent_documents)


@app.route('/admin/delete_user/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    """
    Delete a user and all their related data (documents, quotes, suggestion logs).
    Cascade delete is handled by SQLAlchemy relationship configuration.
    Admins cannot delete their own account to prevent lockout.
    """
    user = User.query.get_or_404(user_id)

    # Safety check: prevent admin from deleting themselves
    if user.id == current_user.id:
        flash('Cannot delete your own account.', 'error')
        return redirect(url_for('admin'))

    username = user.username
    try:
        db.session.delete(user)
        db.session.commit()
        flash(f'User "{username}" deleted successfully.', 'success')
    except Exception:
        db.session.rollback()
        flash(f'Error deleting user "{username}". Please try again.', 'error')
    return redirect(url_for('admin'))


@app.route('/admin/delete_document/<int:doc_id>', methods=['POST'])
@login_required
@admin_required
def admin_delete_document(doc_id):
    """
    Delete a document. Admins can delete any document.
    """
    document = Document.query.get_or_404(doc_id)
    title = document.title
    try:
        db.session.delete(document)
        db.session.commit()
        flash(f'Document "{title}" deleted successfully.', 'success')
    except Exception:
        db.session.rollback()
        flash(f'Error deleting document "{title}". Please try again.', 'error')
    return redirect(url_for('admin'))


# ============================================
# Admin Quote Management
# ============================================

def normalize_text(text):
    """Normalize text for quote matching: lowercase and collapse whitespace."""
    if text is None:
        return ""
    return " ".join(str(text).lower().split())

@app.route('/admin/quotes/add', methods=['POST'])
@login_required
@admin_required
def admin_add_quote():
    """
    Admin-only route to add a quote with analysis chunks.
    Blocks duplicate normalized quotes; merges new chunks into existing quotes.
    """

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid JSON payload."}), 400

    quote_text = (data.get('quote_text') or '').strip()
    source_label = (data.get('source_label') or '').strip() or None
    analysis_chunks = data.get('analysis_chunks', [])

    if not quote_text:
        return jsonify({"error": "quote_text is required."}), 400
    if not isinstance(analysis_chunks, list) or not analysis_chunks:
        return jsonify({"error": "analysis_chunks must be a non-empty list of strings."}), 400

    normalized = normalize_text(quote_text)
    existing = QuoteEntry.query.filter_by(quote_normalized=normalized).first()

    if existing:
        # Merge: add only new chunks
        existing_texts = {normalize_text(c.chunk_text) for c in existing.analysis_chunks}
        added = 0
        for chunk_str in analysis_chunks:
            chunk_str = str(chunk_str).strip()
            if not chunk_str:
                continue
            if normalize_text(chunk_str) not in existing_texts:
                db.session.add(AnalysisChunk(quote_id=existing.id, chunk_text=chunk_str))
                existing_texts.add(normalize_text(chunk_str))
                added += 1
        db.session.commit()
        return jsonify({"status": "merged", "quote_id": existing.id, "chunks_added": added})

    quote = QuoteEntry(
        user_id=current_user.id,
        quote_text=quote_text,
        quote_normalized=normalized,
        source_label=source_label
    )
    db.session.add(quote)
    db.session.flush()  # get quote.id before adding chunks

    for chunk_str in analysis_chunks:
        chunk_str = str(chunk_str).strip()
        if chunk_str:
            db.session.add(AnalysisChunk(quote_id=quote.id, chunk_text=chunk_str))

    db.session.commit()
    return jsonify({"status": "created", "quote_id": quote.id, "chunks_added": len(analysis_chunks)})


# ============================================
# User Quote Management (CRUD)
# ============================================

def get_or_create_tag(name, category):
    """Get an existing tag or create a new one. Name is stored lowercase-stripped."""
    name = name.strip().lower()
    if not name:
        return None
    tag = Tag.query.filter_by(name=name, category=category).first()
    if not tag:
        tag = Tag(name=name, category=category)
        db.session.add(tag)
    return tag


@app.route('/quotes/new', methods=['GET', 'POST'])
@login_required
def add_quote():
    """Display the quote creation page or process quote submission."""
    if request.method == 'POST':
        quote_text = request.form.get('quote_text', '').strip()
        source_label = request.form.get('source_label', '').strip() or None
        themes_raw = request.form.get('themes', '').strip()
        techniques_raw = request.form.get('techniques', '').strip()

        if not quote_text:
            flash('Quote text is required.', 'error')
            return redirect(url_for('add_quote'))

        normalized = normalize_text(quote_text)
        existing = QuoteEntry.query.filter_by(quote_normalized=normalized).first()

        if existing:
            flash('This quote already exists in the bank.', 'error')
            return redirect(url_for('add_quote'))

        quote = QuoteEntry(
            user_id=current_user.id,
            quote_text=quote_text,
            quote_normalized=normalized,
            source_label=source_label
        )
        db.session.add(quote)

        for name in themes_raw.split(','):
            tag = get_or_create_tag(name, 'theme')
            if tag:
                quote.tags.append(tag)

        for name in techniques_raw.split(','):
            tag = get_or_create_tag(name, 'technique')
            if tag:
                quote.tags.append(tag)

        db.session.commit()

        flash('Quote added successfully.', 'success')
        return redirect(url_for('quote_bank'))

    return render_template('add_quote.html')


@app.route('/quotes/edit/<int:quote_id>', methods=['POST'])
@login_required
def edit_quote(quote_id):
    """Update an existing quote's text, source, and tags."""
    quote = QuoteEntry.query.get_or_404(quote_id)

    quote_text = request.form.get('quote_text', '').strip()
    source_label = request.form.get('source_label', '').strip() or None
    themes_raw = request.form.get('themes', '').strip()
    techniques_raw = request.form.get('techniques', '').strip()

    if not quote_text:
        flash('Quote text is required.', 'error')
        return redirect(url_for('quote_bank'))

    normalized = normalize_text(quote_text)
    existing = QuoteEntry.query.filter_by(quote_normalized=normalized).first()
    if existing and existing.id != quote.id:
        flash('Another quote with this text already exists.', 'error')
        return redirect(url_for('quote_bank'))

    quote.quote_text = quote_text
    quote.quote_normalized = normalized
    quote.source_label = source_label

    quote.tags.clear()
    for name in themes_raw.split(','):
        tag = get_or_create_tag(name, 'theme')
        if tag:
            quote.tags.append(tag)
    for name in techniques_raw.split(','):
        tag = get_or_create_tag(name, 'technique')
        if tag:
            quote.tags.append(tag)

    db.session.commit()
    flash('Quote updated.', 'success')
    return redirect(url_for('quote_bank'))


@app.route('/quotes/delete/<int:quote_id>', methods=['POST'])
@login_required
def delete_quote(quote_id):
    """
    Allow users to delete any quote (including seeded quotes).
    """
    quote = QuoteEntry.query.get_or_404(quote_id)

    db.session.delete(quote)
    db.session.commit()
    flash('Quote deleted.', 'success')
    return redirect(url_for('quote_bank'))


@app.route('/quotes')
@login_required
def quote_bank():
    """Dedicated Quote Bank page with filtering by themes and techniques."""
    quotes = QuoteEntry.query.order_by(QuoteEntry.created_at.desc()).all()
    themes = Tag.query.filter_by(category='theme').order_by(Tag.name).all()
    techniques = Tag.query.filter_by(category='technique').order_by(Tag.name).all()
    return render_template('quote_bank.html', quotes=quotes, themes=themes, techniques=techniques)


# ============================================
# Quote Search API
# ============================================

@app.route('/api/quotes/search')
@login_required
def api_search_quotes():
    """
    JSON API endpoint for the quote search engine.
    Accepts a query string parameter 'q' and returns ranked quote results.
    Protected by @login_required — unauthenticated requests are redirected.
    """
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify([])

    results = search_quotes(query, limit=5)
    return jsonify(results)


# ============================================
# Database Initialization
# ============================================

# Create database tables if they don't exist
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)
