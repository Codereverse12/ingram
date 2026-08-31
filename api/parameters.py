from apifairy.decorators import other_responses
from flask import Blueprint, abort
from apifairy import authenticate, body, response
import sqlalchemy as sa

from api import db
from api.models import Parameter, Permission
from api.schemas import ParameterSchema
from api.auth import token_auth
from api.decorators import permission_required, paginated_response

parameters = Blueprint('parameters', __name__)
parameter_schema = ParameterSchema()
parameters_schema = ParameterSchema(many=True)
update_parameter_schema = ParameterSchema(partial=True)


@parameters.route('/parameters', methods=['POST'])
@authenticate(token_auth)
@permission_required(Permission.EQUIPMENT)
@body(parameter_schema)
@response(parameter_schema, 201)
def new(args):
    """Create a new equipment parameter"""
    parameter = Parameter(**args)
    db.session.add(parameter)
    db.session.commit()
    return parameter


@parameters.route('/parameters', methods=['GET'])
@authenticate(token_auth)
@permission_required(Permission.EQUIPMENT)
@paginated_response(parameters_schema)
def all():
    """Retrieve all equipment parameters"""
    return sa.select(Parameter)


@parameters.route('/parameters/<int:id>', methods=['GET'])
@authenticate(token_auth)
@permission_required(Permission.EQUIPMENT)
@response(parameter_schema)
@other_responses({404: 'Parameter not found'})
def get(id):
    """Retrieve an equipment parameter by id"""
    return db.session.get(Parameter, id) or abort(404)


@parameters.route('/parameters/<int:id>', methods=['PUT'])
@authenticate(token_auth)
@permission_required(Permission.EQUIPMENT)
@body(update_parameter_schema)
@response(parameter_schema)
@other_responses({404: 'Parameter not found'})
def put(data, id):
    """Edit an equipment parameter"""
    parameter = db.session.get(Parameter, id) or abort(404)
    parameter.update(data)
    db.session.commit()
    return parameter


@parameters.route('/parameters/<int:id>', methods=['DELETE'])
@authenticate(token_auth)
@permission_required(Permission.EQUIPMENT)
@other_responses({404: 'Parameter not found'})
def delete(id):
    """Delete an equipment parameter"""
    parameter = db.session.get(Parameter, id) or abort(404)
    db.session.delete(parameter)
    db.session.commit()
    return '', 204
