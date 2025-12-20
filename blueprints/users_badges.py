from flask import Blueprint, render_template, request, redirect, url_for, flash
from wtforms import Form, StringField, validators, TextAreaField
import time
from extensions import mysql
from utils.auth import login_required   
from flask import session, render_template

users_badges_bp = Blueprint("users_badges_bp", __name__)

class BadgeForm(Form):
    UserId = StringField("User ID", [validators.DataRequired()])
    Name = StringField("Badge Name", [validators.DataRequired(), validators.Length(max=255)])


class UserInsertForm(Form):
    DisplayName = StringField("Display Name", [validators.DataRequired(), validators.Length(max=255)])
    Reputation = StringField("Reputation", [validators.DataRequired()])
    Location = StringField("Location", [validators.Optional(), validators.Length(max=255)])
    Age = StringField("Age", [validators.Optional()])


class EditProfileForm(Form):
    Location = StringField("Location", [validators.Optional(), validators.Length(max=255)])
    WebsiteUrl = StringField("Website", [validators.Optional(), validators.Length(max=255)])
    AboutMe = StringField("About", [validators.Optional(), validators.Length(max=2000)])
    ProfileImageUrl = StringField("Profile Image URL", [validators.Optional(), validators.Length(max=255)])


@users_badges_bp.route("/users", endpoint="users")
@login_required
def users():
    cur = mysql.connection.cursor()
    sql = """
        SELECT Id, Reputation, CreationDate, DisplayName, LastAccessDate,
               Location, Views, UpVotes, DownVotes, Age
        FROM users
        ORDER BY Id DESC
        LIMIT 500;
    """
    cur.execute(sql)
    rows = cur.fetchall()
    cur.close()
    return render_template("users/list.html", users=rows)


@users_badges_bp.route("/users/add", methods=["GET", "POST"], endpoint="add_user")
@login_required
def add_user():
    form = UserInsertForm(request.form)

    if request.method == "POST" and form.validate():
        display_name = form.DisplayName.data
        reputation = int(form.Reputation.data)
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
            flash("User added successfully.", "success")
            return redirect(url_for("users_badges_bp.users"))
        except Exception as e:
            mysql.connection.rollback()
            flash(f"An error occurred while adding the user: {e}", "danger")
        finally:
            cur.close()

    return render_template("users/add.html", form=form)


@users_badges_bp.route("/badges", endpoint="badges")
@login_required
def badges():
    cur = mysql.connection.cursor()
    sql = """
        SELECT Id, UserId, Name, Date
        FROM badges
        ORDER BY Id DESC
        LIMIT 500;
    """
    cur.execute(sql)
    rows = cur.fetchall()
    cur.close()
    return render_template("badges/list.html", badges=rows)


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

    # 2) Earned badges
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

    # 4) Rank (nested query)
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
        is_owner=True                  
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
        is_owner=is_owner
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
    return render_template("users/edit_profile.html", form=form)
