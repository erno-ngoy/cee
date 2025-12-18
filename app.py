from flask import Flask, render_template, request, redirect, send_file
import psycopg2
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
    if username in users_auth and \
            check_password_hash(users_auth.get(username), password):
        return username


# =========================
# CONNEXION POSTGRESQL
# =========================
def get_db_connection():
    # Railway injecte l'url dans DATABASE_URL
    url = os.environ.get('DATABASE_URL')

    # Si Railway ne la trouve pas, on utilise l'url en dur (fallback)
    if not url:
        url = "postgresql://postgres:xwpTRSXROyoktPEmOiswTYAeJrDkRJJw@postgres.railway.internal:5432/railway"

    # Correction indispensable : postgres:// doit être postgresql:// pour Python
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)

    return psycopg2.connect(url)


def init_db():
    try:
        conn = get_db_connection()
        c = conn.cursor()
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
        print("Base de données initialisée avec succès.")
    except Exception as e:
        print(f"Erreur lors de l'initialisation de la DB : {e}")


# Initialisation forcée au démarrage
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

        try:
            conn = get_db_connection()
            c = conn.cursor()

            # Compter pour générer le numéro (ex: 001, 002)
            c.execute("SELECT COUNT(*) FROM users WHERE promotion = %s", (promotion,))
            count = c.fetchone()[0] + 1
            numero = str(count).zfill(3)
            user_id = f"{promotion}-{nom}-{numero}"

            c.execute("""
                INSERT INTO users (user_id, nom, postnom, prenom, telephone, promotion)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (user_id, nom, postnom, prenom, telephone, promotion))

            conn.commit()
            conn.close()
            return f"<h3>Inscription réussie ✔</h3><p>ID : <b>{user_id}</b></p><a href='/'>Retour</a>"
        except Exception as e:
            return f"Erreur base de données : {e}"

    return render_template('index.html')


@app.route('/admin')
@auth.login_required
def admin():
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM users ORDER BY id DESC")
        users = c.fetchall()
        conn.close()
        return render_template('admin.html', users=users)
    except Exception as e:
        return f"Erreur Admin : {e}"


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
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(50, y, "LISTE DES INSCRITS - CLUB ECHECS ESI")
    y -= 40
    pdf.setFont("Helvetica", 10)

    for u in users:
        pdf.drawString(50, y, f"{u[0]} | {u[1]} {u[2]} | {u[5]} | Tel: {u[4]}")
        y -= 20
        if y < 50:
            pdf.showPage()
            y = 800

    pdf.save()
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name="liste_club.pdf", mimetype="application/pdf")


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)