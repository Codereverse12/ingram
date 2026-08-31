from marshmallow import validate, validates, ValidationError, \
    post_dump, validates_schema
import sqlalchemy as sa
from api import ma, db
from api.models import (User, UserPhoneNumber, Role, Equipment, EquipmentParameter,
                        Parameter, Category, Hospital, HospitalContact, Installation,
                        EquipmentInstallation, Service, ServicePart, Part)

paginated_schema_cache = {}

class PagePaginationSchema(ma.Schema):
    class Meta:
        ordered = True
    
    page = ma.Integer()
    per_page = ma.Integer()
    prev_url = ma.String(dump_only=True)
    next_url = ma.String(dump_only=True)
    count = ma.Integer(dump_only=True)
    total = ma.Integer(dump_only=True)

def PaginatedCollection(schema):
    if schema in paginated_schema_cache:
        return paginated_schema_cache[schema]
    
    class PaginatedSchema(ma.Schema):
        class Meta:
            ordered = True

        pagination = ma.Nested(PagePaginationSchema)
        data = ma.Nested(schema)

    PaginatedSchema.__name__ = 'Paginated{}'.format(schema.__class__.__name__)
    paginated_schema_cache[schema] = PaginatedSchema
    return PaginatedSchema
        
class EmptySchema(ma.Schema):
    pass

class TokenSchema(ma.Schema):
    class Meta:
        ordered = True

    access_token = ma.String(required=True)

class RoleSchema(ma.SQLAlchemySchema):
    class Meta:
        model = Role
        ordered = True

    id = ma.auto_field(dump_only=True)
    name = ma.auto_field(dump_only=True)

class UserPhoneNumberSchema(ma.SQLAlchemySchema):
    class Meta:
        model = UserPhoneNumber
        ordered = True

    id = ma.auto_field(dump_only=True)
    phone_number = ma.auto_field(required=True, validate=[validate.Length(max=50)])


class UserSchema(ma.SQLAlchemySchema):
    class Meta:
        model = User
        ordered = True

    id = ma.auto_field(dump_only=True)
    first_name = ma.auto_field(required=True, validate=[validate.Length(max=120)])
    last_name = ma.auto_field(validate=[validate.Length(max=120)])
    email = ma.auto_field(required=True, validate=[validate.Length(max=120),
                                                   validate.Email()])
    password = ma.String(required=True, load_only=True,
                         validate=validate.Length(min=8))
    has_password = ma.Boolean(dump_only=True)
    date_of_hire = ma.auto_field()
    date_of_termination = ma.auto_field()
    role_id = ma.Integer(load_only=True)
    role = ma.Nested(RoleSchema, dump_only=True)
    phone_numbers = ma.List(ma.Nested(UserPhoneNumberSchema()), dump_only=True)
    phone_number_list = ma.List(ma.String(validate=validate.Length(max=50)),
                                load_only=True)

    @validates('email')
    def validate_email(self, value, **kwargs):
        if db.session.scalar(sa.select(User).where(User.email == value)):
            raise ValidationError('Use a different email.')

    @validates('role_id')
    def validate_role_id(self, value, **kwargs):
        if db.session.get(Role, value) is None:
            raise ValidationError('Role not found.')

class UpdateUserSchema(UserSchema):
    old_password = ma.String(load_only=True, validate=validate.Length(min=3))

    @validates('email')
    def validate_email(self, value, **kwargs):
        pass

    @validates('old_password')
    def validate_old_password(self, value, **kwargs):
        from api.auth import token_auth
        if not token_auth.current_user().verify_password(value):
            raise ValidationError('Password is incorrect')
            
class CategorySchema(ma.SQLAlchemySchema):
    class Meta:
        model = Category
        ordered = True

    id = ma.auto_field(dump_only=True)
    name = ma.auto_field(required=True, validate=[validate.Length(max=255)])


class ParameterSchema(ma.SQLAlchemySchema):
    class Meta:
        model = Parameter
        ordered = True

    id = ma.auto_field(dump_only=True)
    name = ma.auto_field(required=True, validate=[validate.Length(max=255)])
    unit = ma.auto_field(validate=[validate.Length(max=64)])


class EquipmentParameterSchema(ma.SQLAlchemySchema):
    class Meta:
        model = EquipmentParameter
        ordered = True

    parameter_id = ma.Integer(load_only=True, required=True)
    parameter = ma.Nested(ParameterSchema(), dump_only=True)
    value = ma.auto_field()


class EquipmentSchema(ma.SQLAlchemySchema):
    class Meta:
        model = Equipment
        ordered = True

    id = ma.auto_field(dump_only=True)
    name = ma.auto_field(required=True, validate=[validate.Length(max=255)])
    serial_number = ma.auto_field(validate=[validate.Length(max=255)])
    model = ma.auto_field(validate=[validate.Length(max=64)])
    category_id = ma.auto_field()
    ownership_type = ma.auto_field(validate=[validate.Length(max=64)])
    status = ma.auto_field(validate=[validate.Length(max=64)])
    category = ma.Nested(CategorySchema(), dump_only=True)
    equipment_parameters = ma.List(ma.Nested(EquipmentParameterSchema()), dump_only=True)

    @validates('serial_number')
    def validate_serial_number(self, value, **kwargs):
        if value and db.session.scalar(sa.select(Equipment).where(Equipment.serial_number == value)):
            raise ValidationError('Use a different serial number.')

    @validates('category_id')
    def validate_category_id(self, value, **kwargs):
        if value is not None and db.session.get(Category, value) is None:
            raise ValidationError('Category not found.')


class UpdateEquipmentSchema(EquipmentSchema):
    @validates('serial_number')
    def validate_serial_number(self, value, **kwargs):
        pass

class HospitalContactSchema(ma.SQLAlchemySchema):
    class Meta:
        model = HospitalContact
        ordered = True

    id = ma.auto_field(dump_only=True)
    name = ma.auto_field(required=True, validate=[validate.Length(max=255)])
    phone_number = ma.auto_field(validate=[validate.Length(max=50)])
    email = ma.auto_field(validate=[validate.Length(max=255), validate.Email()])


class HospitalSchema(ma.SQLAlchemySchema):
    class Meta:
        model = Hospital
        ordered = True

    id = ma.auto_field(dump_only=True)
    name = ma.auto_field(required=True, validate=[validate.Length(max=255)])
    address = ma.auto_field(validate=[validate.Length(max=500)])
    contacts = ma.List(ma.Nested(HospitalContactSchema()), dump_only=True)

class EquipmentInstallationSchema(ma.SQLAlchemySchema):
    class Meta:
        model = EquipmentInstallation
        ordered = True

    equipment = ma.Nested(EquipmentSchema(), dump_only=True)
    removed_date = ma.auto_field()
    warranty_start_date = ma.auto_field()
    warranty_end_date = ma.auto_field()


class InstallationSchema(ma.SQLAlchemySchema):
    class Meta:
        model = Installation
        ordered = True
    
    id = ma.auto_field(dump_only=True)
    install_date = ma.auto_field(required=True)
    installation_type = ma.auto_field(validate=[validate.Length(max=64)])
    note = ma.auto_field(validate=[validate.Length(max=500)])
    status = ma.auto_field(validate=[validate.Length(max=64)])
    hospital = ma.Nested(HospitalSchema(), dump_only=True)
    equipment_installations = ma.List(ma.Nested(EquipmentInstallationSchema()), dump_only=True)
    users = ma.List(ma.Nested(UserSchema()), dump_only=True)

class UpdateInstallationSchema(InstallationSchema):
    equipment_ids = ma.List(ma.UUID(), load_only=True)    
    hospital_id = ma.UUID(load_only=True)
    user_ids = ma.List(ma.UUID(), load_only=True)


# ── Parts ──────────────────────────────────────────────────────────────────

class PartSchema(ma.SQLAlchemySchema):
    class Meta:
        model = Part
        ordered = True

    id = ma.auto_field(dump_only=True)
    name = ma.auto_field(required=True, validate=[validate.Length(max=255)])


# ── Service Parts ──────────────────────────────────────────────────────────

class ServicePartSchema(ma.SQLAlchemySchema):
    class Meta:
        model = ServicePart
        ordered = True

    part = ma.Nested(PartSchema(), dump_only=True)
    part_id = ma.Integer(load_only=True, required=True)
    quantity = ma.auto_field(validate=[validate.Length(max=500)])


# ── Services ───────────────────────────────────────────────────────────────

class ServiceSchema(ma.SQLAlchemySchema):
    class Meta:
        model = Service
        ordered = True

    id = ma.auto_field(dump_only=True)
    opened_date = ma.auto_field()
    closed_date = ma.auto_field()
    status = ma.auto_field(validate=[validate.Length(max=64)])
    problem_description = ma.auto_field(validate=[validate.Length(max=1000)])
    fix_description = ma.auto_field(validate=[validate.Length(max=1000)])
    equipment_id = ma.UUID(load_only=True, required=True)
    hospital_id = ma.UUID(load_only=True)
    equipment = ma.Nested(EquipmentSchema(), dump_only=True)
    hospital = ma.Nested(HospitalSchema(), dump_only=True)
    users = ma.List(ma.Nested(UserSchema()), dump_only=True)
    service_parts = ma.List(ma.Nested(ServicePartSchema()), dump_only=True)


class UpdateServiceSchema(ServiceSchema):
    """Schema for updating a service — all fields optional, plus write-only relationship fields."""
    equipment_id = ma.UUID(load_only=True)  # override to make not-required for updates
    user_ids = ma.List(ma.UUID(), load_only=True)
