import base64
import cv2
import numpy as np
from flask import Blueprint, request, jsonify
from app.extensions import db
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime

# Blueprint untuk API History (prefix /api/history)
history_bp = Blueprint('history_api', __name__, url_prefix='/api/history')


# ============================================================
# 1. SIMPAN HISTORY BARU (POST) - DIPERBAIKI
# ============================================================
@history_bp.route('/', methods=['POST'])
@history_bp.route('', methods=['POST'])
@jwt_required()  # memastikan user login via JWT
def add_history():
    try:
        # Ambil user email dari JWT token
        email = get_jwt_identity()
        
        # Validasi: file gambar wajib ada
        if 'image' not in request.files:
            return jsonify({"status": "error", "message": "File gambar tidak ditemukan"}), 400
        
        file = request.files['image']

        # --- PERBAIKAN DI SINI: AMBIL DATA LENGKAP ---
        style_name = request.form.get('style_name', 'My Style')
        face_shape = request.form.get('face_shape', 'Unknown') # ✅ Tangkap Face Shape
        gender = request.form.get('gender', 'Unknown')         # ✅ Tangkap Gender
        
        # Konversi file → numpy array
        file_bytes = np.frombuffer(file.read(), np.uint8)
        img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

        # Validasi file
        if img is None:
            return jsonify({"status": "error", "message": "File rusak atau bukan gambar"}), 400

        # Resize gambar agar tidak terlalu besar saat disimpan
        h, w = img.shape[:2]
        max_dim = 512
        if max(h, w) > max_dim:
            scale = max_dim / max(h, w)
            new_w, new_h = int(w * scale), int(h * scale)
            img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)

        # Kompres ke format JPG (Quality 70)
        _, buffer = cv2.imencode('.jpg', img, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
        
        # Encode → Base64 → string
        img_base64 = base64.b64encode(buffer).decode('utf-8')
        
        # Format Base64 lengkap dengan header (sesuai kode lama Anda)
        final_image_string = f"data:image/jpeg;base64,{img_base64}"

        # Buat objek yang disimpan di Firestore
        new_history = {
            "userId": email,                
            "style_name": style_name,       
            "face_shape": face_shape,       # ✅ Simpan ke Database
            "gender": gender,               # ✅ Simpan ke Database
            "result_image_url": final_image_string,  
            "timestamp": datetime.now(),    
            "is_favorite": False            
        }

        # Insert ke collection Firestore (style_history)
        db.collection('style_history').add(new_history)

        print(f"[HISTORY] Berhasil simpan history untuk {email} | Shape: {face_shape}")
        return jsonify({
            "status": "success",
            "message": "History berhasil disimpan"
        }), 201

    except Exception as e:
        print(f"[HISTORY ERROR] {e}")
        return jsonify({"status": "error", "message": f"Server Error: {str(e)}"}), 500


# ============================================================
# 2. GET ALL HISTORY LIST BY USER (GET) - TETAP SAMA
# ============================================================
@history_bp.route('', methods=['GET'])
@history_bp.route('/', methods=['GET'])
@jwt_required()
def get_history():
    try:
        email = get_jwt_identity()

        # Query semua history milik user
        docs = db.collection('style_history') \
                 .where('userId', '==', email) \
                 .order_by('timestamp', direction='DESCENDING') \
                 .get()
        
        history_list = []

        # Loop dan ubah ke JSON
        for doc in docs:
            data = doc.to_dict()

            # Konversi datetime → string supaya bisa dikirim JSON
            if 'timestamp' in data and data['timestamp']:
                data['timestamp'] = data['timestamp'].isoformat()

            data['id'] = doc.id  # tambahkan documentId
            history_list.append(data)
        
        return jsonify({
            "status": "success",
            "count": len(history_list),
            "data": history_list
        }), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ============================================================
# 3. GET DETAIL HISTORY BY ID (GET) - TETAP SAMA
# ============================================================
@history_bp.route('/<history_id>', methods=['GET'])
@jwt_required()
def get_history_detail(history_id):
    try:
        email = get_jwt_identity()

        doc = db.collection('style_history').document(history_id).get()

        if not doc.exists:
            return jsonify({"status": "error", "message": "History tidak ditemukan"}), 404
        
        data = doc.to_dict()

        # Security: pastikan data milik user pemilik token
        if data.get('userId') != email:
            return jsonify({"status": "error", "message": "Unauthorized"}), 403
        
        if 'timestamp' in data and data['timestamp']:
            data['timestamp'] = data['timestamp'].isoformat()

        data['id'] = doc.id
        
        return jsonify({"status": "success", "data": data}), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ============================================================
# 4. DELETE 1 HISTORY BY ID (DELETE) - TETAP SAMA
# ============================================================
@history_bp.route('/<history_id>', methods=['DELETE'])
@jwt_required()
def delete_history(history_id):
    try:
        email = get_jwt_identity()

        doc_ref = db.collection('style_history').document(history_id)
        doc = doc_ref.get()

        if not doc.exists:
            return jsonify({"status": "error", "message": "History tidak ditemukan"}), 404
        
        if doc.to_dict().get('userId') != email:
            return jsonify({"status": "error", "message": "Unauthorized"}), 403
        
        doc_ref.delete()

        return jsonify({"status": "success", "message": "History berhasil dihapus"}), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ============================================================
# 5. DELETE SEMUA HISTORY MILIK USER (DELETE) - TETAP SAMA
# ============================================================
@history_bp.route('/clear', methods=['DELETE'])
@jwt_required()
def clear_all_history():
    try:
        email = get_jwt_identity()

        docs = db.collection('style_history').where('userId', '==', email).get()
        
        deleted_count = 0
        for doc in docs:
            doc.reference.delete()
            deleted_count += 1
        
        return jsonify({
            "status": "success",
            "message": f"{deleted_count} history dihapus"
        }), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ============================================================
# 6. UPDATE HISTORY (PUT) - TETAP SAMA
# ============================================================
@history_bp.route('/<history_id>', methods=['PUT'])
@jwt_required()
def update_history(history_id):
    try:
        email = get_jwt_identity()
        data = request.get_json()

        doc_ref = db.collection('style_history').document(history_id)
        doc = doc_ref.get()

        if not doc.exists:
            return jsonify({"status": "error", "message": "Not found"}), 404

        if doc.to_dict().get('userId') != email:
            return jsonify({"status": "error", "message": "Unauthorized"}), 403
        
        update_fields = {}

        # Boleh update style_name dan is_favorite
        if 'style_name' in data: update_fields['style_name'] = data['style_name']
        if 'is_favorite' in data: update_fields['is_favorite'] = data['is_favorite']

        # Jika ada perubahan, lakukan update
        if update_fields:
            doc_ref.update(update_fields)
            return jsonify({"status": "success", "message": "Updated"}), 200
        
        return jsonify({"status": "error", "message": "No changes"}), 400

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500