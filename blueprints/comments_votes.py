from utils.auth import login_required
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, abort
from wtforms import Form, StringField, TextAreaField, validators
import time
from extensions import mysql
import datetime
import MySQLdb.cursors
import math

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



def recalc_user_reputation(user_id: int) -> int:
    """
    Basit rep modeli:
      - Question (PostTypeId=1) upvote  +5
      - Answer   (PostTypeId=2) upvote +10
      - Downvote (her ikisi)            -2
      - Favorite (VoteTypeId=5)         0
    """
    cur = mysql.connection.cursor()
    try:
        cur.execute("""
            SELECT COALESCE(SUM(
                CASE
                    WHEN v.VoteTypeId = 2 AND p.PostTypeId = 2 THEN 10
                    WHEN v.VoteTypeId = 2 AND p.PostTypeId = 1 THEN 5
                    WHEN v.VoteTypeId = 3 THEN -2
                    ELSE 0
                END
            ), 0) AS rep
            FROM Votes v
            JOIN Posts p ON p.Id = v.PostId
            WHERE p.OwnerUserId = %s
        """, (user_id,))
        rep = int(cur.fetchone()["rep"])

        cur.execute("UPDATE Users SET Reputation = %s WHERE Id = %s", (rep, user_id))
        mysql.connection.commit()
        return rep
    finally:
        cur.close()


@comments_votes_bp.route("/comments", endpoint="comments", methods=["GET", "POST"])
@login_required
def comments():
    post_id_filter = request.args.get("post_id")
    search_query = request.args.get("q", "").strip()
    page = request.args.get("page", 1, type=int)
    per_page = 20 
    offset = (page - 1) * per_page
    
    form = CommentInsertForm(request.form)
    cur = mysql.connection.cursor()

    logged_in_id = session.get('user_id')
    user_stats = None
    if logged_in_id:
        cur.execute("SELECT ProfileImageUrl, Reputation FROM Users WHERE Id = %s", (logged_in_id,))
        user_stats = cur.fetchone()


    if request.method == "POST" and form.validate():

        pass 

    if post_id_filter:

        cur.execute("""
            SELECT P.*, U.DisplayName, U.Reputation
            FROM Posts P
            LEFT JOIN Users U ON P.OwnerUserId = U.Id
            WHERE P.Id = %s
        """, (post_id_filter,))
        post_detail = cur.fetchone()


        sql_comments = """
            SELECT C.*, COALESCE(U.DisplayName, C.UserDisplayName) as UserDisplayName
            FROM Comments C
            LEFT JOIN Users U ON C.UserId = U.Id
            WHERE C.PostId = %s
            ORDER BY C.CreationDate ASC
        """
        cur.execute(sql_comments, (post_id_filter,))
        comment_rows = cur.fetchall()

        import MySQLdb.cursors
 
        cur_related = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        

        sql_related = """
            SELECT DISTINCT P.Id, P.Title, P.Score, P.CreaionDate, PL.Id AS LinkId
            FROM Posts P
            JOIN PostLinks PL ON (PL.PostId = %s AND P.Id = PL.RelatedPostId) 
                              OR (PL.RelatedPostId = %s AND P.Id = PL.PostId)
            ORDER BY P.Score DESC LIMIT 10
        """
        cur_related.execute(sql_related, (post_id_filter, post_id_filter))
        related_posts = cur_related.fetchall()
        cur_related.close()
        

        page_title = post_detail["Title"] if post_detail and post_detail.get("Title") else "Yorumlar"
        cur.close()
        
        return render_template(
            "comments/post_comments.html",
            comments=comment_rows,
            post=post_detail,
            page_title=page_title,
            form=form,
            post_id=post_id_filter,
            related_posts=related_posts,
            user_stats=user_stats
        )


    else:
        if search_query:
   
            count_sql = "SELECT COUNT(*) as total FROM Comments WHERE Text LIKE %s"
            cur.execute(count_sql, (f"%{search_query}%",))
            

            data_sql = "SELECT * FROM Comments WHERE Text LIKE %s ORDER BY Id DESC LIMIT %s OFFSET %s"
            data_params = (f"%{search_query}%", per_page, offset)
            page_title = f"'{search_query}' için Sonuçlar"
        else:
   
            count_sql = "SELECT COUNT(*) as total FROM Comments"
            cur.execute(count_sql)
            

            data_sql = "SELECT * FROM Comments ORDER BY Id DESC LIMIT %s OFFSET %s"
            data_params = (per_page, offset)
            page_title = "Tüm Yorumlar"


        total_count = cur.fetchone()["total"]
        total_pages = math.ceil(total_count / per_page)

        cur.execute(data_sql, data_params)
        rows = cur.fetchall()
        cur.close()

 
        return render_template(
            "comments/list.html", 
            comments=rows, 
            page_title=page_title, 
            user_stats=user_stats,
            q=search_query,       
            page=page,            
            total_pages=total_pages 
        )

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

        now_str = time.strftime("%Y-%m-%d %H:%M:%S")

        cur = mysql.connection.cursor()
        cur.execute("SELECT IFNULL(MAX(Id), 0) + 1 AS next_id FROM Comments")
        row = cur.fetchone()
        comment_id = row["next_id"] if row else 1

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
            user_display_name,
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

    cur.execute("SELECT UserId, PostId FROM Comments WHERE Id = %s", (comment_id,))
    comment = cur.fetchone()

    if not comment:
        flash("Comment not found.", "danger")
        return redirect(request.referrer or url_for("comments_votes_bp.comments"))

    if session.get("user_id") == comment["UserId"] or session.get("is_admin"):
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
    return redirect(url_for("comments_votes_bp.comments", post_id=comment["PostId"]))


@comments_votes_bp.route("/comments/edit/<int:comment_id>", methods=["GET", "POST"], endpoint="edit_comment")
@login_required
def edit_comment(comment_id):
    cur = mysql.connection.cursor()
    

    cur.execute("SELECT * FROM Comments WHERE Id = %s", (comment_id,))
    comment = cur.fetchone()

    if not comment:
        cur.close()
        flash("Comment not found.", "danger")
        return redirect(url_for("comments_votes_bp.comments"))


    if not (session.get("user_id") == comment["UserId"] or session.get("is_admin")):
        cur.close()
        flash("You are not authorized to edit this comment.", "danger")
        return redirect(url_for("comments_votes_bp.comments"))


    form = CommentInsertForm(request.form)
    if request.method == "GET":
        form.PostId.data = comment["PostId"]
        form.Score.data = comment["Score"]
        form.Text.data = comment["Text"]
        form.UserId.data = comment["UserId"]
        form.UserDisplayName.data = comment["UserDisplayName"]


    if request.method == "POST" and form.validate():
        try:
            sql = """
                UPDATE Comments 
                SET Score = %s, Text = %s, UserDisplayName = %s
                WHERE Id = %s
            """
            cur.execute(sql, (
                form.Score.data,
                form.Text.data,
                form.UserDisplayName.data,
                comment_id
            ))
            mysql.connection.commit()
            flash("Comment updated successfully.", "success")
            return redirect(url_for("comments_votes_bp.comments", post_id=comment["PostId"]))
        except Exception as e:
            mysql.connection.rollback()
            flash(f"Error: {e}", "danger")
        finally:
            cur.close()

    return render_template("comments/add.html", form=form, edit_mode=True, comment_id=comment_id)


@comments_votes_bp.route("/posts/<int:post_id>/favorite", methods=["POST"], endpoint="favorite_post")
@login_required
def favorite_post(post_id):
    FAVORITE = 5
    user_id = int(session["user_id"])
    cur = mysql.connection.cursor()

    try:
        cur.execute("SELECT Id FROM Posts WHERE Id = %s", (post_id,))
        if not cur.fetchone():
            abort(404)

        cur.execute("""
            SELECT Id
            FROM Votes
            WHERE PostId = %s AND UserId = %s AND VoteTypeId = %s
            ORDER BY Id DESC
            LIMIT 1
        """, (post_id, user_id, FAVORITE))
        existing = cur.fetchone()

        if existing:
            cur.execute("DELETE FROM Votes WHERE Id = %s", (existing["Id"],))
            my_fav = 0
        else:
            cur.execute("SELECT IFNULL(MAX(Id),0) + 1 AS next_id FROM Votes")
            vote_id = cur.fetchone()["next_id"]

            cur.execute("""
                INSERT INTO Votes (Id, PostId, VoteTypeId, CreationDate, UserId, BountyAmount)
                VALUES (%s, %s, %s, NOW(), %s, %s)
            """, (vote_id, post_id, FAVORITE, user_id, None))
            my_fav = 1

        cur.execute("""
            SELECT COUNT(*) AS fav
            FROM Votes
            WHERE PostId = %s AND VoteTypeId = %s
        """, (post_id, FAVORITE))
        fav_count = int(cur.fetchone()["fav"])

        mysql.connection.commit()

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return {"ok": True, "fav": fav_count, "my_fav": my_fav}

    except Exception as e:
        mysql.connection.rollback()
        if request.headers.get("X-Requested-With") == "XMLHttpHttpRequest":
            return {"ok": False, "error": str(e)}, 500
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return {"ok": False, "error": str(e)}, 500
        raise
    finally:
        cur.close()

    return redirect(request.referrer or url_for("posts_bp.forum_posts"))


@comments_votes_bp.route("/votes", endpoint="votes")
@login_required
def votes():
    user_id_filter = request.args.get("user_id")
    vote_type_filter = request.args.get("vote_type") 
    cur = mysql.connection.cursor()

    only_mine = request.args.get("only_mine")  

    logged_in_id = session.get('user_id')
    cur.execute("SELECT ProfileImageUrl, Reputation FROM Users WHERE Id = %s", (logged_in_id,))
    user_stats = cur.fetchone()

    stats = []

    if user_id_filter:
        sql_stats = """
            SELECT 
                CASE 
                    WHEN VoteTypeId = 2 THEN 'UpMod'
                    WHEN VoteTypeId = 3 THEN 'DownMod'
                    WHEN VoteTypeId = 5 THEN 'Favorite'
                END as Name, 
                COUNT(*) as VoteCount
            FROM Votes
            WHERE UserId = %s AND VoteTypeId IN (2, 3, 5)
            GROUP BY VoteTypeId
        """
        cur.execute(sql_stats, (user_id_filter,))
        stats = cur.fetchall()

        sql = """
            SELECT 
                V.Id,
                P.Id as TargetPostId,
                V.CreationDate, V.BountyAmount, V.VoteTypeId,
                P.Title as PostTitle,
                P.Score as PostScore,
                U_Voter.DisplayName as VoterName,
                U_Owner.DisplayName as PostOwnerName
            FROM Votes V
            JOIN Posts P ON V.PostId = P.Id
            LEFT JOIN Users U_Voter ON V.UserId = U_Voter.Id
            LEFT JOIN Users U_Owner ON P.OwnerUserId = U_Owner.Id
            WHERE V.UserId = %s
        """

        params = [user_id_filter]

        if vote_type_filter and vote_type_filter != "all":
            sql += " AND V.VoteTypeId = %s"
            params.append(vote_type_filter)
            
        sql += " ORDER BY V.CreationDate DESC"

        cur.execute(sql, tuple(params))
        rows = cur.fetchall()

        cur.close()
        return render_template("votes/user_votes.html", votes=rows, stats=stats, current_type=vote_type_filter, user_id=user_id_filter,user_stats=user_stats)

    else:
        sql = """
            SELECT 
                V.Id,
                V.PostId,
                V.CreationDate, V.BountyAmount, V.VoteTypeId,
                P.Title as PostTitle,
                P.Score as PostScore,
                U_Voter.DisplayName as VoterName,
                U_Owner.DisplayName as PostOwnerName
            FROM Votes V
            JOIN Posts P ON V.PostId = P.Id
            LEFT JOIN Users U_Voter ON V.UserId = U_Voter.Id
            LEFT JOIN Users U_Owner ON P.OwnerUserId = U_Owner.Id
            WHERE 1=1
        """
        params = []


        if vote_type_filter and vote_type_filter != "all":
            sql += " AND V.VoteTypeId = %s"
            params.append(vote_type_filter)

        sql += " ORDER BY V.CreationDate DESC LIMIT 100"

        cur.execute(sql, tuple(params))
        rows = cur.fetchall()
        cur.close()

        return render_template(
            "votes/list.html",
            votes=rows,
            stats=None,
            user_stats=user_stats,
            current_type=vote_type_filter)


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

        now_str = time.strftime("%Y-%m-%d %H:%M:%S")

        cur = mysql.connection.cursor()
        cur.execute("SELECT IFNULL(MAX(Id), 0) + 1 AS next_id FROM Votes")
        row = cur.fetchone()
        vote_id = row["next_id"] if row else 1

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
            bounty_val,
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


@comments_votes_bp.route("/posts/<int:post_id>/vote", methods=["POST"], endpoint="vote_post")
@login_required
def vote_post(post_id):
    vote_type = request.form.get("vote_type")
    if vote_type not in ("up", "down"):
        abort(400)

 
    UPVOTE = 2
    DOWNVOTE = 3
    desired_vote = UPVOTE if vote_type == "up" else DOWNVOTE

    user_id = int(session["user_id"])
    cur = mysql.connection.cursor()

    try:

        cur.execute("SELECT Id, OwnerUserId FROM Posts WHERE Id = %s", (post_id,))
        post_row = cur.fetchone()
        if not post_row:
            abort(404)

        owner_id = int(post_row.get("OwnerUserId") or 0)


        cur.execute("""
            SELECT Id, VoteTypeId
            FROM Votes
            WHERE PostId = %s AND UserId = %s AND VoteTypeId IN (2,3)
            ORDER BY Id DESC
        """, (post_id, user_id))
        existing_rows = cur.fetchall()
        existing = existing_rows[0] if existing_rows else None

  
        if existing_rows and len(existing_rows) > 1:
            ids_to_delete = [r["Id"] for r in existing_rows[1:]]
            cur.execute(
                f"DELETE FROM Votes WHERE Id IN ({','.join(['%s']*len(ids_to_delete))})",
                tuple(ids_to_delete)
            )


        if not existing:

            cur.execute("SELECT IFNULL(MAX(Id),0) + 1 AS next_id FROM Votes")
            vote_id = cur.fetchone()["next_id"]

            cur.execute("""
                INSERT INTO Votes
                (Id, PostId, VoteTypeId, CreationDate, UserId, BountyAmount)
                VALUES (%s, %s, %s, NOW(), %s, %s)
            """, (vote_id, post_id, desired_vote, user_id, None))
            my_vote = desired_vote

        else:
            old_vote = existing["VoteTypeId"]
            vote_id = existing["Id"]

            if old_vote == desired_vote:
  
                cur.execute("DELETE FROM Votes WHERE Id = %s", (vote_id,))
                my_vote = None
            else:
   
                cur.execute("""
                    UPDATE Votes
                    SET VoteTypeId = %s,
                        CreationDate = NOW()
                    WHERE Id = %s
                """, (desired_vote, vote_id))
                my_vote = desired_vote

 
        cur.execute("""
            UPDATE Posts
            SET Score = (
                SELECT COALESCE(SUM(
                    CASE
                        WHEN VoteTypeId = 2 THEN 1
                        WHEN VoteTypeId = 3 THEN -1
                        ELSE 0
                    END
                ), 0)
                FROM Votes
                WHERE PostId = %s
            )
            WHERE Id = %s
        """, (post_id, post_id))


        cur.execute("""
            SELECT
              COALESCE(SUM(CASE WHEN VoteTypeId = 2 THEN 1 ELSE 0 END),0) AS up,
              COALESCE(SUM(CASE WHEN VoteTypeId = 3 THEN 1 ELSE 0 END),0) AS down
            FROM Votes
            WHERE PostId = %s
        """, (post_id,))
        counts = cur.fetchone()
        up = int(counts["up"])
        down = int(counts["down"])

        owner_rep = 0
        if owner_id:
            cur.execute("""
                SELECT COALESCE(SUM(
                    CASE
                        WHEN v.VoteTypeId = 2 AND p.PostTypeId = 2 THEN 10
                        WHEN v.VoteTypeId = 2 AND p.PostTypeId = 1 THEN 5
                        WHEN v.VoteTypeId = 3 THEN -2
                        ELSE 0
                    END
                ), 0) AS rep
                FROM Votes v
                JOIN Posts p ON p.Id = v.PostId
                WHERE p.OwnerUserId = %s
            """, (owner_id,))
            owner_rep = int(cur.fetchone()["rep"])

            cur.execute("UPDATE Users SET Reputation = %s WHERE Id = %s", (owner_rep, owner_id))

        mysql.connection.commit()


        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return {"ok": True, "up": up, "down": down, "my_vote": my_vote, "owner_rep": owner_rep}

    except Exception as e:
        mysql.connection.rollback()
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return {"ok": False, "error": str(e)}, 500
        raise
    finally:
        cur.close()

    return redirect(request.referrer or url_for("posts_bp.forum_posts"))



@comments_votes_bp.route("/votes/edit/<int:vote_id>", methods=["GET", "POST"], endpoint="edit_vote")
@login_required
def edit_vote(vote_id):
    cur = mysql.connection.cursor()
    
 
    cur.execute("SELECT * FROM Votes WHERE Id = %s", (vote_id,))
    vote = cur.fetchone()

    if not vote:
        cur.close()
        flash("Vote not found.", "danger")
        return redirect(url_for("comments_votes_bp.votes"))

  
    if not (session.get("user_id") == vote["UserId"] or session.get("is_admin")):
        cur.close()
        flash("You are not authorized to edit this vote.", "danger")
        return redirect(url_for("comments_votes_bp.votes"))


    form = VoteInsertForm(request.form)
    if request.method == "GET":
        form.PostId.data = vote["PostId"]
        form.VoteTypeId.data = vote["VoteTypeId"]
        form.UserId.data = vote["UserId"]
        form.BountyAmount.data = vote["BountyAmount"]

 
    if request.method == "POST" and form.validate():
        try:
            sql = """
                UPDATE Votes 
                SET VoteTypeId = %s, BountyAmount = %s
                WHERE Id = %s
            """
            cur.execute(sql, (
                form.VoteTypeId.data,
                form.BountyAmount.data if form.BountyAmount.data else None,
                vote_id
            ))
            mysql.connection.commit()
            flash("Vote updated successfully.", "success")
            return redirect(url_for("comments_votes_bp.votes"))
        except Exception as e:
            mysql.connection.rollback()
            flash(f"Error: {e}", "danger")
        finally:
            cur.close()

    return render_template("votes/add.html", form=form, edit_mode=True, vote_id=vote_id)


@comments_votes_bp.route("/votes/delete/<int:vote_id>", methods=["POST"], endpoint="delete_vote")
@login_required
def delete_vote(vote_id):
    if not session.get("is_admin"):
        flash("Only admins can delete votes.", "danger")
        return redirect(url_for("comments_votes_bp.votes"))

    cur = mysql.connection.cursor()
    try:
        cur.execute("DELETE FROM Votes WHERE Id = %s", (vote_id,))
        mysql.connection.commit()
        flash("Vote deleted successfully.", "success")
    except Exception as e:
        mysql.connection.rollback()
        flash(f"Error: {e}", "danger")
    finally:
        cur.close()
    
    return redirect(url_for("comments_votes_bp.votes"))


@comments_votes_bp.route("/votes/report", endpoint="votes_report")
@login_required
def votes_report():
    vote_type = request.args.get("vote_type", "all")

    sql = """
        SELECT
            V.Id AS VoteId,
            V.CreationDate,
            V.VoteTypeId,
            P.Id AS PostId,
            P.Title,
            P.Score,
            U_Voter.DisplayName AS VoterName,
            U_Owner.DisplayName AS PostOwnerName
        FROM Votes V
        JOIN Posts P ON V.PostId = P.Id
        LEFT JOIN Users U_Voter ON V.UserId = U_Voter.Id
        LEFT JOIN Users U_Owner ON P.OwnerUserId = U_Owner.Id
        WHERE 1=1
    """
    params = []

    if vote_type != "all":
        sql += " AND V.VoteTypeId = %s"
        params.append(vote_type)

    sql += " ORDER BY V.CreationDate DESC LIMIT 200"

    cur = mysql.connection.cursor()
    cur.execute(sql, tuple(params))
    rows = cur.fetchall()
    cur.close()

    return render_template("votes/report.html", votes=rows, current_type=vote_type)