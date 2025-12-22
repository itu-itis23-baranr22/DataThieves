from utils.auth import login_required, admin_required
from flask import (
    Blueprint, render_template, request,
    redirect, url_for, flash, session, abort, jsonify
)
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
import time
from extensions import mysql
from math import ceil
import uuid
import json

posts_bp = Blueprint("posts_bp", __name__)

def _get_col(row, key, idx=0, default=None):
    if row is None:
        return default
    if isinstance(row, dict) or hasattr(row, "keys"):
        return row.get(key, default)
    try:
        return row[idx]
    except Exception:
        return default

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

# ---- AUTH FORMS ----

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
@admin_required
def posts():
    cur = mysql.connection.cursor()

    q = (request.args.get("q") or "").strip()

    try:
        page = int(request.args.get("page", 1))
    except ValueError:
        page = 1
    page = max(page, 1)

    per_page = 20
    offset = (page - 1) * per_page

    count_sql = """
        SELECT COUNT(*) AS total
        FROM Posts
        WHERE 1=1
    """
    count_params = []
    if q:
        count_sql += " AND Title LIKE %s"
        count_params.append(f"%{q}%")

    cur.execute(count_sql, tuple(count_params))
    total = cur.fetchone()["total"]
    total_pages = max(1, ceil(total / per_page))

    if page > total_pages:
        page = total_pages
        offset = (page - 1) * per_page

    sql = """
        SELECT Id, PostTypeId, AcceptedAnswerId, CreaionDate, Score,
               ViewCount, Title, AnswerCount, CommentCount, FavoriteCount
        FROM Posts
        WHERE 1=1
    """
    params = []
    if q:
        sql += " AND Title LIKE %s"
        params.append(f"%{q}%")

    sql += """
        ORDER BY Id DESC
        LIMIT %s OFFSET %s;
    """
    params.extend([per_page, offset])

    cur.execute(sql, tuple(params))
    rows = cur.fetchall()

    user_stats = None
    if "user_id" in session:
        cur.execute(
            "SELECT DisplayName, Reputation, ProfileImageUrl FROM Users WHERE Id = %s",
            (session["user_id"],)
        )
        user_stats = cur.fetchone()

    cur.close()

    return render_template(
        "posts/list.html",
        posts=rows,
        q=q,
        page=page,
        total_pages=total_pages,
        per_page=per_page,
        total=total,
        user_stats=user_stats
    )


@posts_bp.route("/posts/<int:post_id>/delete", methods=["POST"], endpoint="delete_post")
@login_required
def delete_post(post_id):
    cur = mysql.connection.cursor()
    try:
        cur.execute("SELECT OwnerUserId FROM Posts WHERE Id = %s", (post_id,))
        row = cur.fetchone()
        if not row:
            cur.close()
            abort(404)

        owner_id = int(row["OwnerUserId"] or 0)
        current_user_id = int(session.get("user_id", 0))
        is_admin = bool(session.get("is_admin"))

        if (not is_admin) and (owner_id != current_user_id):
            cur.close()
            abort(403)

        cur.execute("DELETE FROM Posts WHERE Id = %s", (post_id,))
        mysql.connection.commit()
        flash("Post deleted successfully.", "success")

    except Exception as e:
        mysql.connection.rollback()
        flash(f"Delete error: {e}", "danger")
    finally:
        cur.close()

    q = (request.args.get("q") or "").strip()
    try:
        page = int(request.args.get("page", 1))
    except ValueError:
        page = 1

    return redirect(url_for("posts_bp.forum_posts", q=q, page=page))


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
                LastEditDate, ParentId, ClosedDate,
                OwnerDisplayName, LastEditorDisplayName
            ) VALUES (
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s
            )
        """

        params = (
            post_id,
            post_type_id,
            None,
            now_str,
            0,
            0,
            body,
            owner_user_id_val,
            now_str,
            title,
            tags,
            0, 0, 0,
            None, None,
            parent_id_val,
            None,
            owner_display_name,
            None
        )

        try:
            cur.execute(sql, params)
            mysql.connection.commit()
            flash("Post added successfully.", "success")
            return redirect(url_for("posts_bp.forum_posts"))
        except Exception as e:
            mysql.connection.rollback()
            flash(f"An error occurred while adding the post: {e}", "danger")
        finally:
            cur.close()

    return render_template("posts/add.html", form=form)




@posts_bp.route("/forum")
def forum_posts():
    cur = mysql.connection.cursor()

    q = (request.args.get("q") or "").strip()
    search = f"%{q}%"

    scope = (request.args.get("scope") or "all").strip().lower()
    if scope not in ("all", "title", "body", "tags", "comments"):
        scope = "all"

    unanswered = (request.args.get("unanswered") == "1")
    myfav = (request.args.get("myfav") == "1")
    hascomments = (request.args.get("hascomments") == "1")

    sort = (request.args.get("sort") or "popular").strip().lower()
    if sort not in ("popular", "new"):
        sort = "popular"

    #Pagination
    try:
        page = int(request.args.get("page", 1))
    except ValueError:
        page = 1
    page = max(page, 1)

    per_page = 20
    offset = (page - 1) * per_page

    current_user_id = session.get("user_id")
    current_user_id_int = int(current_user_id) if current_user_id else 0

    if sort == "new":
        order_by = "p.CreaionDate DESC"
    else:
        order_by = "(p.Score + p.ViewCount) DESC"


    search_sql = ""
    search_params = []

    if q:
        if scope == "title":
            search_sql = " AND (p.Title LIKE %s)"
            search_params = [search]
        elif scope == "body":
            search_sql = " AND (p.Body LIKE %s)"
            search_params = [search]
        elif scope == "tags":
            search_sql = " AND (p.Tags LIKE %s)"
            search_params = [search]
        elif scope == "comments":
            search_sql = """
                AND EXISTS (
                    SELECT 1 FROM Comments c
                    WHERE c.PostId = p.Id AND c.Text LIKE %s
                )
            """
            search_params = [search]
        else:
            # all
            search_sql = """
                AND (
                    p.Title LIKE %s
                    OR p.Body LIKE %s
                    OR p.Tags LIKE %s
                    OR EXISTS (
                        SELECT 1 FROM Comments c
                        WHERE c.PostId = p.Id AND c.Text LIKE %s
                    )
                )
            """
            search_params = [search, search, search, search]

    filter_sql = ""
    filter_params = []

    if unanswered:
        filter_sql += " AND COALESCE(a.RealAnswerCount,0) = 0 "

    if hascomments:
        filter_sql += " AND COALESCE(cs.CommentCount,0) > 0 "

    if myfav:
        filter_sql += """
            AND EXISTS (
                SELECT 1 FROM Votes v
                WHERE v.PostId = p.Id AND v.UserId = %s AND v.VoteTypeId = 5
            )
        """
        filter_params.append(current_user_id_int)

    count_query = f"""
        SELECT COUNT(*) AS total
        FROM Posts p

        LEFT JOIN (
            SELECT ParentId, COUNT(*) AS RealAnswerCount
            FROM Posts
            WHERE PostTypeId = 2
            GROUP BY ParentId
        ) a ON a.ParentId = p.Id

        LEFT JOIN (
            SELECT PostId, COUNT(*) AS CommentCount
            FROM Comments
            GROUP BY PostId
        ) cs ON cs.PostId = p.Id

        WHERE p.PostTypeId = 1
          AND p.Title IS NOT NULL AND p.Title != ''
          {search_sql}
          {filter_sql}
    """

    count_params = []
    count_params.extend(search_params)
    count_params.extend(filter_params)

    cur.execute(count_query, tuple(count_params))
    row = cur.fetchone()
    total = _get_col(row, "total", 0, default=0)

    total_pages = max(1, ceil(total / per_page))
    if page > total_pages:
        page = total_pages
        offset = (page - 1) * per_page

    posts_query = f"""
        SELECT
            p.Id, p.OwnerUserId, p.Title, p.Body, p.ViewCount,
            COALESCE(a.RealAnswerCount, 0) AS AnswerCount,
            COALESCE(cs.CommentCount, 0) AS CommentCount,
            p.CreaionDate, p.Score, p.Tags,
            u.DisplayName, u.Reputation, u.ProfileImageUrl,
            COALESCE(vs.UpCount, 0) AS UpCount,
            COALESCE(vs.DownCount, 0) AS DownCount,
            COALESCE(vs.FavCount, 0) AS FavCount,
            COALESCE(vs.MyVoteTypeId, NULL) AS MyVoteTypeId,
            COALESCE(vs.MyFav, 0) AS MyFav

        FROM Posts p
        LEFT JOIN Users u ON p.OwnerUserId = u.Id
        LEFT JOIN (
            SELECT ParentId, COUNT(*) AS RealAnswerCount
            FROM Posts
            WHERE PostTypeId = 2
            GROUP BY ParentId
        ) a ON a.ParentId = p.Id
        LEFT JOIN (
            SELECT PostId, COUNT(*) AS CommentCount
            FROM Comments
            GROUP BY PostId
        ) cs ON cs.PostId = p.Id
        LEFT JOIN (
            SELECT
                PostId,
                SUM(CASE WHEN VoteTypeId = 2 THEN 1 ELSE 0 END) AS UpCount,
                SUM(CASE WHEN VoteTypeId = 3 THEN 1 ELSE 0 END) AS DownCount,
                SUM(CASE WHEN VoteTypeId = 5 THEN 1 ELSE 0 END) AS FavCount,
                MAX(CASE WHEN UserId = %s AND VoteTypeId IN (2,3) THEN VoteTypeId ELSE NULL END) AS MyVoteTypeId,
                MAX(CASE WHEN UserId = %s AND VoteTypeId = 5 THEN 1 ELSE 0 END) AS MyFav
            FROM Votes
            GROUP BY PostId
        ) vs ON vs.PostId = p.Id
        WHERE p.PostTypeId = 1
          AND p.Title IS NOT NULL AND p.Title != ''
          {search_sql}
          {filter_sql}
        ORDER BY {order_by}
        LIMIT %s OFFSET %s
    """

    posts_params = [current_user_id_int, current_user_id_int]
    posts_params.extend(search_params)
    posts_params.extend(filter_params)
    posts_params.extend([per_page, offset])

    cur.execute(posts_query, tuple(posts_params))
    posts = cur.fetchall()

    user_stats = None
    if "user_id" in session:
        cur.execute("""
            SELECT DisplayName, Reputation, Location, Age, ProfileImageUrl
            FROM Users
            WHERE Id = %s
        """, (session["user_id"],))
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
        q=q,
        sort=sort,

        scope=scope,
        unanswered=unanswered,
        myfav=myfav,
        hascomments=hascomments
    )




@posts_bp.route("/posts/<int:post_id>/edit", methods=["GET", "POST"], endpoint="edit_post")
@login_required
def edit_post(post_id):
    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT Id, OwnerUserId, Title, Body, Tags
        FROM Posts
        WHERE Id = %s
    """, (post_id,))
    post = cur.fetchone()

    if not post:
        cur.close()
        abort(404)

    is_admin = bool(session.get("is_admin"))
    current_user_id = int(session.get("user_id", 0))
    owner_id = int(post["OwnerUserId"] or 0)

    if (not is_admin) and (owner_id != current_user_id):
        cur.close()
        abort(403)

    form = PostEditForm(request.form, data={
        "Title": post.get("Title") or "",
        "Body": post.get("Body") or "",
        "Tags": post.get("Tags") or ""
    })

    if request.method == "POST" and form.validate():
        new_title = (form.Title.data or "").strip()
        new_body  = (form.Body.data or "").strip()
        new_tags  = (form.Tags.data or "").strip()
        edit_comment = (form.EditComment.data or "").strip()

        now_str = time.strftime("%Y-%m-%d %H:%M:%S")

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

        cur.execute("SELECT IFNULL(MAX(Id),0) + 1 AS next_id FROM PostHistory")
        hist_id = cur.fetchone()["next_id"]

        snapshot = {"Title": new_title, "Body": new_body, "Tags": new_tags}
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
            edit_comment if edit_comment else None,
            session.get("DisplayName")
        ))

        mysql.connection.commit()
        cur.close()

        flash("Post updated (+ history saved).", "success")
        return redirect(url_for("posts_bp.forum_posts"))

    cur.close()
    return render_template("posts/edit.html", form=form, post=post)



@posts_bp.route("/posts/<int:post_id>/answers")
def post_answers(post_id):
    cur = mysql.connection.cursor()

    current_user_id = session.get("user_id")
    current_user_id_int = int(current_user_id) if current_user_id else 0

    cur.execute("""
        SELECT
            p.Id, p.OwnerUserId, p.Body, p.Score, p.CreaionDate,
            u.DisplayName, u.Reputation, u.ProfileImageUrl,
            COALESCE(vs.UpCount, 0) AS UpCount,
            COALESCE(vs.DownCount, 0) AS DownCount,
            COALESCE(vs.MyVoteTypeId, NULL) AS MyVoteTypeId,
            COALESCE(cs.CommentCount, 0) AS CommentCount
        FROM Posts p
        LEFT JOIN Users u ON u.Id = p.OwnerUserId
        LEFT JOIN (
            SELECT
                PostId,
                SUM(CASE WHEN VoteTypeId = 2 THEN 1 ELSE 0 END) AS UpCount,
                SUM(CASE WHEN VoteTypeId = 3 THEN 1 ELSE 0 END) AS DownCount,
                MAX(CASE WHEN UserId = %s AND VoteTypeId IN (2,3) THEN VoteTypeId ELSE NULL END) AS MyVoteTypeId
            FROM Votes
            GROUP BY PostId
        ) vs ON vs.PostId = p.Id

        LEFT JOIN (
            SELECT PostId, COUNT(*) AS CommentCount
            FROM Comments
            GROUP BY PostId
        ) cs ON cs.PostId = p.Id

        WHERE p.PostTypeId = 2
          AND p.ParentId = %s
        ORDER BY p.Score DESC, p.CreaionDate ASC
    """, (current_user_id_int, post_id))

    answers = cur.fetchall()
    cur.close()
    return render_template("posts/_answers_partial.html", answers=answers)


@posts_bp.route("/posts/<int:post_id>/answer", methods=["POST"], endpoint="add_answer")
@login_required
def add_answer(post_id):
    body = (request.form.get("body") or "").strip()
    if not body:
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return {"ok": False, "error": "Empty answer."}, 400
        flash("Answer cannot be empty.", "danger")
        return redirect(url_for("posts_bp.forum_posts"))

    user_id = int(session["user_id"])
    now_str = time.strftime("%Y-%m-%d %H:%M:%S")

    cur = mysql.connection.cursor()
    try:
        cur.execute("SELECT IFNULL(MAX(Id),0) + 1 AS next_id FROM Posts")
        next_id_row = cur.fetchone()
        answer_id = next_id_row["next_id"] if isinstance(next_id_row, dict) else next_id_row[0]

        cur.execute("""
            INSERT INTO Posts
              (Id, PostTypeId, ParentId, Body, OwnerUserId, CreaionDate, LasActivityDate, Score)
            VALUES
              (%s, 2, %s, %s, %s, %s, %s, 0)
        """, (answer_id, post_id, body, user_id, now_str, now_str))

        mysql.connection.commit()

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return {"ok": True, "answer_id": answer_id}

        flash("Answer posted.", "success")
        return redirect(url_for("comments_votes_bp.comments", post_id=post_id))

    except Exception as e:
        mysql.connection.rollback()
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return {"ok": False, "error": str(e)}, 500
        flash(f"Error: {e}", "danger")
        return redirect(url_for("posts_bp.forum_posts"))
    finally:
        cur.close()







# ------------ AUTH ROUTES ------------

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

            if int(id_entered) in (101010, 150220100, 123456789, 676767, 242424):
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

