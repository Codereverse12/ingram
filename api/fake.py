import random
import click
from flask import Blueprint
from faker import Faker
from sqlalchemy.exc import IntegrityError
from api import db
import sqlalchemy as sa
from api.models import User, Role, Hospital, Equipment, Installation, \
    EquipmentInstallation

fake = Blueprint('fake', __name__)
faker = Faker()

@fake.cli.command()
@click.option('--count', type=int, default=100, help='Number of users to generate.')
@click.option('--role-id', type=int, default=None, help='Role ID for the users.')
def users(count, role_id):
    """Generate fake users."""
    if role_id is None:
        role_id = db.session.scalar(sa.select(Role.id).where(Role.name == "Technician"))
    role = db.session.get(Role, role_id)

    i = 0
    while i < count:
        u = User(email=faker.email(), role=role)
        db.session.add(u)
        try:
            db.session.commit()
            i += 1
        except IntegrityError:
            db.session.rollback()
    
    click.echo(f'Created {i} user(s).')

@fake.cli.command()
@click.option('--count', type=int, default=100, help='Number of hospitals to generate.')
def hospitals(count):
    """Generate fake hospitals."""
    i = 0
    while i < count:
        h = Hospital(name=faker.company())
        db.session.add(h)
        try:
            db.session.commit()
            i += 1
        except IntegrityError:
            db.session.rollback()

    click.echo(f'Created {i} hospital(s).')

@fake.cli.command()
@click.option('--count', type=int, default=100, help='Number of equipments to generate.')
def equipments(count):
    """Generate fake equipments."""
    def generate_equipment():
        equipment_name = f"{faker.word().capitalize()} {faker.word().capitalize()} {faker.unique.random_int(min=100, max=999)}"
        
        prefix = "EQ"
        part1 = faker.lexify("???").upper()
        part2 = faker.numerify("###")
        serial_number = f"{prefix}-{part1}-{part2}"
        
        return equipment_name, serial_number
    
    i = 0
    while i < count:
        name, serial_number = generate_equipment()
        e = Equipment(name=name, serial_number=serial_number)
        db.session.add(e)
        try:
            db.session.commit()
            i += 1
        except IntegrityError:
            db.session.rollback()

    click.echo(f'Created {i} equipment(s).')

# Internal randomization ranges (not exposed as CLI options)
MIN_USERS, MAX_USERS = 1, 3
MIN_EQUIPMENTS, MAX_EQUIPMENTS = 1, 5
EXCLUSIVE_EQUIPMENT = True  # each equipment lives in at most one installation
 
 
@fake.cli.command()
@click.option('--count', type=int, default=100, show_default=True,
              help='Number of installations to generate.')
def installations(count):
    """Generate fake installations, assigned to random users, a hospital, and equipments."""
 
    users = db.session.scalars(sa.select(User)).all()
    hospitals = db.session.scalars(sa.select(Hospital)).all()
    equipments = db.session.scalars(sa.select(Equipment)).all()
 
    if not users or not hospitals or not equipments:
        click.echo('Need at least one User, one Hospital and one Equipment before generating installations.')
        return
 
    # Pool of equipment still available for assignment (shrinks since EXCLUSIVE_EQUIPMENT=True)
    available_equipments = list(equipments)
 
    created = 0
    attempts = 0
    max_attempts = count * 10  # safety valve against infinite loops on IntegrityError storms
 
    while created < count and attempts < max_attempts:
        attempts += 1
 
        pool = available_equipments if EXCLUSIVE_EQUIPMENT else equipments
 
        if len(pool) < MIN_EQUIPMENTS:
            click.echo(f'Ran out of assignable equipment after {created} installation(s). Stopping early.')
            break
 
        n_users = random.randint(MIN_USERS, min(MAX_USERS, len(users)))
        n_equip = random.randint(MIN_EQUIPMENTS, min(MAX_EQUIPMENTS, len(pool)))
 
        chosen_users = random.sample(users, n_users)
        chosen_equipments = random.sample(pool, n_equip)
        chosen_hospital = random.choice(hospitals)
 
        installation = Installation(
            install_date=faker.date_time_between(start_date='-3y', end_date='now'),
            hospital_id=chosen_hospital.id,
            users=chosen_users,
            equipment_installations=[
                EquipmentInstallation(equipment_id=equipment.id)
                for equipment in chosen_equipments
            ],
        )
        db.session.add(installation)
 
        try:
            db.session.commit()
        except sa.exc.IntegrityError:
            db.session.rollback()
            continue  # try again with a fresh random combination
 
        if EXCLUSIVE_EQUIPMENT:
            for equipment in chosen_equipments:
                available_equipments.remove(equipment)
 
        created += 1
 
    click.echo(f'Created {created} installation(s).')