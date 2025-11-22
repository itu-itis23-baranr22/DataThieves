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
    DisplayName = StringField("Username",validators=[validators.Length(min = 4,max = 25)])
    id = PasswordField("Id",validators=[
        validators.DataRequired(message = "Lütfen bir id belirleyin"),
        validators.EqualTo(fieldname = "confirm",message="id uyuşmuyor...")
    ])
    confirm = PasswordField("Id Doğrula")
class LoginForm(Form):
    DisplayName = StringField("Username")
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
        DisplayName = form.DisplayName.data
        id = sha256_crypt.encrypt(form.password.data)

        cursor = mysql.connection.cursor()

        sorgu = "Insert into users(DisplayName,id) VALUES(%s,%s)"

        cursor.execute(sorgu,(DisplayName,id))
        mysql.connection.commit()

        cursor.close()
        flash("Başarıyla Kayıt Oldunuz...","success")
        return redirect(url_for("login"))
    else:
        return render_template("register.html",form = form)

@app.route("/login",methods =["GET","POST"])
def login():
    form = LoginForm(request.form)
    if request.method == "POST":
       DisplayName = form.DisplayName.data
       id_entered = form.id.data

       cursor = mysql.connection.cursor()

       sorgu = "Select * From users where DisplayName = %s"

       result = cursor.execute(sorgu,(DisplayName,))

       if result > 0:
           data = cursor.fetchone()
           real_id = data["id"]
           if sha256_crypt.verify(id_entered,real_id):
               flash("Başarıyla Giriş Yaptınız...","success")

               session["logged_in"] = True
               session["DisplayName"] = DisplayName

               return redirect(url_for("index"))
           else:
               flash("Id'nizi Yanlış Girdiniz...","danger")
               return redirect(url_for("login")) 

       else:
           flash("Böyle bir kullanıcı bulunmuyor...","danger")
           return redirect(url_for("login"))

    
    return render_template("login.html",form = form)

@app.errorhandler(404)
def not_found_error(error):
    return "<h1>404 Not Found</h1><p>Aradığınız sayfa bulunamadı. Lütfen URL'yi kontrol edin.</p>", 404


if __name__ == "__main__":

    app.run(debug=True)


