from functools import wraps
from flask import abort, current_app, request, url_for
from apifairy import arguments, response
import sqlalchemy as sa
from api import db
from api.schemas import PagePaginationSchema, PaginatedCollection
from api.models import Permission
from api.auth import token_auth

def permission_required(permission):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not token_auth.current_user().can(permission):
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def admin_required(f):
    return permission_required(Permission.ADMIN)(f)

def paginated_response(schema, max_limit=12, order_by=None,
                       order_direction='asc'):
    def inner(f):
        @wraps(f)
        def paginate(*args, **kwargs):
            args = list(args)
            page_pagination = args.pop(-1)
            select_query = f(*args, **kwargs)
            if order_by is not None:
                o = order_by.desc() if order_direction == 'desc' else order_by
                select_query = select_query.order_by(o)
            
            page = page_pagination.get('page', 1)
            per_page = page_pagination.get('per_page', max_limit)
            
            if (per_page > max_limit):
                per_page = max_limit

            pagination = db.paginate(
                select_query,
                page=page,
                per_page=per_page,
                error_out=False
            )

            data = pagination.items
            prev = None
            if pagination.has_prev:
                prev = url_for(request.endpoint, page=page - 1, **kwargs)
            next = None
            if pagination.has_next:
                next = url_for(request.endpoint, page=page + 1, **kwargs)

            return {
                'data': data,
                'pagination': {
                    "page": page,
                    "per_page": per_page,
                    "prev_url": prev,
                    "next_url": next,
                    "count": len(data),
                    "total": pagination.total
                }
            }

        
        return arguments(PagePaginationSchema)(
            response(PaginatedCollection(
                schema
            ))(paginate))
    
    return inner