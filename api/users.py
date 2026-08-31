from apifairy.decorators import other_responses
from flask import Blueprint, abort
from apifairy import authenticate, body, response
import sqlalchemy as sa

from api import db
from api.models import User, Permission
from api.schemas import UserSchema, UpdateUserSchema
from api.auth import token_auth
from api.decorators import permission_required, paginated_response


users = Blueprint('users', __name__)
user_schema = UserSchema()
users_schema = UserSchema(many=True)
update_user_schema = UpdateUserSchema(partial=True)


@users.route('/users', methods=['POST'])
@authenticate(token_auth)
@permission_required(Permission.USERS)
@body(user_schema)
@response(user_schema, 201)
def new(args):
    """Register a new user"""
    user = User(**args)
    db.session.add(user)
    db.session.commit()
    return user


@users.route('/users', methods=['GET'])
@authenticate(token_auth)
@permission_required(Permission.USERS)
@paginated_response(users_schema)
def all():
    """Retrieve all users"""
    return sa.select(User)


@users.route('/users/<uuid:id>', methods=['GET'])
@authenticate(token_auth)
@permission_required(Permission.USERS)
@response(user_schema)
@other_responses({404: 'User not found'})
def get(id):
    """Retrieve a user by id"""
    return db.session.get(User, id) or abort(404)


@users.route('/users/<uuid:id>', methods=['PUT'])
@authenticate(token_auth)
@permission_required(Permission.USERS)
@body(update_user_schema)
@response(user_schema)
@other_responses({403: 'Not allowed to edit this user',
                  404: 'User not found'})
def put(data, id):
    """Edit a user"""
    user = db.session.get(User, id) or abort(404)
    user.update(data)
    db.session.commit()
    return user


@users.route('/users/<uuid:id>', methods=['DELETE'])
@authenticate(token_auth)
@permission_required(Permission.USERS)
@other_responses({403: 'Not allowed to delete this user',
                  404: 'User not found'})
def delete(id):
    """Delete a user"""
    user = db.session.get(User, id) or abort(404)
    db.session.delete(user)
    db.session.commit()
    return '', 204


@users.route('/me', methods=['GET'])
@authenticate(token_auth)
@response(user_schema)
def me():
    """Retrieve the authenticated user"""
    return token_auth.current_user()

@users.route('/me', methods=['PUT'])
@authenticate(token_auth)
@body(update_user_schema)
@response(user_schema)
def put_me(data):
    """Edit authenticated user"""
    user = token_auth.current_user()
    if 'password' in data and ('old_password' not in data or
                               not user.verify_password(data['old_password'])):
        abort(400)
    user.update(data)
    db.session.commit()
    return user