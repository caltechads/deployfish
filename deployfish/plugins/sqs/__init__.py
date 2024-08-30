
from .hooks import process_service_update

def load(app):
    app.hook.register('post_object_update', process_service_update)
