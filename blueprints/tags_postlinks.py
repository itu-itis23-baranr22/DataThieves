from utils.auth import login_required
import MySQLdb.cursors
import math
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from wtforms import Form, StringField, validators
import time
from extensions import mysql


tags_postlinks_bp = Blueprint("tags_postlinks_bp", __name__)

# --- Form Sınıfları ---
class PostLinkInsertForm(Form):
    PostId = StringField("Post ID", [validators.DataRequired()])
    RelatedPostId = StringField("Related Post ID", [validators.DataRequired()])
    LinkTypeId = StringField("Link Type ID", [validators.DataRequired()])

class TagInsertForm(Form):
    TagName = StringField("Tag Name", [validators.DataRequired(), validators.Length(max=100)])
    Count = StringField("Count", [validators.DataRequired()])
    ExcerptPostId = StringField("Excerpt Post ID", [validators.Optional()])
    WikiPostId = StringField("Wiki Post ID", [validators.Optional()])


# --- PostLinks Rotaları ---
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
            INSERT INTO PostLinks (Id, CreationDate, PostId, RelatedPostId, LinkTypeId)
            VALUES (%s, %s, %s, %s, %s)
        """
        params = (link_id, now_str, post_id, related_post_id, link_type_id)

        try:
            cur.execute(sql, params)
            mysql.connection.commit()
            flash("PostLink added successfully.", "success")
            return redirect(url_for("tags_postlinks_bp.post_links"))
        except Exception as e:
            mysql.connection.rollback()
            flash(f"An error occurred: {e}", "danger")
        finally:
            cur.close()

    return render_template("post_links/add.html", form=form)


# --- TAGS Rotaları (Sayfalama + Arama + Taşma Çözümü) ---
@tags_postlinks_bp.route("/tags", endpoint="tags")
@login_required
def tags():
    # 1. Parametreleri Al
    tab = request.args.get('tab', 'popular')     
    search = request.args.get('search', '')      
    page = request.args.get('page', 1, type=int) 
    
    
    per_page = 12 
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    where_clause = ""
    params = []

    if search:
        where_clause = "WHERE TagName LIKE %s"
        params.append(f"%{search}%")

    if tab == 'name':
        order_sql = "ORDER BY TagName ASC"
    elif tab == 'new':
        order_sql = "ORDER BY Id DESC"
    else:
        order_sql = "ORDER BY Count DESC"

    count_sql = f"SELECT COUNT(*) as total FROM tags {where_clause}"
    cur.execute(count_sql, tuple(params))
    total_records = cur.fetchone()['total']
    
    total_pages = math.ceil(total_records / per_page)

    offset = (page - 1) * per_page
    
    data_sql = f"""
        SELECT Id, TagName, Count, ExcerptPostId, WikiPostId
        FROM tags
        {where_clause}
        {order_sql}
        LIMIT %s OFFSET %s
    """
    params.extend([per_page, offset])
    
    cur.execute(data_sql, tuple(params))
    rows = cur.fetchall()
    cur.close()

    return render_template(
        "tags/list.html", 
        tags=rows, 
        page=page, 
        total_pages=total_pages, 
        tab=tab, 
        search=search
    )


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

        sql = "INSERT INTO Tags (Id, TagName, Count, ExcerptPostId, WikiPostId) VALUES (%s, %s, %s, %s, %s)"
        params = (tag_id, tag_name, count, excerpt_id_val, wiki_id_val)

        try:
            cur.execute(sql, params)
            mysql.connection.commit()
            flash("Tag added successfully.", "success")
            return redirect(url_for("tags_postlinks_bp.tags"))
        except Exception as e:
            mysql.connection.rollback()
            flash(f"Error: {e}", "danger")
        finally:
            cur.close()

    return render_template("tags/add.html", form=form)


@tags_postlinks_bp.route("/tagged/<string:tag_name>", endpoint="tagged_posts")
def tagged_posts(tag_name):
    
    tag_name = tag_name.strip()

    page = request.args.get('page', 1, type=int)
    per_page = 50
    offset = (page - 1) * per_page
    
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    search_term = f"%{tag_name}%"

    count_sql = "SELECT COUNT(*) as total FROM Posts WHERE Tags LIKE %s"
    cur.execute(count_sql, (search_term,))
    total_records = cur.fetchone()['total']
    total_pages = math.ceil(total_records / per_page)
    
    sql = """
        SELECT 
            p.Id, p.Title, p.Body, p.ViewCount, p.AnswerCount, 
            p.Score, p.Tags, p.CreaionDate,
            u.DisplayName, u.Reputation, u.ProfileImageUrl, p.OwnerUserId
        FROM Posts p
        LEFT JOIN Users u ON p.OwnerUserId = u.Id
        WHERE p.Tags LIKE %s
        ORDER BY p.CreaionDate DESC
        LIMIT %s OFFSET %s;
    """
    
    cur.execute(sql, (search_term, per_page, offset))
    posts = cur.fetchall()
    
    user_stats = None
    if "user_id" in session:
        cur.execute("SELECT Id, DisplayName, Reputation, ProfileImageUrl FROM Users WHERE Id = %s", (session["user_id"],))
        user_stats = cur.fetchone()

    cur.close()
    
    return render_template(
        "tags/tagged.html", 
        posts=posts, 
        tag_name=tag_name, 
        user_stats=user_stats,
        page=page,
        total_pages=total_pages
    )

@tags_postlinks_bp.route("/forum/<int:post_id>", endpoint="forum_post_detail")
def forum_post_detail(post_id):
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    try:
        # 1. Post Detayı (Post tablosunda typo VAR: p.CreaionDate)
        post_query = """
            SELECT 
                p.Id, p.Title, p.Body, p.ViewCount, 
                p.CreaionDate as CreationDate,  -- Veritabanında hatalı, burada düzeltip alıyoruz
                p.Tags, p.OwnerUserId, p.Score,
                u.DisplayName AS OwnerName, u.Reputation AS OwnerReputation, u.ProfileImageUrl
            FROM Posts p
            LEFT JOIN Users u ON p.OwnerUserId = u.Id
            WHERE p.Id = %s
        """
        cur.execute(post_query, (post_id,))
        post = cur.fetchone()

        if not post:
            return render_template("error404.html"), 404

        # 2. Yorumlar (Comments tablosunda typo YOK: c.CreationDate)
        comments_query = """
            SELECT 
                c.Id, c.Text, 
                c.CreationDate, -- BURASI DÜZELTİLDİ (c.CreaionDate değil!)
                COALESCE(u.DisplayName, c.UserDisplayName) AS CommentAuthor,
                u.Reputation AS CommentReputation, c.Score, c.UserId,
                u.ProfileImageUrl
            FROM Comments c
            LEFT JOIN Users u ON c.UserId = u.Id
            WHERE c.PostId = %s
            ORDER BY c.CreationDate ASC
        """
        cur.execute(comments_query, (post_id,))
        comments = cur.fetchall()

        # 3. RELATED POSTS
        # Burada da Posts tablosuna join attığımız için typo'lu hali (CreaionDate) gerekebilir
        # Ancak sadece ID, Title ve Score alıyorsan tarihe gerek yok, alacaksan dikkat et.
        related_sql = """
            SELECT 
                P.Id, 
                P.Title, 
                P.Score, 
                P.CreaionDate -- Posts tablosundan geldiği için yine typo'lu
            FROM PostLinks PL
            INNER JOIN Posts P ON PL.RelatedPostId = P.Id
            WHERE PL.PostId = %s
            ORDER BY P.Score DESC
            LIMIT 10
        """
        cur.execute(related_sql, (post_id,))
        related_posts = cur.fetchall()
        
        # Ters yön kontrolü (Opsiyonel, yukarıdaki kodda vardı)
        if len(related_posts) == 0:
            related_sql_reverse = """
                SELECT 
                    P.Id, 
                    P.Title, 
                    P.Score, 
                    P.CreaionDate
                FROM PostLinks PL
                INNER JOIN Posts P ON PL.PostId = P.Id
                WHERE PL.RelatedPostId = %s
                ORDER BY P.Score DESC
                LIMIT 10
            """
            cur.execute(related_sql_reverse, (post_id,))
            related_posts = cur.fetchall()

        return render_template("comments/post_comments.html", 
                             post=post, 
                             comments=comments, 
                             related_posts=related_posts)

    except Exception as e:
        print(f"HATA: {e}")
        # Hata detayını ekrana basmak debug için iyidir, production'da kaldırılır.
        return f"Veritabanı hatası oluştu: {e}", 500
        
    finally:
        cur.close()



@tags_postlinks_bp.route("/tags/delete/<int:tag_id>", methods=["POST"], endpoint="delete_tag")
@login_required
def delete_tag(tag_id):
   
    cur = mysql.connection.cursor()
    try:
        cur.execute("DELETE FROM Tags WHERE Id = %s", (tag_id,))
        mysql.connection.commit()
        flash("Tag is succesfully deleted", "success")
    except Exception as e:
        mysql.connection.rollback()
        flash(f"Error: {e}", "danger")
    finally:
        cur.close()

    return redirect(url_for("tags_postlinks_bp.tags"))