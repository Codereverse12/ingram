from apifairy.decorators import other_responses
from flask import Blueprint, abort
from apifairy import authenticate, body, response
import sqlalchemy as sa

from api import db
from api.models import Hospital, Permission
from api.schemas import HospitalSchema, EmptySchema
from api.auth import token_auth
from api.decorators import permission_required, paginated_response

hospitals = Blueprint('hospitals', __name__)
hospital_schema = HospitalSchema()
hospitals_schema = HospitalSchema(many=True)
update_hospital_schema = HospitalSchema(partial=True)


@hospitals.route('/hospitals', methods=['POST'])
@authenticate(token_auth)
@permission_required(Permission.HOSPITAL)
@body(hospital_schema)
@response(hospital_schema, 201)
def new(args):
    """Create a new hospital"""
    hospital = Hospital(**args)
    db.session.add(hospital)
    db.session.commit()
    return hospital

@hospitals.route('/hospitals/<uuid:id>', methods=['GET'])
@authenticate(token_auth)
@permission_required(Permission.HOSPITAL)
@response(hospital_schema)
@other_responses({404: 'Hospital not found'})
def get(id):
    """Retrieve an hospital by id"""
    return db.session.get(Hospital, id) or abort(404)

@hospitals.route('/hospitals', methods=['GET'])
@authenticate(token_auth)
@permission_required(Permission.HOSPITAL)
@paginated_response(hospitals_schema)
def all():
    """Retrieve all hospitals"""
    return sa.select(Hospital)


@hospitals.route('/hospitals/<uuid:id>', methods=['PUT'])
@authenticate(token_auth)
@permission_required(Permission.HOSPITAL)
@body(update_hospital_schema)
@response(hospital_schema)
@other_responses({403: 'Not allowed to edit this hospital',
                  404: 'Hospital not found'})
def put(data, id):
    """Edit an hospital"""
    hospital = db.session.get(Hospital, id) or abort(404)
    hospital.update(data)
    db.session.commit()
    return hospital


@hospitals.route('/hospitals/<uuid:id>', methods=['DELETE'])
@authenticate(token_auth)
@permission_required(Permission.HOSPITAL)
@other_responses({403: 'Not allowed to delete this hospital',
                  404: 'Hospital not found'})
def delete(id):
    """Delete an hospital"""
    hospital = db.session.get(Hospital, id) or abort(404)
    db.session.delete(hospital)
    db.session.commit()
    return '', 204