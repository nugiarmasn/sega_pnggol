from flask import Blueprint, request, jsonify
from app.extensions import db
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime

feedback_bp = Blueprint('feedback_api', __name__, url_prefix='/api/feedback')

@feedback_bp.route('/submit', methods=['POST'])
@jwt_required()
def submit_feedback():
    try:
        # 1. Ambil Email dari Token JWT yang dikirim Flutter
        current_email = get_jwt_identity()
        
        # 2. Ambil data lengkap user dari Firestore (untuk kelengkapan data feedback)
        user_doc = db.collection('users').document(current_email).get()
        user_data = user_doc.to_dict() if user_doc.exists else {}

        # 3. Ambil Input dari Flutter
        data = request.get_json()
        rating = data.get('rating')
        message = data.get('message')

        if not message:
            return jsonify({"message": "Pesan tidak boleh kosong"}), 400

        # 4. Siapkan Data Feedback
        new_feedback = {
            "user_email": current_email,
            "user_name": user_data.get('full_name', 'Unknown User'),
            "user_photo": user_data.get('profile_image_url', None), # Berguna untuk Admin Panel nanti
            "rating": rating,
            "message": message,
            "created_at": datetime.now(),
            "status": "unread" # Status untuk Admin (unread/read)
        }

        # 5. Simpan ke Collection 'feedbacks'
        db.collection('feedbacks').add(new_feedback)

        return jsonify({"status": "success", "message": "Feedback berhasil dikirim"}), 201

    except Exception as e:
        return jsonify({"message": f"Error: {str(e)}"}), 500