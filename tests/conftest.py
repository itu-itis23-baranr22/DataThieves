# tests/conftest.py
import pytest
from tests.fakes import FakeMySQL


@pytest.fixture
def app():
    # App'i gerçek mysql ile oluştur (mysql.init_app(app) çalışsın)
    from app import create_app
    app = create_app()
    app.config["TESTING"] = True
    return app


@pytest.fixture
def fake_mysql(monkeypatch, app):
    """
    App oluşturulduktan sonra sadece blueprint modülündeki mysql referansını fake'e çevir.
    Böylece app.py içindeki mysql.init_app hiç etkilenmez.
    """
    fm = FakeMySQL()

    import blueprints.users_badges as users_badges_mod
    monkeypatch.setattr(users_badges_mod, "mysql", fm, raising=True)

    return fm


@pytest.fixture
def client(app, fake_mysql):
    return app.test_client()
