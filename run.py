from app import create_app, socketio

app = create_app()

if __name__ == '__main__':
    print("Membuka server MyHeadStyle di port 5000...")
    # host 0.0.0.0 agar bisa diakses dari Flutter dalam 1 wifi
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)