from flask import Blueprint, request, jsonify
from app.extensions import db
from app.services.ai_service import ai_service
import base64
import datetime
import cv2
import numpy as np

# Inisialisasi Blueprint
style_bp = Blueprint('style_api', __name__, url_prefix='/api/style')

@style_bp.route('/analyze', methods=['POST'])
def analyze():
    try:
        # 1. Validasi Input Gambar
        if 'image' not in request.files:
            return jsonify({
                "status": "error",
                "message": "File gambar tidak ditemukan"
            }), 400
        
        file = request.files['image']
        user_id = request.form.get('user_id', 'anonymous')
        
        # --- TAMBAHAN: TANGKAP DATA GENDER & HIJAB DARI FLUTTER ---
        # Gender diharapkan: 'Laki-laki' atau 'Perempuan'
        gender = request.form.get('gender', 'Laki-laki') 
        # is_hijab diharapkan: 'true' atau 'false' (string dari multipart form)
        is_hijab_str = request.form.get('is_hijab', 'false').lower()
        is_hijab = True if is_hijab_str == 'true' else False
        
        # Baca bytes gambar asli untuk dikirim ke AI
        img_bytes = file.read()
        
        # 2. Jalankan Analisis AI (Mendeteksi Face Shape: Oval, Round, Square)
        res = ai_service.analyze_face(img_bytes)
        
        if not res:
            return jsonify({
                "status": "error", 
                "message": "Wajah tidak terdeteksi. Gunakan foto selfie yang lebih jelas."
            }), 400

        # 3. KOMPRESI GAMBAR (Agar muat di Base64 Firestore)
        nparr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is not None:
            height, width = img.shape[:2]
            new_width = 400
            new_height = int(height * (new_width / width))
            resized_img = cv2.resize(img, (new_width, new_height))
            _, buffer = cv2.imencode('.jpg', resized_img, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
            img_base64 = base64.b64encode(buffer).decode('utf-8')
        else:
            return jsonify({"status": "error", "message": "Gagal memproses gambar"}), 500

        # 4. LOGIKA REKOMENDASI DINAMIS (Opsional: Menyesuaikan Gender)
        # Ini agar respons API awal juga sedikit nyambung sebelum masuk Chatbot
        raw_recs = res['recommendations']
        if gender == 'Perempuan':
            if is_hijab:
                recommendations = ["Gaya Hijab Layered", "Pashmina Flowy", "Ciput Ninja Nyaman"]
            else:
                recommendations = ["Long Layered Cut", "Side Swept Bangs", "Bob Cut"]
        else:
            # Jika Laki-laki, gunakan rekomendasi dari ai_service (Undercut, dll)
            recommendations = raw_recs.split(", ")

        # 5. SIMPAN DATA LENGKAP KE FIRESTORE
        doc_data = {
            "user_id": user_id,
            "gender": gender,
            "is_hijab": is_hijab,
            "face_shape": res['face_shape'],
            "confidence": res['confidence'],
            "all_scores": res['all_scores'],
            "recommendations": recommendations,
            "photo_base64": img_base64,
            "created_at": datetime.datetime.now()
        }
        
        # Simpan ke koleksi 'style_history'
        db.collection('style_history').add(doc_data)

        # 6. RESPONSE FINAL
        return jsonify({
            "status": "success",
            "data": {
                "user_id": user_id,
                "gender": gender,
                "is_hijab": is_hijab,
                "face_shape": res['face_shape'],
                "confidence": res['confidence'],
                "recommendations": recommendations,
                "photo_base64": img_base64
            }
        }), 200

    except Exception as e:
        print(f"❌ Route Error: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Server error: {str(e)}"
        }), 500