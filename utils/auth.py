from functools import wraps
from flask import session, flash, redirect, url_for

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "logged_in" in session:
            return f(*args, **kwargs)
        else:
            flash("Please log in to view this page.", "danger")
            return redirect(url_for("posts_bp.login"))
        # IMPORTANT: Points to blueprint login route
    return decorated_function

def is_admin():
    return session.get("is_admin", False)
