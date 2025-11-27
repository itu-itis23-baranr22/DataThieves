from flask import Flask,render_template,flash,redirect,url_for,session,logging,request
from flask_mysqldb import MySQL
from passlib.hash import sha256_crypt
from wtforms import Form,StringField,TextAreaField,PasswordField,validators
from functools import wraps
import time

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

# --- Flask App Setup ---

app = Flask(__name__,template_folder="tables")
app.secret_key = "data_thieves_secret" 

app.config["MYSQL_HOST"] = "127.0.0.1"
app.config["MYSQL_USER"] = "root"
app.config["MYSQL_PASSWORD"] = "976431"
app.config["MYSQL_DB"] = "local_stats"
app.config["MYSQL_CURSORCLASS"] = "DictCursor" 


mysql = MySQL(app)

# --- Routes ---

@app.route("/")
def index():
    return render_template("index.html")

################################
# POST HISTORY
################################
@app.route("/postHistory")
def post_history():
    cur = mysql.connection.cursor()
    sql = """
        SELECT Id, PostHistoryTypeId, PostId, RevisionGUID, CreationDate,
               UserId, Text, Comment, UserDisplayName
        FROM postHistory
        LIMIT 100;
    """
    cur.execute(sql)
    rows = cur.fetchall()
    cur.close()
    return render_template("postHistory.html", postHistory=rows)


@app.route("/tables")
def tables():
    return render_template("tables.html")


@app.route("/dashboard")
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
        id_entered = str(form.Id.data) 
        
        hashed_id = sha256_crypt.encrypt(id_entered)

        cursor = mysql.connection.cursor()

        account_id = int(time.time() * 1000) 
        creation_date = '2024-01-01 00:00:00'
        last_access_date = creation_date
    
        sorgu = """
        INSERT INTO users (
            Id, DisplayName, Reputation, CreationDate, LastAccessDate, 
            Views, UpVotes, DownVotes, AccountId, WebsiteUrl, Location, AboutMe, Age, ProfileImageUrl
        ) VALUES (
            %s, %s, %s, %s, %s, 
            %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        """
        
        # Parameters:
        params = (
            hashed_id,                  
            DisplayName,                
            20,                         
            creation_date,              
            last_access_date,           
            0,                         
            0,                         
            0,                          
            account_id,                 
            None,                       
            None,                       
            None,                       
            None,                       
            None                       
        )
        
        try:
            cursor.execute(sorgu, params)
            mysql.connection.commit()
            flash("Başarıyla Kayıt Oldunuz...","success")
            return redirect(url_for("login"))
        except Exception as e:
            mysql.connection.rollback()
            flash(f"Kayıt Hatası: {e}","danger")
            return redirect(url_for("register"))
        finally:
            cursor.close()

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
           real_id = data["Id"]
           
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

@app.route("/logout")
def logout():
    session.clear()
    flash("Oturumunuz Kapatıldı.","success")
    return redirect(url_for("index"))

@app.errorhandler(404)
def not_found_error(error):
    return "<h1>404 Not Found</h1><p>Aradığınız sayfa bulunamadı. Lütfen URL'yi kontrol edin.</p>", 404


if __name__ == "__main__":

    app.run(debug=True)