from flask import Blueprint, request, jsonify
from app.services.edit_service import EditService

# Membuat blueprint endpoint khusus edit gambar
edit_api = Blueprint('edit_api', __name__)

# Instance service yang berisi fungsi manipulasi gambar
service = EditService()

@edit_api.route('/edit-style', methods=['POST'])
def edit_style():
    try:
        # Ambil JSON yang dikirim dari frontend
        data = request.json
        
        # Base64 dari gambar asli sebelum di-edit
        img_base64 = data.get('image_base64')

        # Jenis editnya: 'color', 'hair', 'glasses', 'hijab'
        edit_type = data.get('edit_type')

        # Value tambahan: bisa hex (untuk warna) atau nama file asset (untuk overlay)
        value = data.get('value')

        # Decode Base64 → format gambar numpy
        img = service.decode_image(img_base64)
        
        # Jika user mengubah warna rambut
        if edit_type == 'color':
            result_img = service.apply_hair_color(img, value)
        else:
            # Jika pakai asset PNG (kacamata, rambut, hijab, dsb)
            result_img = service.apply_overlay(img, edit_type, value)

        # Encode kembali ke Base64 untuk dikirim kembali ke frontend
        result_base64 = service.encode_image(result_img)
        
        # Response sukses
        return jsonify({
            "status": "success",
            "image_result": result_base64
        })

    except Exception as e:
        # Jika ada error sistem/backend
        return jsonify({"status": "error", "message": str(e)}), 500
