from app import create_app, socketio

app = create_app()

if __name__ == '__main__':
    # --- TAMBAHKAN KODE INI UNTUK CEK ALAMAT ---
    with app.app_context():
        print("\n=== DAFTAR ALAMAT API YANG AKTIF ===")
        for rule in app.url_map.iter_rules():
            # Kita cari yang ada kata 'chat'
            if 'chat' in rule.rule or 'style' in rule.rule:
                print(f"✅ Alamat: {rule.rule} --> Fungsi: {rule.endpoint}")
        print("====================================\n")
    # ------------------------------------------

    print("Membuka server MyHeadStyle di port 5000...")
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)