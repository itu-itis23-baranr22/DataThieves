from utils.auth import login_required
# blueprints/post_history.py
from flask import Blueprint, render_template, request, redirect, url_for, flash
from wtforms import Form, StringField, TextAreaField, validators
import time
from extensions import mysql
import math

# Dictionary mapping for PostHistoryTypeId 
POST_HISTORY_TYPE_MAPPING = {
    1: "Initial Title",
    2: "Initial Body",
    3: "Initial Tags",
    4: "Title Edit",
    5: "Body Edit",
    6: "Tags Edit",
    7: "Title Rollback",
    8: "Body Rollback",
    9: "Tags Rollback",
    10: "Closed Vote (Status)",
    11: "Reopened Vote (Status)",
    12: "Deleted Vote (Status)",
    13: "Undeleted Vote (Status)",
    14: "Locked (Status)",
    15: "Unlocked (Status)",
    16: "Community Owned (Status)",
    25: "Migrated Away (Source) (Status)",
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

@post_history_bp.route("/post/<int:post_id>/history", endpoint="post_history_timeline")
@login_required
def post_history_timeline(post_id):
    active_filter = request.args.get('filter', 'all')

    cur = mysql.connection.cursor()
    
    filter_query = ""
    if active_filter == 'title':
        filter_query = "AND PH.PostHistoryTypeId IN (1, 4, 7)"
    elif active_filter == 'body':
        filter_query = "AND PH.PostHistoryTypeId IN (2, 5, 8)"
    elif active_filter == 'tags':
        filter_query = "AND PH.PostHistoryTypeId IN (3, 6, 9)"

    sql = f"""
        SELECT
            PH.Id AS HistoryId,
            PH.CreationDate,
            PH.Text AS RevisionText,
            PH.Comment AS EditComment,
            PH.PostHistoryTypeId,
            COALESCE(U.DisplayName, PH.UserDisplayName, 'Anonymous User') AS UserName,
            P.Title AS PostTitle,
            P.Body AS CurrentBody
        FROM
            PostHistory AS PH
        INNER JOIN Posts AS P ON PH.PostId = P.Id
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

    # Map PostHistoryTypeId
    processed_records = []
    post_title = f"Post ID: {post_id}"
    current_post_body = ""

    if history_records:
        post_title = history_records[0].get('PostTitle', post_title)
        current_post_body = history_records[0].get('CurrentBody', "")

    for record in history_records:
        type_id = record['PostHistoryTypeId']
        record['ChangeType'] = POST_HISTORY_TYPE_MAPPING.get(type_id, f"Unknown Type ({type_id})")
        processed_records.append(record)

    return render_template(
        "post_history/history_timeline.html",
        post_id=post_id,
        post_title=post_title,
        current_post_body=current_post_body,
        history_records=processed_records,
        active_filter=active_filter
    )

@post_history_bp.route("/postHistory", endpoint="post_history")
@login_required
def post_history():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)

    safe_sort_columns = {
        'Id': 'Id', 
        'Type': 'PostHistoryTypeId', 
        'PostId': 'PostId', 
        'User': 'UserId', 
        'Date': 'CreationDate'
    }
    
    sort_by = request.args.get('sort_by', 'Id')
    sort_direction = request.args.get('sort_direction', 'DESC').upper()
    
    if sort_by not in safe_sort_columns:
        sort_by = 'Id'
    db_sort_column = safe_sort_columns[sort_by]

    if sort_direction not in ('ASC', 'DESC'):
        sort_direction = 'DESC'

    offset = (page - 1) * per_page
    
    cur = mysql.connection.cursor()

    count_sql = "SELECT COUNT(*) AS total_count FROM postHistory"
    cur.execute(count_sql)
    total_count = cur.fetchone()['total_count']
    total_pages = math.ceil(total_count / per_page)

    data_sql = f"""
        SELECT Id, PostHistoryTypeId, PostId, RevisionGUID, CreationDate,
               UserId, Text, Comment, UserDisplayName
        FROM postHistory
        ORDER BY {db_sort_column} {sort_direction}
        LIMIT %s OFFSET %s;
    """
    
    cur.execute(data_sql, (per_page, offset))
    rows = cur.fetchall()
    cur.close()
    
    pagination_context = {
        'current_page': page,
        'total_pages': total_pages,
        'per_page': per_page,
        'total_count': total_count,
        'sort_by': sort_by,
        'sort_direction': sort_direction,
    }

    return render_template("post_history/list.html", 
                           postHistory=rows, 
                           pagination=pagination_context)


@post_history_bp.route("/postHistory/add", methods=["GET", "POST"], endpoint="add_post_history")
@login_required
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