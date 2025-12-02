# blueprints/users_badges.py
from flask import Blueprint, render_template, request, redirect, url_for, flash
from wtforms import Form, StringField, validators
import time
from extensions import mysql

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
