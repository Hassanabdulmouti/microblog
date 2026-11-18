"""
Fixtures for tests
"""
# pylint: disable=redefined-outer-name
import pytest
from flask_migrate import upgrade
from app import create_app, db
from app.config import TestConfig

@pytest.fixture(scope='function')
def test_app(tmp_path):
    """
    Create Flask app fixture
    """
    class MigrationTestConfig(TestConfig):
        """Use an isolated database shared with the migration connection."""
        SQLALCHEMY_DATABASE_URI = f'sqlite:///{tmp_path / "test.db"}'

    app = create_app(MigrationTestConfig)
    app_context = app.app_context()
    app_context.push()
    upgrade()

    yield app

    db.session.remove()
    db.drop_all()
    app_context.pop()


@pytest.fixture(scope="function")
def client(test_app):
    """
    Create client for app
    """
    return test_app.test_client()
