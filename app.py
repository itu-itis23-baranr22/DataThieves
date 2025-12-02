# app.py
import os
from flask import Flask, render_template
from dotenv import load_dotenv
from extensions import mysql

def create_app():
    load_dotenv()

    app = Flask(__name__, template_folder="templates")

    # --- Config ---
    app.secret_key = os.getenv("SECRET_KEY", "dev_secret_key")
    app.config["MYSQL_HOST"] = os.getenv("MYSQL_HOST", "127.0.0.1")
    app.config["MYSQL_USER"] = os.getenv("MYSQL_USER", "root")
    app.config["MYSQL_PORT"] = int(os.getenv("MYSQL_PORT", 3306))
    app.config["MYSQL_PASSWORD"] = os.getenv("MYSQL_PASSWORD", "")
    app.config["MYSQL_DB"] = os.getenv("MYSQL_DB", "local_stats")
    app.config["MYSQL_CURSORCLASS"] = "DictCursor"

    # MySQL'i app'e bağla
    mysql.init_app(app)

    # --- Blueprint'ler ---
    from blueprints.posts import posts_bp
    from blueprints.post_history import post_history_bp
    from blueprints.users_badges import users_badges_bp
    from blueprints.comments_votes import comments_votes_bp
    from blueprints.tags_postlinks import tags_postlinks_bp

    app.register_blueprint(posts_bp)
    app.register_blueprint(post_history_bp)
    app.register_blueprint(users_badges_bp)
    app.register_blueprint(comments_votes_bp)
    app.register_blueprint(tags_postlinks_bp)

    # --- Ortak basit sayfalar ---
    @app.route("/", endpoint="index")
    def index():
        return render_template("index.html")

    @app.route("/tables", endpoint="tables")
    def tables():
        return render_template("tables.html")

    @app.errorhandler(404)
    def not_found_error(error):
        return (
            "<h1>404 Not Found</h1>"
            "<p>The page you are looking for could not be found. Please check the URL.</p>",
            404,
        )

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
