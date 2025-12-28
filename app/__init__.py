from flask import Flask
from config import Config
from app.extensions import socketio, cors, db, login_manager, bcrypt, jwt

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    socketio.init_app(app)
    cors.init_app(app)
    login_manager.init_app(app)
    bcrypt.init_app(app)
    jwt.init_app(app)

    from app.routes.style_routes import style_bp
    from app.routes.admin_routes import admin_bp
    from app.routes.auth_routes import auth_bp
    
    app.register_blueprint(style_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(auth_bp)

    @app.route('/')
    def index():
        return "Backend AI Stylish MyHeadStyle sedang berjalan!"

    return app