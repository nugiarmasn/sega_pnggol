from app.extensions import socketio
from flask import request

# Event WebRTC signaling untuk mengirimkan offer/answer/ICE candidate antar client
@socketio.on('webrtc_signal')
def handle_webrtc(data):
    room = data.get('room')
    
    # Emit ke pengguna lain dalam room (include_self=False agar tidak kembali ke pengirim)
    socketio.emit('webrtc_signal', data, room=room, include_self=False)

# Event untuk join ke room tertentu
@socketio.on('join_room')
def on_join(data):
    room = data.get('room')
    
    # Memasukkan user ke room via socket session ID
    socketio.server.enter_room(request.sid, room)

    # Logging untuk debugging
    print(f"User masuk ke room video call: {room}")
