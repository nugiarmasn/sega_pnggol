from flask import Blueprint, request, jsonify
from app.extensions import db, bcrypt
from flask_jwt_extended import create_access_token
from datetime import datetime

# Definisi Blueprint untuk API Auth
auth_bp = Blueprint('auth_api', __name__, url_prefix='/api/auth')

# --- 1. FUNGSI REGISTER (DAFTAR) ---
@auth_bp.route('/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        full_name = data.get('full_name')

        if not email or not password:
            return jsonify({"message": "Email dan Password wajib diisi"}), 400

        # Cek apakah email sudah terdaftar di Firestore
        user_doc_ref = db.collection('users').document(email)
        if user_doc_ref.get().exists:
            return jsonify({"message": "Email sudah terdaftar"}), 400

        # Enkripsi Password agar aman
        hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')

        # Data User Baru
        new_user = {
            "full_name": full_name,
            "email": email,
            "password_hash": hashed_pw,
            "role": "USER",
            "is_online": False,
            "created_at": datetime.now()
        }

        # Simpan ke Firebase Firestore
        user_doc_ref.set(new_user)

        return jsonify({"message": "Berhasil daftar", "email": email}), 201
    
    except Exception as e:
        return jsonify({"message": f"Error: {str(e)}"}), 500


# --- 2. FUNGSI LOGIN (MASUK) ---
@auth_bp.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')

        # Ambil data user dari Firestore berdasarkan email
        user_doc_ref = db.collection('users').document(email)
        user_doc = user_doc_ref.get()

        if user_doc.exists:
            user_data = user_doc.to_dict()
            
            # Verifikasi password yang diketik dengan yang ada di DB
            if bcrypt.check_password_hash(user_data['password_hash'], password):
                
                # --- UPDATE JEJAK LOGIN DI FIREBASE ---
                user_doc_ref.update({
                    "last_login": datetime.now(),
                    "is_online": True
                })
                # --------------------------------------

                # Buat Token JWT untuk keamanan akses AI
                token = create_access_token(identity=email)
                
                return jsonify({
                    "message": "Login Berhasil",
                    "token": token,
                    "full_name": user_data.get('full_name'),
                    "role": user_data.get('role')
                }), 200
        
        return jsonify({"message": "Login Gagal! Email atau Password salah"}), 401

    except Exception as e:
        return jsonify({"message": f"Error: {str(e)}"}), 500