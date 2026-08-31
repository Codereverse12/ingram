from apifairy.decorators import other_responses
from flask import Blueprint, abort
from apifairy import authenticate, body, response
import sqlalchemy as sa

from api import db
from api.models import Role, Permission
from api.schemas import RoleSchema
from api.auth import token_auth
from api.decorators import permission_required

roles = Blueprint('roles', __name__)
role_schema = RoleSchema()
roles_schema = RoleSchema(many=True)

@roles.route('/roles', methods=['GET'])
@authenticate(token_auth)
@permission_required(Permission.USERS)
@response(roles_schema)
@other_responses({401: 'Unauthorized', 403: 'Forbidden'})
def all():
    """Retrieve all roles"""
    return db.session.scalars(
        sa.select(Role).
        where(Role.name != "Administrator").
        order_by(Role.id)).all()