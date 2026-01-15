# =========================
# IMPORT LIBRARY
# =========================

from flask import (
    Blueprint,          # Untuk membuat blueprint Flask
    request,            # Mengambil data request (form, query, dll)
    redirect,           # Redirect ke endpoint lain
    url_for,            # Generate URL endpoint
    flash,              # Flash message (alert)
    render_template     # Render file HTML (Jinja2)
)
from flask_login import (
    login_user,         # Login user ke session
    logout_user,        # Logout user
    login_required,     # Proteksi route (harus login)
    current_user        # User yang sedang login
)
from app.extensions import db, bcrypt   # Firestore DB & bcrypt
from app.models.user import User        # Model User untuk Flask-Login
from firebase_admin import firestore    # Firestore query (order_by)
import collections                      # Untuk Counter (chart)


# =========================
# BLUEPRINT ADMIN
# =========================

# Blueprint admin dengan prefix /admin
admin_bp = Blueprint('admin_bp', __name__, url_prefix='/admin')


# =========================================================
# 1. LOGIN ADMIN
# =========================================================
@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    # Jika admin sudah login, langsung ke dashboard
    if current_user.is_authenticated:
        return redirect(url_for('admin_bp.dashboard'))

    # Jika request POST (submit form login)
    if request.method == 'POST':

        # Ambil data dari form
        email = request.form.get('username')
        password = request.form.get('password')
        
        # Query Firestore untuk mencari user berdasarkan email
        users_ref = db.collection('users').where('email', '==', email).limit(1).stream()

        # Ambil dokumen pertama (jika ada)
        user_doc = next(users_ref, None)

        # Jika user ditemukan
        if user_doc:
            data = user_doc.to_dict()

            # Cek password hash dan validasi password
            if data.get('password_hash') and bcrypt.check_password_hash(data['password_hash'], password):
                
                # Ambil role user
                raw_role = data.get('role', 'USER')

                # Normalisasi role (uppercase & trim)
                clean_role = str(raw_role).upper().strip()

                # Debug log
                print(f"[DEBUG] Login Email: {email}, Role: {clean_role}")

                # Hanya ADMIN yang boleh login
                if clean_role == 'ADMIN':

                    # Buat object User untuk Flask-Login
                    user_obj = User(
                        user_doc.id,              # ID dokumen Firestore
                        data['email'],            # Email user
                        data.get('full_name', 'Admin'),
                        clean_role                # Role
                    )

                    # Login user ke session
                    login_user(user_obj)

                    # Redirect ke dashboard admin
                    return redirect(url_for('admin_bp.dashboard'))
                else:
                    flash(f"Gagal! Role Anda '{raw_role}'. Harusnya 'ADMIN'", "danger")
            else:
                flash("Password salah!", "danger")
        else:
            flash("Email tidak ditemukan!", "danger")
    
    # Render halaman login admin
    return render_template('admin_login.html')


# =========================================================
# 2. DASHBOARD ADMIN
# =========================================================
@admin_bp.route('/dashboard')
@login_required
def dashboard():
    # Ambil semua user
    users_ref = db.collection('users').stream()

    # Ambil semua history
    history_ref = db.collection('history').stream()

    # Ambil semua feedback
    feedback_ref = db.collection('feedbacks').stream()

    # Convert ke list dictionary
    users_list = [u.to_dict() for u in users_ref]
    histories_list = [h.to_dict() for h in history_ref]
    feedbacks_list = [f.to_dict() for f in feedback_ref]

    # Hitung total data
    total_users = len(users_list)
    total_styles = len(histories_list)
    total_feedbacks = len(feedbacks_list)

    # Hitung rata-rata rating
    avg_rating = 0
    if total_feedbacks > 0:
        total_stars = sum([f.get('rating', 0) for f in feedbacks_list])
        avg_rating = round(total_stars / total_feedbacks, 1)

    # Hitung jumlah feedback per rating (1–5)
    rating_counts = collections.Counter([f.get('rating', 0) for f in feedbacks_list])

    # Data chart feedback (rating 1–5)
    chart_feedback_data = [rating_counts.get(i, 0) for i in range(1, 6)]
    
    # Dummy data chart user (contoh)
    chart_user_labels = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
    chart_user_data = [2, 5, 3, 8, 12, 15, 20] 

    # Render dashboard dengan data
    return render_template(
        'dashboard.html', 
        current_user=current_user,
        t_users=total_users, 
        t_styles=total_styles, 
        t_feedbacks=total_feedbacks,
        avg_rating=avg_rating,
        c_feed_data=chart_feedback_data,
        c_user_labels=chart_user_labels,
        c_user_data=chart_user_data
    )


# =========================================================
# 3. LIST FEEDBACK
# =========================================================
@admin_bp.route('/feedbacks')
@login_required
def feedback_list():

    # Ambil feedback dengan urutan terbaru
    docs = db.collection('feedbacks') \
             .order_by('created_at', direction=firestore.Query.DESCENDING) \
             .stream()
    
    feedbacks_data = []

    # Loop semua feedback
    for doc in docs:
        d = doc.to_dict()

        # Simpan ID dokumen (penting untuk delete)
        d['id'] = doc.id
        
        # Format tanggal
        if d.get('created_at'):
            d['date_str'] = d['created_at'].strftime("%d %b %Y, %H:%M")
        else:
            d['date_str'] = "-"

        feedbacks_data.append(d)

    # Render halaman feedback
    return render_template('feedbacks.html', feedbacks=feedbacks_data)


# =========================================================
# 4. LIST USER
# =========================================================
@admin_bp.route('/users')
@login_required
def user_list():
    # Ambil semua user
    users_ref = db.collection('users').stream()
    users_data = []
    
    for doc in users_ref:
        d = doc.to_dict()

        # Simpan UID dokumen
        d['uid'] = doc.id
        
        # Format tanggal join
        if d.get('created_at'):
            d['join_date'] = d['created_at'].strftime("%d %b %Y")
        else:
            d['join_date'] = "-"
            
        users_data.append(d)

    # Render halaman users
    return render_template('users.html', users=users_data)


# =========================================================
# 5. DELETE FEEDBACK
# =========================================================
@admin_bp.route('/feedback/delete/<id>')
@login_required
def delete_feedback(id):
    try:
        # Hapus feedback berdasarkan ID
        db.collection('feedbacks').document(id).delete()
        flash('Feedback berhasil dihapus.', 'success')
    except Exception as e:
        flash(f'Gagal menghapus: {e}', 'danger')
        
    return redirect(url_for('admin_bp.feedback_list'))


# =========================================================
# 6. DELETE USER
# =========================================================
@admin_bp.route('/user/delete/<uid>')
@login_required
def delete_user(uid):

    # Cegah admin menghapus dirinya sendiri
    if uid == current_user.id:
        flash('Tidak bisa menghapus akun sendiri!', 'danger')
        return redirect(url_for('admin_bp.user_list'))

    try:
        # Hapus user dari Firestore
        db.collection('users').document(uid).delete()
        flash('User berhasil dihapus.', 'success')
    except Exception as e:
        flash(f'Gagal menghapus user: {e}', 'danger')

    return redirect(url_for('admin_bp.user_list'))


# =========================================================
# 7. LOGOUT ADMIN
# =========================================================
@admin_bp.route('/logout')
@login_required
def logout():
    # Logout session admin
    logout_user()

    # Redirect ke halaman login admin
    return redirect(url_for('admin_bp.login'))
