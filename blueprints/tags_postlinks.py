# blueprints/tags_postlinks.py
from flask import Blueprint, render_template, request, redirect, url_for, flash
from wtforms import Form, StringField, validators
import time
from extensions import mysql

tags_postlinks_bp = Blueprint("tags_postlinks_bp", __name__)

class PostLinkInsertForm(Form):
    PostId = StringField("Post ID", [validators.DataRequired()])
    RelatedPostId = StringField("Related Post ID", [validators.DataRequired()])
    LinkTypeId = StringField("Link Type ID", [validators.DataRequired()])


class TagInsertForm(Form):
    TagName = StringField("Tag Name", [validators.DataRequired(), validators.Length(max=100)])
    Count = StringField("Count", [validators.DataRequired()])
    ExcerptPostId = StringField("Excerpt Post ID", [validators.Optional()])
    WikiPostId = StringField("Wiki Post ID", [validators.Optional()])


@tags_postlinks_bp.route("/postLinks", endpoint="post_links")
def post_links():
    cur = mysql.connection.cursor()
    sql = """
        SELECT Id, CreationDate, PostId, RelatedPostId, LinkTypeId
        FROM postLinks
        ORDER BY Id DESC
        LIMIT 500;
    """
    cur.execute(sql)
    rows = cur.fetchall()
    cur.close()
    return render_template("post_links/list.html", postLinks=rows)


@tags_postlinks_bp.route("/postLinks/add", methods=["GET", "POST"], endpoint="add_post_link")
def add_post_link():
    form = PostLinkInsertForm(request.form)

    if request.method == "POST" and form.validate():
        post_id = int(form.PostId.data)
        related_post_id = int(form.RelatedPostId.data)
        link_type_id = int(form.LinkTypeId.data)

        now_str = time.strftime('%Y-%m-%d %H:%M:%S')

        cur = mysql.connection.cursor()
        cur.execute("SELECT IFNULL(MAX(Id), 0) + 1 AS next_id FROM PostLinks")
        row = cur.fetchone()
        link_id = row["next_id"]

        sql = """
            INSERT INTO PostLinks (
                Id, CreationDate, PostId, RelatedPostId, LinkTypeId
            )
            VALUES (%s, %s, %s, %s, %s)
        """

        params = (
            link_id,
            now_str,
            post_id,
            related_post_id,
            link_type_id
        )

        try:
            cur.execute(sql, params)
            mysql.connection.commit()
            flash("PostLink added successfully.", "success")
            return redirect(url_for("tags_postlinks_bp.post_links"))
        except Exception as e:
            mysql.connection.rollback()
            flash(f"An error occurred while adding the PostLink: {e}", "danger")
        finally:
            cur.close()

    return render_template("post_links/add.html", form=form)


@tags_postlinks_bp.route("/tags", endpoint="tags")
def tags():
    cur = mysql.connection.cursor()
    sql = """
        SELECT Id, TagName, Count, ExcerptPostId, WikiPostId
        FROM tags
        ORDER BY Id DESC
        LIMIT 500;
    """
    cur.execute(sql)
    rows = cur.fetchall()
    cur.close()
    return render_template("tags/list.html", tags=rows)


@tags_postlinks_bp.route("/tags/add", methods=["GET", "POST"], endpoint="add_tag")
def add_tag():
    form = TagInsertForm(request.form)

    if request.method == "POST" and form.validate():
        tag_name = form.TagName.data
        count = int(form.Count.data)

        excerpt_id = form.ExcerptPostId.data
        excerpt_id_val = int(excerpt_id) if excerpt_id else None

        wiki_id = form.WikiPostId.data
        wiki_id_val = int(wiki_id) if wiki_id else None

        cur = mysql.connection.cursor()
        cur.execute("SELECT IFNULL(MAX(Id), 0) + 1 AS next_id FROM Tags")
        row = cur.fetchone()
        tag_id = row["next_id"]

        sql = """
            INSERT INTO Tags (
                Id, TagName, Count, ExcerptPostId, WikiPostId
            )
            VALUES (%s, %s, %s, %s, %s)
        """

        params = (
            tag_id,
            tag_name,
            count,
            excerpt_id_val,
            wiki_id_val
        )

        try:
            cur.execute(sql, params)
            mysql.connection.commit()
            flash("Tag added successfully.", "success")
            return redirect(url_for("tags_postlinks_bp.tags"))
        except Exception as e:
            mysql.connection.rollback()
            flash(f"An error occurred while adding the tag: {e}", "danger")
        finally:
            cur.close()

    return render_template("tags/add.html", form=form)
