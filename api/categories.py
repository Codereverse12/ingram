from apifairy.decorators import other_responses
from flask import Blueprint, abort
from apifairy import authenticate, body, response
import sqlalchemy as sa

from api import db
from api.models import Category, Permission
from api.schemas import CategorySchema
from api.auth import token_auth
from api.decorators import permission_required, paginated_response

categories = Blueprint('categories', __name__)
category_schema = CategorySchema()
categories_schema = CategorySchema(many=True)
update_category_schema = CategorySchema(partial=True)


@categories.route('/categories', methods=['POST'])
@authenticate(token_auth)
@permission_required(Permission.EQUIPMENT)
@body(category_schema)
@response(category_schema, 201)
def new(args):
    """Create a new equipment category"""
    category = Category(**args)
    db.session.add(category)
    db.session.commit()
    return category


@categories.route('/categories', methods=['GET'])
@authenticate(token_auth)
@permission_required(Permission.EQUIPMENT)
@paginated_response(categories_schema)
def all():
    """Retrieve all equipment categories"""
    return sa.select(Category)


@categories.route('/categories/<int:id>', methods=['GET'])
@authenticate(token_auth)
@permission_required(Permission.EQUIPMENT)
@response(category_schema)
@other_responses({404: 'Category not found'})
def get(id):
    """Retrieve an equipment category by id"""
    return db.session.get(Category, id) or abort(404)


@categories.route('/categories/<int:id>', methods=['PUT'])
@authenticate(token_auth)
@permission_required(Permission.EQUIPMENT)
@body(update_category_schema)
@response(category_schema)
@other_responses({404: 'Category not found'})
def put(data, id):
    """Edit an equipment category"""
    category = db.session.get(Category, id) or abort(404)
    category.update(data)
    db.session.commit()
    return category


@categories.route('/categories/<int:id>', methods=['DELETE'])
@authenticate(token_auth)
@permission_required(Permission.EQUIPMENT)
@other_responses({404: 'Category not found'})
def delete(id):
    """Delete an equipment category"""
    category = db.session.get(Category, id) or abort(404)
    db.session.delete(category)
    db.session.commit()
    return '', 204
