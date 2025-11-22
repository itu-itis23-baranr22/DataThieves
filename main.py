from flask import Flask,render_template,flash,redirect,url_for,session,logging,request
from flask_mysqldb import MySQL
import mysql.connector
from mysql.connector import Error
from passlib.hash import sha256_crypt
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
class RegisterForm(Form):
    Displayname = StringField("Username",validators=[validators.Length(min = 4,max = 25)])
    id = PasswordField("Id",validators=[
        validators.DataRequired(message = "Lütfen bir id belirleyin"),
        validators.EqualTo(fieldname = "confirm",message="id uyuşmuyor...")
    ])
    confirm = PasswordField("Id Doğrula")
class LoginForm(Form):
    Displayname = StringField("Username")
    id = PasswordField("Id")

app = Flask(__name__,template_folder="tables")


mysql = MySQL(app)


@app.route("/")
def index():
    return render_template("index.html")

@app.route("/tables")
def tables():
    return render_template("tables.html")

@app.route("/register",methods = ["GET","POST"])
def register():
    form = RegisterForm(request.form)

    if request.method == "POST" and form.validate():
        Displayname = form.Displayname.data
        id = sha256_crypt.encrypt(form.password.data)

        cursor = mysql.connection.cursor()

        sorgu = "Insert into users(Displayname,id) VALUES(%s,%s)"

        cursor.execute(sorgu,(Displayname,id))
        mysql.connection.commit()

        cursor.close()
        flash("Başarıyla Kayıt Oldunuz...","success")
        return redirect(url_for("login"))
    else:
        return render_template("register.html",form = form)


@app.errorhandler(404)
def not_found_error(error):
    return "<h1>404 Not Found</h1><p>Aradığınız sayfa bulunamadı. Lütfen URL'yi kontrol edin.</p>", 404


if __name__ == "__main__":

    app.run(debug=True)


