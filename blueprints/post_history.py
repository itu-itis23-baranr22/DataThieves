# blueprints/post_history.py
from flask import Blueprint, render_template, request, redirect, url_for, flash
from wtforms import Form, StringField, TextAreaField, validators
import time
from extensions import mysql

post_history_bp = Blueprint("post_history_bp", __name__)

class PostHistoryInsertForm(Form):
    PostHistoryTypeId = StringField("Post History Type ID", [validators.DataRequired()])
    PostId = StringField("Post ID", [validators.DataRequired()])
    RevisionGUID = StringField("Revision GUID", [validators.DataRequired(), validators.Length(max=36)])
    Text = TextAreaField("Text", [validators.Optional()])
    Comment = TextAreaField("Comment", [validators.Optional()])
    UserId = StringField("User ID", [validators.Optional()])
    UserDisplayName = StringField("User Display Name", [validators.Optional(), validators.Length(max=255)])


@post_history_bp.route("/postHistory", endpoint="post_history")
def post_history():
    cur = mysql.connection.cursor()
    sql = """
        SELECT Id, PostHistoryTypeId, PostId, RevisionGUID, CreationDate,
               UserId, Text, Comment, UserDisplayName
        FROM postHistory
        ORDER BY Id DESC
        LIMIT 500;
    """
    cur.execute(sql)
    rows = cur.fetchall()
    cur.close()
    return render_template("post_history/list.html", postHistory=rows)


@post_history_bp.route("/postHistory/add", methods=["GET", "POST"], endpoint="add_post_history")
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

        cur = mysql.connection.cursor()
        cur.execute("SELECT IFNULL(MAX(Id), 0) + 1 AS next_id FROM PostHistory")
        row = cur.fetchone()
        ph_id = row["next_id"]

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
            flash("PostHistory record added successfully.", "success")
            return redirect(url_for("post_history_bp.post_history"))
        except Exception as e:
            mysql.connection.rollback()
            flash(f"An error occurred while adding the PostHistory record: {e}", "danger")
        finally:
            cur.close()

    return render_template("post_history/add.html", form=form)
