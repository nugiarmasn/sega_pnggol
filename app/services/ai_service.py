import os
import cv2
import numpy as np
import tensorflow as tf

class AIService:
    def __init__(self):
        # --- AMBIL PATH FOLDER SAAT INI (app/services) ---
        current_file_path = os.path.dirname(os.path.abspath(__file__))

        # --- NAIK SATU LEVEL KE FOLDER 'app' ---
        app_dir = os.path.dirname(current_file_path)

        # --- GABUNGKAN DENGAN FOLDER MODEL (cross platform Windows/Linux) ---
        self.model_path = os.path.join(app_dir, 'model_ai')
        
        # Label hasil prediksi bentuk wajah
        self.class_names = ['Oval', 'Round', 'Square']
        self.interpreter = None

        print(f"DEBUG: Mencari model di: {self.model_path}")

        try:
            # Path file model TFLite
            tflite_file = os.path.join(self.model_path, "face_shape_model.tflite")
            
            # Cek apakah model benar-benar ada
            if not os.path.exists(tflite_file):
                print(f"❌ ERROR: File {tflite_file} tidak ditemukan!")
            else:
                # Load dan inisialisasi interpreter TFLite
                self.interpreter = tf.lite.Interpreter(model_path=tflite_file)
                self.interpreter.allocate_tensors()

                # Ambil detail input dan output model
                self.input_details = self.interpreter.get_input_details()
                self.output_details = self.interpreter.get_output_details()
                print("✅ Model TFLite Berhasil Dimuat!")
        except Exception as e:
            print(f"❌ Error saat inisialisasi AI: {e}")


    def analyze_face(self, img_bytes):
        try:
            # Convert bytes → np array → OpenCV image
            nparr = np.frombuffer(img_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is None:
                return None

            # Deteksi wajah menggunakan Haar Cascade
            face_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            )
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, 1.3, 5)

            if len(faces) == 0:
                return None  # Tidak ada wajah ditemukan

            # Ambil wajah pertama
            (x, y, w, h) = faces[0]

            # Tambah offset agar framing lebih luas (lebih natural)
            offset_w = int(w * 0.2)
            offset_h = int(h * 0.2)

            x1 = max(0, x - offset_w)
            y1 = max(0, y - offset_h)
            x2 = min(img.shape[1], x + w + offset_w)
            y2 = min(img.shape[0], y + h + offset_h)
            
            # Crop wajah
            face_img = img[y1:y2, x1:x2]

            # Konversi BGR → RGB (sesuai input training model)
            face_rgb = cv2.cvtColor(face_img, cv2.COLOR_BGR2RGB)

            # Resize sesuai input model EfficientNet
            face_resized = cv2.resize(face_rgb, (224, 224))

            # Tidak dibagi 255 karena EfficientNet scaling internal
            img_array = np.expand_dims(face_resized, axis=0).astype('float32')

            # Set input ke model
            self.interpreter.set_tensor(
                self.input_details[0]['index'], img_array
            )
            self.interpreter.invoke()

            # Ambil hasil output
            prediction = self.interpreter.get_tensor(
                self.output_details[0]['index']
            )[0]

            # Ambil kelas dengan skor tertinggi
            idx = np.argmax(prediction)
            shape = self.class_names[idx]
            
            # Buat output untuk semua skor (dalam %)
            all_scores = {
                self.class_names[i]: f"{round(float(prediction[i] * 100), 2)}%"
                for i in range(len(self.class_names))
            }

            # Rekomendasi gaya rambut berdasarkan bentuk wajah
            recs_map = {
                "Oval": "Undercut, Pompadour, Side Part",
                "Round": "Faux Hawk, High Fade, Quiff",
                "Square": "Buzz Cut, Crew Cut, Slicked Back"
            }

            return {
                "face_shape": shape,
                "confidence": f"{round(float(prediction[idx] * 100), 2)}%",
                "all_scores": all_scores,
                "recommendations": recs_map.get(shape, "Standar")
            }

        except Exception as e:
            print(f"❌ Error saat analisis wajah: {e}")
            return None

ai_service = AIService()
