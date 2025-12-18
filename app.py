from flask import Flask, render_template, request, redirect, send_file
import psycopg2
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
# Identifiants pour la page /admin
users_auth = {
    "admin": generate_password_hash("esi-echecs-2025")
}


@auth.verify_password
def verify_password(username, password):
    if username in users_auth and \
            check_password_hash(users_auth.get(username), password):
        return username


# =========================
# CONNEXION POSTGRESQL (CORRIGÉE)
# =========================
def get_db_connection():
    # Récupération de l'URL depuis les variables Railway
    url = os.environ.get('DATABASE_URL')

    if not url:
        raise ValueError("ERREUR : La variable DATABASE_URL est absente sur Railway.")

    # Correction pour les versions récentes de SQLAlchemy/psycopg2
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)

    return psycopg2.connect(url)


def init_db():
    try:
        conn = get_db_connection()
        c = conn.cursor()
        # Création de la table si elle n'existe pas
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
    except Exception as e:
        print(f"Erreur initialisation DB : {e}")


# Initialisation au démarrage
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

        # Calcul du numéro d'ordre
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
            return f"Erreur lors de l'inscription : {e}"
        finally:
            conn.close()

        return f"<h3>Inscription réussie ✔</h3><p>ID : <b>{user_id}</b></p><a href='/'>Retour</a>"

    return render_template('index.html')


@app.route('/admin')
@auth.login_required
def admin():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM users ORDER BY id DESC")
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
    width, height = A4

    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(200, height - 50, "LISTE DES MEMBRES - CLUB ECHECS")

    pdf.setFont("Helvetica", 10)
    y = height - 100
    for u in users:
        text = f"ID: {u[0]} | {u[1]} {u[2]} | Promo: {u[5]} | Tel: {u[4]}"
        pdf.drawString(50, y, text)
        y -= 20
        if y < 50:
            pdf.showPage()
            y = height - 50

    pdf.save()
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name="inscrits_echecs.pdf", mimetype="application/pdf")


# =========================
# LANCEMENT
# =========================
if __name__ == '__main__':
    # Configuration du port pour Railway
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)