import cv2
import mediapipe as mp
import numpy as np
import base64
import os
import math

class EditService:
    def __init__(self):
        # Segmentasi selfie Mediapipe:
        # digunakan untuk memisahkan bagian tubuh/ rambut dari background
        self.mp_selfie = mp.solutions.selfie_segmentation
        self.segment = self.mp_selfie.SelfieSegmentation(model_selection=1)
        
        # Face Mesh Mediapipe:
        # memberikan koordinat titik wajah (468 landmark) untuk presisi posisi stiker
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            static_image_mode=True, 
            max_num_faces=1, 
            refine_landmarks=True
        )

    # --- Utility: decode base64 → cv2 image ---
    def decode_image(self, base64_string):
        try:
            decoded_data = base64.b64decode(base64_string)
            np_data = np.frombuffer(decoded_data, np.uint8)
            return cv2.imdecode(np_data, cv2.IMREAD_COLOR)
        except:
            return None

    # --- Utility: encode cv2 image → base64 untuk dikirim ke frontend ---
    def encode_image(self, image):
        try:
            _, buffer = cv2.imencode('.jpg', image, [cv2.IMWRITE_JPEG_QUALITY, 90])
            return base64.b64encode(buffer).decode('utf-8')
        except:
            return ""

    # --- 1. GANTI WARNA RAMBUT SECARA NATURAL (via HSV + Masking) ---
    def apply_hair_color(self, image, hex_color):
        try:
            # Konversi hex → RGB → BGR (OpenCV default)
            hex_color = hex_color.lstrip('#')
            rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
            target_bgr = np.array([rgb[2], rgb[1], rgb[0]], dtype=np.uint8)

            img_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            h, w, _ = image.shape

            # Segmentasi tubuh (mask tubuh)
            seg_results = self.segment.process(img_rgb)
            body_mask = seg_results.segmentation_mask > 0.4

            # Face mesh untuk membuat perisai wajah (agar warna tidak kena muka/baju)
            face_results = self.face_mesh.process(img_rgb)
            face_shield = np.zeros((h, w), dtype=np.uint8)
            
            if face_results.multi_face_landmarks:
                landmarks = face_results.multi_face_landmarks[0].landmark
                
                # Outline wajah (menghindari alis, mata, kulit, baju)
                face_outline = [
                    10, 338, 297, 332, 284, 251, 389, 356, 454,
                    323, 361, 288, 397, 365, 379, 378, 400, 377,
                    152, 148, 176, 149, 150, 136, 172, 58, 132,
                    93, 234, 127, 162, 21, 54, 103, 67, 109
                ]

                pts = np.array([[landmarks[idx].x * w, landmarks[idx].y * h] for idx in face_outline], np.int32)
                cv2.fillPoly(face_shield, [pts], 255)

                # Tutup area bawah agar baju tidak kena
                chin_y = int(landmarks[152].y * h)
                face_shield[chin_y:h, :] = 255

            # Rambut = tubuh - wajah/baju
            hair_mask = np.logical_and(body_mask, np.logical_not(face_shield > 0))

            # Gunakan HSV agar highlight & tekstur rambut tidak hilang
            hsv_img = cv2.cvtColor(image, cv2.COLOR_BGR2HSV).astype(np.float32)
            target_hsv = cv2.cvtColor(np.full((1,1,3), target_bgr, dtype=np.uint8), cv2.COLOR_BGR2HSV)[0][0]

            # H = hue (ubah warna), S = saturation (atur vividness)
            hsv_img[hair_mask, 0] = target_hsv[0]
            hsv_img[hair_mask, 1] = target_hsv[1] * 0.7

            colored_img = cv2.cvtColor(hsv_img.astype(np.uint8), cv2.COLOR_HSV2BGR)

            # Soft blending agar transisi rambut → kulit lebih halus
            mask_float = hair_mask.astype(float)
            mask_float = cv2.GaussianBlur(mask_float, (15, 15), 0)
            
            for c in range(3):
                image[:, :, c] = image[:, :, c] * (1 - mask_float) + colored_img[:, :, c] * mask_float

            return image.astype(np.uint8)

        except:
            return image

    # --- 2. TEMPEL RAMBUT/HIJAB/KACAMATA DENGAN ROTASI & SKALA PRESISI ---
    def apply_overlay(self, image, category, asset_name):
        try:
            # Baca asset PNG yang sudah ada alpha channel
            asset_path = os.path.join('assets', category, f"{asset_name}.png")
            overlay = cv2.imread(asset_path, cv2.IMREAD_UNCHANGED)
            if overlay is None:
                return image

            h_img, w_img, _ = image.shape
            results = self.face_mesh.process(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
            if not results.multi_face_landmarks:
                return image

            landmarks = results.multi_face_landmarks[0].landmark

            # Hitung rotasi kepala berdasarkan kedua mata
            p_left_eye = landmarks[33]
            p_right_eye = landmarks[263]
            dy = (p_right_eye.y - p_left_eye.y) * h_img
            dx = (p_right_eye.x - p_left_eye.x) * w_img
            angle = math.degrees(math.atan2(dy, dx))

            # Hitung skala berdasarkan lebar wajah (pipi kiri → pipi kanan)
            p_l_pipi = landmarks[234]
            p_r_pipi = landmarks[454]
            face_width = math.dist(
                (p_l_pipi.x * w_img, p_l_pipi.y * h_img),
                (p_r_pipi.x * w_img, p_r_pipi.y * h_img)
            )

            # Default scale berdasarkan kategori
            scale = 1.9 if category == 'hijab' else 1.25
            if category == 'glasses':
                scale = 0.9

            w_new = int(face_width * scale)
            h_new = int(w_new * overlay.shape[0] / overlay.shape[1])

            # Rotasi stiker mengikuti rotasi kepala
            M = cv2.getRotationMatrix2D((overlay.shape[1]/2, overlay.shape[0]/2), -angle, 1)
            rotated = cv2.warpAffine(overlay, M, (overlay.shape[1], overlay.shape[0]), flags=cv2.INTER_CUBIC)

            # Resize stiker
            resized = cv2.resize(rotated, (w_new, h_new))

            # Anchor point:
            # rambut/hijab → dahi (id landmark 10)
            # kacamata → pangkal hidung (id landmark 6)
            anchor = landmarks[10] if category != 'glasses' else landmarks[6]
            cx, cy = int(anchor.x * w_img), int(anchor.y * h_img)

            x1 = cx - int(w_new / 2)
            # Y offset agar rambut tidak turun ke alis
            y_off = int(h_new * 0.48) if category != 'glasses' else int(h_new / 2)
            y1 = cy - y_off

            return self.soft_alpha_blend(image, resized, x1, y1)

        except:
            return image

    # --- 3. Soft Alpha Blend (anti-edge patchy) ---
    def soft_alpha_blend(self, background, overlay, x, y):
        bh, bw, _ = background.shape
        oh, ow, _ = overlay.shape

        # Cek bounding agar overlay tidak keluar frame
        x_s, y_s = max(0, x), max(0, y)
        x_e, y_e = min(bw, x + ow), min(bh, y + oh)
        ox_s, oy_s = max(0, -x), max(0, -y)
        ox_e, oy_e = ox_s + (x_e - x_s), oy_s + (y_e - y_s)

        if x_s >= x_e or y_s >= y_e:
            return background

        region = background[y_s:y_e, x_s:x_e]
        sticker = overlay[oy_s:oy_e, ox_s:ox_e]

        # Channel alpha PNG → transisi halus
        alpha = sticker[:, :, 3] / 255.0
        alpha = cv2.GaussianBlur(alpha, (3, 3), 0)
        
        for c in range(3):
            region[:, :, c] = alpha * sticker[:, :, c] + (1 - alpha) * region[:, :, c]

        background[y_s:y_e, x_s:x_e] = region
        return background
