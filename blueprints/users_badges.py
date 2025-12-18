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

    query = """
        SELECT 
            Id,
            DisplayName,
            Reputation,
            CreationDate,
            LastAccessDate,
            Location,
            AboutMe,
            Age,
            ProfileImageUrl
        FROM users
        WHERE Id = %s
    """
    cur.execute(query, (user_id,))
    user = cur.fetchone()
    cur.close()

    if not user:
        flash("User profile could not be loaded.", "danger")
        return redirect(url_for("posts_bp.login"))

    return render_template("users/profile.html", user=user)
@users_badges_bp.route("/users/<int:user_id>", endpoint="user_profile")
@login_required
def user_profile(user_id):
    cur = mysql.connection.cursor()

    # ---- 1) User + badge_count (LEFT JOIN + GROUP BY) ----
    user_sql = """
        SELECT
            u.Id, u.DisplayName, u.Reputation, u.CreationDate, u.LastAccessDate,
            u.Location, u.WebsiteUrl, u.AboutMe, u.Age, u.ProfileImageUrl,
            COUNT(b.Id) AS badge_count
        FROM users u
        LEFT JOIN badges b ON b.UserId = u.Id
        WHERE u.Id = %s
        GROUP BY u.Id
    """
    cur.execute(user_sql, (user_id,))
    user = cur.fetchone()

    if not user:
        cur.close()
        flash("User not found.", "danger")
        return redirect(url_for("users_badges_bp.users"))

    # ---- 2) Badge vitrin listesi ----
    badges_sql = """
        SELECT Id, Name, Date
        FROM badges
        WHERE UserId = %s
        ORDER BY Date DESC
        LIMIT 50
    """
    cur.execute(badges_sql, (user_id,))
    badges = cur.fetchall()

    # ---- 3) 4+ tablo stats (Users + Posts + Comments + Badges + Votes) ----
    stats_sql = """
        SELECT
          u.Id,
          COALESCE(p.post_count, 0)    AS post_count,
          COALESCE(c.comment_count, 0) AS comment_count,
          COALESCE(b2.badge_count, 0)  AS badge_count,
          COALESCE(v.vote_count, 0)    AS vote_count
        FROM users u

        LEFT JOIN (
          SELECT OwnerUserId, COUNT(*) AS post_count
          FROM posts
          GROUP BY OwnerUserId
        ) p ON p.OwnerUserId = u.Id

        LEFT JOIN (
          SELECT UserId, COUNT(*) AS comment_count
          FROM comments
          GROUP BY UserId
        ) c ON c.UserId = u.Id

        LEFT JOIN (
          SELECT UserId, COUNT(*) AS badge_count
          FROM badges
          GROUP BY UserId
        ) b2 ON b2.UserId = u.Id

        LEFT JOIN (
          SELECT UserId, COUNT(*) AS vote_count
          FROM votes
          GROUP BY UserId
        ) v ON v.UserId = u.Id

        WHERE u.Id = %s
    """
    cur.execute(stats_sql, (user_id,))
    stats = cur.fetchone()

    # ---- 4) Nested query ile rank (reputation sıralaması) ----
    rank_sql = """
        SELECT t.rnk
        FROM (
          SELECT u2.Id,
                 (SELECT COUNT(*) + 1
                  FROM users u3
                  WHERE u3.Reputation > u2.Reputation) AS rnk
          FROM users u2
        ) t
        WHERE t.Id = %s
    """
    cur.execute(rank_sql, (user_id,))
    r = cur.fetchone()
    rank = r["rnk"] if r else None

    cur.close()

    return render_template(
        "users/public_profile.html",
        user=user,
        badges=badges,
        stats=stats,
        rank=rank
    )
