import os
import click
import sqlalchemy as sa
import sqlalchemy.orm as so
from api import create_app, db
from api.models import (
    User, Equipment, Hospital,
    Category, Installation,
    Role, Permission, Token,
    Service, Part
)

app = create_app(os.getenv('FLASK_CONFIG') or 'default')

@app.shell_context_processor
def make_shell_context():
    return dict(
        db=db,
        sa=sa,
        so=so,
        User=User,
        Equipment=Equipment,
        Hospital=Hospital,
        Installation=Installation,
        Category=Category,
        Role=Role,
        Permission=Permission,
        Token=Token,
        Service=Service,
        Part=Part,
    )

@app.cli.command()
def test():
    """Run the unit tests."""
    import unittest
    tests = unittest.TestLoader().discover('tests')
    unittest.TextTestRunner(verbosity=2).run(tests)

@app.cli.command()
def insert_roles():
    """Insert roles."""
    Role.insert_roles()
    click.echo('Roles inserted.')

@app.cli.command()
def insert_categories():
    """Insert equipment categories."""
    Category.insert_categories()
    click.echo('Categories inserted.')