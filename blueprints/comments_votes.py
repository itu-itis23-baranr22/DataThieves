# blueprints/comments_votes.py
from flask import Blueprint, render_template, request, redirect, url_for, flash
from wtforms import Form, StringField, TextAreaField, validators
import time
from extensions import mysql

comments_votes_bp = Blueprint("comments_votes_bp", __name__)

class CommentInsertForm(Form):
    PostId = StringField("Post ID", [validators.DataRequired()])
    Score = StringField("Score", [validators.DataRequired()])
    Text = TextAreaField("Comment Text", [validators.DataRequired()])
    UserId = StringField("User ID", [validators.Optional()])
    UserDisplayName = StringField("User Display Name", [validators.Optional(), validators.Length(max=255)])


class VoteInsertForm(Form):
    PostId = StringField("Post ID", [validators.DataRequired()])
    VoteTypeId = StringField("Vote Type ID", [validators.DataRequired()])
    UserId = StringField("User ID", [validators.Optional()])
    BountyAmount = StringField("Bounty Amount", [validators.Optional()])


@comments_votes_bp.route("/comments", endpoint="comments")
def comments():
    # URL'den 'q' parametresini (arama kelimesini) al
    search_query = request.args.get('q')
    
    cur = mysql.connection.cursor()
    
    if search_query:
        # Eğer arama yapıldıysa WHERE koşulu ekle
        # %s kullanarak SQL Injection'ı önlüyoruz
        sql = """
            SELECT Id, PostId, Score, Text, CreationDate, UserId, UserDisplayName
            FROM comments
            WHERE Text LIKE %s
            ORDER BY Id DESC
            LIMIT 500;
        """
        # Arama teriminin başına ve sonuna % ekleyerek "içinde geçen" araması yapıyoruz
        cur.execute(sql, (f"%{search_query}%",))
    else:
        # Arama yoksa eski sorgu çalışsın
        sql = """
            SELECT Id, PostId, Score, Text, CreationDate, UserId, UserDisplayName
            FROM comments
            ORDER BY Id DESC
            LIMIT 500;
        """
        cur.execute(sql)
        
    rows = cur.fetchall()
    cur.close()
    return render_template("comments/list.html", comments=rows)


@comments_votes_bp.route("/comments/add", methods=["GET", "POST"], endpoint="add_comment")
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

        cur = mysql.connection.cursor()
        cur.execute("SELECT IFNULL(MAX(Id), 0) + 1 AS next_id FROM Comments")
        row = cur.fetchone()
        comment_id = row["next_id"]

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
            flash("Comment added successfully.", "success")
            return redirect(url_for("comments_votes_bp.comments"))
        except Exception as e:
            mysql.connection.rollback()
            flash(f"An error occurred while adding the comment: {e}", "danger")
        finally:
            cur.close()

    return render_template("comments/add.html", form=form)


@comments_votes_bp.route("/votes", endpoint="votes")
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
    return render_template("votes/list.html", votes=rows)


@comments_votes_bp.route("/votes/add", methods=["GET", "POST"], endpoint="add_vote")
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
        cur.execute("SELECT IFNULL(MAX(Id), 0) + 1 AS next_id FROM Votes")
        row = cur.fetchone()
        vote_id = row["next_id"]

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
            flash("Vote added successfully.", "success")
            return redirect(url_for("comments_votes_bp.votes"))
        except Exception as e:
            mysql.connection.rollback()
            flash(f"Database error while adding vote: {e}", "danger")
        finally:
            cur.close()

    return render_template("votes/add.html", form=form)
