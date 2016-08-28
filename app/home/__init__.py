from flask import Blueprint
from ..models import Permission
home = Blueprint('home',__name__)

@home.app_context_processor
def inject_permissions():
    return dict(Permission=Permission)

#@home.app_context_processor
#def inject_status():
#    return dict(Status=Status)

from . import views,errors