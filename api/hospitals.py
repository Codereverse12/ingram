from apifairy.decorators import other_responses
from flask import Blueprint, abort
from apifairy import authenticate, body, response
import sqlalchemy as sa

from api import db
from api.models import Hospital, HospitalContact, Permission
from api.schemas import HospitalSchema, HospitalContactSchema, EmptySchema
from api.auth import token_auth
from api.decorators import permission_required, paginated_response

hospitals = Blueprint('hospitals', __name__)
hospital_schema = HospitalSchema()
hospitals_schema = HospitalSchema(many=True)
update_hospital_schema = HospitalSchema(partial=True)
contact_schema = HospitalContactSchema()
contacts_schema = HospitalContactSchema(many=True)
update_contact_schema = HospitalContactSchema(partial=True)


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


@hospitals.route('/hospitals/<uuid:id>/contacts', methods=['GET'])
@authenticate(token_auth)
@permission_required(Permission.HOSPITAL)
@response(contacts_schema)
@other_responses({404: 'Hospital not found'})
def get_contacts(id):
    """Retrieve all contacts of a hospital"""
    hospital = db.session.get(Hospital, id) or abort(404)
    return hospital.contacts


@hospitals.route('/hospitals/<uuid:id>/contacts', methods=['POST'])
@authenticate(token_auth)
@permission_required(Permission.HOSPITAL)
@body(contact_schema)
@response(contact_schema, 201)
@other_responses({404: 'Hospital not found'})
def new_contact(args, id):
    """Add a contact to a hospital"""
    hospital = db.session.get(Hospital, id) or abort(404)
    contact = HospitalContact(hospital=hospital, **args)
    db.session.add(contact)
    db.session.commit()
    return contact


@hospitals.route('/contacts/<int:id>', methods=['PUT'])
@authenticate(token_auth)
@permission_required(Permission.HOSPITAL)
@body(update_contact_schema)
@response(contact_schema)
@other_responses({404: 'Contact not found'})
def put_contact(data, id):
    """Edit a hospital contact"""
    contact = db.session.get(HospitalContact, id) or abort(404)
    contact.update(data)
    db.session.commit()
    return contact


@hospitals.route('/contacts/<int:id>', methods=['DELETE'])
@authenticate(token_auth)
@permission_required(Permission.HOSPITAL)
@other_responses({404: 'Contact not found'})
def delete_contact(id):
    """Delete a hospital contact"""
    contact = db.session.get(HospitalContact, id) or abort(404)
    db.session.delete(contact)
    db.session.commit()
    return '', 204