# blueprints/comments_votes.py
from utils.auth import login_required
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
@login_required
def comments():
    post_id_filter = request.args.get('post_id')
    search_query = request.args.get('q')
    
    cur = mysql.connection.cursor()
    
    if post_id_filter:
        # 4+ Table Join (Comments, Posts, Users-1, Users-2) ve Outer Join
        sql = """
            SELECT 
                C.Id, C.Text, C.Score, C.CreationDate,
                C.UserId,
                U_Commenter.DisplayName as UserDisplayName,  -- Yorumu Yazan (User 1)
                P.Title as PostTitle,                        -- Post Başlığı
                U_PostOwner.DisplayName as PostOwnerName     -- Post Sahibi (User 2)
            FROM Comments C
            LEFT JOIN Users U_Commenter ON C.UserId = U_Commenter.Id  -- OUTER JOIN (Yorum sahibi silinmiş olabilir)
            JOIN Posts P ON C.PostId = P.Id                           -- JOIN 3 (Post tablosu)
            JOIN Users U_PostOwner ON P.OwnerUserId = U_PostOwner.Id  -- JOIN 4 (Post sahibini bulmak için Users tablosu tekrar)
            WHERE C.PostId = %s
            ORDER BY C.Score DESC
        """
        cur.execute(sql, (post_id_filter,))
        rows = cur.fetchall()
        
        page_title = rows[0]['PostTitle'] if rows else "Bu postta yorum yok"
        
        return render_template("comments/post_comments.html", comments=rows, page_title=page_title)

    elif search_query:
        sql = "SELECT * FROM comments WHERE Text LIKE %s ORDER BY Id DESC LIMIT 500"
        cur.execute(sql, (f"%{search_query}%",))
        rows = cur.fetchall()
        return render_template("comments/list.html", comments=rows, page_title="Arama Sonuçları", filter_active=False)
    
    else:
        sql = "SELECT * FROM comments ORDER BY Id DESC LIMIT 500"
        cur.execute(sql)
        rows = cur.fetchall()
        return render_template("comments/list.html", comments=rows, page_title="Tüm Yorumlar", filter_active=False)


@comments_votes_bp.route("/comments/add", methods=["GET", "POST"], endpoint="add_comment")
@login_required
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
@login_required
def votes():
    user_id_filter = request.args.get('user_id')
    cur = mysql.connection.cursor()
    stats = []
    
    if user_id_filter:
        # Group By (Tablo yoksa CASE ile isimlendirme yapıyoruz)
        # VoteTypes tablosu olmadığı için ID'ye göre grupluyoruz.
        sql_stats = """
            SELECT 
                CASE 
                    WHEN VoteTypeId = 1 THEN 'AcceptedByOriginator'
                    WHEN VoteTypeId = 2 THEN 'UpMod'
                    WHEN VoteTypeId = 3 THEN 'DownMod'
                    ELSE CONCAT('Type-', VoteTypeId) 
                END as Name, 
                COUNT(*) as VoteCount
            FROM Votes
            WHERE UserId = %s
            GROUP BY VoteTypeId
        """
        cur.execute(sql_stats, (user_id_filter,))
        stats = cur.fetchall()

        # Complex Join (4 Tables) + Nested Query
        # Tablolar: Votes, Posts, Users (Oyu Veren), Users (Post Sahibi)
        sql = """
            SELECT 
                V.Id, V.CreationDate, V.BountyAmount, V.VoteTypeId,
                P.Title as PostTitle,
                P.Score as PostScore,
                U_Voter.DisplayName as VoterName,        -- Oyu Veren (User 1)
                U_Owner.DisplayName as PostOwnerName     -- Post Sahibi (User 2)
            FROM Votes V
            JOIN Posts P ON V.PostId = P.Id                          -- Table 2
            LEFT JOIN Users U_Voter ON V.UserId = U_Voter.Id         -- Table 3 (Outer Join)
            LEFT JOIN Users U_Owner ON P.OwnerUserId = U_Owner.Id    -- Table 4 (Users tekrar)
            WHERE V.UserId = %s
            AND P.Score > (SELECT AVG(Score) FROM Posts)             -- NESTED QUERY
            ORDER BY V.CreationDate DESC
        """
        cur.execute(sql, (user_id_filter,))
        rows = cur.fetchall()
        
        cur.close()
        return render_template("votes/user_votes.html", votes=rows, stats=stats)

    else:
        sql = "SELECT * FROM Votes ORDER BY CreationDate DESC LIMIT 100"
        cur.execute(sql)
        rows = cur.fetchall()
        cur.close()
        return render_template("votes/list.html", votes=rows, stats=None, filter_active=False)

@comments_votes_bp.route("/votes/add", methods=["GET", "POST"], endpoint="add_vote")
@login_required
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
