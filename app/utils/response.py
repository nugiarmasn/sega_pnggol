from flask import jsonify

def success(data=None, message="Success", status_code=200):
    return jsonify({"status": status_code, "message": message, "data": data}), status_code

def error(message="Error", status_code=400):
    return jsonify({"status": status_code, "message": message, "data": None}), status_codeapp/routes/admin_routes.py