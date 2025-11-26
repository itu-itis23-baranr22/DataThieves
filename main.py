from flask import Flask,render_template,flash,redirect,url_for,session,logging,request
from flask_mysqldb import MySQL
import mysql.connector
from mysql.connector import Error
from passlib.hash import sha256_crypt
from wtforms import Form,StringField,TextAreaField,PasswordField,validators
from functools import wraps


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
    Id = PasswordField("Id",validators=[
        validators.DataRequired(message = "Lütfen bir id belirleyin"),
        validators.EqualTo(fieldname = "confirm",message="id uyuşmuyor...")
    ])
    confirm = PasswordField("Id Doğrula")

class LoginForm(Form):
    DisplayName = StringField("Username")
    id = PasswordField("Id")

app = Flask(__name__,template_folder="tables")

app.config["MYSQL_HOST"] = "Mydatabase"
app.config["MYSQL_PORT"] = 3306
app.config["MYSQL_USER"] = "data"
app.config["MYSQL_PASSWORD"] = "data"
app.config["MYSQL_DB"] = "web_stats"


mysql = MySQL(app)

def test_db_connection():
    with app.app_context():   # <-- create application context
        try:
            cur = mysql.connection.cursor()
            cur.execute("SELECT DATABASE();")
            db_name = cur.fetchone()[0]
            print("Connected to database:", db_name)
        except Exception as e:
            print("Database connection failed:", e)
@app.route("/testdb")
def testdb():
    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT DATABASE();")
        db_name = cur.fetchone()[0]
        return f"Connected to database: {db_name}"
    except Exception as e:
        return f"Database connection failed: {e}"

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/tables")
def tables():
    return render_template("tables.html")


@app.route("/dashboard")
@login_required
def dashboard():
    cursor = mysql.connection.cursor()

    sorgu = "Select * From posts where OwnerDisplayName = %s"

    result = cursor.execute(sorgu,(session["DisplayName"],))

    if result > 0:
        posts = cursor.fetchall()
        return render_template("dashboard.html",posts = posts)
    else:
        return render_template("dashboard.html")
    

@app.route("/register",methods = ["GET","POST"])
def register():
    form = RegisterForm(request.form)

    if request.method == "POST" and form.validate():
        DisplayName = form.DisplayName.data
        Id = sha256_crypt.encrypt(form.Id.data)

        cursor = mysql.connection.cursor()

        sorgu = "Insert into users(DisplayName,id) VALUES(%s,%s)"

        cursor.execute(sorgu,(DisplayName,Id))
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



