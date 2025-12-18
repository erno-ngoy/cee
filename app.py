from flask import Flask, render_template, request, redirect, send_file
import psycopg2 # Pour PostgreSQL
from psycopg2.extras import RealDictCursor
import io
import os
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
auth = HTTPBasicAuth()

# =========================
# SÉCURITÉ ADMIN
# =========================
users_auth = {
    "admin": generate_password_hash("esi-echecs-2025")
}

@auth.verify_password
def verify_password(username, password):
    if username in users_auth and check_password_hash(users_auth.get(username), password):
        return username

# =========================
# CONNEXION POSTGRESQL
# =========================
def get_db_connection():
    # Railway injecte DATABASE_URL automatiquement
    url = os.environ.get('DATABASE_URL')
    return psycopg2.connect(url)

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    # Note : On utilise SERIAL pour l'auto-incrément au lieu de INTEGER PRIMARY KEY AUTOINCREMENT
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            user_id TEXT UNIQUE,
            nom TEXT,
            postnom TEXT,
            prenom TEXT,
            telephone TEXT,
            promotion TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# =========================
# ROUTES
# =========================
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        nom = request.form['nom'].upper()
        postnom = request.form['postnom']
        prenom = request.form['prenom']
        telephone = request.form['telephone']
        promotion = request.form['promotion']

        conn = get_db_connection()
        c = conn.cursor()

        c.execute("SELECT COUNT(*) FROM users WHERE promotion = %s", (promotion,))
        count = c.fetchone()[0] + 1
        numero = str(count).zfill(3)
        user_id = f"{promotion}-{nom}-{numero}"

        try:
            c.execute("""
                INSERT INTO users (user_id, nom, postnom, prenom, telephone, promotion)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (user_id, nom, postnom, prenom, telephone, promotion))
            conn.commit()
        except Exception as e:
            return f"Erreur : {e}"
        finally:
            conn.close()

        return f"<h3>Inscription réussie ✔</h3><p>ID : <b>{user_id}</b></p><a href='/'>Retour</a>"

    return render_template('index.html')

@app.route('/admin')
@auth.login_required
def admin():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM users")
    users = c.fetchall()
    conn.close()
    return render_template('admin.html', users=users)

@app.route('/delete/<int:id>')
@auth.login_required
def delete(id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE id = %s", (id,))
    conn.commit()
    conn.close()
    return redirect('/admin')

@app.route('/export_pdf')
@auth.login_required
def export_pdf():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT user_id, nom, postnom, prenom, telephone, promotion FROM users")
    users = c.fetchall()
    conn.close()

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    y = 800
    pdf.drawString(40, y, "LISTE DES INSCRITS")
    y -= 30
    for u in users:
        pdf.drawString(40, y, f"{u[0]} | {u[1]} {u[2]} | {u[5]}")
        y -= 20
    pdf.save()
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name="liste.pdf", mimetype="application/pdf")

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)