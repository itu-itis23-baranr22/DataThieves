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

class BadgeForm(Form):
    UserId = StringField("User Id", [validators.DataRequired()])
    Name = StringField("Rozet Adı", [validators.DataRequired(), validators.Length(max=255)])


class UserInsertForm(Form):
    DisplayName = StringField("Display Name", [validators.DataRequired(), validators.Length(max=255)])
    Reputation = StringField("Reputation", [validators.DataRequired()])
    Location = StringField("Location", [validators.Optional(), validators.Length(max=255)])
    Age = StringField("Yaş", [validators.Optional()])


class PostInsertForm(Form):
    PostTypeId = StringField("Post Type Id", [validators.DataRequired()])
    Title = StringField("Başlık", [validators.Optional(), validators.Length(max=255)])
    Body = TextAreaField("İçerik", [validators.Optional()])
    OwnerUserId = StringField("Owner User Id", [validators.Optional()])
    Tags = StringField("Tags", [validators.Optional(), validators.Length(max=255)])
    ParentId = StringField("Parent Id", [validators.Optional()])
    OwnerDisplayName = StringField("Owner Display Name", [validators.Optional(), validators.Length(max=255)])


class CommentInsertForm(Form):
    PostId = StringField("Post Id", [validators.DataRequired()])
    Score = StringField("Score", [validators.DataRequired()])
    Text = TextAreaField("Yorum Metni", [validators.DataRequired()])
    UserId = StringField("User Id", [validators.Optional()])
    UserDisplayName = StringField("User Display Name", [validators.Optional(), validators.Length(max=255)])


class VoteInsertForm(Form):
    PostId = StringField("Post Id", [validators.DataRequired()])
    VoteTypeId = StringField("Vote Type Id", [validators.DataRequired()])
    UserId = StringField("User Id", [validators.Optional()])
    BountyAmount = StringField("Bounty Amount", [validators.Optional()])


class PostLinkInsertForm(Form):
    PostId = StringField("Post Id", [validators.DataRequired()])
    RelatedPostId = StringField("Related Post Id", [validators.DataRequired()])
    LinkTypeId = StringField("Link Type Id", [validators.DataRequired()])


class TagInsertForm(Form):
    TagName = StringField("Tag Name", [validators.DataRequired(), validators.Length(max=100)])
    Count = StringField("Count", [validators.DataRequired()])
    ExcerptPostId = StringField("Excerpt Post Id", [validators.Optional()])
    WikiPostId = StringField("Wiki Post Id", [validators.Optional()])


class PostHistoryInsertForm(Form):
    PostHistoryTypeId = StringField("Post History Type Id", [validators.DataRequired()])
    PostId = StringField("Post Id", [validators.DataRequired()])
    RevisionGUID = StringField("Revision GUID", [validators.DataRequired(), validators.Length(max=36)])
    Text = TextAreaField("Text", [validators.Optional()])
    Comment = TextAreaField("Comment", [validators.Optional()])
    UserId = StringField("User Id", [validators.Optional()])
    UserDisplayName = StringField("User Display Name", [validators.Optional(), validators.Length(max=255)])



# --- Flask App Setup ---

app = Flask(__name__,template_folder="templates")
app.secret_key = "data_thieves_secret" 

app.config["MYSQL_HOST"] = "127.0.0.1"
app.config["MYSQL_USER"] = "root"
app.config["MYSQL_PASSWORD"] = "12345"
app.config["MYSQL_DB"] = "local_stats"
app.config["MYSQL_CURSORCLASS"] = "DictCursor" 


mysql = MySQL(app)

# --- Routes ---

@app.route("/")
def index():
    return render_template("index.html")

################################
# BADGES
################################
@app.route("/badges")
def badges():
    cur = mysql.connection.cursor()
    sql = """
        SELECT Id, UserId, Name, Date
        FROM badges
        LIMIT 500;
    """
    cur.execute(sql)
    rows = cur.fetchall()
    cur.close()
    return render_template("badges.html", badges=rows)

################################
# USERS
################################
@app.route("/users")
def users():
    cur = mysql.connection.cursor()
    sql = """
        SELECT Id, Reputation, CreationDate, DisplayName, LastAccessDate,
               Location, Views, UpVotes, DownVotes, Age
        FROM users

    """
    # WebsiteUrl, AboutMe, ProfileImageUrl vs. istersen ekleyebilirsin.
    cur.execute(sql)
    rows = cur.fetchall()
    cur.close()
    return render_template("users.html", users=rows)


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
        LIMIT 500;
    """
    cur.execute(sql)
    rows = cur.fetchall()
    cur.close()
    return render_template("postHistory.html", postHistory=rows)

################################
# POSTS
################################
@app.route("/posts")
def posts():
    cur = mysql.connection.cursor()
    sql = """
    SELECT Id, PostTypeId, AcceptedAnswerId, CreationDate, Score,
           ViewCount, Title, AnswerCount, CommentCount, FavoriteCount
    FROM posts
    ORDER BY Id DESC
    LIMIT 500;
"""

    # İstersen Body, Tags vs. de ekleyebilirsin ama tablo çok genişler.
    cur.execute(sql)
    rows = cur.fetchall()
    cur.close()
    return render_template("posts.html", posts=rows)



################################
# COMMENTS
################################
@app.route("/comments")
def comments():
    cur = mysql.connection.cursor()
    sql = """
        SELECT Id, PostId, Score, Text, CreationDate, UserId, UserDisplayName
        FROM comments
        LIMIT 500;
    """
    cur.execute(sql)
    rows = cur.fetchall()
    cur.close()
    return render_template("comments.html", comments=rows)


################################
# VOTES
################################
@app.route("/votes")
def votes():
    cur = mysql.connection.cursor()
    sql = """
        SELECT Id, PostId, VoteTypeId, CreationDate, UserId, BountyAmount
        FROM votes
        ORDER BY CreationDate DESC
        LIMIT 500;
    """
    cur.execute(sql)
    rows = cur.fetchall()
    cur.close()
    return render_template("votes.html", votes=rows)



# POST LINKS
################################
@app.route("/postLinks")
def post_links():
    cur = mysql.connection.cursor()
    sql = """
        SELECT Id, CreationDate, PostId, RelatedPostId, LinkTypeId
        FROM postLinks
        ORDER BY Id DESC

    """
    cur.execute(sql)
    rows = cur.fetchall()
    cur.close()
    return render_template("postLinks.html", postLinks=rows)

################################
# TAGS
################################
@app.route("/tags")
def tags():
    cur = mysql.connection.cursor()
    sql = """
        SELECT Id, TagName, Count, ExcerptPostId, WikiPostId
        FROM tags
        ORDER BY Id DESC

    """
    cur.execute(sql)
    rows = cur.fetchall()
    cur.close()
    return render_template("tags.html", tags=rows)


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
    
  
    
@app.route("/badges/add", methods=["GET", "POST"])
def add_badge():
    form = BadgeForm(request.form)

    if request.method == "POST" and form.validate():
        user_id = int(form.UserId.data)
        name = form.Name.data
        now_str = time.strftime('%Y-%m-%d %H:%M:%S')

        cur = mysql.connection.cursor()
        badge_id = int(time.time() * 1000)

        sql = """
            INSERT INTO Badges (Id, UserId, Name, Date)
            VALUES (%s, %s, %s, %s)
        """
        params = (badge_id, user_id, name, now_str)

        try:
            cur.execute(sql, params)
            mysql.connection.commit()
            flash("Badge başarıyla eklendi.", "success")
            return redirect(url_for("badges"))
        except Exception as e:
            mysql.connection.rollback()
            flash(f"Badge eklenirken hata oluştu: {e}", "danger")
        finally:
            cur.close()

    return render_template("add_badge.html", form=form)

@app.route("/users/add", methods=["GET", "POST"])
def add_user():
    form = UserInsertForm(request.form)

    if request.method == "POST" and form.validate():
        display_name = form.DisplayName.data
        reputation = int(form.Reputation.data)
        location = form.Location.data or None
        age = form.Age.data
        age_value = int(age) if age else None

        now_str = time.strftime('%Y-%m-%d %H:%M:%S')
        user_id = int(time.time() * 1000)

        cur = mysql.connection.cursor()

        sql = """
            INSERT INTO Users (
                Id, Reputation, CreationDate, DisplayName, LastAccessDate,
                WebsiteUrl, Location, AboutMe, Views, UpVotes, DownVotes,
                AccountId, Age, ProfileImageUrl
            )
            VALUES (%s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s,
                    %s, %s, %s)
        """
        params = (
            user_id,
            reputation,
            now_str,
            display_name,
            now_str,
            None,
            location,
            None,
            0,
            0,
            0,
            None,
            age_value,
            None
        )

        try:
            cur.execute(sql, params)
            mysql.connection.commit()
            flash("User başarıyla eklendi.", "success")
            return redirect(url_for("users"))
        except Exception as e:
            mysql.connection.rollback()
            flash(f"User eklenirken hata oluştu: {e}", "danger")
        finally:
            cur.close()

    return render_template("add_user.html", form=form)

    
@app.route("/posts/add", methods=["GET", "POST"])
def add_post():
    form = PostInsertForm(request.form)

    if request.method == "POST" and form.validate():

        post_type_id = int(form.PostTypeId.data)
        title = form.Title.data or None
        body = form.Body.data or None
        owner_user_id = form.OwnerUserId.data
        owner_user_id_val = int(owner_user_id) if owner_user_id else None
        tags = form.Tags.data or None
        parent_id = form.ParentId.data
        parent_id_val = int(parent_id) if parent_id else None
        owner_display_name = form.OwnerDisplayName.data or None

        now_str = time.strftime('%Y-%m-%d %H:%M:%S')

        cur = mysql.connection.cursor()

        # ---- Id Out of Range olmaması için MAX(Id)+1 ----
        cur.execute("SELECT IFNULL(MAX(Id), 0) + 1 AS next_id FROM Posts")
        row = cur.fetchone()
        post_id = row["next_id"]

        sql = """
            INSERT INTO Posts (
                Id, PostTypeId, AcceptedAnswerId, CreaionDate, Score,
                ViewCount, Body, OwnerUserId, LasActivityDate, Title, Tags,
                AnswerCount, CommentCount, FavoriteCount, LastEditorUserId,
                LastEditDate, CommunityOwnedDate, ParentId, ClosedDate,
                OwnerDisplayName, LastEditorDisplayName
            ) VALUES (
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s
            )
        """

        params = (
            post_id,
            post_type_id,
            None,           # AcceptedAnswerId
            now_str,        # CreaionDate
            0,              # Score
            0,              # ViewCount
            body,
            owner_user_id_val,
            now_str,        # LasActivityDate
            title,
            tags,
            0, 0, 0,         # Counts
            None, None, None,    # Editor fields
            parent_id_val,
            None,               # ClosedDate
            owner_display_name,
            None                # LastEditorDisplayName
        )

        try:
            cur.execute(sql, params)
            mysql.connection.commit()
            flash("Post başarıyla eklendi.", "success")
            return redirect(url_for("posts"))
        except Exception as e:
            mysql.connection.rollback()
            flash(f"Post eklenirken hata oluştu: {e}", "danger")
        finally:
            cur.close()

    return render_template("add_post.html", form=form)


@app.route("/comments/add", methods=["GET", "POST"])
def add_comment():
    form = CommentInsertForm(request.form)

    if request.method == "POST" and form.validate():
        post_id = int(form.PostId.data)
        score = int(form.Score.data)
        text = form.Text.data
        user_id = form.UserId.data
        user_id_val = int(user_id) if user_id else None
        user_display_name = form.UserDisplayName.data or None

        now_str = time.strftime('%Y-%m-%d %H:%M:%S')
        comment_id = int(time.time() * 1000)

        cur = mysql.connection.cursor()

        sql = """
            INSERT INTO Comments (
                Id, PostId, Score, Text, CreationDate,
                UserId, UserDisplayName
            )
            VALUES (%s, %s, %s, %s, %s,
                    %s, %s)
        """
        params = (
            comment_id,
            post_id,
            score,
            text,
            now_str,
            user_id_val,
            user_display_name
        )

        try:
            cur.execute(sql, params)
            mysql.connection.commit()
            flash("Comment başarıyla eklendi.", "success")
            return redirect(url_for("comments"))
        except Exception as e:
            mysql.connection.rollback()
            flash(f"Comment eklenirken hata oluştu: {e}", "danger")
        finally:
            cur.close()

    return render_template("add_comment.html", form=form)

@app.route("/votes/add", methods=["GET", "POST"])
def add_vote():
    form = VoteInsertForm(request.form)

    if request.method == "POST" and form.validate():
        post_id = int(form.PostId.data)
        vote_type_id = int(form.VoteTypeId.data)
        user_id = form.UserId.data
        user_id_val = int(user_id) if user_id else None
        bounty = form.BountyAmount.data
        bounty_val = int(bounty) if bounty else None

        now_str = time.strftime('%Y-%m-%d %H:%M:%S')

        cur = mysql.connection.cursor()

        # --- ÖNCE yeni Id'yi hesapla (MAX(Id) + 1) ---
        cur.execute("SELECT IFNULL(MAX(Id), 0) + 1 AS next_id FROM Votes")
        row = cur.fetchone()
        vote_id = row["next_id"]   # DictCursor kullandığın için kolon adıyla alıyoruz

        sql = """
            INSERT INTO Votes (
                Id, PostId, VoteTypeId, CreationDate,
                UserId, BountyAmount
            )
            VALUES (%s, %s, %s, %s,
                    %s, %s)
        """
        params = (
            vote_id,
            post_id,
            vote_type_id,
            now_str,
            user_id_val,
            bounty_val
        )

        try:
            cur.execute(sql, params)
            mysql.connection.commit()
            flash("Vote başarıyla eklendi.", "success")
            return redirect(url_for("votes"))
        except Exception as e:
            mysql.connection.rollback()
            flash(f"Vote eklenirken veritabanı hatası: {e}", "danger")
        finally:
            cur.close()

    return render_template("add_vote.html", form=form)


@app.route("/postLinks/add", methods=["GET", "POST"])
def add_post_link():
    form = PostLinkInsertForm(request.form)

    if request.method == "POST" and form.validate():
        post_id = int(form.PostId.data)
        related_post_id = int(form.RelatedPostId.data)
        link_type_id = int(form.LinkTypeId.data)

        now_str = time.strftime('%Y-%m-%d %H:%M:%S')

        cur = mysql.connection.cursor()
        cur.execute("SELECT IFNULL(MAX(Id), 0) + 1 AS next_id FROM PostLinks")
        row = cur.fetchone()
        link_id = row["next_id"]

        sql = """
            INSERT INTO PostLinks (
                Id, CreationDate, PostId, RelatedPostId, LinkTypeId
            )
            VALUES (%s, %s, %s, %s, %s)
        """
        params = (
            link_id,
            now_str,
            post_id,
            related_post_id,
            link_type_id
        )

        try:
            cur.execute(sql, params)
            mysql.connection.commit()
            flash("PostLink başarıyla eklendi.", "success")
            return redirect(url_for("post_links"))
        except Exception as e:
            mysql.connection.rollback()
            flash(f"PostLink eklenirken hata oluştu: {e}", "danger")
        finally:
            cur.close()

    return render_template("add_post_link.html", form=form)

@app.route("/tags/add", methods=["GET", "POST"])
def add_tag():
    form = TagInsertForm(request.form)

    if request.method == "POST" and form.validate():
        tag_name = form.TagName.data
        count = int(form.Count.data)
        excerpt_id = form.ExcerptPostId.data
        excerpt_id_val = int(excerpt_id) if excerpt_id else None
        wiki_id = form.WikiPostId.data
        wiki_id_val = int(wiki_id) if wiki_id else None

        cur = mysql.connection.cursor()
        cur.execute("SELECT IFNULL(MAX(Id), 0) + 1 AS next_id FROM Tags")
        row = cur.fetchone()
        tag_id = row["next_id"]

        sql = """
            INSERT INTO Tags (
                Id, TagName, Count, ExcerptPostId, WikiPostId
            )
            VALUES (%s, %s, %s, %s, %s)
        """
        params = (
            tag_id,
            tag_name,
            count,
            excerpt_id_val,
            wiki_id_val
        )

        try:
            cur.execute(sql, params)
            mysql.connection.commit()
            flash("Tag başarıyla eklendi.", "success")
            return redirect(url_for("tags"))
        except Exception as e:
            mysql.connection.rollback()
            flash(f"Tag eklenirken hata oluştu: {e}", "danger")
        finally:
            cur.close()

    return render_template("add_tag.html", form=form)


@app.route("/postHistory/add", methods=["GET", "POST"])
def add_post_history():
    form = PostHistoryInsertForm(request.form)

    if request.method == "POST" and form.validate():
        ph_type_id = int(form.PostHistoryTypeId.data)
        post_id = int(form.PostId.data)
        revision_guid = form.RevisionGUID.data
        text = form.Text.data or None
        comment = form.Comment.data or None
        user_id = form.UserId.data
        user_id_val = int(user_id) if user_id else None
        user_display_name = form.UserDisplayName.data or None

        now_str = time.strftime('%Y-%m-%d %H:%M:%S')
        ph_id = int(time.time() * 1000)

        cur = mysql.connection.cursor()

        sql = """
            INSERT INTO PostHistory (
                Id, PostHistoryTypeId, PostId, RevisionGUID,
                CreationDate, UserId, Text, Comment, UserDisplayName
            )
            VALUES (%s, %s, %s, %s,
                    %s, %s, %s, %s, %s)
        """
        params = (
            ph_id,
            ph_type_id,
            post_id,
            revision_guid,
            now_str,
            user_id_val,
            text,
            comment,
            user_display_name
        )

        try:
            cur.execute(sql, params)
            mysql.connection.commit()
            flash("PostHistory kaydı başarıyla eklendi.", "success")
            return redirect(url_for("post_history"))
        except Exception as e:
            mysql.connection.rollback()
            flash(f"PostHistory eklenirken hata oluştu: {e}", "danger")
        finally:
            cur.close()

    return render_template("add_post_history.html", form=form)

    
  

@app.route("/register",methods = ["GET","POST"])
def register():
    form = RegisterForm(request.form)

    if request.method == "POST" and form.validate():
        DisplayName = form.DisplayName.data
        # Id (Password) field'ı çekilir
        id_entered = str(form.Id.data) 
        
        # Parola hashlenir
        hashed_id = sha256_crypt.encrypt(id_entered)

        cursor = mysql.connection.cursor()

        # Varsayılan değerler oluşturulur
        account_id = int(time.time() * 1000) 
        creation_date = '2024-01-01 00:00:00' # Bu kısmı dinamik olarak 'datetime.now()' ile değiştirmek daha iyi olabilir
        last_access_date = creation_date
    
        # Kullanıcıyı USERS tablosuna ekleyen SORGULAMA (INSERT)
        sorgu = """
        INSERT INTO users (
            Id, DisplayName, Reputation, CreationDate, LastAccessDate, 
            Views, UpVotes, DownVotes, AccountId, WebsiteUrl, Location, AboutMe, Age, ProfileImageUrl
        ) VALUES (
            %s, %s, %s, %s, %s, 
            %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        """
        
        # Parameters (Hashed ID burada Id sütununa yazılır):
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
            # SQL sorgusu çalıştırılır
            cursor.execute(sorgu, params)
            mysql.connection.commit()
            
            # Başarılı Kayıt Mesajı (Türkçe'den İngilizce'ye çevrildi)
            flash("Registration Successful! Please log in.","success")
            return redirect(url_for("login"))
        except Exception as e:
            mysql.connection.rollback()
            # Hata Mesajı (Türkçe'den İngilizce'ye çevrildi)
            flash(f"Registration Error: {e}","danger")
            return redirect(url_for("register"))
        finally:
            cursor.close()

    # Eğer form GET isteği ise veya doğrulama başarısız olursa
    return render_template("register.html",form = form)

# ... (main.py dosyasının geri kalanı aynı kalır)


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