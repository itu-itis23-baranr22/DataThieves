from flask import Flask,render_template,flash,redirect,url_for,session,logging,request
from flask_mysqldb import MySQL
import mysql.connector
from mysql.connector import Error
from wtforms import Form,StringField,TextAreaField,PasswordField,validators


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "logged_in" in session:
            return f(*args, **kwargs)
        else:
            flash("Bu sayfayı görüntülemek için lütfen giriş yapın.","danger")
            return redirect(url_for("login"))

    return decorated_function


app = Flask(__name__,template_folder="tables")


mysql = MySQL(app)


@app.route("/")
def index():
    return render_template("index.html")

@app.route("/tables")
def tables():
    return render_template("tables.html")


@app.errorhandler(404)
def not_found_error(error):
    return "<h1>404 Not Found</h1><p>Aradığınız sayfa bulunamadı. Lütfen URL'yi kontrol edin.</p>", 404


if __name__ == "__main__":

    app.run(debug=True)

