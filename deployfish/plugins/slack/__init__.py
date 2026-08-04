from .hooks import process_service_update


def load(app):
    """
    Load.

    Args:
        app: app.

    """
    app.hook.register("post_object_update", process_service_update)
