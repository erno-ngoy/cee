from flask import Flask, render_template, request, redirect, send_file, render_template_string
import psycopg2
import io
import os
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import generate_password_hash, check_password_hash

# Imports pour le PDF
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.units import cm

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
    url = os.environ.get('DATABASE_URL')
    if not url:
        url = "postgresql://postgres:xwpTRSXROyoktPEmOiswTYAeJrDkRJJw@postgres.railway.internal:5432/railway"
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return psycopg2.connect(url)

def init_db():
    try:
        conn = get_db_connection()
        c = conn.cursor()
        # Création de la table avec la colonne points
        c.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                user_id TEXT UNIQUE,
                nom TEXT,
                postnom TEXT,
                prenom TEXT,
                telephone TEXT,
                promotion TEXT,
                points INTEGER DEFAULT 0
            )
        ''')
        # Sécurité : Si la colonne points n'existe pas encore chez certains
        c.execute('''
            DO $$ 
            BEGIN 
                IF NOT EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME='users' AND COLUMN_NAME='points') THEN
                    ALTER TABLE users ADD COLUMN points INTEGER DEFAULT 0;
                END IF;
            END $$;
        ''')
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Erreur DB : {e}")

init_db()

# =========================
# DESIGN DE LA CARTE DE CONFIRMATION
# =========================
SUCCESS_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { background: linear-gradient(135deg, #0f2027, #2c5364); font-family: 'Segoe UI', sans-serif; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; padding: 20px; text-align: center; }
        .card { background: white; padding: 30px; border-radius: 20px; box-shadow: 0 20px 40px rgba(0,0,0,0.5); max-width: 450px; width: 100%; animation: pop 0.4s ease-out; border-top: 8px solid #1a2a6c; }
        @keyframes pop { from { transform: scale(0.8); opacity: 0; } to { transform: scale(1); opacity: 1; } }
        .badge { background: #e8f5e9; color: #2e7d32; padding: 5px 15px; border-radius: 50px; font-size: 0.8em; font-weight: bold; margin-bottom: 15px; display: inline-block; }
        .badge.already { background: #fff3e0; color: #ef6c00; }
        .icon { font-size: 50px; margin: 10px 0; }
        h2 { color: #1a2a6c; margin: 10px 0; }
        .id-box { background: #1a2a6c; color: #ffd700; padding: 20px; margin: 15px 0; border-radius: 12px; font-size: 1.5em; font-weight: bold; font-family: monospace; }
        .btn { display: block; text-decoration: none; background: #ffd700; color: #000; padding: 15px; border-radius: 12px; font-weight: bold; transition: 0.3s; margin-top: 20px; }
        .btn:hover { background: #e6c200; transform: translateY(-2px); }
    </style>
</head>
<body>
    <div class="card">
        {% if is_already %} <div class="badge already">DÉJÀ INSCRIT</div> {% else %} <div class="badge">INSCRIPTION RÉUSSIE</div> {% endif %}
        <div class="icon">🏆</div>
        <h2>Félicitations {{prenom}} !</h2>
        <div class="id-box">{{user_id}}</div>
        <p>Ton compte est actif. Tu peux maintenant participer aux tournois et gagner des points.</p>
        <a href="/classement" class="btn">VOIR LE CLASSEMENT PUBLIC</a>
    </div>
</body>
</html>
"""

# =========================
# ROUTES
# =========================

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        nom = request.form['nom'].upper().strip()
        postnom = request.form['postnom'].upper().strip()
        prenom = request.form['prenom'].capitalize().strip()
        telephone = request.form['telephone'].strip()
        promotion = request.form['promotion']

        try:
            conn = get_db_connection()
            c = conn.cursor()
            c.execute("SELECT user_id FROM users WHERE nom=%s AND postnom=%s AND prenom=%s", (nom, postnom, prenom))
            existing_user = c.fetchone()

            if existing_user:
                user_id = existing_user[0]
                is_already = True
            else:
                c.execute("SELECT COUNT(*) FROM users WHERE promotion = %s", (promotion,))
                count = c.fetchone()[0] + 1
                user_id = f"{promotion}-{nom}-{str(count).zfill(3)}"
                c.execute("INSERT INTO users (user_id, nom, postnom, prenom, telephone, promotion) VALUES (%s, %s, %s, %s, %s, %s)",
                          (user_id, nom, postnom, prenom, telephone, promotion))
                conn.commit()
                is_already = False
            conn.close()
            return render_template_string(SUCCESS_HTML, user_id=user_id, prenom=prenom, is_already=is_already)
        except Exception as e:
            return f"Erreur : {e}"
    return render_template('index.html')

@app.route('/classement')
def classement():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT prenom, nom, promotion, points FROM users ORDER BY points DESC, nom ASC")
    members = c.fetchall()
    conn.close()
    return render_template('classement.html', members=members)

@app.route('/admin')
@auth.login_required
def admin():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT id, user_id, nom, postnom, prenom, telephone, promotion, points FROM users ORDER BY points DESC, nom ASC")
    users = c.fetchall()
    conn.close()
    return render_template('admin.html', users=users)

@app.route('/add_point/<int:id>')
@auth.login_required
def add_point(id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("UPDATE users SET points = points + 1 WHERE id = %s", (id,))
    conn.commit()
    conn.close()
    return redirect('/admin')

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
    c.execute("SELECT user_id, nom, postnom, prenom, points, promotion FROM users ORDER BY points DESC")
    users = c.fetchall()
    conn.close()
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()
    elements.append(Paragraph("CLASSEMENT OFFICIEL - CLUB ESI", styles['Title']))
    data = [["ID", "NOM COMPLET", "PROMO", "PTS"]]
    for u in users:
        data.append([u[0], f"{u[1]} {u[3]}", u[5], u[4]])
    t = Table(data, colWidths=[4*cm, 8*cm, 3*cm, 2*cm])
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.grey),('GRID',(0,0),(-1,-1),1,colors.black)]))
    elements.append(t)
    doc.build(elements)
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name="classement.pdf", mimetype="application/pdf")

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)