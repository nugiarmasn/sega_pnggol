import os
import cv2
import numpy as np
import tensorflow as tf

class AIService:
    def __init__(self):
        self.model_path = "/home/nugi/ai-stylish-backend/app/model_ai/"
        # Sesuai abjad dari flow_from_directory: Oval, Round, Square
        self.class_names = ['Oval', 'Round', 'Square']
        self.interpreter = None

        try:
            tflite_file = os.path.join(self.model_path, "face_shape_model.tflite")
            self.interpreter = tf.lite.Interpreter(model_path=tflite_file)
            self.interpreter.allocate_tensors()
            self.input_details = self.interpreter.get_input_details()
            self.output_details = self.interpreter.get_output_details()
            print("✅ Model TFLite Sinkron dengan Colab!")
        except Exception as e:
            print(f"❌ Error: {e}")

    def analyze_face(self, img_bytes):
        try:
            nparr = np.frombuffer(img_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is None: return None

            face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            # Gunakan scaleFactor 1.3 dan minNeighbors 5 agar lebih akurat
            faces = face_cascade.detectMultiScale(gray, 1.3, 5)

            if len(faces) == 0: return None

            # CROP DENGAN PADDING LEBIH LUAS (20%) agar rahang Square terlihat
            (x, y, w, h) = faces[0]
            offset_w = int(w * 0.2)
            offset_h = int(h * 0.2)
            x1 = max(0, x - offset_w)
            y1 = max(0, y - offset_h)
            x2 = min(img.shape[1], x + w + offset_w)
            y2 = min(img.shape[0], y + h + offset_h)
            
            face_img = img[y1:y2, x1:x2]
            face_rgb = cv2.cvtColor(face_img, cv2.COLOR_BGR2RGB)
            face_resized = cv2.resize(face_rgb, (224, 224))

            # --- PERBAIKAN PENTING DISINI ---
            # JANGAN dibagi 255.0 karena di Colab Anda tidak pakai rescale
            img_array = np.expand_dims(face_resized, axis=0).astype('float32') 
            # --------------------------------

            self.interpreter.set_tensor(self.input_details[0]['index'], img_array)
            self.interpreter.invoke()
            prediction = self.interpreter.get_tensor(self.output_details[0]['index'])[0]

            idx = np.argmax(prediction)
            shape = self.class_names[idx]
            
            # Ambil semua skor untuk analisa
            all_scores = {
                self.class_names[i]: f"{round(float(prediction[i] * 100), 2)}%"
                for i in range(len(self.class_names))
            }

            recs_map = {
                "Oval": "Undercut, Pompadour, Side Part",
                "Round": "Faux Hawk, High Fade, Quiff",
                "Square": "Buzz Cut, Crew Cut, Slicked Back"
            }

            return {
                "face_shape": shape,
                "confidence": f"{round(float(prediction[idx] * 100), 2)}%",
                "all_scores": all_scores,
                "recommendations": recs_map.get(shape, "Gaya Standar")
            }
        except Exception as e:
            print(f"Error: {e}")
            return None

ai_service = AIService()