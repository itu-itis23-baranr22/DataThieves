# blueprints/comments_votes.py
from utils.auth import login_required
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
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

@comments_votes_bp.route("/comments", endpoint="comments", methods=["GET", "POST"])
@login_required
def comments():
    post_id_filter = request.args.get('post_id')
    search_query = request.args.get('q')
    form = CommentInsertForm(request.form)
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
        
        page_title = rows[0]['PostTitle'] if rows else "There are no comments on this post."
        
        return render_template("comments/post_comments.html", comments=rows, page_title=page_title)

    # --- POST İŞLEMİ: Yeni Yorum Ekleme (Aynı kalıyor) ---
    if request.method == "POST" and form.validate():
        try:
            post_id = int(form.PostId.data)
            score = int(form.Score.data)
            text = form.Text.data
            user_id = form.UserId.data
            user_id_val = int(user_id) if user_id else None
            user_display_name = form.UserDisplayName.data or None
            now_str = time.strftime('%Y-%m-%d %H:%M:%S')

            cur.execute("SELECT IFNULL(MAX(Id), 0) + 1 AS next_id FROM Comments")
            comment_id = cur.fetchone()["next_id"]

            sql_insert = """
                INSERT INTO Comments (Id, PostId, Score, Text, CreationDate, UserId, UserDisplayName)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            cur.execute(sql_insert, (comment_id, post_id, score, text, now_str, user_id_val, user_display_name))
            mysql.connection.commit()
            flash("Comment added successfully!", "success")
            return redirect(url_for("comments_votes_bp.comments", post_id=post_id))
        except Exception as e:
            mysql.connection.rollback()
            flash(f"Error: {e}", "danger")
        finally:
            cur.close()

    # --- GET İŞLEMİ: Listeleme ve Post İçeriği ---
    if post_id_filter:
        cur.execute("""
            SELECT P.*, U.DisplayName, U.Reputation
            FROM Posts P
            JOIN Users U ON P.OwnerUserId = U.Id
            WHERE P.Id = %s
        """, (post_id_filter,))
        post_detail = cur.fetchone()

        sql_comments = """
            SELECT 
                C.Id, C.Text, C.Score, C.CreationDate, C.UserId,
                -- Önce Users tablosundaki isme bak, yoksa Comments tablosuna kaydedilen ismi kullan
                COALESCE(U_Commenter.DisplayName, C.UserDisplayName) as UserDisplayName,
                U_PostOwner.DisplayName as PostOwnerName
            FROM Comments C
            LEFT JOIN Users U_Commenter ON C.UserId = U_Commenter.Id
            JOIN Posts P ON C.PostId = P.Id
            JOIN Users U_PostOwner ON P.OwnerUserId = U_PostOwner.Id
            WHERE C.PostId = %s
            ORDER BY C.CreationDate ASC
        """
        cur.execute(sql_comments, (post_id_filter,))
        comment_rows = cur.fetchall()
        
        page_title = post_detail['Title'] if post_detail else "Bu postta yorum yok"
        
        # post_comments.html'e 'post' objesini de gönderiyoruz
        return render_template("comments/post_comments.html", 
                               comments=comment_rows, 
                               post=post_detail, 
                               page_title=page_title, 
                               form=form, 
                               post_id=post_id_filter)

    # Arama ve Genel Liste kısımları aynı kalabilir...
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
            return redirect(url_for("comments_votes_bp.comments", post_id=post_id))
        except Exception as e:
            mysql.connection.rollback()
            flash(f"An error occurred while adding the comment: {e}", "danger")
        finally:
            cur.close()

    return render_template("comments/add.html", form=form)

@comments_votes_bp.route("/comments/delete/<int:comment_id>", methods=["POST"])
@login_required
def delete_comment(comment_id):
    cur = mysql.connection.cursor()
    
    # 1. Yorumu ve ait olduğu PostId'yi bul
    cur.execute("SELECT UserId, PostId FROM Comments WHERE Id = %s", (comment_id,))
    comment = cur.fetchone()
    
    # Eğer yorum yoksa, kullanıcıyı geldiği sayfaya geri gönder
    if not comment:
        flash("Comment not found.", "danger")
        return redirect(request.referrer or url_for("comments_votes_bp.comments"))

    # Silme yetkisi kontrolü
    if session.get('user_id') == comment['UserId'] or session.get('is_admin'):
        try:
            cur.execute("DELETE FROM Comments WHERE Id = %s", (comment_id,))
            mysql.connection.commit()
            flash("Comment deleted successfully.", "success")
        except Exception as e:
            mysql.connection.rollback()
            flash(f"Error: {e}", "danger")
    else:
        flash("You are not authorized to delete this comment.", "danger")
    
    cur.close()

    return redirect(url_for("comments_votes_bp.comments", post_id=comment['PostId']))

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
