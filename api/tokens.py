from flask import Blueprint, request, abort, current_app, url_for, session
from werkzeug.http import dump_cookie
from apifairy import authenticate, body, response, other_responses

from api import db
from api.auth import basic_auth, token_auth
from api.models import User, Token
from api.schemas import TokenSchema, EmptySchema

tokens = Blueprint('tokens', __name__)
token_schema = TokenSchema()

def token_response(token):
    headers = {}
    samesite = 'strict'
    if current_app.config['USE_CORS']:
        samesite = 'lax' if current_app.debug else 'none'
    headers['Set-Cookie'] = dump_cookie(
        'refresh_token', token.refresh_token,
        path=url_for('tokens.new'), secure=not current_app.debug,
        httponly=True, samesite=samesite)
    
    return {
        'access_token': token.access_token_jwt
    }, 200, headers

@tokens.route('/tokens', methods=['POST'])
@authenticate(basic_auth)
@response(token_schema)
@other_responses({401: 'Invalid email or password'})
def new():
    """Create new access and refresh tokens

    The refresh token is returned in a secure, HTTP-only
    cookie.
    """
    user = basic_auth.current_user()
    token = user.generate_auth_token()
    db.session.add(token)
    Token.clean()  # keep token table clean of old tokens
    db.session.commit()
    return token_response(token)


@tokens.route('/tokens', methods=['PUT'])
@body(token_schema)
@response(token_schema, description='Newly issued access and refresh tokens')
@other_responses({401: 'Invalid access or refresh token'})
def refresh(args):
    """Refresh an access token

    The client pass the refresh token in a `refresh_token` cookie. 
    The access token must be passed in the body of the request.
    """
    access_token_jwt = args['access_token']
    refresh_token = args.get('refresh_token', request.cookies.get(
        'refresh_token'))
    if not access_token_jwt or not refresh_token:
        abort(401)
    token = User.verify_refresh_token(refresh_token, access_token_jwt)
    if not token:
        abort(401)
    token.expire()
    new_token = token.user.generate_auth_token()
    db.session.add_all([token, new_token])
    db.session.commit()
    return token_response(new_token)


@tokens.route('/tokens', methods=['DELETE'])
@authenticate(token_auth)
@response(EmptySchema, status_code=204, description='Token revoked')
@other_responses({401: 'Invalid access token'})
def revoke():
    """Revoke an access token"""
    access_token_jwt = request.headers['Authorization'].split()[1]
    token = Token.from_jwt(access_token_jwt)
    if not token:  # pragma: no cover
        abort(401)
    token.expire()
    db.session.commit()
    return {}