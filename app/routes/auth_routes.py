# =========================
# IMPORT LIBRARY
# =========================

import base64                      # Untuk encode gambar ke base64
import cv2                         # OpenCV untuk manipulasi gambar
import numpy as np                 # Numpy untuk manipulasi array
from flask import Blueprint, request, jsonify  # Flask core
from app.extensions import db, bcrypt           # Firestore DB & bcrypt
from flask_jwt_extended import (
    create_access_token,           # Membuat JWT token
    jwt_required,                  # Proteksi endpoint dengan JWT
    get_jwt_identity               # Ambil identity dari token
)
from datetime import datetime      # Untuk timestamp
from google.oauth2 import id_token # Validasi token Google
from google.auth.transport import requests as google_requests


# =========================
# BLUEPRINT AUTH
# =========================

# Blueprint untuk endpoint authentication dengan prefix /api/auth
auth_bp = Blueprint('auth_api', __name__, url_prefix='/api/auth')


# ============================================================
# 1. REGISTER USER
# ============================================================
@auth_bp.route('/register', methods=['POST'])
def register():
    try:
        # Ambil data JSON dari request
        data = request.get_json()

        # Ambil field yang dibutuhkan
        email = data.get('email')
        password = data.get('password')
        full_name = data.get('full_name')

        # Validasi input wajib
        if not email or not password:
            return jsonify({"message": "Email dan Password wajib diisi"}), 400

        # Referensi dokumen user berdasarkan email
        user_doc_ref = db.collection('users').document(email)

        # Cek apakah user sudah terdaftar
        if user_doc_ref.get().exists:
            return jsonify({"message": "Email sudah terdaftar"}), 400

        # Hash password menggunakan bcrypt
        hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')

        # Data user baru
        new_user = {
            "full_name": full_name,
            "email": email,
            "password_hash": hashed_pw,
            "role": "USER",
            "is_online": False,
            "profile_image_url": None,
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }

        # Simpan user ke Firestore
        user_doc_ref.set(new_user)

        # Response sukses
        return jsonify({"message": "Berhasil daftar", "email": email}), 201

    except Exception as e:
        # Error handling
        return jsonify({"message": f"Error: {str(e)}"}), 500


# ============================================================
# 2. LOGIN USER (EMAIL + PASSWORD)
# ============================================================
@auth_bp.route('/login', methods=['POST'])
def login():
    try:
        # Ambil data request
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')

        # Ambil user dari Firestore
        user_doc = db.collection('users').document(email).get()

        # Jika user tidak ada
        if not user_doc.exists:
            return jsonify({"message": "Email tidak terdaftar"}), 401

        # Ambil data user
        user_data = user_doc.to_dict()
        stored_hash = user_data.get('password_hash')

        # Jika user tidak punya password (login Google)
        if not stored_hash:
            return jsonify({"message": "User tidak memiliki password"}), 500

        # Verifikasi password
        if not bcrypt.check_password_hash(stored_hash, password):
            return jsonify({"message": "Password salah"}), 401

        # Update status online & last login
        db.collection('users').document(email).update({
            "last_login": datetime.now(),
            "is_online": True
        })

        # Generate JWT token
        token = create_access_token(identity=email)

        # Response sukses
        return jsonify({
            "message": "Login Berhasil",
            "token": token,
            "user": {
                "email": email,
                "full_name": user_data.get('full_name'),
                "role": user_data.get('role'),
                "profile_image_url": user_data.get('profile_image_url')
            }
        }), 200

    except Exception as e:
        return jsonify({"message": f"Error: {str(e)}"}), 500


# ============================================================
# 3. GET PROFILE USER
# ============================================================
@auth_bp.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    try:
        # Ambil email dari JWT
        email = get_jwt_identity()

        # Ambil data user
        user_doc = db.collection('users').document(email).get()

        # Jika user tidak ditemukan
        if not user_doc.exists:
            return jsonify({"message": "User tidak ditemukan"}), 404

        user_data = user_doc.to_dict()

        # Hapus password hash agar aman
        user_data.pop('password_hash', None)

        # Konversi datetime ke string
        for key in ['created_at', 'updated_at', 'last_login']:
            if key in user_data and hasattr(user_data[key], 'isoformat'):
                user_data[key] = user_data[key].isoformat()

        return jsonify({"status": "success", "user": user_data}), 200

    except Exception as e:
        return jsonify({"message": f"Server Error: {str(e)}"}), 500


# ============================================================
# 4. UPDATE PROFILE
# ============================================================
@auth_bp.route('/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    try:
        # Email dari token
        current_email = get_jwt_identity()

        # Data request
        data = request.get_json()
        new_name = data.get('full_name')
        new_email = data.get('email')

        # Validasi nama
        if not new_name:
            return jsonify({"message": "Nama tidak boleh kosong"}), 400

        # Ambil dokumen user
        user_doc_ref = db.collection('users').document(current_email)
        user_doc = user_doc_ref.get()

        if not user_doc.exists:
            return jsonify({"message": "User tidak ditemukan"}), 404

        # Data update
        update_data = {
            "full_name": new_name,
            "updated_at": datetime.now()
        }

        # Jika user mengganti email
        if new_email and new_email != current_email:

            # Cek email baru
            if db.collection('users').document(new_email).get().exists:
                return jsonify({"message": "Email sudah digunakan"}), 400

            # Pindahkan data ke email baru
            old_data = user_doc.to_dict()
            old_data.update(update_data)
            old_data['email'] = new_email

            db.collection('users').document(new_email).set(old_data)
            user_doc_ref.delete()

            # Buat token baru
            new_token = create_access_token(identity=new_email)

            return jsonify({
                "status": "success",
                "message": "Profil berhasil diperbarui",
                "token": new_token
            }), 200

        # Update nama saja
        user_doc_ref.update(update_data)

        return jsonify({"status": "success", "message": "Profil berhasil diperbarui"}), 200

    except Exception as e:
        return jsonify({"message": f"Error: {str(e)}"}), 500


# ============================================================
# 5. CHANGE PASSWORD
# ============================================================
@auth_bp.route('/change-password', methods=['POST'])
@jwt_required()
def change_password():
    try:
        email = get_jwt_identity()
        data = request.get_json()

        current_password = data.get('current_password')
        new_password = data.get('new_password')

        # Validasi input
        if not current_password or not new_password:
            return jsonify({"message": "Password lama & baru wajib diisi"}), 400

        # Ambil data user
        user_doc = db.collection('users').document(email).get()
        user_data = user_doc.to_dict()

        # Verifikasi password lama
        if not bcrypt.check_password_hash(user_data['password_hash'], current_password):
            return jsonify({"message": "Password lama salah"}), 401

        # Update password baru
        db.collection('users').document(email).update({
            "password_hash": bcrypt.generate_password_hash(new_password).decode('utf-8'),
            "updated_at": datetime.now()
        })

        return jsonify({"status": "success", "message": "Password berhasil diubah"}), 200

    except Exception as e:
        return jsonify({"message": f"Error: {str(e)}"}), 500


# ============================================================
# 6. UPLOAD FOTO PROFILE
# ============================================================
@auth_bp.route('/upload-photo', methods=['POST'])
@jwt_required()
def upload_photo():
    try:
        email = get_jwt_identity()

        # Validasi file
        if 'image' not in request.files:
            return jsonify({"message": "Tidak ada file gambar"}), 400

        file = request.files['image']

        # Convert file ke numpy array
        file_bytes = np.frombuffer(file.read(), np.uint8)

        # Decode menjadi gambar
        img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

        if img is None:
            return jsonify({"message": "File bukan gambar"}), 400

        # Resize gambar jika terlalu besar
        h, w = img.shape[:2]
        max_dim = 512

        if max(h, w) > max_dim:
            scale = max_dim / max(h, w)
            img = cv2.resize(
                img,
                (int(w * scale), int(h * scale)),
                interpolation=cv2.INTER_AREA
            )

        # Kompres JPG kualitas 70%
        _, buffer = cv2.imencode('.jpg', img, [int(cv2.IMWRITE_JPEG_QUALITY), 70])

        # Encode base64
        img_base64 = base64.b64encode(buffer).decode('utf-8')
        profile_image_url = f"data:image/jpeg;base64,{img_base64}"

        # Simpan ke Firestore
        db.collection('users').document(email).update({
            "profile_image_url": profile_image_url,
            "updated_at": datetime.now()
        })

        return jsonify({
            "status": "success",
            "message": "Foto profil berhasil diupdate",
            "image_url": profile_image_url
        }), 200

    except Exception as e:
        return jsonify({"message": f"Gagal memproses gambar: {str(e)}"}), 500


# ============================================================
# 7. LOGOUT USER
# ============================================================
@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    try:
        email = get_jwt_identity()

        # Set status offline
        db.collection('users').document(email).update({
            "is_online": False
        })

        return jsonify({"status": "success", "message": "Logout berhasil"}), 200

    except Exception as e:
        return jsonify({"message": f"Error: {str(e)}"}), 500


# ============================================================
# 8. LOGIN GOOGLE OAUTH
# ============================================================
@auth_bp.route('/google-login', methods=['POST'])
def google_login():
    try:
        data = request.get_json()
        token = data.get('id_token')

        # Token wajib ada
        if not token:
            return jsonify({"message": "Token Google tidak ditemukan"}), 400

        # Verifikasi token Google
        id_info = id_token.verify_oauth2_token(
            token,
            google_requests.Request()
        )

        email = id_info.get('email')
        name = id_info.get('name')
        picture = id_info.get('picture')

        user_doc_ref = db.collection('users').document(email)
        user_doc = user_doc_ref.get()

        # Jika user baru
        if not user_doc.exists:
            new_user = {
                "full_name": name,
                "email": email,
                "password_hash": None,
                "role": "USER",
                "is_online": True,
                "profile_image_url": picture,
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
                "login_method": "GOOGLE"
            }
            user_doc_ref.set(new_user)
        else:
            # Update status login
            user_doc_ref.update({
                "is_online": True,
                "last_login": datetime.now()
            })

        # Generate JWT
        app_token = create_access_token(identity=email)

        return jsonify({
            "status": "success",
            "message": "Login Google Berhasil",
            "token": app_token,
            "user": {
                "email": email,
                "full_name": name,
                "profile_image_url": picture
            }
        }), 200

    except ValueError:
        return jsonify({"message": "Token Google Tidak Valid"}), 401

    except Exception as e:
        return jsonify({"message": f"Server Error: {str(e)}"}), 500
