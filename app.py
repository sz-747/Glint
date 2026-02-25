import re
from pathlib import Path

from flask import Flask, jsonify, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

from models import db, User, Document, QuoteEntry, AnalysisChunk, SuggestionLog

app = Flask(__name__)

# Configure SQLite database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///glint.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your-secret-key-here'  # Required for sessions and CSRF protection

# Initialize extensions
db.init_app(app)
login_manager = LoginManager(app)  # Initialize Flask-Login
login_manager.login_view = 'login'  # Redirect to login page if user is not authenticated

# User loader callback for Flask-Login
# This tells Flask-Login how to reload the user object from the user ID stored in the session
@login_manager.user_loader
def load_user(user_id):
    """
    Load user by ID for Flask-Login.
    Called on each request to retrieve the current user from the session.
    """
    return User.query.get(int(user_id))

# ============================================
# Text Normalization & Matching Helpers
# ============================================

def normalize_text(text):
    """Normalize text for deterministic quote matching: lowercase, strip punctuation, collapse whitespace."""
    if text is None:
        return ""
    lowered = str(text).lower()
    no_punctuation = re.sub(r"[^\w\s']", " ", lowered)
    collapsed = re.sub(r"\s+", " ", no_punctuation).strip()
    return collapsed


def extract_recent_window(text, max_chars=220):
    """Return the last max_chars characters of text for quote matching."""
    if not text:
        return ""
    return text[-max_chars:]


def find_quote_match(recent_text):
    """
    Match recent_text against stored quotes using exact substring and prefix strategies.
    Returns a dict with quote_id, match_type, score on match, or None.
    """
    normalized = normalize_text(recent_text)
    if not normalized:
        return None

    quotes = QuoteEntry.query.with_entities(QuoteEntry.id, QuoteEntry.quote_normalized).all()

    # Exact: check if any stored normalized quote appears as a substring in the recent text
    for quote_id, quote_norm in quotes:
        if quote_norm in normalized:
            return {"quote_id": quote_id, "match_type": "exact", "score": 1.0}

    # Prefix: check if any stored quote starts with the recent text
    for quote_id, quote_norm in quotes:
        if quote_norm.startswith(normalized) and len(normalized) >= 4:
            return {"quote_id": quote_id, "match_type": "prefix", "score": 0.9}

    return None


# ============================================
# Authentication Routes
# ============================================

@app.route('/')
def home():
    """
    Home route - redirects authenticated users to their appropriate dashboard.
    Unauthenticated users are redirected to login.
    """
    if current_user.is_authenticated:
        # Admin users go to admin panel, regular users go to dashboard
        if current_user.role == 'admin':
            return redirect(url_for('admin'))
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

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

        # Validate input
        if not username or not password:
            flash('Username and password are required.', 'error')
            return redirect(url_for('signup'))

        # Check if username already exists
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists. Please choose another.', 'error')
            return redirect(url_for('signup'))

        # Determine role: if username contains 'admin', make admin
        # This is a simple role assignment logic for demonstration
        role = 'admin' if 'admin' in username.lower() else 'user'

        # Hash password for secure database storage
        hashed_password = generate_password_hash(password)

        # Create new user
        new_user = User(username=username, password_hash=hashed_password, role=role)
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
        remember = request.form.get('remember', False)  # "Remember me" checkbox

        # Find user by username
        user = User.query.filter_by(username=username).first()

        # Verify password hash against submitted password
        if user and check_password_hash(user.password_hash, password):
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
    Destroys the user session and redirects to login page.
    """
    logout_user()
    flash('Logged out successfully.', 'success')
    return redirect(url_for('login'))

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
    if documents:
        if selected_doc_id is not None:
            selected_document = next((doc for doc in documents if doc.id == selected_doc_id), None)
            if selected_document is None:
                flash('Requested document was not found.', 'error')
        if selected_document is None:
            selected_document = documents[0]

    return render_template(
        'dashboard.html',
        documents=documents,
        selected_document=selected_document
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
    content = request.form.get('content', '')
    word_count = len(content.split())

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

@app.route('/admin')
@login_required  # Requires user to be logged in
def admin():
    if current_user.role != 'admin':
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    return f"<h1>Admin Panel</h1><p>Welcome {current_user.username}</p><a href='/logout'>Logout</a>"


# ============================================
# Admin Quote Management
# ============================================

@app.route('/admin/quotes/add', methods=['POST'])
@login_required
def admin_add_quote():
    """
    Admin-only route to add a quote with analysis chunks.
    Blocks duplicate normalized quotes; merges new chunks into existing quotes.
    """
    if current_user.role != 'admin':
        return jsonify({"error": "Admin privileges required."}), 403

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
# Suggestion API
# ============================================

@app.route('/api/suggest-analysis', methods=['POST'])
@login_required
def suggest_analysis():
    """
    Low-latency endpoint for editor-side analysis suggestion retrieval.
    Accepts editor text, runs quote matching, returns best analysis chunk.
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"suggestion": None})

    text = data.get('text', '')
    recent = extract_recent_window(text)
    match = find_quote_match(recent)

    if match is None:
        return jsonify({"suggestion": None, "quote_id": None, "analysis_chunk_id": None, "score": None, "match_type": None})

    chunk = (
        AnalysisChunk.query
        .filter_by(quote_id=match["quote_id"])
        .order_by(AnalysisChunk.quality_score.desc())
        .first()
    )

    if chunk is None:
        return jsonify({"suggestion": None, "quote_id": match["quote_id"], "analysis_chunk_id": None, "score": match["score"], "match_type": match["match_type"]})

    return jsonify({
        "suggestion": chunk.chunk_text,
        "quote_id": match["quote_id"],
        "analysis_chunk_id": chunk.id,
        "score": match["score"],
        "match_type": match["match_type"]
    })


@app.route('/api/log-suggestion', methods=['POST'])
@login_required
def log_suggestion():
    """
    Records suggestion acceptance/display events for analytics.
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"status": "ok"})

    log = SuggestionLog(
        user_id=current_user.id,
        quote_id=data.get('quote_id'),
        analysis_chunk_id=data.get('analysis_chunk_id'),
        typed_context=data.get('typed_context'),
        accepted=bool(data.get('accepted', False))
    )
    db.session.add(log)
    db.session.commit()
    return jsonify({"status": "ok"})


# ============================================
# Database Initialization
# ============================================

# Create database tables if they don't exist
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)
