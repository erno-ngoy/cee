from flask import Flask, render_template, request, redirect, send_file
import sqlite3
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
# Modifiez le mot de passe ici
users_auth = {
    "admin": generate_password_hash("esi-echecs-2025")
}

@auth.verify_password
def verify_password(username, password):
    if username in users_auth and \
            check_password_hash(users_auth.get(username), password):
        return username

# =========================
# INITIALISATION DE LA DB
# =========================
def init_db():
    conn = sqlite3.connect('inscriptions.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
# FORMULAIRE (PUBLIC)
# =========================
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        nom = request.form['nom'].upper()
        postnom = request.form['postnom']
        prenom = request.form['prenom']
        telephone = request.form['telephone']
        promotion = request.form['promotion']

        conn = sqlite3.connect('inscriptions.db')
        c = conn.cursor()

        c.execute("SELECT COUNT(*) FROM users WHERE promotion = ?", (promotion,))
        count = c.fetchone()[0] + 1
        numero = str(count).zfill(3)

        user_id = f"{promotion}-{nom}-{numero}"

        try:
            c.execute("""
                INSERT INTO users (user_id, nom, postnom, prenom, telephone, promotion)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, nom, postnom, prenom, telephone, promotion))
            conn.commit()
        except sqlite3.IntegrityError:
            return "Erreur : Cet utilisateur existe déjà."
        finally:
            conn.close()

        return f"<h3>Inscription réussie ✔</h3><p>ID : <b>{user_id}</b></p><a href='/'>Retour</a>"

    return render_template('index.html')

# =========================
# PAGE ADMIN (SÉCURISÉE)
# =========================
@app.route('/admin')
@auth.login_required
def admin():
    conn = sqlite3.connect('inscriptions.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users")
    users = c.fetchall()
    conn.close()
    return render_template('admin.html', users=users)

# =========================
# SUPPRIMER (SÉCURISÉ)
# =========================
@app.route('/delete/<int:id>')
@auth.login_required
def delete(id):
    conn = sqlite3.connect('inscriptions.db')
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return redirect('/admin')

# =========================
# EXPORT PDF (SÉCURISÉ)
# =========================
@app.route('/export_pdf')
@auth.login_required
def export_pdf():
    conn = sqlite3.connect('inscriptions.db')
    c = conn.cursor()
    c.execute("SELECT user_id, nom, postnom, prenom, telephone, promotion FROM users")
    users = c.fetchall()
    conn.close()

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(40, height - 40, "LISTE DES INSCRITS")
    pdf.setFont("Helvetica", 10)
    y = height - 70

    for u in users:
        line = f"{u[0]} | {u[1]} {u[2]} {u[3]} | {u[4]} | {u[5]}"
        pdf.drawString(40, y, line)
        y -= 15
        if y < 40:
            pdf.showPage()
            pdf.setFont("Helvetica", 10)
            y = height - 40

    pdf.save()
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name="liste_inscrits.pdf", mimetype="application/pdf")

# =========================
# LANCEMENT
# =========================
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)