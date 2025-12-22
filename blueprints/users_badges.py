from flask import Blueprint, render_template, request, redirect, url_for, flash
from wtforms import Form, StringField, validators, TextAreaField, SelectField
import time
from extensions import mysql
from utils.auth import login_required, admin_required
from flask import session, render_template

users_badges_bp = Blueprint("users_badges_bp", __name__)

class BadgeForm(Form):
    UserId = StringField("User ID", [validators.DataRequired()])
    Name = StringField("Badge Name", [validators.DataRequired(), validators.Length(max=255)])

class UserInsertForm(Form):
    DisplayName = StringField("Display Name", [validators.DataRequired(), validators.Length(max=255)])
    Location = StringField("Location", [validators.Optional(), validators.Length(max=255)])
    Age = StringField("Age", [validators.Optional()])

class EditProfileForm(Form):
    Location = StringField("Location", [validators.Optional(), validators.Length(max=255)])
    WebsiteUrl = StringField("Website", [validators.Optional(), validators.Length(max=255)])
    AboutMe = StringField("About", [validators.Optional(), validators.Length(max=2000)])
    ProfileImageUrl = StringField("Profile Image URL", [validators.Optional(), validators.Length(max=255)])

class UserEditForm(Form):
    DisplayName = StringField("Name", [validators.Optional(), validators.Length(max=255)])
    Reputation = StringField("Reputation", [validators.Optional()])
    Location = StringField("Location", [validators.Optional(), validators.Length(max=255)])
    WebsiteUrl = StringField("Website Url", [validators.Optional(), validators.Length(max=255)])
    AboutMe = TextAreaField("About Me", [validators.Optional()])
    Age = StringField("Age", [validators.Optional()])
    ProfileImageUrl = StringField("Profile Image Url", [validators.Optional(), validators.Length(max=255)])

DEFAULT_BADGES = [
    ("Student", "Student"),
    ("Teacher", "Teacher"),
    ("Popular Question", "Popular Question"),
    ("Nice Answer", "Nice Answer"),
    ("Supporter", "Supporter"),
    ("Editor", "Editor"),
    ("Commentator", "Commentator"),
    ("Enthusiast", "Enthusiast"),
    ("Yearling", "Yearling"),
    ("Custodian", "Custodian"),
]

class AddProfileBadgeForm(Form):
    preset = SelectField("Choose a badge", choices=[("", "Select...")] + DEFAULT_BADGES)
    custom = StringField("Or custom badge", [validators.Optional(), validators.Length(max=255)])


@users_badges_bp.route("/users", endpoint="users")
@admin_required
def users():
    # 1) Query parametreleri (GET)
    q = (request.args.get("q") or "").strip()
    location = (request.args.get("location") or "").strip()

    min_rep = (request.args.get("minRep") or "").strip()
    max_rep = (request.args.get("maxRep") or "").strip()
    min_age = (request.args.get("minAge") or "").strip()
    max_age = (request.args.get("maxAge") or "").strip()

    # 2) Pagination
    page = request.args.get("page", 1, type=int)
    per_page = 50
    offset = (page - 1) * per_page

    where = []
    params = []

    # 3) Filtreler
    if q:
        where.append("DisplayName LIKE %s")
        params.append(f"%{q}%")

    if location:
        where.append("Location LIKE %s")
        params.append(f"%{location}%")

    # Reputation min/max
    if min_rep.isdigit():
        where.append("Reputation >= %s")
        params.append(int(min_rep))

    if max_rep.isdigit():
        where.append("Reputation <= %s")
        params.append(int(max_rep))

    # Age min/max (Age NULL olanları filtreye sokmamak için: Age IS NOT NULL)
    if min_age.isdigit():
        where.append("Age IS NOT NULL AND Age >= %s")
        params.append(int(min_age))

    if max_age.isdigit():
        where.append("Age IS NOT NULL AND Age <= %s")
        params.append(int(max_age))

    where_sql = (" WHERE " + " AND ".join(where)) if where else ""

    cur = mysql.connection.cursor()

    # 4) Total count (pagination için)
    count_sql = "SELECT COUNT(*) AS cnt FROM Users" + where_sql
    cur.execute(count_sql, tuple(params))
    total = cur.fetchone()["cnt"]

    total_pages = (total + per_page - 1) // per_page if total else 1
    if page < 1:
        page = 1
    if page > total_pages:
        page = total_pages
    offset = (page - 1) * per_page

    # 5) Liste query
    data_sql = f"""
        SELECT
            Id, DisplayName, Reputation, Location, CreationDate, LastAccessDate,
            Views, UpVotes, DownVotes, Age, WebsiteUrl, AboutMe, AccountId, ProfileImageUrl
        FROM Users
        {where_sql}
        ORDER BY Id DESC
        LIMIT %s OFFSET %s
    """
    data_params = params + [per_page, offset]
    cur.execute(data_sql, tuple(data_params))
    rows = cur.fetchall()
    cur.close()

    return render_template(
        "users/users.html",
        users=rows,
        # filtre değerlerini template'e geri basmak için:
        q=q,
        location=location,
        minRep=min_rep,
        maxRep=max_rep,
        minAge=min_age,
        maxAge=max_age,
        # pagination info:
        page=page,
        total=total,
        total_pages=total_pages
    )


@users_badges_bp.route("/users/<int:user_id>/delete", methods=["POST"], endpoint="delete_user")
@admin_required
def delete_user(user_id):
    cur = mysql.connection.cursor()
    try:
        cur.execute("DELETE FROM users WHERE Id = %s", (user_id,))
        mysql.connection.commit()
        flash("User deleted.", "success")
    except Exception as e:
        mysql.connection.rollback()
        flash(f"Delete error: {e}", "danger")
    finally:
        cur.close()

    return redirect(url_for("users_badges_bp.users"))


@users_badges_bp.route("/users/<int:user_id>/edit", methods=["GET", "POST"], endpoint="edit_user")
@admin_required
def edit_user(user_id):
    cur = mysql.connection.cursor()

    # user getir
    cur.execute("""
        SELECT Id, DisplayName, Reputation, Location, WebsiteUrl, AboutMe, Age, ProfileImageUrl
        FROM users
        WHERE Id = %s
    """, (user_id,))
    user = cur.fetchone()

    if not user:
        cur.close()
        flash("User not found.", "danger")
        return redirect(url_for("users_badges_bp.users"))

    form = UserEditForm(request.form)

    # GET -> formu doldur
    if request.method == "GET":
        form.DisplayName.data = user.get("DisplayName")
        form.Reputation.data = user.get("Reputation")
        form.Location.data = user.get("Location")
        form.WebsiteUrl.data = user.get("WebsiteUrl")
        form.AboutMe.data = user.get("AboutMe")
        form.Age.data = user.get("Age")
        form.ProfileImageUrl.data = user.get("ProfileImageUrl")

    # POST -> update
    if request.method == "POST" and form.validate():
        try:
            def to_int(x):
                x = (x or "").strip()
                return int(x) if x.isdigit() else None

            cur.execute("""
                UPDATE users
                SET DisplayName=%s,
                    Reputation=%s,
                    Location=%s,
                    WebsiteUrl=%s,
                    AboutMe=%s,
                    Age=%s,
                    ProfileImageUrl=%s
                WHERE Id=%s
            """, (
                form.DisplayName.data or None,
                to_int(form.Reputation.data),
                form.Location.data or None,
                form.WebsiteUrl.data or None,
                form.AboutMe.data or None,
                to_int(form.Age.data),
                form.ProfileImageUrl.data or None,
                user_id
            ))
            mysql.connection.commit()
            flash("User updated.", "success")
            return redirect(url_for("users_badges_bp.users"))
        except Exception as e:
            mysql.connection.rollback()
            flash(f"Update error: {e}", "danger")
        finally:
            cur.close()
            return render_template("users/edit_user.html", form=form, user=user)

    cur.close()
    return render_template("users/edit_user.html", form=form, user=user)


@users_badges_bp.route("/users/add", methods=["GET", "POST"], endpoint="add_user")
@admin_required
def add_user():
    form = UserInsertForm(request.form)

    if request.method == "POST" and form.validate():
        display_name = form.DisplayName.data
        location = form.Location.data or None
        age = form.Age.data
        age_value = int(age) if age else None

        now_str = time.strftime('%Y-%m-%d %H:%M:%S')

        cur = mysql.connection.cursor()
        cur.execute("SELECT IFNULL(MAX(Id), 0) + 1 AS next_id FROM Users")
        row = cur.fetchone()
        user_id = row["next_id"]

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
            0,
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
            flash("User added successfully.", "success")
            return redirect(url_for("users_badges_bp.users"))
        except Exception as e:
            mysql.connection.rollback()
            flash(f"An error occurred while adding the user: {e}", "danger")
        finally:
            cur.close()

    return render_template("users/add.html", form=form)





@users_badges_bp.route("/badges/add", methods=["GET", "POST"], endpoint="add_badge")
@login_required
def add_badge():
    form = BadgeForm(request.form)

    if request.method == "POST" and form.validate():
        user_id = int(form.UserId.data)
        name = form.Name.data
        now_str = time.strftime('%Y-%m-%d %H:%M:%S')

        cur = mysql.connection.cursor()
        cur.execute("SELECT IFNULL(MAX(Id), 0) + 1 AS next_id FROM Badges")
        row = cur.fetchone()
        badge_id = row["next_id"]

        sql = """
            INSERT INTO Badges (Id, UserId, Name, Date)
            VALUES (%s, %s, %s, %s)
        """
        params = (badge_id, user_id, name, now_str)

        try:
            cur.execute(sql, params)
            mysql.connection.commit()
            flash("Badge added successfully.", "success")
            return redirect(url_for("users_badges_bp.badges"))
        except Exception as e:
            mysql.connection.rollback()
            flash(f"An error occurred while adding the badge: {e}", "danger")
        finally:
            cur.close()

    return render_template("badges/add.html", form=form)

@users_badges_bp.route("/profile")
@login_required
def profile():
    user_id = session.get("user_id")
    if not user_id:
        flash("User not found in session.", "danger")
        return redirect(url_for("posts_bp.login"))

    cur = mysql.connection.cursor()

    # 1) User info
    user_sql = """
        SELECT
            Id, DisplayName, Reputation, CreationDate, LastAccessDate,
            WebsiteUrl, Location, AboutMe, Age, ProfileImageUrl
        FROM users
        WHERE Id = %s
    """
    cur.execute(user_sql, (user_id,))
    user = cur.fetchone()

    if not user:
        cur.close()
        flash("User profile could not be loaded.", "danger")
        return redirect(url_for("posts_bp.login"))

    # 2) Badges
    badges_sql = """
        SELECT Id, UserId, Name, Date
        FROM badges
        WHERE UserId = %s
        ORDER BY Date DESC
        LIMIT 50
    """
    cur.execute(badges_sql, (user_id,))
    earned_badges = cur.fetchall()

    # 3) Stats
    stats_sql = """
        SELECT
            (SELECT COUNT(*) FROM posts    p WHERE p.OwnerUserId = %s) AS posts,
            (SELECT COUNT(*) FROM comments c WHERE c.UserId      = %s) AS comments,
            (SELECT COUNT(*) FROM badges   b WHERE b.UserId      = %s) AS badges,
            (SELECT COUNT(*) FROM votes    v WHERE v.UserId      = %s) AS votes
    """
    cur.execute(stats_sql, (user_id, user_id, user_id, user_id))
    stats = cur.fetchone()

    # 4) Rank
    rank_sql = """
        SELECT 1 + (
            SELECT COUNT(*)
            FROM users u2
            WHERE u2.Reputation > u.Reputation
        ) AS user_rank
        FROM users u
        WHERE u.Id = %s
    """
    cur.execute(rank_sql, (user_id,))
    rank_row = cur.fetchone()
    rank = rank_row["user_rank"] if rank_row else None

    # 5) Recent Posts (template: user_posts)
    posts_sql = """
        SELECT
            p.Id,
            p.Title,
            p.Score,
            p.CreationDate
        FROM posts p
        WHERE p.OwnerUserId = %s
        ORDER BY p.Id DESC
        LIMIT 10
    """
    try:
        cur.execute(posts_sql, (user_id,))
        user_posts = cur.fetchall()
    except Exception:
        # posts tablosunda CreationDate yoksa fallback:
        posts_sql_no_date = """
            SELECT
                p.Id,
                p.Title,
                p.Score
            FROM posts p
            WHERE p.OwnerUserId = %s
            ORDER BY p.Id DESC
            LIMIT 10
        """
        cur.execute(posts_sql_no_date, (user_id,))
        user_posts = cur.fetchall()

    # 6) Recent Comments (template: user_comments)
    comments_sql = """
        SELECT
            c.Id,
            c.Text,
            c.PostId,
            c.CreationDate,
            p.Title AS PostTitle
        FROM comments c
        LEFT JOIN posts p ON p.Id = c.PostId
        WHERE c.UserId = %s
        ORDER BY c.Id DESC
        LIMIT 10
    """
    cur.execute(comments_sql, (user_id,))
    user_comments = cur.fetchall()

    # navbar için user_stats
    user_stats = None
    if "user_id" in session:
        me_id = session["user_id"]
        cur.execute(
            "SELECT DisplayName, Reputation, Location, Age, ProfileImageUrl FROM users WHERE Id = %s",
            (me_id,)
        )
        user_stats = cur.fetchone()

    cur.close()

    return render_template(
        "users/public_profile.html",
        user=user,
        earned_badges=earned_badges,
        stats=stats,
        rank=rank,
        user_stats=user_stats,
        is_owner=True,
        user_posts=user_posts,
        user_comments=user_comments
    )

@users_badges_bp.route("/users/<int:user_id>", endpoint="user_profile")
def user_profile(user_id):
    cur = mysql.connection.cursor()

    # 1) User bilgisi
    user_sql = """
        SELECT
            Id, DisplayName, Reputation, CreationDate, LastAccessDate,
            WebsiteUrl, Location, AboutMe, Age, ProfileImageUrl
        FROM users
        WHERE Id = %s
    """
    cur.execute(user_sql, (user_id,))
    user = cur.fetchone()

    if not user:
        cur.close()
        flash("User not found.", "danger")
        return redirect(url_for("posts_bp.forum_posts"))

    # 2) Earned badges listesi
    badges_sql = """
        SELECT Id, UserId, Name, Date
        FROM badges
        WHERE UserId = %s
        ORDER BY Date DESC
        LIMIT 50
    """
    cur.execute(badges_sql, (user_id,))
    earned_badges = cur.fetchall()

    # 3) Stats: posts/comments/badges/votes sayıları
    # Not: posts.OwnerUserId, comments.UserId, badges.UserId, votes.UserId üzerinden sayıyoruz.
    stats_sql = """
        SELECT
            (SELECT COUNT(*) FROM posts    p WHERE p.OwnerUserId = %s) AS posts,
            (SELECT COUNT(*) FROM comments c WHERE c.UserId      = %s) AS comments,
            (SELECT COUNT(*) FROM badges   b WHERE b.UserId      = %s) AS badges,
            (SELECT COUNT(*) FROM votes    v WHERE v.UserId      = %s) AS votes
    """
    cur.execute(stats_sql, (user_id, user_id, user_id, user_id))
    stats = cur.fetchone()  # dict: {"posts":..., "comments":..., "badges":..., "votes":...}

    # 3.5) User'ın son postları (liste)
    posts_sql = """
        SELECT
            Id, Title, CreaionDate, Score, ViewCount
        FROM posts
        WHERE OwnerUserId = %s
        ORDER BY CreaionDate DESC
        LIMIT 10
    """
    cur.execute(posts_sql, (user_id,))
    user_posts = cur.fetchall()

    # 3.6) User'ın son yorumları (liste)
    comments_sql = """
        SELECT
            c.Id, c.PostId, c.CreationDate, c.Text,
            p.Title AS PostTitle
        FROM comments c
        LEFT JOIN posts p ON p.Id = c.PostId
        WHERE c.UserId = %s
        ORDER BY c.CreationDate DESC
        LIMIT 10
    """
    cur.execute(comments_sql, (user_id,))
    user_comments = cur.fetchall()

    # 4) Rank (nested query): daha yüksek reputation kaç kişi var? +1
    rank_sql = """
        SELECT 1 + (
            SELECT COUNT(*)
            FROM users u2
            WHERE u2.Reputation > u.Reputation
        ) AS user_rank
        FROM users u
        WHERE u.Id = %s
    """
    cur.execute(rank_sql, (user_id,))
    rank_row = cur.fetchone()
    rank = rank_row["user_rank"] if rank_row else None

    # 5) Sidebar "My Zone" için login'li kullanıcının mini bilgisi (forum ile aynı)
    user_stats = None
    if "user_id" in session:
        me_id = session["user_id"]
        cur.execute(
            "SELECT DisplayName, Reputation, Location, Age, ProfileImageUrl FROM users WHERE Id = %s",
            (me_id,)
        )
        user_stats = cur.fetchone()

    cur.close()

    session_user_id = session.get("user_id")
    is_owner = (session_user_id is not None) and (int(session_user_id) == int(user_id))

    return render_template(
        "users/public_profile.html",
        user=user,
        earned_badges=earned_badges,
        stats=stats,
        rank=rank,
        user_stats=user_stats,
        is_owner=is_owner,
        user_posts=user_posts,
        user_comments=user_comments
    )

@users_badges_bp.route("/profile/edit", methods=["GET", "POST"], endpoint="edit_profile")
@login_required
def edit_profile():
    user_id = session.get("user_id")
    if not user_id:
        flash("You must be logged in.", "danger")
        return redirect(url_for("posts_bp.login"))

    cur = mysql.connection.cursor()

    # mevcut bilgileri çek
    cur.execute("""
        SELECT Location, WebsiteUrl, AboutMe, ProfileImageUrl
        FROM users
        WHERE Id = %s
    """, (user_id,))
    user = cur.fetchone()

    if not user:
        cur.close()
        flash("User not found.", "danger")
        return redirect(url_for("posts_bp.login"))

    form = EditProfileForm(request.form)

    # GET ise formu doldur
    if request.method == "GET":
        form.Location.data = user.get("Location")
        form.WebsiteUrl.data = user.get("WebsiteUrl")
        form.AboutMe.data = user.get("AboutMe")
        form.ProfileImageUrl.data = user.get("ProfileImageUrl")

    # POST ise update
    if request.method == "POST" and form.validate():
        location = form.Location.data or None
        website = form.WebsiteUrl.data or None
        about = form.AboutMe.data or None
        avatar = form.ProfileImageUrl.data or None

        try:
            cur.execute("""
                UPDATE users
                SET Location=%s, WebsiteUrl=%s, AboutMe=%s, ProfileImageUrl=%s
                WHERE Id=%s
            """, (location, website, about, avatar, user_id))
            mysql.connection.commit()
            flash("Profile updated successfully.", "success")
            return redirect(url_for("users_badges_bp.profile"))
        except Exception as e:
            mysql.connection.rollback()
            flash(f"Update error: {e}", "danger")
        finally:
            cur.close()

    cur.close()
    return render_template("users/edit_profile.html", form=form, user=user)

@users_badges_bp.route("/profile/badges/add", methods=["GET", "POST"], endpoint="add_profile_badge")
@login_required
def add_profile_badge():
    user_id = session.get("user_id")
    form = AddProfileBadgeForm(request.form)

    if request.method == "POST" and form.validate():
        # seçilen preset varsa onu al, yoksa custom kullan
        badge_name = (form.preset.data or "").strip()
        custom_name = (form.custom.data or "").strip()

        name_to_insert = badge_name if badge_name else custom_name

        if not name_to_insert:
            flash("Please select a badge or type a custom one.", "danger")
            return render_template("users/add_profile_badge.html", form=form)

        cur = mysql.connection.cursor()
        try:
            cur.execute(
                "SELECT 1 FROM badges WHERE UserId=%s AND Name=%s LIMIT 1",
                (user_id, name_to_insert)
            )
            exists = cur.fetchone()
            if exists:
                flash("This badge already exists on your profile.", "warning")
                return redirect(url_for("users_badges_bp.profile"))

            cur.execute("SELECT IFNULL(MAX(Id), 0) + 1 AS next_id FROM badges")
            badge_id = cur.fetchone()["next_id"]

            now_str = time.strftime('%Y-%m-%d %H:%M:%S')

            cur.execute(
                "INSERT INTO badges (Id, UserId, Name, Date) VALUES (%s, %s, %s, %s)",
                (badge_id, user_id, name_to_insert, now_str)
            )
            mysql.connection.commit()
            flash("Badge added to your profile!", "success")
            return redirect(url_for("users_badges_bp.profile"))
        except Exception as e:
            mysql.connection.rollback()
            flash(f"Error: {e}", "danger")
        finally:
            cur.close()

    return render_template("users/add_profile_badge.html", form=form)


@users_badges_bp.route("/profile/badges/<int:badge_id>/delete", methods=["POST"], endpoint="delete_profile_badge")
@login_required
def delete_profile_badge(badge_id):
    user_id = session.get("user_id")
    if not user_id:
        flash("You must be logged in.", "danger")
        return redirect(url_for("posts_bp.login"))

    cur = mysql.connection.cursor()
    try:
        # Badge gerçekten bu kullanıcıya mı ait?
        cur.execute("SELECT Id, UserId FROM badges WHERE Id=%s", (badge_id,))
        b = cur.fetchone()

        if not b:
            flash("Badge not found.", "danger")
            return redirect(url_for("users_badges_bp.user_profile", user_id=user_id))

        if int(b["UserId"]) != int(user_id):
            flash("You cannot delete someone else's badge.", "danger")
            return redirect(url_for("users_badges_bp.user_profile", user_id=user_id))

        # Sil
        cur.execute("DELETE FROM badges WHERE Id=%s", (badge_id,))
        mysql.connection.commit()
        flash("Badge deleted.", "success")

    except Exception as e:
        mysql.connection.rollback()
        flash(f"Delete error: {e}", "danger")
    finally:
        cur.close()

    return redirect(url_for("users_badges_bp.user_profile", user_id=user_id))


@users_badges_bp.route("/badges", endpoint="badges")
@admin_required
def badges():
    # --- Filters ---
    q = (request.args.get("q") or "").strip()              # badge name search
    user_id = (request.args.get("userId") or "").strip()   # optional exact userId

    # --- Pagination ---
    page = request.args.get("page", 1, type=int)
    per_page = 50
    offset = (page - 1) * per_page

    where = []
    params = []

    if q:
        where.append("Name LIKE %s")
        params.append(f"%{q}%")

    if user_id.isdigit():
        where.append("UserId = %s")
        params.append(int(user_id))

    where_sql = (" WHERE " + " AND ".join(where)) if where else ""

    cur = mysql.connection.cursor()

    # total
    count_sql = "SELECT COUNT(*) AS cnt FROM badges" + where_sql
    cur.execute(count_sql, tuple(params))
    total = cur.fetchone()["cnt"]

    total_pages = (total + per_page - 1) // per_page if total else 1
    if page < 1:
        page = 1
    if page > total_pages:
        page = total_pages
    offset = (page - 1) * per_page

    # data
    data_sql = f"""
        SELECT Id, UserId, Name, Date
        FROM badges
        {where_sql}
        ORDER BY Id DESC
        LIMIT %s OFFSET %s
    """
    cur.execute(data_sql, tuple(params + [per_page, offset]))
    rows = cur.fetchall()
    cur.close()

    return render_template(
        "badges/badges.html",
        badges=rows,
        q=q,
        userId=user_id,
        page=page,
        total=total,
        total_pages=total_pages
    )

@users_badges_bp.route("/badges/<int:badge_id>/edit", methods=["GET", "POST"], endpoint="edit_badge")
@admin_required
def edit_badge(badge_id):
    cur = mysql.connection.cursor()

    # mevcut badge
    cur.execute("SELECT Id, UserId, Name, Date FROM badges WHERE Id=%s", (badge_id,))
    b = cur.fetchone()
    if not b:
        cur.close()
        flash("Badge not found.", "danger")
        return redirect(url_for("users_badges_bp.badges"))

    if request.method == "POST":
        name = (request.form.get("Name") or "").strip()
        user_id = (request.form.get("UserId") or "").strip()

        if not name:
            flash("Name is required.", "danger")
            cur.close()
            return render_template("badges/edit_badge.html", badge=b)

        if not user_id.isdigit():
            flash("UserId must be a number.", "danger")
            cur.close()
            return render_template("badges/edit_badge.html", badge=b)

        # Date'i istersen sabit bırak, istersen now yap
        now_str = time.strftime('%Y-%m-%d %H:%M:%S')

        try:
            cur.execute(
                "UPDATE badges SET UserId=%s, Name=%s, Date=%s WHERE Id=%s",
                (int(user_id), name, now_str, badge_id)
            )
            mysql.connection.commit()
            flash("Badge updated.", "success")
            return redirect(url_for("users_badges_bp.badges"))
        except Exception as e:
            mysql.connection.rollback()
            flash(f"Update error: {e}", "danger")
        finally:
            cur.close()

    cur.close()
    return render_template("badges/edit_badge.html", badge=b)

@users_badges_bp.route("/badges/<int:badge_id>/delete", methods=["POST"], endpoint="delete_badge")
@admin_required
def delete_badge(badge_id):
    cur = mysql.connection.cursor()
    try:
        cur.execute("DELETE FROM badges WHERE Id=%s", (badge_id,))
        mysql.connection.commit()
        flash("Badge deleted.", "success")
    except Exception as e:
        mysql.connection.rollback()
        flash(f"Delete error: {e}", "danger")
    finally:
        cur.close()
    return redirect(url_for("users_badges_bp.badges"))

@users_badges_bp.route("/users/top", endpoint="top_users")
@login_required
def top_users():
    q = (request.args.get("q") or "").strip()
    location = (request.args.get("location") or "").strip()

    where = []
    params = []

    if q:
        where.append("DisplayName LIKE %s")
        params.append(f"%{q}%")

    if location:
        where.append("Location LIKE %s")
        params.append(f"%{location}%")

    where_sql = (" WHERE " + " AND ".join(where)) if where else ""

    cur = mysql.connection.cursor()

    sql = f"""
        SELECT
            Id, DisplayName, Reputation, Location, ProfileImageUrl,
            WebsiteUrl, Age, CreationDate, LastAccessDate, Views, UpVotes, DownVotes,
            (1 + (SELECT COUNT(*) FROM users u2 WHERE u2.Reputation > u.Reputation)) AS user_rank
        FROM users u
        {where_sql}
        ORDER BY u.Reputation DESC
        LIMIT 100
    """
    cur.execute(sql, tuple(params))
    rows = cur.fetchall()
    top3 = rows[:3]  # Get top 3 users
    cur.close()

    return render_template(
        "users/top_users.html",
        users=rows,
        top3=top3,
        q=q,
        location=location
    )



