from utils.auth import login_required, admin_required
from flask import Blueprint, render_template, request, redirect, url_for, flash
from wtforms import Form, StringField, TextAreaField, validators
import time
from extensions import mysql
import math
from flask import session, abort
import uuid


PH_CONTENT_TITLE_TYPES = (1, 4, 7)
PH_CONTENT_BODY_TYPES = (2, 5, 8)
PH_CONTENT_TAGS_TYPES = (3, 6, 9)
PH_CONTENT_ALL_TYPES = PH_CONTENT_TITLE_TYPES + PH_CONTENT_BODY_TYPES + PH_CONTENT_TAGS_TYPES


POST_HISTORY_TYPE_MAPPING = {
    1: "Initial Title",
    2: "Initial Body",
    3: "Initial Tags",
    4: "Edit Title",
    5: "Edit Body",
    6: "Edit Tags",
    7: "Rollback Title",
    8: "Rollback Body",
    9: "Rollback Tags",

    10: "Post Closed",
    11: "Post Reopened",
    12: "Post Deleted",
    13: "Post Undeleted",
    14: "Post Locked",
    15: "Post Unlocked",
    16: "Community Owned",
    17: "Post Migrated",
    18: "Question Merged",
    19: "Question Protected",
    20: "Question Unprotected",
    21: "Post Dissociated",

    23: "Legacy System Event (23)",
    24: "Legacy System Event (24)",
    25: "Migrated Away (Source) (Status)",
    26: "Legacy System Event (26)",
    27: "Legacy System Event (27)",
    28: "Legacy System Event (28)",
    29: "Legacy System Event (29)",
    30: "Legacy System Event (30)",
    35: "Migrated Away (Status)",
    36: "Migrated Here (Status)",
}

post_history_bp = Blueprint("post_history_bp", __name__)


class PostHistoryInsertForm(Form):
    PostHistoryTypeId = StringField("Post History Type ID", [validators.DataRequired()])
    PostId = StringField("Post ID", [validators.DataRequired()])
    RevisionGUID = StringField("Revision GUID", [validators.DataRequired(), validators.Length(max=36)])
    Text = TextAreaField("Text", [validators.Optional()])
    Comment = TextAreaField("Comment", [validators.Optional()])
    UserId = StringField("User ID", [validators.Optional()])
    UserDisplayName = StringField("User Display Name", [validators.Optional(), validators.Length(max=255)])


def _get_post_owner_id(cur, post_id: int) -> int:
    cur.execute("SELECT OwnerUserId FROM Posts WHERE Id = %s", (post_id,))
    row = cur.fetchone()
    if not row:
        abort(404)
    return int((row.get("OwnerUserId") if hasattr(row, "get") else row["OwnerUserId"]) or 0)


def _require_owner_or_admin(cur, post_id: int):
    is_admin = bool(session.get("is_admin"))
    current_user_id = int(session.get("user_id", 0))
    owner_id = _get_post_owner_id(cur, post_id)
    if (not is_admin) and (owner_id != current_user_id):
        abort(403)


@post_history_bp.route("/post/<int:post_id>/history", endpoint="post_history_timeline")
@login_required
def post_history_timeline(post_id):
    active_filter = request.args.get("filter", "all")

    cur = mysql.connection.cursor()

    cur.execute("SELECT Title, Body, OwnerUserId FROM Posts WHERE Id = %s", (post_id,))
    post_row = cur.fetchone()
    if not post_row:
        cur.close()
        abort(404)

    post_title = post_row.get("Title") or f"Post ID: {post_id}"
    current_post_body = post_row.get("Body") or ""

    is_admin = bool(session.get("is_admin"))
    current_user_id = int(session.get("user_id", 0))
    owner_id = int(post_row.get("OwnerUserId") or 0)
    can_edit_history_comment = is_admin or (owner_id == current_user_id)

    filter_query = ""
    if active_filter == "title":
        filter_query = "AND PH.PostHistoryTypeId IN (1, 4, 7)"
    elif active_filter == "body":
        filter_query = "AND PH.PostHistoryTypeId IN (2, 5, 8)"
    elif active_filter == "tags":
        filter_query = "AND PH.PostHistoryTypeId IN (3, 6, 9)"
    elif active_filter == "others":
        filter_query = f"AND PH.PostHistoryTypeId NOT IN ({','.join(str(x) for x in PH_CONTENT_ALL_TYPES)})"

    sql = f"""
        SELECT
            PH.Id AS HistoryId,
            PH.CreationDate,
            PH.Text AS RevisionText,
            PH.Comment AS EditComment,
            PH.PostHistoryTypeId,
            COALESCE(U.DisplayName, PH.UserDisplayName, 'Anonymous User') AS UserName
        FROM
            PostHistory AS PH
        LEFT OUTER JOIN Users AS U ON PH.UserId = U.Id
        INNER JOIN (
            SELECT PostId, COUNT(Id) AS TotalRevisions
            FROM PostHistory
            GROUP BY PostId
        ) AS T_Revisions ON PH.PostId = T_Revisions.PostId
        INNER JOIN (
            SELECT MAX(Id) AS MaxTagId, 'GLOBAL_KEY' AS JoinKey
            FROM Tags GROUP BY JoinKey
        ) AS T_Tags_Check ON 1=1
        WHERE
            PH.PostId = %s {filter_query}
        ORDER BY
            PH.CreationDate DESC;
    """

    cur.execute(sql, (post_id,))
    history_records = cur.fetchall()
    cur.close()

    processed_records = []
    for record in history_records:
        type_id = int(record["PostHistoryTypeId"])
        record["ChangeType"] = POST_HISTORY_TYPE_MAPPING.get(type_id, f"Other Event (Type {type_id})")
        processed_records.append(record)

    return render_template(
        "post_history/history_timeline.html",
        post_id=post_id,
        post_title=post_title,
        current_post_body=current_post_body,
        history_records=processed_records,
        active_filter=active_filter,
        can_edit_history_comment=can_edit_history_comment
    )


@post_history_bp.route("/postHistory", endpoint="post_history")
@login_required
@admin_required
def post_history():
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 50, type=int)

    safe_sort_columns = {
        "Id": "Id",
        "Type": "PostHistoryTypeId",
        "PostId": "PostId",
        "User": "UserId",
        "Date": "CreationDate"
    }

    sort_by = request.args.get("sort_by", "Id")
    sort_direction = request.args.get("sort_direction", "DESC").upper()

    if sort_by not in safe_sort_columns:
        sort_by = "Id"
    db_sort_column = safe_sort_columns[sort_by]

    if sort_direction not in ("ASC", "DESC"):
        sort_direction = "DESC"

    offset = (page - 1) * per_page

    cur = mysql.connection.cursor()

    count_sql = "SELECT COUNT(*) AS total_count FROM PostHistory"
    cur.execute(count_sql)
    total_count = cur.fetchone()["total_count"]
    total_pages = math.ceil(total_count / per_page)

    data_sql = f"""
        SELECT Id, PostHistoryTypeId, PostId, RevisionGUID, CreationDate,
               UserId, Text, Comment, UserDisplayName
        FROM PostHistory
        ORDER BY {db_sort_column} {sort_direction}
        LIMIT %s OFFSET %s;
    """

    cur.execute(data_sql, (per_page, offset))
    rows = cur.fetchall()
    cur.close()

    pagination_context = {
        "current_page": page,
        "total_pages": total_pages,
        "per_page": per_page,
        "total_count": total_count,
        "sort_by": sort_by,
        "sort_direction": sort_direction,
    }

    return render_template(
        "post_history/list.html",
        postHistory=rows,
        pagination=pagination_context
    )


@post_history_bp.route("/postHistory/add", methods=["GET", "POST"], endpoint="add_post_history")
@login_required
@admin_required
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
        now_str = time.strftime("%Y-%m-%d %H:%M:%S")

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


@post_history_bp.route("/postHistory/<int:history_id>/comment", methods=["POST"], endpoint="update_history_comment")
@login_required
def update_history_comment(history_id):
    cur = mysql.connection.cursor()
    try:
        new_comment = (request.form.get("comment") or "").strip()
        post_id = int(request.form.get("post_id") or 0)

        cur.execute("SELECT Id, PostId FROM PostHistory WHERE Id = %s", (history_id,))
        row = cur.fetchone()
        if not row:
            abort(404)

        if not post_id:
            post_id = int(row["PostId"])

        _require_owner_or_admin(cur, post_id)

        cur.execute("""
            UPDATE PostHistory
            SET Comment = %s
            WHERE Id = %s
        """, (new_comment if new_comment else None, history_id))

        mysql.connection.commit()
        flash("Edit comment updated.", "success")
        return redirect(url_for("post_history_bp.post_history_timeline", post_id=post_id))

    except Exception as e:
        mysql.connection.rollback()
        flash(f"Update comment error: {e}", "danger")
        return redirect(request.referrer or url_for("post_history_bp.post_history"))
    finally:
        cur.close()


@post_history_bp.route("/post/<int:post_id>/history/undo_last", methods=["POST"], endpoint="undo_last_edit")
@login_required
def undo_last_edit(post_id):
    cur = mysql.connection.cursor()
    try:
        _require_owner_or_admin(cur, post_id)

        current_user_id = int(session.get("user_id", 0))

        cur.execute("""
            SELECT Id, PostHistoryTypeId, CreationDate
            FROM PostHistory
            WHERE PostId = %s
            ORDER BY CreationDate DESC
            LIMIT 1
        """, (post_id,))
        last = cur.fetchone()

        if not last:
            flash("No history to undo.", "warning")
            return redirect(url_for("post_history_bp.post_history_timeline", post_id=post_id))

        last_id = int(last["Id"])
        t = int(last["PostHistoryTypeId"])
        last_date = last["CreationDate"]

        if t in PH_CONTENT_TITLE_TYPES:
            col = "Title"
            prev_types = PH_CONTENT_TITLE_TYPES
            rollback_type = 7
        elif t in PH_CONTENT_BODY_TYPES:
            col = "Body"
            prev_types = PH_CONTENT_BODY_TYPES
            rollback_type = 8
        elif t in PH_CONTENT_TAGS_TYPES:
            col = "Tags"
            prev_types = PH_CONTENT_TAGS_TYPES
            rollback_type = 9
        else:
            cur.execute("DELETE FROM PostHistory WHERE Id = %s", (last_id,))
            mysql.connection.commit()
            flash(f"Last history item deleted (type={t}). No rollback applied.", "success")
            return redirect(url_for("post_history_bp.post_history_timeline", post_id=post_id))

        cur.execute(f"""
            SELECT Text
            FROM PostHistory
            WHERE PostId = %s
              AND PostHistoryTypeId IN ({",".join(["%s"]*len(prev_types))})
              AND CreationDate < %s
            ORDER BY CreationDate DESC
            LIMIT 1
        """, (post_id, *prev_types, last_date))
        prev = cur.fetchone()
        prev_text = (prev["Text"] if prev else None)

        cur.execute("DELETE FROM PostHistory WHERE Id = %s", (last_id,))

        now_str = time.strftime("%Y-%m-%d %H:%M:%S")
        cur.execute(f"""
            UPDATE Posts
            SET {col} = %s,
                LasActivityDate = %s,
                LastEditDate = %s,
                LastEditorUserId = %s,
                LastEditorDisplayName = %s
            WHERE Id = %s
        """, (
            prev_text,
            now_str,
            now_str,
            current_user_id,
            session.get("DisplayName"),
            post_id
        ))

        cur.execute("SELECT IFNULL(MAX(Id),0) + 1 AS next_id FROM PostHistory")
        new_id = int(cur.fetchone()["next_id"])

        cur.execute("""
            INSERT INTO PostHistory
                (Id, PostHistoryTypeId, PostId, RevisionGUID, CreationDate,
                 UserId, Text, Comment, UserDisplayName)
            VALUES
                (%s, %s, %s, %s, %s,
                 %s, %s, %s, %s)
        """, (
            new_id,
            rollback_type,
            post_id,
            str(uuid.uuid4()),
            now_str,
            current_user_id,
            prev_text,
            f"Undo last edit: deleted history #{last_id}",
            session.get("DisplayName")
        ))

        mysql.connection.commit()
        flash("Last edit undone (deleted + rolled back).", "success")
        return redirect(url_for("post_history_bp.post_history_timeline", post_id=post_id))

    except Exception as e:
        mysql.connection.rollback()
        flash(f"Undo error: {e}", "danger")
        return redirect(url_for("post_history_bp.post_history_timeline", post_id=post_id))
    finally:
        cur.close()
