"""Health checks must detect an incomplete production database schema."""
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from app import db
from app.models import followers


def test_migrations_match_models(test_app):
    """Production migrations must create every table and column used by the app."""
    assert test_app.testing
    with db.engine.connect() as connection:
        assert compare_metadata(MigrationContext.configure(connection), db.metadata) == []


def test_health_after_migrations(client):
    """The migration-created database is ready for application queries."""
    response = client.get('/health')
    assert response.status_code == 200
    assert response.get_json() == {'status': 'healthy'}


def test_health_rejects_missing_followers(client):
    """A working HTTP server alone must not make an incomplete database healthy."""
    followers.drop(db.engine)
    response = client.get('/health')
    assert response.status_code == 503
    assert response.get_json() == {'status': 'unhealthy'}
