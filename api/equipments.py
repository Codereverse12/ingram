from apifairy.decorators import other_responses
from flask import Blueprint, abort
from apifairy import authenticate, body, response
import sqlalchemy as sa

from api import db
from api.models import Equipment, Permission
from api.schemas import EquipmentSchema
from api.auth import token_auth
from api.decorators import permission_required, paginated_response

equipments = Blueprint('equipments', __name__)
equipment_schema = EquipmentSchema()
equipments_schema = EquipmentSchema(many=True)
update_equipment_schema = EquipmentSchema(partial=True)


@equipments.route('/equipments', methods=['POST'])
@authenticate(token_auth)
@permission_required(Permission.EQUIPMENT)
@body(equipment_schema)
@response(equipment_schema, 201)
def new(args):
    """Create a new equipment"""
    equipment = Equipment(**args)
    db.session.add(equipment)
    db.session.commit()
    return equipment


@equipments.route('/equipments/<uuid:id>', methods=['GET'])
@authenticate(token_auth)
@permission_required(Permission.EQUIPMENT)
@response(equipment_schema)
@other_responses({404: 'Equipment not found'})
def get(id):
    """Retrieve an equipment by id"""
    return db.session.get(Equipment, id) or abort(404)


@equipments.route('/equipments', methods=['GET'])
@authenticate(token_auth)
@permission_required(Permission.EQUIPMENT)
@paginated_response(equipments_schema)
def all():
    """Retrieve all equipments"""
    return sa.select(Equipment)


@equipments.route('/equipments/<serial_number>', methods=['GET'])
@authenticate(token_auth)
@permission_required(Permission.EQUIPMENT)
@response(equipment_schema)
@other_responses({404: 'Equipment not found'})
def get_by_serial_number(serial_number):
    """Retrieve an equipment by serial number"""
    return db.session.scalar(
        sa.select(Equipment).where(Equipment.serial_number == serial_number)
    ) or \
        abort(404)


@equipments.route('/equipments/<uuid:id>', methods=['PUT'])
@authenticate(token_auth)
@permission_required(Permission.EQUIPMENT)
@body(update_equipment_schema)
@response(equipment_schema)
@other_responses({403: 'Not allowed to edit this equipment',
                  404: 'Equipment not found'})
def put(data, id):
    """Edit an equipment"""
    equipment = db.session.get(Equipment, id) or abort(404)
    equipment.update(data)
    db.session.commit()
    return equipment


@equipments.route('/equipments/<uuid:id>', methods=['DELETE'])
@authenticate(token_auth)
@permission_required(Permission.EQUIPMENT)
@other_responses({403: 'Not allowed to delete this equipment',
                  404: 'Equipment not found'})
def delete(id):
    """Delete an equipment"""
    equipment = db.session.get(Equipment, id) or abort(404)
    db.session.delete(equipment)
    db.session.commit()
    return '', 204




