from app.extensions import socketio
from flask import request

@socketio.on('webrtc_signal')
def handle_webrtc(data):
    room = data.get('room')
    socketio.emit('webrtc_signal', data, room=room, include_self=False)

@socketio.on('join_room')
def on_join(data):
    room = data.get('room')
    socketio.server.enter_room(request.sid, room)
    print(f"User masuk ke room video call: {room}")