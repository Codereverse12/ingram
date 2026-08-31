from apifairy.decorators import other_responses
from flask import Blueprint, abort
from apifairy import authenticate, body, response
import sqlalchemy as sa

from api import db
from api.models import Service, ServicePart, Part, Equipment, Hospital, User, Permission
from api.schemas import ServiceSchema, UpdateServiceSchema, PartSchema, \
    ServicePartSchema, EmptySchema
from api.auth import token_auth
from api.decorators import permission_required, paginated_response

services = Blueprint('services', __name__)

service_schema = ServiceSchema()
services_schema = ServiceSchema(many=True)
update_service_schema = UpdateServiceSchema(partial=True)
part_schema = PartSchema()
parts_schema = PartSchema(many=True)
service_part_schema = ServicePartSchema()


# ── Service CRUD ──────────────────────────────────────────────────────────


@services.route('/services', methods=['POST'])
@authenticate(token_auth)
@permission_required(Permission.INSTALLATION)
@body(service_schema)
@response(service_schema, 201)
def new(args):
    """Create a new service record"""
    if db.session.get(Equipment, args['equipment_id']) is None:
        abort(400, 'Equipment not found or has been deleted.')
    if 'hospital_id' in args and \
            db.session.get(Hospital, args['hospital_id']) is None:
        abort(400, 'Hospital not found or has been deleted.')
    service = Service(**args)
    db.session.add(service)
    db.session.commit()
    return service


@services.route('/services/<uuid:id>', methods=['GET'])
@authenticate(token_auth)
@permission_required(Permission.INSTALLATION)
@response(service_schema)
@other_responses({404: 'Service not found'})
def get(id):
    """Retrieve a service record by id"""
    return db.session.get(Service, id) or abort(404)


@services.route('/services', methods=['GET'])
@authenticate(token_auth)
@permission_required(Permission.INSTALLATION)
@paginated_response(services_schema)
def all():
    """Retrieve all service records"""
    return sa.select(Service)


@services.route('/services/<uuid:id>', methods=['PUT'])
@authenticate(token_auth)
@permission_required(Permission.INSTALLATION)
@body(update_service_schema)
@response(service_schema)
@other_responses({400: 'Invalid reference (equipment, hospital, or user not found)',
                  403: 'Not allowed to edit this service',
                  404: 'Service not found'})
def put(data, id):
    """Edit a service record"""
    service = db.session.get(Service, id) or abort(404)
    _update_service(service, data)
    db.session.commit()
    return service


@services.route('/services/<uuid:id>', methods=['DELETE'])
@authenticate(token_auth)
@permission_required(Permission.INSTALLATION)
@other_responses({403: 'Not allowed to delete this service',
                  404: 'Service not found'})
def delete(id):
    """Delete a service record"""
    service = db.session.get(Service, id) or abort(404)
    db.session.delete(service)
    db.session.commit()
    return '', 204


# ── Sub-resource: services by equipment / hospital / user ─────────────────


@services.route('/equipments/<uuid:id>/services', methods=['GET'])
@authenticate(token_auth)
@permission_required(Permission.INSTALLATION)
@paginated_response(services_schema)
def get_services_by_equipment(id):
    """Retrieve all services for an equipment"""
    db.session.get(Equipment, id) or abort(404)
    return sa.select(Service).where(Service.equipment_id == id)


@services.route('/hospitals/<uuid:id>/services', methods=['GET'])
@authenticate(token_auth)
@permission_required(Permission.INSTALLATION)
@paginated_response(services_schema)
def get_services_by_hospital(id):
    """Retrieve all services for a hospital"""
    db.session.get(Hospital, id) or abort(404)
    return sa.select(Service).where(Service.hospital_id == id)


@services.route('/users/<uuid:id>/services', methods=['GET'])
@authenticate(token_auth)
@permission_required(Permission.INSTALLATION)
@paginated_response(services_schema)
def get_services_by_user(id):
    """Retrieve all services assigned to a user"""
    user = db.session.get(User, id) or abort(404)
    return user.services.select()


# ── Service parts management ──────────────────────────────────────────────


@services.route('/services/<uuid:id>/parts', methods=['GET'])
@authenticate(token_auth)
@permission_required(Permission.INSTALLATION)
@response(parts_schema)
@other_responses({404: 'Service not found'})
def get_parts(id):
    """Retrieve all parts used in a service"""
    service = db.session.get(Service, id) or abort(404)
    parts = [sp.part for sp in service.service_parts]
    return parts


@services.route('/services/<uuid:service_id>/parts', methods=['POST'])
@authenticate(token_auth)
@permission_required(Permission.INSTALLATION)
@body(service_part_schema)
@response(service_schema)
@other_responses({400: 'Part not found',
                  404: 'Service not found'})
def add_part(args, service_id):
    """Add a part to a service record

    The request body must include `part_id` and optionally `quantity`.
    """
    service = db.session.get(Service, service_id) or abort(404)
    part_id = args['part_id']
    part = db.session.get(Part, part_id)
    if part is None:
        abort(400, 'Part not found.')

    # check for duplicate
    existing = db.session.scalar(
        sa.select(ServicePart).where(
            ServicePart.service_id == service.id,
            ServicePart.part_id == part_id
        )
    )
    if existing:
        existing.quantity = args.get('quantity', existing.quantity)
    else:
        sp = ServicePart(
            service_id=service.id,
            part_id=part_id,
            quantity=args.get('quantity')
        )
        db.session.add(sp)

    db.session.commit()
    return service


@services.route('/services/<uuid:service_id>/parts/<int:part_id>', methods=['DELETE'])
@authenticate(token_auth)
@permission_required(Permission.INSTALLATION)
@other_responses({404: 'Service or part not found'})
def remove_part(service_id, part_id):
    """Remove a part from a service record"""
    service = db.session.get(Service, service_id) or abort(404)
    sp = db.session.scalar(
        sa.select(ServicePart).where(
            ServicePart.service_id == service.id,
            ServicePart.part_id == part_id
        )
    )
    if sp is None:
        abort(404, 'Part not linked to this service.')
    db.session.delete(sp)
    db.session.commit()
    return '', 204


# ── Parts CRUD ────────────────────────────────────────────────────────────


@services.route('/parts', methods=['POST'])
@authenticate(token_auth)
@permission_required(Permission.INSTALLATION)
@body(part_schema)
@response(part_schema, 201)
def new_part(args):
    """Create a new part"""
    part = Part(**args)
    db.session.add(part)
    db.session.commit()
    return part


@services.route('/parts', methods=['GET'])
@authenticate(token_auth)
@permission_required(Permission.INSTALLATION)
@paginated_response(parts_schema)
def all_parts():
    """Retrieve all parts"""
    return sa.select(Part)


@services.route('/parts/<int:id>', methods=['GET'])
@authenticate(token_auth)
@permission_required(Permission.INSTALLATION)
@response(part_schema)
@other_responses({404: 'Part not found'})
def get_part(id):
    """Retrieve a part by id"""
    return db.session.get(Part, id) or abort(404)


@services.route('/parts/<int:id>', methods=['PUT'])
@authenticate(token_auth)
@permission_required(Permission.INSTALLATION)
@body(PartSchema(partial=True))
@response(part_schema)
@other_responses({404: 'Part not found'})
def put_part(data, id):
    """Edit a part"""
    part = db.session.get(Part, id) or abort(404)
    part.update(data)
    db.session.commit()
    return part


@services.route('/parts/<int:id>', methods=['DELETE'])
@authenticate(token_auth)
@permission_required(Permission.INSTALLATION)
@other_responses({404: 'Part not found'})
def delete_part(id):
    """Delete a part"""
    part = db.session.get(Part, id) or abort(404)
    db.session.delete(part)
    db.session.commit()
    return '', 204


# ── Internal helpers ──────────────────────────────────────────────────────


def _update_service(service: Service, data: dict):
    """Apply update data to a service, validating all FK references."""
    if 'equipment_id' in data:
        equipment = db.session.get(Equipment, data['equipment_id'])
        if equipment is None:
            abort(400, 'Equipment not found or has been deleted.')
        service.equipment = equipment

    if 'hospital_id' in data:
        hospital = db.session.get(Hospital, data['hospital_id'])
        if hospital is None:
            abort(400, 'Hospital not found or has been deleted.')
        service.hospital = hospital

    if 'user_ids' in data:
        user_ids = data['user_ids']
        users = db.session.scalars(
            sa.select(User).where(User.id.in_(user_ids))
        ).all()
        if len(users) != len(user_ids):
            abort(400, 'One or more user IDs are invalid or no longer exist.')
        service.users = users

    service.update(data, ignore=['equipment_id', 'hospital_id', 'user_ids'])
