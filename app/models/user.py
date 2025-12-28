from flask_login import UserMixin
from app.extensions import login_manager, db

class User(UserMixin):
    def __init__(self, user_id, email, full_name, role):
        self.id = user_id
        self.email = email
        self.full_name = full_name
        self.role = role

@login_manager.user_loader
def load_user(user_id):
    u = db.collection('users').document(user_id).get()
    if u.exists:
        data = u.to_dict()
        return User(u.id, data['email'], data['full_name'], data['role'])
    return None