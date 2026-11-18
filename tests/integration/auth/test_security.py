"""Regression checks for authentication after the security dependency updates."""
import logging
import pytest
from flask import url_for
from app import db
from app.models import User


@pytest.mark.parametrize('next_page', ['https://example.org', '//example.org', 'javascript:alert(1)'])
def test_login_rejects_external_redirect(client, register_user_response, user_dict, next_page):
    """A next parameter must not redirect an authenticated user to another site."""
    assert register_user_response.status_code == 200
    response = client.post('/login', query_string={'next': next_page}, data=user_dict)
    assert response.status_code == 302
    with client.application.test_request_context():
        assert response.location == url_for('main.index')


def test_password_hash_round_trip_and_no_password_logging(test_app, caplog):
    """Modern hashes fit the schema and password verification never logs the password."""
    password = 'regression-password-do-not-log'
    user = User(username='security', email='security@example.com')
    user.set_password(password)
    assert len(user.password_hash) <= User.password_hash.type.length
    db.session.add(user)
    db.session.commit()
    db.session.expire_all()
    saved_user = User.query.filter_by(username='security').one()
    with caplog.at_level(logging.DEBUG, logger=test_app.logger.name):
        assert saved_user.check_password(password)
    assert password not in caplog.text
