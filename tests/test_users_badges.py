# tests/test_users_badges.py
def test_users_page_non_admin_forbidden(client):
    """
    /users is protected by @admin_required in users_badges.py
    utils/auth.py -> if not logged_in or not is_admin: abort(403)
    """
    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["is_admin"] = False
        #sess["user_id"] = 1

    resp = client.get("/users")
    assert resp.status_code == 403


def test_users_page_admin_ok_and_queries_run(client, fake_mysql):
    """
    Admin can open /users.
    users_badges.py runs:
      - COUNT(*) query (fetchone -> {"cnt": ...})
      - data query (fetchall -> rows)
    We feed those planned results to fake cursor.
    """
    # Plan DB outputs for /users route:
    cur = fake_mysql.cursor_obj
    cur.plan_fetchone({"cnt": 0}, None)  # 1) COUNT sonucu 2) navbar fetchone için
    cur.plan_fetchall([])               # data rows


    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["is_admin"] = True
        #sess["user_id"] = 1

    resp = client.get("/users")
    assert resp.status_code == 200

    # Verify at least 2 SQL executions happened (count + data)
    assert len(cur.executed) >= 2
    # Simple sanity: first query should be a COUNT
    first_sql, _ = cur.executed[0]
    assert "COUNT" in first_sql.upper()


def test_add_profile_badge_requires_login(client):
    """
    /profile/badges/add is protected by @login_required (utils/auth.py).
    If not logged_in: redirects to posts_bp.login.
    We don't hardcode the login URL; just check redirect.
    """
    resp = client.get("/profile/badges/add", follow_redirects=False)
    assert resp.status_code in (302, 303)


def test_add_profile_badge_duplicate_shows_warning_and_redirects(client, fake_mysql):
    """
    When adding a badge:
      - checks existing: SELECT 1 FROM badges WHERE UserId=%s AND Name=%s LIMIT 1
      - if exists -> flashes warning and redirects to profile
    We simulate "exists" by returning a row for fetchone().
    """
    cur = fake_mysql.cursor_obj
    # In add_profile_badge(), first fetchone() is for "exists"
    cur.plan_fetchone({"1": 1})

    with client.session_transaction() as sess:
        sess["logged_in"] = True
        #sess["user_id"] = 5  # needed by add_profile_badge()

    # Submit the form. Your AddProfileBadgeForm uses fields: preset/custom.
    resp = client.post(
        "/profile/badges/add",
        data={"preset": "Student", "custom": ""},
        follow_redirects=False,
    )
    assert resp.status_code in (302, 303)

    # Confirm that the duplicate-check SQL was executed
    executed_sqls = [sql.upper() for (sql, _params) in cur.executed]
    assert any("FROM BADGES" in s and "SELECT 1" in s for s in executed_sqls)
