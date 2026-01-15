from flask_login import UserMixin
from app.extensions import login_manager, db

# Model user sederhana untuk sistem login/authorization
# UserMixin memberikan fitur built-in untuk Flask-Login (is_authenticated, get_id, dll.)
class User(UserMixin):
    def __init__(self, user_id, email, full_name, role):
        self.id = user_id         # unique identifier user (ID document Firestore)
        self.email = email        # email untuk login
        self.full_name = full_name  # nama lengkap
        self.role = role          # role: admin / user

# Loader untuk mengembalikan objek user berdasarkan session user_id
# Flask-Login otomatis memanggil ini saat session aktif
@login_manager.user_loader
def load_user(user_id):
    # Ambil user dari Firestore berdasarkan ID dokumen
    u = db.collection('users').document(user_id).get()
    
    # Jika data user tersedia, konversi ke object User()
    if u.exists:
        data = u.to_dict()
        return User(u.id, data['email'], data['full_name'], data['role'])

    # Jika tidak ditemukan, return None agar dianggap tidak login
    return None
