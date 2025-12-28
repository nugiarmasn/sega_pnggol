import firebase_admin
from firebase_admin import credentials, firestore, storage
from flask_socketio import SocketIO
from flask_cors import CORS
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager
import os

base_dir = os.path.abspath(os.path.dirname(__file__))
cert_path = os.path.join(os.path.dirname(base_dir), "serviceAccountKey.json")

if not firebase_admin._apps:
    cred = credentials.Certificate(cert_path)
    firebase_admin.initialize_app(cred, {
        'storageBucket': "myheadstyle.firebasestorage.app"
    })

db = firestore.client()
bucket = storage.bucket()
socketio = SocketIO(cors_allowed_origins="*")
cors = CORS()
bcrypt = Bcrypt()
jwt = JWTManager()
login_manager = LoginManager()
login_manager.login_view = 'admin_bp.login'