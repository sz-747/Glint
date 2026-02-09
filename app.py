from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User

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
    User dashboard - placeholder for Task 1.4
    """
    return f"<h1>Welcome {current_user.username}!</h1><p>Dashboard coming soon...</p><a href='/logout'>Logout</a>"

@app.route('/admin')
@login_required  # Requires user to be logged in
def admin():
    """
    Admin panel - placeholder for Task 3.2
    Only accessible to users with admin role
    """
    if current_user.role != 'admin':
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    return f"<h1>Admin Panel</h1><p>Welcome {current_user.username}</p><a href='/logout'>Logout</a>"

# ============================================
# Database Initialization
# ============================================

# Create database tables if they don't exist
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)
