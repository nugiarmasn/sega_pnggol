import os
import requests
import datetime
import base64
import cv2
import uuid
import numpy as np
import traceback
import json
import time
from flask import Blueprint, request, jsonify, current_app
from app.extensions import db
from app.services.ai_service import ai_service
from firebase_admin import firestore

style_bp = Blueprint('style_api', __name__, url_prefix='/api/style')

# ==============================================================================
# 1. KONFIGURASI API KEY (LIGHTX V2)
# ==============================================================================
LIGHTX_API_KEY = "d9b68e13818e4b199384f83347223938cb5d8d7fd80e405aab5d993467d1e81a_andoraitools"

# LightX API v2 Endpoints
UPLOAD_URL = "https://api.lightxeditor.com/external/api/v2/uploadImageUrl"
HAIRSTYLE_URL = "https://api.lightxeditor.com/external/api/v2/hairstyle"
STATUS_URL = "https://api.lightxeditor.com/external/api/v2/order-status"

# ==============================================================================
# 2. KAMUS STYLE (PROMPT ENGINEERING)
# ==============================================================================
STYLES_DB = {
    # --- PRIA ---
    "side_swept": "Male side swept hairstyle, textured short hair, black color, neat professional look",
    "quiff_grey": "Voluminous Quiff hairstyle, silver grey highlights, modern male cut",
    "wolf_cut": "Male Wolf Cut hairstyle, medium length, messy layers, trendy look",
    "side_part": "Classic side part hairstyle, professional look, dark brown hair",
    
    # --- WANITA ---
    "layered": "Long layered hairstyle with side bangs, dark brown color, feminine elegant look",
    "messy_bun": "High messy bun hairstyle, black hair, casual chic look",
    "wavy_blonde": "Long wavy blonde hairstyle, voluminous curls, elegant glamorous look",
    "straight": "Long straight black hairstyle with front bangs, shiny smooth texture",
    
    # --- KACAMATA ---
    "wayfarer": "wearing black Wayfarer sunglasses, classic cool style",
    "round": "wearing round thin frame glasses, intellectual smart look",
    "aviator": "wearing black Aviator sunglasses, pilot style",
    "sporty": "wearing sporty sunglasses with orange reflective lens",
    
    # --- HIJAB ---
    "black_basic": "wearing black instant hijab, simple and modest style",
    "navy_shawl": "wearing navy blue Pashmina hijab, elegant drape style",
    "cream": "wearing beige cream hijab, soft fabric, natural modest look",
    "pink": "wearing soft pink shawl hijab, feminine elegant style",
    
    # --- WARNA ---
    "silver": "Silver grey hair color",
    "blonde": "Golden blonde hair color",
    "red": "Dark red mahogany hair color",
    "blue": "Dark blue midnight hair color",
    "black": "Jet black hair color",
    "brown": "Chestnut brown hair color"
}

# ==============================================================================
# 3. HELPER: LIGHTX V2 - UPLOAD IMAGE
# ==============================================================================
def upload_image_to_lightx(image_bytes):
    """
    Step 1: Upload image ke LightX S3, dapat imageUrl
    """
    try:
        # Get image size
        image_size = len(image_bytes)
        
        print(f">>> [STEP 1] Uploading image to LightX ({image_size} bytes)...")
        
        # Request uploadUrl
        headers = {
            "Content-Type": "application/json",
            "x-api-key": LIGHTX_API_KEY
        }
        
        payload = {
            "uploadType": "imageUrl",
            "size": image_size,
            "contentType": "image/jpeg"
        }
        
        response = requests.post(UPLOAD_URL, headers=headers, json=payload, timeout=30)
        
        if response.status_code != 200:
            print(f"❌ Upload request failed: {response.text}")
            return None
        
        data = response.json()
        
        if data.get('statusCode') != 2000:
            print(f"❌ LightX error: {data.get('message')}")
            return None
        
        upload_url = data['body']['uploadImage']
        image_url = data['body']['imageUrl']
        
        print(f">>> [STEP 1.1] Uploading to S3: {upload_url[:80]}...")
        
        # Upload image to S3 using PUT
        put_headers = {"Content-Type": "image/jpeg"}
        put_response = requests.put(upload_url, headers=put_headers, data=image_bytes, timeout=60)
        
        if put_response.status_code != 200:
            print(f"❌ S3 upload failed: {put_response.status_code}")
            return None
        
        print(f"✅ Image uploaded! URL: {image_url}")
        return image_url
        
    except Exception as e:
        print(f"❌ Exception during upload: {e}")
        traceback.print_exc()
        return None

# ==============================================================================
# 4. HELPER: LIGHTX V2 - GENERATE HAIRSTYLE
# ==============================================================================
def generate_hairstyle(image_url, text_prompt):
    """
    Step 2: Generate hairstyle, dapat orderId
    """
    try:
        print(f">>> [STEP 2] Generating hairstyle...")
        print(f">>> Prompt: {text_prompt}")
        
        headers = {
            "Content-Type": "application/json",
            "x-api-key": LIGHTX_API_KEY
        }
        
        payload = {
            "imageUrl": image_url,
            "textPrompt": text_prompt
        }
        
        response = requests.post(HAIRSTYLE_URL, headers=headers, json=payload, timeout=30)
        
        if response.status_code != 200:
            print(f"❌ Hairstyle request failed: {response.text}")
            return None
        
        data = response.json()
        
        if data.get('statusCode') != 2000:
            print(f"❌ LightX error: {data.get('message')}")
            return None
        
        order_id = data['body']['orderId']
        print(f"✅ Order created: {order_id}")
        
        return order_id
        
    except Exception as e:
        print(f"❌ Exception during generation: {e}")
        traceback.print_exc()
        return None

# ==============================================================================
# 5. HELPER: LIGHTX V2 - CHECK STATUS
# ==============================================================================
def check_order_status(order_id, max_retries=5):
    """
    Step 3: Check status berkala sampai 'active'
    """
    try:
        print(f">>> [STEP 3] Checking order status...")
        
        headers = {
            "Content-Type": "application/json",
            "x-api-key": LIGHTX_API_KEY
        }
        
        payload = {"orderId": order_id}
        
        for attempt in range(max_retries):
            print(f">>> Retry {attempt + 1}/{max_retries}...")
            
            response = requests.post(STATUS_URL, headers=headers, json=payload, timeout=30)
            
            if response.status_code != 200:
                print(f"⚠️ Status check failed: {response.text}")
                time.sleep(3)
                continue
            
            data = response.json()
            
            if data.get('statusCode') != 2000:
                print(f"⚠️ Error: {data.get('message')}")
                time.sleep(3)
                continue
            
            status = data['body']['status']
            print(f">>> Status: {status}")
            
            if status == 'active':
                output_url = data['body']['output']
                print(f"✅ Generation complete! URL: {output_url}")
                return output_url
            elif status == 'failed':
                print(f"❌ Generation failed")
                return None
            
            # Status masih 'init', tunggu 3 detik
            time.sleep(3)
        
        print(f"❌ Timeout after {max_retries} retries")
        return None
        
    except Exception as e:
        print(f"❌ Exception during status check: {e}")
        traceback.print_exc()
        return None

# ==============================================================================
# 6. ENDPOINT: EDIT STYLE (UPDATED FOR V2)
# ==============================================================================
@style_bp.route('/edit-style', methods=['POST'], strict_slashes=False)
def edit_style():
    print(f"\n{'='*70}")
    print(f">>> [AI GEN] LightX API v2 - Edit Style Request")
    print(f"{'='*70}")
    
    try:
        data = request.json
        
        original_base64 = data.get('image_base64')
        ui_value = data.get('value') 
        if not ui_value:
            ui_value = data.get('style_name')

        if not original_base64 or not ui_value:
            return jsonify({
                "status": "error", 
                "message": "Data tidak lengkap (perlu image_base64 dan value)"
            }), 400

        print(f">>> Received style value: {ui_value}")

        # Decode Base64 ke bytes
        if "," in original_base64:
            original_base64 = original_base64.split(",")[1]
        
        image_bytes = base64.b64decode(original_base64)
        
        # Normalisasi prompt
        normalized_key = ui_value.lower().replace(" ", "_")
        text_prompt = STYLES_DB.get(normalized_key, f"{ui_value} hairstyle")
        final_prompt = f"{text_prompt}, photorealistic, 8k, highly detailed"
        
        # === STEP 1: Upload Image ===
        image_url = upload_image_to_lightx(image_bytes)
        if not image_url:
            return jsonify({
                "status": "error", 
                "message": "Gagal upload image ke LightX"
            }), 500
        
        # === STEP 2: Generate Hairstyle ===
        order_id = generate_hairstyle(image_url, final_prompt)
        if not order_id:
            return jsonify({
                "status": "error", 
                "message": "Gagal generate hairstyle"
            }), 500
        
        # === STEP 3: Check Status (Polling) ===
        output_url = check_order_status(order_id)
        if not output_url:
            return jsonify({
                "status": "error", 
                "message": "Gagal mendapatkan hasil (timeout atau failed)"
            }), 500
        
        # === Download Result & Convert to Base64 ===
        print(f">>> Downloading result from: {output_url}")
        result_response = requests.get(output_url, timeout=30)
        result_b64 = base64.b64encode(result_response.content).decode('utf-8')
        final_b64 = f"data:image/jpeg;base64,{result_b64}"
        
        print(f"✅ SUCCESS! Hairstyle generation complete.")
        
        return jsonify({
            "status": "success", 
            "image_result": final_b64,
            "type": "base64",
            "message": "AI styling berhasil!"
        }), 200

    except Exception as e:
        print(f"\n❌ Error Backend:")
        print(traceback.format_exc())
        return jsonify({
            "status": "error", 
            "message": f"Server Error: {str(e)}"
        }), 500


# ==============================================================================
# 7. ENDPOINT LAINNYA (ANALYZE & CHAT)
# ==============================================================================
@style_bp.route('/analyze', methods=['POST'], strict_slashes=False)
def analyze():
    print("\n>>> [API] Request Analyze Masuk! <<<")
    try:
        if 'image' not in request.files: 
            return jsonify({"status": "error", "message": "No image file"}), 400
            
        file = request.files['image']
        user_id = request.form.get('user_id', 'anonymous')
        gender = request.form.get('gender', 'Pria')
        
        img_bytes = file.read()
        res = ai_service.analyze_face(img_bytes) 
        if not res: 
            return jsonify({"status": "error", "message": "Face analysis failed"}), 400
        
        nparr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        img_base64 = ""
        if img is not None:
            h, w = img.shape[:2]
            new_w = 400
            new_h = int(h * (new_w / w))
            resized = cv2.resize(img, (new_w, new_h))
            _, buf = cv2.imencode('.jpg', resized, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
            img_base64 = base64.b64encode(buf).decode('utf-8')
            
        raw_recs = res['recommendations']
        recs = raw_recs.split(", ") if gender in ['Pria', 'Laki-laki'] else ["Long Layer Cut", "Bob Cut"]
        
        now = datetime.datetime.now()
        db_data = {
            "userId": user_id, 
            "gender": gender, 
            "face_shape": res['face_shape'], 
            "confidence": res['confidence'], 
            "timestamp": now, 
            "recommendations": recs, 
            "photo_base64": img_base64
        }
        db.collection('style_history').add(db_data)
        
        resp = db_data.copy()
        resp['timestamp'] = now.isoformat()
        return jsonify({"status": "success", "data": resp}), 200
        
    except Exception as e:
        print(f"❌ Error Analyze: {e}")
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500

@style_bp.route('/chat', methods=['POST'], strict_slashes=False)
def chat():
    try:
        msg = request.json.get('message', '')
        res = requests.post(
            "http://localhost:11434/api/generate", 
            json={"model": "llama3.2:1b", "prompt": f"Jawab: {msg}", "stream": False}, 
            timeout=60
        )
        return jsonify({
            "status": "success", 
            "reply": res.json().get('response', 'Error')
        })
    except Exception as e:
        print(f"❌ Error Chat: {e}")
        return jsonify({"status": "error", "reply": "Chat service unavailable"}), 500