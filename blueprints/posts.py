from utils.auth import login_required, admin_required
from flask import (
    Blueprint, render_template, request,
    redirect, url_for, flash, session, abort
)
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
import time
from extensions import mysql
from math import ceil
import uuid
import json


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

class PostEditForm(Form):
    Title = StringField("Title", [validators.DataRequired(), validators.Length(max=255)])
    Body = TextAreaField("Body", [validators.Optional()])
    Tags = StringField("Tags", [validators.Optional(), validators.Length(max=255)])
    EditComment = StringField("Edit comment", [validators.Optional(), validators.Length(max=255)])
# ---- AUTH FORMS (ROJHAT) ----

class RegisterForm(Form):
    DisplayName = StringField("Username", validators=[validators.Length(min=4, max=25)])
    Age = StringField("Age", validators=[validators.Length(min=1, max=3)])
    AboutYou = StringField("About You", validators=[validators.Length(min=1, max=500)])
    Location = StringField("Location", validators=[validators.Length(min=1, max=50)])
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
@login_required
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
@login_required
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


@posts_bp.route("/dashboard")
@login_required
def dashboard():
    cur = mysql.connection.cursor()

    # page param
    try:
        page = int(request.args.get("page", 1))
    except ValueError:
        page = 1
    page = max(page, 1)

    per_page = 10
    offset = (page - 1) * per_page

    user_id = int(session["user_id"])

    # 1) Summary cards (nested query + group by mantığı)
    summary_query = """
        SELECT
            COUNT(*) AS total_posts,
            COALESCE(SUM(p.ViewCount),0) AS total_views,
            COALESCE(SUM(p.Score),0) AS total_score,
            COALESCE(AVG(p.Score),0) AS avg_score
        FROM Posts p
        WHERE p.OwnerUserId = %s AND p.Title IS NOT NULL AND p.Title != '';
    """
    cur.execute(summary_query, (user_id,))
    summary = cur.fetchone()

    # 2) total count for pagination
    count_query = """
        SELECT COUNT(*) AS total
        FROM Posts p
        WHERE p.OwnerUserId = %s AND p.Title IS NOT NULL AND p.Title != '';
    """
    cur.execute(count_query, (user_id,))
    total = cur.fetchone()["total"]
    total_pages = max(1, ceil(total / per_page))

    if page > total_pages:
        page = total_pages
        offset = (page - 1) * per_page

    # 3) paged posts list
    posts_query = """
        SELECT
            p.Id, p.Title, p.Score, p.ViewCount, p.AnswerCount, p.CommentCount, p.CreaionDate, p.Tags
        FROM Posts p
        WHERE p.OwnerUserId = %s AND p.Title IS NOT NULL AND p.Title != ''
        ORDER BY p.Score DESC
        LIMIT %s OFFSET %s;
    """
    cur.execute(posts_query, (user_id, per_page, offset))
    posts = cur.fetchall()

    cur.close()

    return render_template(
        "posts/dashboard.html",
        posts=posts,
        summary=summary,
        page=page,
        total_pages=total_pages
    )



@posts_bp.route("/forum")
def forum_posts():
    cur = mysql.connection.cursor()

    # ---------- 1) Search ----------
    q = request.args.get("q", "").strip()
    search = f"%{q}%"

    # ---------- 2) Pagination ----------
    try:
        page = int(request.args.get("page", 1))
    except ValueError:
        page = 1
    page = max(page, 1)

    per_page = 20
    offset = (page - 1) * per_page

    # ---------- 3) Total count ----------
    count_query = """
        SELECT COUNT(DISTINCT p.Id) AS total
        FROM Posts p
        LEFT JOIN Comments c ON c.PostId = p.Id
        WHERE p.Title IS NOT NULL AND p.Title != ''
    """
    count_params = []

    if q:
        count_query += """
            AND (
                p.Title LIKE %s
                OR p.Body LIKE %s
                OR p.Tags LIKE %s
                OR c.Text LIKE %s
            )
        """
        count_params.extend([search, search, search, search])

    cur.execute(count_query, count_params)
    total = cur.fetchone()["total"]

    total_pages = max(1, ceil(total / per_page))

    # clamp
    if page > total_pages:
        page = total_pages
        offset = (page - 1) * per_page

    # ---------- 4) Paged posts ----------
    posts_query = """
        SELECT DISTINCT
            p.Id,
            p.OwnerUserId,
            p.Title,
            p.Body,
            p.ViewCount,
            p.AnswerCount,
            p.CommentCount,
            p.CreaionDate,
            p.Score,
            p.Tags,
            u.DisplayName,
            u.Reputation,
            u.ProfileImageUrl
        FROM Posts p
        LEFT JOIN Users u ON p.OwnerUserId = u.Id
        LEFT JOIN Comments c ON c.PostId = p.Id
        WHERE p.Title IS NOT NULL AND p.Title != ''
    """
    posts_params = []

    if q:
        posts_query += """
            AND (
                p.Title LIKE %s
                OR p.Body LIKE %s
                OR p.Tags LIKE %s
                OR c.Text LIKE %s
            )
        """
        posts_params.extend([search, search, search, search])

    posts_query += """
        ORDER BY p.CreaionDate DESC
        LIMIT %s OFFSET %s
    """
    posts_params.extend([per_page, offset])

    cur.execute(posts_query, posts_params)
    posts = cur.fetchall()

    # ---------- 5) Sidebar user stats ----------
    user_stats = None
    if "user_id" in session:
        user_id = session["user_id"]
        user_query = """
            SELECT DisplayName, Reputation, Location, Age, ProfileImageUrl
            FROM Users
            WHERE Id = %s
        """
        cur.execute(user_query, (user_id,))
        user_stats = cur.fetchone()

    cur.close()

    return render_template(
        "posts/posts_forum.html",
        posts=posts,
        user_stats=user_stats,
        page=page,
        total_pages=total_pages,
        per_page=per_page,
        total=total,
        q=q
    )



@posts_bp.route("/posts/<int:post_id>/edit", methods=["GET", "POST"], endpoint="edit_post")
@login_required
def edit_post(post_id):
    cur = mysql.connection.cursor()

    # 1) Postu getir
    cur.execute("""
        SELECT Id, OwnerUserId, Title, Body, Tags
        FROM Posts
        WHERE Id = %s
    """, (post_id,))
    post = cur.fetchone()

    if not post:
        cur.close()
        abort(404)

    # 2) Permission: admin veya post sahibi
    is_admin = bool(session.get("is_admin"))
    current_user_id = int(session.get("user_id", 0))
    owner_id = int(post["OwnerUserId"] or 0)

    if (not is_admin) and (owner_id != current_user_id):
        cur.close()
        abort(403)

    # 3) Form (GET'te mevcut değerleri basar)
    form = PostEditForm(request.form, data={
        "Title": post.get("Title") or "",
        "Body": post.get("Body") or "",
        "Tags": post.get("Tags") or ""
    })

    if request.method == "POST" and form.validate():
        new_title = (form.Title.data or "").strip()
        new_body  = (form.Body.data or "").strip()
        new_tags  = (form.Tags.data or "").strip()
        edit_comment = (form.EditComment.data or "").strip()   # ✅ commit message

        now_str = time.strftime("%Y-%m-%d %H:%M:%S")

        # 4) Posts update
        cur.execute("""
            UPDATE Posts
            SET Title = %s,
                Body = %s,
                Tags = %s,
                LasActivityDate = %s,
                LastEditDate = %s,
                LastEditorUserId = %s,
                LastEditorDisplayName = %s
            WHERE Id = %s
        """, (
            new_title,
            new_body,
            new_tags,
            now_str,
            now_str,
            current_user_id,
            session.get("DisplayName"),
            post_id
        ))

        # 5) PostHistory insert (önce next id)
        cur.execute("SELECT IFNULL(MAX(Id),0) + 1 AS next_id FROM PostHistory")
        hist_id = cur.fetchone()["next_id"]

        # PostHistory.Text içine "snapshot" koyuyoruz (istersen sadece body de koyabilirsin)
        snapshot = {
            "Title": new_title,
            "Body": new_body,
            "Tags": new_tags
        }

        # PostHistoryTypeId: StackOverflow dump’larında genelde 2 = Edit
        POST_HISTORY_EDIT_TYPE = 2

        cur.execute("""
            INSERT INTO PostHistory
                (Id, PostId, UserId, CreationDate, PostHistoryTypeId, Text, Comment, UserDisplayName)
            VALUES
                (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            hist_id,
            post_id,
            current_user_id,
            now_str,
            POST_HISTORY_EDIT_TYPE,
            json.dumps(snapshot, ensure_ascii=False),
            edit_comment if edit_comment else None,  # ✅ commit message
            session.get("DisplayName")
        ))

        mysql.connection.commit()
        cur.close()

        flash("Post updated (+ history saved).", "success")
        return redirect(url_for("posts_bp.forum_posts"))

    cur.close()
    return render_template("posts/edit.html", form=form, post=post)

# ------------ AUTH ROUTES (ROJHAT) ------------

@posts_bp.route("/register", methods=["GET", "POST"], endpoint="register")
def register():
    form = RegisterForm(request.form)

    if request.method == "POST" and form.validate():
        DisplayName = form.DisplayName.data
        id_entered = form.Id.data
        Age = int(form.Age.data)
        AboutYou = form.AboutYou.data
        Location = form.Location.data
        cursor2 = mysql.connection.cursor()
        query2 = "SELECT Id FROM users WHERE Id = %s"
        result2 = cursor2.execute(query2, (id_entered,))
        if result2 > 0:
            flash("ID already exists. Please choose a different ID.", "danger")
            cursor2.close()
            return render_template("auth/register.html", form=form)
        cursor = mysql.connection.cursor()

        creation_date = time.strftime('%Y-%m-%d %H:%M:%S')
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
            id_entered,
            DisplayName,
            0,
            creation_date,
            last_access_date,
            0,
            0,
            0,
            0,
            None,
            Location,
            AboutYou,
            Age,
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

        query = "SELECT * FROM users WHERE Id = %s AND DisplayName = %s"
        result = cursor.execute(query, (id_entered, DisplayName))

        if result > 0:

            flash("You have logged in successfully!", "success")
            session["logged_in"] = True
            session["user_id"] = id_entered
            session["DisplayName"] = DisplayName
            
            if int(id_entered) == 101010:
                session["is_admin"] = True
            elif int(id_entered) == 150220100:
                session["is_admin"] = True
            elif int(id_entered) == 123456789:
                session["is_admin"] = True
            elif int(id_entered) == 676767:
                session["is_admin"] = True
            elif int(id_entered) == 242424:
                session["is_admin"] = True
            else:
                session["is_admin"] = False
                
            return redirect(url_for("index"))
        else:
                flash("No such a user found.", "danger")

        cursor.close()

    return render_template("auth/login.html", form=form)


@posts_bp.route("/logout", endpoint="logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("index"))


# blueprints/posts.py dosyasının en altına yapıştırın:

@posts_bp.route("/forum/<int:post_id>")
def forum_post_detail(post_id):
    cur = mysql.connection.cursor()

    # 1. Post detayını ve yazarını çek
    post_query = """
        SELECT 
            p.Id,
            p.Title,
            p.Body,
            p.ViewCount,
            p.CreaionDate,
            p.OwnerUserId,
            u.DisplayName AS OwnerName,
            u.Reputation   AS OwnerReputation,
            u.Location     AS OwnerLocation,
            u.ProfileImageUrl
        FROM Posts p
        LEFT JOIN Users u ON p.OwnerUserId = u.Id
        WHERE p.Id = %s
    """
    cur.execute(post_query, (post_id,))
    post = cur.fetchone()

    if not post:
        cur.close()
        # Post bulunamazsa 404 sayfasına veya ana sayfaya at
        return render_template("error404.html"), 404

    # 2. Yorumları çek
    comments_query = """
        SELECT 
            c.Id,
            c.Text,
            c.CreationDate,
            COALESCE(u.DisplayName, c.UserDisplayName) AS CommentAuthor,
            u.Reputation AS CommentReputation
        FROM Comments c
        LEFT JOIN Users u ON c.UserId = u.Id
        WHERE c.PostId = %s
        ORDER BY c.CreationDate ASC
    """
    cur.execute(comments_query, (post_id,))
    comments = cur.fetchall()
    cur.close()

    # Detay sayfasına gönder
    return render_template("posts/post_forum_detail.html", post=post, comments=comments)