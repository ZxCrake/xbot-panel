from .auth import bp as auth_bp
from .user import bp as user_bp
from .admin import bp as admin_bp
from .pages import bp as pages_bp


def register(app):
    app.register_blueprint(auth_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(pages_bp)
