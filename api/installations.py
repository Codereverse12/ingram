from apifairy.decorators import other_responses
from flask import Blueprint, abort
from apifairy import authenticate, body, response
import sqlalchemy as sa

from api import db
from api.models import Installation, Equipment, Hospital, User, Permission, EquipmentInstallation
from api.schemas import InstallationSchema, UpdateInstallationSchema, EmptySchema
from api.auth import token_auth
from api.decorators import permission_required, paginated_response

installations = Blueprint('installations', __name__)
installation_schema = InstallationSchema()
installations_schema = InstallationSchema(many=True)
new_installation_schema = UpdateInstallationSchema()
update_installation_schema = UpdateInstallationSchema(partial=True)


@installations.route('/installations', methods=['POST'])
@authenticate(token_auth)
@permission_required(Permission.INSTALLATION)
@body(new_installation_schema)
@response(installation_schema, 201)
@other_responses({400: 'Invalid reference (equipment, hospital, or user not found)'})
def new(args):
    """Create a new installation"""
    if 'hospital_id' not in args:
        abort(400, 'hospital_id is required.')
    installation = Installation(install_date=args['install_date'])
    installation.update_installation(args)
    db.session.add(installation)
    db.session.commit()
    return installation

@installations.route('/installations/<uuid:id>', methods=['GET'])
@authenticate(token_auth)
@permission_required(Permission.INSTALLATION)
@response(installation_schema)
@other_responses({404: 'Installation not found'})
def get(id):
    """Retrieve an installation by id"""
    return db.session.get(Installation, id) or abort(404)


@installations.route('/installations', methods=['GET'])
@authenticate(token_auth)
@permission_required(Permission.INSTALLATION)
@paginated_response(installations_schema)
def all():
    """Retrieve all installations"""
    return sa.select(Installation)

@installations.route('/equipments/<uuid:id>/installations', methods=['GET'])
@authenticate(token_auth)
@permission_required(Permission.INSTALLATION)
@paginated_response(installations_schema)
def get_installations_by_equipment(id):
    """Retrieve all installations for an equipment"""
    db.session.get(Equipment, id) or abort(404)
    return (
        sa.select(Installation)
        .join(EquipmentInstallation, EquipmentInstallation.installation_id == Installation.id)
        .where(EquipmentInstallation.equipment_id == id)
    )

@installations.route('/hospitals/<uuid:id>/installations', methods=['GET'])
@authenticate(token_auth)
@permission_required(Permission.INSTALLATION)
@paginated_response(installations_schema)
def get_installations_by_hospital(id):
    """Retrieve all installations for a hospital"""
    hospital = db.session.get(Hospital, id) or abort(404)
    return hospital.installations.select()

@installations.route('/users/<uuid:id>/installations', methods=['GET'])
@authenticate(token_auth)
@permission_required(Permission.INSTALLATION)
@paginated_response(installations_schema)
def get_installations_by_user(id):
    """Retrieve all installations for a user"""
    user = db.session.get(User, id) or abort(404)
    return user.installations.select()

@installations.route('/installations/<uuid:id>', methods=['PUT'])
@authenticate(token_auth)
@permission_required(Permission.INSTALLATION)
@body(update_installation_schema)
@response(installation_schema)
@other_responses({400: 'Invalid reference (equipment, hospital, or user not found)',
                  403: 'Not allowed to edit this installation',
                  404: 'Installation not found'})
def put(data, id):
    """Edit an installation"""
    installation = db.session.get(Installation, id) or abort(404)
    installation.update_installation(data)
    db.session.commit()
    return installation


@installations.route('/installations/<uuid:id>', methods=['DELETE'])
@authenticate(token_auth)
@permission_required(Permission.INSTALLATION)
@other_responses({403: 'Not allowed to delete this installation',
                  404: 'Installation not found'})
def delete(id):
    """Delete an installation"""
    installation = db.session.get(Installation, id) or abort(404)
    db.session.delete(installation)
    db.session.commit()
    return '', 204
