from app import create_app
from app.extensions import db, bcrypt

# Inisialisasi aplikasi agar bisa konek ke Firebase
app = create_app()

with app.app_context():
    # Data Admin yang ingin dibuat
    email = "admin@myheadstyle.com"
    password = "admin123" 
    
    # Enkripsi password agar aman
    hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')
    
    admin_data = {
        "full_name": "Super Admin MyHeadStyle",
        "email": email,
        "password_hash": hashed_pw,
        "role": "ADMIN"
    }
    
    # Masukkan data ke koleksi 'users' di Firestore
    # Kita pakai document email agar tidak duplikat
    db.collection('users').document(email).set(admin_data)
    
    print("\n" + "="*30)
    print("✅ Akun Admin Berhasil Dibuat!")
    print(f"📧 Email: {email}")
    print(f"🔑 Password: {password}")
    print("="*30)