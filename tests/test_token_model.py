import unittest
from datetime import timedelta
from flask import current_app
import sqlalchemy as sa
from api import create_app, db
from api.dates import naive_utcnow
from api.models import Token, User, Role

class TokenModelTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        Role.insert_roles()
    
    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_token_clean(self):
        role = db.session.scalar(
            db.select(Role).where(Role.name == 'Technician')
        )
        user = User(email='test@test.com', role=role)
        db.session.add(user)
        db.session.commit()

        token1 = Token(
            access_token='access1', refresh_token='refresh1',
            access_expiration=naive_utcnow() + timedelta(days=1),
            refresh_expiration=naive_utcnow() + timedelta(days=1),
            user=user
        )

        token2 = Token(
            access_token='access2', refresh_token='refresh2',
            access_expiration=naive_utcnow() - timedelta(days=1),
            refresh_expiration=naive_utcnow() - timedelta(days=1),
            user=user
        )

        db.session.add_all([token1, token2])
        db.session.commit()

        Token.clean()
        db.session.commit()

        tokens = db.session.scalars(
            sa.select(Token)
        ).all()
        
        assert len(tokens) == 1
        assert tokens[0].access_token == 'access1'