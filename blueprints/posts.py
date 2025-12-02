# blueprints/posts.py
from flask import (
    Blueprint, render_template, request,
    redirect, url_for, flash, session
)
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from passlib.hash import sha256_crypt
import time
from extensions import mysql

posts_bp = Blueprint("posts_bp", __name__)

# --- Forms ---

class PostInsertForm(Form):
    PostTypeId = StringField("Post Type ID", [validators.DataRequired()])
    Title = StringField("Title", [validators.Optional(), validators.Length(max=255)])
    Body = TextAreaField("Body", [validators.Optional()])
    OwnerUserId = StringField("Owner User ID", [validators.Optional()])
    Tags = StringField("Tags", [validators.Optional(), validators.Length(max=255)])
    ParentId = StringField("Parent ID", [validators.Optional()])
    OwnerDisplayName = StringField(
        "Owner Display Name", [validators.Optional(), validators.Length(max=255)]
    )

# ---- AUTH FORMS (ROJHAT) ----

class RegisterForm(Form):
    DisplayName = StringField("Username", validators=[validators.Length(min=4, max=25)])
    Id = PasswordField("ID", validators=[
        validators.DataRequired(message="Please choose an ID"),
        validators.EqualTo(fieldname="confirm", message="IDs do not match...")
    ])
    confirm = PasswordField("Confirm ID")


class LoginForm(Form):
    DisplayName = StringField("Username")
    id = PasswordField("ID")


# --- POSTS ROUTES ---

@posts_bp.route("/posts", endpoint="posts")
def posts():
    cur = mysql.connection.cursor()
    sql = """
        SELECT Id, PostTypeId, AcceptedAnswerId, CreaionDate, Score,
               ViewCount, Title, AnswerCount, CommentCount, FavoriteCount
        FROM posts
        ORDER BY Id DESC
        LIMIT 500;
    """
    cur.execute(sql)
    rows = cur.fetchall()
    cur.close()
    return render_template("posts/list.html", posts=rows)


@posts_bp.route("/posts/add", methods=["GET", "POST"], endpoint="add_post")
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
            0, 0, 0,
            None, None, None,
            parent_id_val,
            None,               # ClosedDate
            owner_display_name,
            None                # LastEditorDisplayName
        )

        try:
            cur.execute(sql, params)
            mysql.connection.commit()
            flash("Post added successfully.", "success")
            return redirect(url_for("posts_bp.posts"))
        except Exception as e:
            mysql.connection.rollback()
            flash(f"An error occurred while adding the post: {e}", "danger")
        finally:
            cur.close()

    return render_template("posts/add.html", form=form)


@posts_bp.route("/dashboard", endpoint="dashboard")
def dashboard():
    cursor = mysql.connection.cursor()

    query = "SELECT * FROM posts WHERE OwnerDisplayName = %s"
    result = cursor.execute(query, (session.get("DisplayName"),))

    if result > 0:
        posts = cursor.fetchall()
        cursor.close()
        return render_template("posts/dashboard.html", posts=posts)
    else:
        cursor.close()
        return render_template("posts/dashboard.html")


# ------------ AUTH ROUTES (ROJHAT) ------------

@posts_bp.route("/register", methods=["GET", "POST"], endpoint="register")
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

        query = """
        INSERT INTO users (
            Id, DisplayName, Reputation, CreationDate, LastAccessDate,
            Views, UpVotes, DownVotes, AccountId, WebsiteUrl, Location,
            AboutMe, Age, ProfileImageUrl
        ) VALUES (
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s,
            %s, %s, %s
        )
        """

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
            cursor.execute(query, params)
            mysql.connection.commit()
            flash("You have registered successfully!", "success")
            return redirect(url_for("posts_bp.login"))
        except Exception as e:
            mysql.connection.rollback()
            flash(f"Registration Error: {e}", "danger")
        finally:
            cursor.close()

    return render_template("auth/register.html", form=form)


@posts_bp.route("/login", methods=["GET", "POST"], endpoint="login")
def login():
    form = LoginForm(request.form)

    if request.method == "POST":
        DisplayName = form.DisplayName.data
        id_entered = form.id.data

        cursor = mysql.connection.cursor()

        query = "SELECT * FROM users WHERE DisplayName = %s"
        result = cursor.execute(query, (DisplayName,))

        if result > 0:
            data = cursor.fetchone()
            real_id = data["Id"]

            if sha256_crypt.verify(id_entered, real_id):
                flash("You have logged in successfully!", "success")
                session["logged_in"] = True
                session["DisplayName"] = DisplayName
                return redirect(url_for("index"))
            else:
                flash("Incorrect ID entered.", "danger")
        else:
            flash("No such user found.", "danger")

        cursor.close()

    return render_template("auth/login.html", form=form)


@posts_bp.route("/logout", endpoint="logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("index"))
