from flask import Flask
from config import Config
from app.extensions import socketio, cors, db, login_manager, bcrypt, jwt

def create_app(config_class=Config):
    # 1. Setup Aplikasi
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # 2. Inisialisasi Extensions
    socketio.init_app(app)
    cors.init_app(app)
    login_manager.init_app(app)
    bcrypt.init_app(app)
    jwt.init_app(app)

    # 3. Import Blueprint (Semua Fitur)
    from app.routes.style_routes import style_bp          # AI Styling
    from app.routes.admin_routes import admin_bp          # Admin Panel
    from app.routes.auth_routes import auth_bp            # Login/Register
    from app.routes.edit_routes import edit_api           # Editing Foto
    from app.routes.history_routes import history_bp      # History
    from app.routes.feedback_routes import feedback_bp    # Feedback (Baru)

    # 4. Registrasi Blueprint (Hanya Sekali per Fitur!)
    app.register_blueprint(style_bp)
    app.register_blueprint(admin_bp)   # Pastikan ini cuma satu baris
    app.register_blueprint(auth_bp)
    
    # Registrasi dengan prefix khusus
    app.register_blueprint(edit_api, url_prefix='/api/edit')
    app.register_blueprint(history_bp)
    app.register_blueprint(feedback_bp) # Feedback route

    # 5. Route Halaman Depan (Cek Server)
    @app.route('/')
    def index():
        return "Backend AI Stylish MyHeadStyle Siap Digunakan!"

    return app