from datetime import datetime, timedelta
from hashlib import md5
import secrets
from time import time
from typing import List, Optional
from uuid import UUID, uuid4

from flask import abort, current_app, url_for
import jwt
import sqlalchemy as sa
import sqlalchemy.orm as so
from werkzeug.security import generate_password_hash, check_password_hash

from api import db
from api.dates import naive_utcnow

class Updateable:
    def update(self, data, ignore=None):
        if ignore is None:
            ignore = []
        for attr, value in data.items():
            if attr not in ignore:
                setattr(self, attr, value)


class Permission:
    HOSPITAL = 1
    EQUIPMENT = 2
    INSTALLATION = 4
    USERS = 8
    ADMIN = 16

class EquipmentInstallation(Updateable, db.Model):
    __tablename__ = 'equipments_installations'

    equipment_id: so.Mapped[UUID] = so.mapped_column(
        sa.ForeignKey('equipments.id'), primary_key=True
    )
    installation_id: so.Mapped[UUID] = so.mapped_column(
        sa.ForeignKey('installations.id'), primary_key=True
    )
    removed_date: so.Mapped[Optional[datetime]]
    warranty_start_date: so.Mapped[Optional[datetime]]
    warranty_end_date: so.Mapped[Optional[datetime]]

    equipment: so.Mapped['Equipment'] = so.relationship(
        back_populates='equipment_installations'
    )
    installation: so.Mapped['Installation'] = so.relationship(
        back_populates='equipment_installations'
    )

UserInstallation = sa.Table(
    'users_installations',
    db.metadata,
    sa.Column('user_id', sa.ForeignKey('users.id'), primary_key=True),
    sa.Column('installation_id', sa.ForeignKey('installations.id'), primary_key=True)
)

UserService = sa.Table(
    'users_services',
    db.metadata,
    sa.Column('user_id', sa.ForeignKey('users.id'), primary_key=True),
    sa.Column('service_id', sa.ForeignKey('services.id'), primary_key=True)
)

class Role(db.Model):
    __tablename__ = 'roles'

    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    name: so.Mapped[str] = so.mapped_column(sa.String(64), unique=True)
    permissions: so.Mapped[int]
    
    users: so.WriteOnlyMapped['User'] = so.relationship(
        back_populates='role'
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.permissions is None:
            self.permissions = 0 

    def add_permission(self, perm):
        if not self.has_permission(perm):
            self.permissions += perm
    
    def remove_permission(self, perm):
        if self.has_permission(perm):
            self.permissions -= perm
    
    def reset_permissions(self):
        self.permissions = 0
    
    def has_permission(self, perm):
        return self.permissions & perm == perm

    @staticmethod
    def insert_roles():
        roles = {
            'Technician': [
                Permission.HOSPITAL,
                Permission.EQUIPMENT,
                Permission.INSTALLATION,
            ],
            'Manager': [
                Permission.HOSPITAL,
                Permission.EQUIPMENT,
                Permission.INSTALLATION,
                Permission.USERS,
            ],
            'Administrator': [
                Permission.HOSPITAL,
                Permission.EQUIPMENT,
                Permission.INSTALLATION,
                Permission.USERS,
                Permission.ADMIN,
            ],
        }
        for r in roles:
            role = db.session.scalar(
                sa.select(Role).where(Role.name == r)
            )
            if role is None:
                role = Role(name=r)
            role.reset_permissions()
            for perm in roles[r]:
                role.add_permission(perm)
            db.session.add(role)
        
        db.session.commit()

    def __repr__(self):
        return f'<Role {self.name}>'

class Token(db.Model):
    __tablename__ = 'tokens'

    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    access_token: so.Mapped[str] = so.mapped_column(sa.String(64), index=True)
    access_expiration: so.Mapped[datetime]
    refresh_token: so.Mapped[str] = so.mapped_column(sa.String(64), index=True)
    refresh_expiration: so.Mapped[datetime]
    user_id: so.Mapped[UUID] = so.mapped_column(
        sa.ForeignKey('users.id', ondelete="CASCADE"), index=True)

    user: so.Mapped['User'] = so.relationship(back_populates='tokens')

    @property
    def access_token_jwt(self):
        return jwt.encode({'token': self.access_token},
                          current_app.config['SECRET_KEY'],
                          algorithm='HS256')

    def generate(self):
        self.access_token = secrets.token_urlsafe()
        self.access_expiration = naive_utcnow() + \
            timedelta(minutes=current_app.config['ACCESS_TOKEN_MINUTES'])
        self.refresh_token = secrets.token_urlsafe()
        self.refresh_expiration = naive_utcnow() + \
            timedelta(days=current_app.config['REFRESH_TOKEN_DAYS'])

    def expire(self, delay=None):
        if delay is None:  # pragma: no branch
            # 5 second delay to allow simultaneous requests
            delay = 5 if not current_app.testing else 0
        self.access_expiration = naive_utcnow() + timedelta(seconds=delay)
        self.refresh_expiration = naive_utcnow() + timedelta(seconds=delay)

    @staticmethod
    def clean():
        """Remove any tokens that have been expired for more than a day."""
        yesterday = naive_utcnow() - timedelta(days=1)
        db.session.execute(
            sa.delete(Token).where(
                Token.refresh_expiration < yesterday
            )
        )

    @staticmethod
    def from_jwt(access_token_jwt):
        access_token = None
        try:
            access_token = jwt.decode(access_token_jwt,
                                      current_app.config['SECRET_KEY'],
                                      algorithms=['HS256'])['token']
            return db.session.scalar(sa.select(Token).where(
                Token.access_token == access_token))
        except jwt.PyJWTError:
            pass

    def __repr__(self):
        return f'<Token {self.access_token}>'

class User(Updateable, db.Model):
    __tablename__ = 'users'

    id: so.Mapped[UUID] = so.mapped_column(default=uuid4, primary_key=True)
    first_name: so.Mapped[Optional[str]] = so.mapped_column(sa.String(120))
    last_name: so.Mapped[Optional[str]] = so.mapped_column(sa.String(120))
    email: so.Mapped[str] = so.mapped_column(sa.String(120), unique=True, index=True)
    password_hash: so.Mapped[Optional[str]] = so.mapped_column(sa.String(256))
    date_of_hire: so.Mapped[Optional[datetime]]
    date_of_termination: so.Mapped[Optional[datetime]]
    role_id: so.Mapped[int] = so.mapped_column(
        sa.ForeignKey('roles.id'), index=True
    )

    role: so.Mapped['Role'] = so.relationship(
        back_populates='users'
    )
    tokens: so.WriteOnlyMapped['Token'] = so.relationship(
        back_populates='user',
        cascade="all, delete-orphan",
        passive_deletes=True
    )
    phone_numbers: so.Mapped[list['UserPhoneNumber']] = so.relationship(
        back_populates='user',
        cascade="all, delete-orphan"
    )
    installations: so.WriteOnlyMapped['Installation'] = so.relationship(
        secondary=UserInstallation,
        back_populates='users'
    )
    services: so.WriteOnlyMapped['Service'] = so.relationship(
        secondary=UserService,
        back_populates='users'
    )

    @property
    def url(self):
        return url_for('users.get', id=self.id)

    @property
    def has_password(self):
        return self.password_hash is not None

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')
    
    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        if self.password_hash:
            return check_password_hash(self.password_hash, password)

    def can(self, perm):
        return self.role is not None and self.role.has_permission(perm)
    
    def is_administrator(self):
        return self.can(Permission.ADMIN)

    def generate_auth_token(self):
        token = Token(user=self)
        token.generate()
        return token
    
    @staticmethod
    def verify_access_token(access_token_jwt, refresh_token=None):
        token = Token.from_jwt(access_token_jwt)
        if token and token.access_expiration > naive_utcnow():
                return token.user
    
    @staticmethod
    def verify_refresh_token(refresh_token, access_token_jwt):
        token = Token.from_jwt(access_token_jwt)
        if token and token.refresh_token == refresh_token:
            if token.refresh_expiration > naive_utcnow():
                return token

            # someone tried to refresh with an expired token
            # revoke all tokens from this user as a precaution
            token.user.revoke_all()
            db.session.commit()

    def revoke_all(self):
        db.session.execute(
            sa.delete(Token).where(Token.user == self)
        )
    def __repr__(self):
        return f'<User {self.email}>'

class UserPhoneNumber(db.Model):
    __tablename__ = 'user_phone_numbers'

    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    phone_number: so.Mapped[str] = so.mapped_column(sa.String(50))
    user_id: so.Mapped[UUID] = so.mapped_column(
        sa.ForeignKey('users.id'), index=True
    )

    user: so.Mapped['User'] = so.relationship(
        back_populates='phone_numbers'
    )

    def __repr__(self):
        return f'<UserPhoneNumber {self.phone_number}>'

class Equipment(Updateable, db.Model):
    __tablename__ = 'equipments'

    id: so.Mapped[UUID] = so.mapped_column(default=uuid4, primary_key=True)
    name: so.Mapped[str] = so.mapped_column(sa.String(255), index=True)
    serial_number: so.Mapped[Optional[str]] = so.mapped_column(sa.String(255), unique=True, index=True)
    model: so.Mapped[Optional[str]] = so.mapped_column(sa.String(64))
    category_id: so.Mapped[Optional[int]] = so.mapped_column(
        sa.ForeignKey('categories.id'), index=True
    )
    ownership_type: so.Mapped[Optional[str]] = so.mapped_column(sa.String(64))
    status: so.Mapped[Optional[str]] = so.mapped_column(sa.String(64))

    category: so.Mapped['Category'] = so.relationship(
        back_populates='equipments'
    )

    equipment_installations: so.Mapped[list['EquipmentInstallation']] = so.relationship(
        back_populates='equipment'
    )

    equipment_parameters: so.Mapped[list['EquipmentParameter']] = so.relationship(
        back_populates='equipment'
    )

    services: so.WriteOnlyMapped['Service'] = so.relationship(
        back_populates='equipment'
    )

    def __repr__(self):
        return f'<Equipment {self.name}>'

class Category(Updateable, db.Model):
    __tablename__ = 'categories'   

    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    name: so.Mapped[str] = so.mapped_column(sa.String(255), index=True)

    equipments: so.WriteOnlyMapped['Equipment'] = so.relationship(
        back_populates='category'
    )

    @staticmethod
    def insert_categories():
        for name in [
            'Diagnostic Equipment',
            'Laboratory and Analytical Equipment',
            'Therapeutic Equipment',
            'Monitoring Equipment',
            'Surgical Equipment',
            'Emergency and Trauma Equipment',
            'Orthopedic Equipment',
            'Specialized Equipment',
            'Sterilization and Disinfection',
            'Consumables'
        ]:
            db.session.add(Category(name=name))
        db.session.commit()

    def __repr__(self):
        return f'<Category {self.name}>'

class Parameter(Updateable, db.Model):
    __tablename__ = 'parameters'

    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    name: so.Mapped[str] = so.mapped_column(sa.String(255), unique=True, index=True)
    unit: so.Mapped[Optional[str]] = so.mapped_column(sa.String(64))

    equipment_parameters: so.WriteOnlyMapped['EquipmentParameter'] = so.relationship(
        back_populates='parameter'
    )

    def __repr__(self):
        return f'<Parameter {self.name}>'

class EquipmentParameter(Updateable, db.Model):
    __tablename__ = 'equipments_parameters'

    equipment_id: so.Mapped[UUID] = so.mapped_column(
        sa.ForeignKey('equipments.id'), primary_key=True
    )
    parameter_id: so.Mapped[int] = so.mapped_column(
        sa.ForeignKey('parameters.id'), primary_key=True
    )
    value: so.Mapped[Optional[str]] = so.mapped_column(sa.String(500))

    equipment: so.Mapped['Equipment'] = so.relationship(
        back_populates='equipment_parameters'
    )
    parameter: so.Mapped['Parameter'] = so.relationship(
        back_populates='equipment_parameters'
    )

    def __repr__(self):
        return f'<EquipmentParameter {self.equipment_id.hex}:{self.parameter_id}>'
        
class Hospital(Updateable, db.Model):
    __tablename__ = 'hospitals'

    id: so.Mapped[UUID] = so.mapped_column(default=uuid4, primary_key=True)
    name: so.Mapped[str] = so.mapped_column(sa.String(255), index=True)
    address: so.Mapped[Optional[str]] = so.mapped_column(sa.String(500))

    installations: so.WriteOnlyMapped['Installation'] = so.relationship(
        back_populates='hospital'
    )
    services: so.WriteOnlyMapped['Service'] = so.relationship(
        back_populates='hospital'
    )
    contacts: so.Mapped[list['HospitalContact']] = so.relationship(
        back_populates='hospital',
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f'<Hospital {self.name}>'

class HospitalContact(Updateable, db.Model):
    __tablename__ = 'hospital_contacts'

    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    name: so.Mapped[str] = so.mapped_column(sa.String(255))
    phone_number: so.Mapped[Optional[str]] = so.mapped_column(sa.String(50))
    email: so.Mapped[Optional[str]] = so.mapped_column(sa.String(255))
    hospital_id: so.Mapped[UUID] = so.mapped_column(
        sa.ForeignKey('hospitals.id'), index=True
    )

    hospital: so.Mapped['Hospital'] = so.relationship(
        back_populates='contacts'
    )

    def __repr__(self):
        return f'<HospitalContact {self.name}>'

class Installation(Updateable, db.Model):
    __tablename__ = 'installations'

    id: so.Mapped[UUID] = so.mapped_column(default=uuid4, primary_key=True)
    install_date: so.Mapped[datetime] = so.mapped_column(index=True)
    installation_type: so.Mapped[Optional[str]] = so.mapped_column(sa.String(64))
    note: so.Mapped[Optional[str]] = so.mapped_column(sa.String(500))
    status: so.Mapped[Optional[str]] = so.mapped_column(sa.String(64))
    hospital_id: so.Mapped[UUID] = so.mapped_column(
        sa.ForeignKey('hospitals.id'), index=True
    )

    hospital: so.Mapped['Hospital'] = so.relationship(
        back_populates='installations'
    )
    equipment_installations: so.Mapped[list['EquipmentInstallation']] = so.relationship(
        back_populates='installation',
        cascade="all, delete-orphan"
    )

    users: so.Mapped[list['User']] = so.relationship(
        secondary=UserInstallation,
        back_populates='installations'
    )

    def update_installation(self, data):
        """Apply update data, validating all references."""
        if 'equipment_ids' in data:
            # Deduplicate while preserving order to avoid false validation errors
            equipment_ids = list(dict.fromkeys(data['equipment_ids']))
            equipments = db.session.scalars(
                sa.select(Equipment).where(Equipment.id.in_(equipment_ids))
            ).all()
            if len(equipments) != len(equipment_ids):
                abort(400, 'One or more equipment IDs are invalid or no longer exist.')
            self.equipment_installations = [
                EquipmentInstallation(equipment_id=eq.id)
                for eq in equipments
            ]

        if 'hospital_id' in data:
            hospital = db.session.get(Hospital, data['hospital_id'])
            if hospital is None:
                abort(400, 'Hospital not found or has been deleted.')
            self.hospital = hospital

        if 'user_ids' in data:
            # Deduplicate while preserving order to avoid false validation errors
            user_ids = list(dict.fromkeys(data['user_ids']))
            users = db.session.scalars(
                sa.select(User).where(User.id.in_(user_ids))
            ).all()
            if len(users) != len(user_ids):
                abort(400, 'One or more user IDs are invalid or no longer exist.')
            self.users = users

        self.update(data, ignore=['equipment_ids', 'hospital_id', 'user_ids'])

    def __repr__(self):
        return f'<Installation {self.id.hex}>'


class Service(Updateable, db.Model):
    __tablename__ = 'services'

    id: so.Mapped[UUID] = so.mapped_column(default=uuid4, primary_key=True)
    opened_date: so.Mapped[Optional[datetime]]
    closed_date: so.Mapped[Optional[datetime]]
    status: so.Mapped[Optional[str]] = so.mapped_column(sa.String(64))
    problem_description: so.Mapped[Optional[str]] = so.mapped_column(sa.String(1000))
    fix_description: so.Mapped[Optional[str]] = so.mapped_column(sa.String(1000))
    equipment_id: so.Mapped[UUID] = so.mapped_column(
        sa.ForeignKey('equipments.id'), index=True
    )
    hospital_id: so.Mapped[Optional[UUID]] = so.mapped_column(
        sa.ForeignKey('hospitals.id'), index=True
    )

    equipment: so.Mapped['Equipment'] = so.relationship(
        back_populates='services'
    )
    hospital: so.Mapped['Hospital'] = so.relationship(
        back_populates='services'
    )

    users: so.Mapped[list['User']] = so.relationship(
        secondary=UserService,
        back_populates='services'
    )

    service_parts: so.Mapped[list['ServicePart']] = so.relationship(
        back_populates='service'
    )

    def __repr__(self):
        return f'<Service {self.id.hex}>'

class ServicePart(db.Model):
    __tablename__ = 'service_parts'

    service_id: so.Mapped[UUID] = so.mapped_column(
        sa.ForeignKey('services.id'), primary_key=True
    )
    part_id: so.Mapped[int] = so.mapped_column(
        sa.ForeignKey('parts.id'), primary_key=True
    )
    quantity: so.Mapped[Optional[str]] = so.mapped_column(sa.String(500))


    service: so.Mapped['Service'] = so.relationship(
        back_populates='service_parts'
    )
    part: so.Mapped['Part'] = so.relationship(
        back_populates='service_parts'
    )
    def __repr__(self):
        return f'<ServicePart {self.service_id.hex}:{self.part_id}>'

class Part(Updateable, db.Model):
    __tablename__ = 'parts'

    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    name: so.Mapped[str] = so.mapped_column(sa.String(255))

    service_parts: so.Mapped[list['ServicePart']] = so.relationship(
        back_populates='part'
    )

    def __repr__(self):
        return f'<Part {self.name}>'








