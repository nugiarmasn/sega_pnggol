import firebase_admin
from firebase_admin import credentials, firestore, storage
from flask_socketio import SocketIO
from flask_cors import CORS
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager
import os

# Mendapatkan direktori dasar aplikasi
base_dir = os.path.abspath(os.path.dirname(__file__))

# Path menuju file credential Firebase
cert_path = os.path.join(os.path.dirname(base_dir), "serviceAccountKey.json")

# Inisialisasi Firebase hanya jika belum diinisialisasi
if not firebase_admin._apps:
    cred = credentials.Certificate(cert_path)
    
    # Inisialisasi Firebase dengan credential dan konfigurasi storage
    firebase_admin.initialize_app(cred, {
        'storageBucket': "myheadstyle.firebasestorage.app"
    })

# Inisialisasi Firestore (database)
db = firestore.client()

# Inisialisasi bucket storage Firebase
bucket = storage.bucket()

# Inisialisasi SocketIO untuk komunikasi real-time
socketio = SocketIO(cors_allowed_origins="*")

# Mengaktifkan CORS agar API dapat diakses dari domain lain
cors = CORS()

# Inisialisasi hashing password
bcrypt = Bcrypt()

# Inisialisasi JWT untuk authentication berbasis token
jwt = JWTManager()

# LoginManager untuk session login (biasanya untuk admin dashboard)
login_manager = LoginManager()

# Endpoint redirect jika belum login
login_manager.login_view = 'admin_bp.login'
