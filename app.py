from flask import Flask, render_template, request, redirect, send_file, render_template_string
import psycopg2
import io
import os
import smtplib
from email.mime.text import MIMEText
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import generate_password_hash, check_password_hash

# Imports requis pour la génération du PDF
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.units import cm

app = Flask(__name__)
auth = HTTPBasicAuth()

# =========================
# CONFIGURATION EMAIL
# =========================
EMAIL_EXPEDITEUR = "ton-email@gmail.com"
MOT_DE_PASSE_APP = "ogaipenscpoebifz"
DESTINATAIRES = ["ernongoy@gmail.com", "ernoerno226@gmail.com"]


def notifier_activite(sujet, message_corps):
    """Version sécurisée pour éviter les erreurs 502 et timeouts Railway"""
    try:
        msg = MIMEText(message_corps)
        msg['Subject'] = f"♟️ ESI : {sujet}"
        msg['From'] = EMAIL_EXPEDITEUR
        msg['To'] = ", ".join(DESTINATAIRES)

        with smtplib.SMTP('smtp.gmail.com', 587, timeout=2) as serveur:
            serveur.starttls()
            serveur.login(EMAIL_EXPEDITEUR, MOT_DE_PASSE_APP)
            serveur.sendmail(EMAIL_EXPEDITEUR, DESTINATAIRES, msg.as_string())
    except Exception as e:
        print(f"NOTIFICATION EMAIL IGNORÉE : {e}")


# =========================
# GESTIONNAIRE D'ERREUR GLOBAL
# =========================
@app.errorhandler(Exception)
def handle_exception(e):
    print(f"ERREUR CAPTURÉE : {e}")
    return """
    <div style="text-align:center; padding:50px; font-family:sans-serif; background:#0f2027; color:white; min-height:100vh; display:flex; flex-direction:column; align-items:center; justify-content:center;">
        <h1 style="color:#ffd700; font-size:40px;">♟️ Oups !</h1>
        <p style="font-size:18px;">Une petite erreur technique est survenue.</p>
        <p style="color:#888;">L'administrateur a été notifié dans les logs.</p>
        <a href="/" style="margin-top:20px; color:#ffd700; text-decoration:none; border:1px solid #ffd700; padding:10px 20px; border-radius:5px;">Retour à l'accueil</a>
    </div>
    """, 500


# =========================
# SÉCURITÉ ADMIN
# =========================
users_auth = {"admin": generate_password_hash("esi-echecs-2025")}


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


# =========================
# TEMPLATES HTML INTÉGRÉS
# =========================
PORTAL_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { background: #0f2027; font-family: 'Segoe UI', sans-serif; display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 100vh; margin: 0; color: white; text-align: center; }
        .choice-container { display: flex; gap: 20px; flex-wrap: wrap; justify-content: center; padding: 20px; margin-top: 30px; }
        .card { background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.2); border-radius: 20px; width: 280px; padding: 40px; text-align: center; cursor: pointer; transition: 0.3s; text-decoration: none; color: white; backdrop-filter: blur(10px); }
        .card:hover { transform: translateY(-10px); background: rgba(255,255,255,0.2); border-color: #ffd700; }
        .card h2 { color: #ffd700; margin: 15px 0; }
        .icon { font-size: 50px; }
    </style>
</head>
<body>
    <h1>BIENVENUE À L'ESI</h1>
    <p>Sélectionnez votre club pour vous inscrire ou voir le classement</p>
    <div class="choice-container">
        <a href="/echecs" class="card">
            <div class="icon">♟️</div>
            <h2>ÉCHECS</h2>
            <p>Club d'Échecs ESI</p>
        </a>
        <a href="/orthographe" class="card">
            <div class="icon">📖</div>
            <h2>ORTHOGRAPHE</h2>
            <p>Concours d'Épellation</p>
        </a>
    </div>
    <a href="/admin_portal" style="margin-top:50px; color:#555; text-decoration:none;">Accès Administration</a>
</body>
</html>
"""

SUCCESS_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
    <style>
        body { background: #0f2027; font-family: 'Segoe UI', sans-serif; display: flex; flex-direction: column; align-items: center; min-height: 100vh; margin: 0; padding: 20px; color: white; }
        #memberCard { 
            background: white; color: #333; width: 340px; padding: 25px; border-radius: 20px; 
            box-shadow: 0 15px 35px rgba(0,0,0,0.5); text-align: center; border-top: 12px solid {{color}};
        }
        .user-id { background: {{color}}; color: white; padding: 10px; border-radius: 8px; font-family: monospace; font-size: 18px; font-weight: bold; margin: 15px 0; }
        .qr-area img { width: 120px; height: 120px; }
        .actions { margin-top: 25px; display: flex; flex-direction: column; gap: 10px; width: 340px; }
        .btn { padding: 15px; border-radius: 12px; font-weight: bold; text-align: center; cursor: pointer; text-decoration: none; border: none; }
    </style>
</head>
<body>
    <div id="memberCard">
        <h3 style="color:{{color}}; margin:0;">{{club_name}}</h3>
        <p style="font-size:12px; color:#666;">CARTE OFFICIELLE</p>
        <div style="text-align:left; margin-top:15px;">
            <small style="color:#999; font-weight:bold;">NOM COMPLET</small><br>
            <span style="font-weight:bold; color:{{color}};">{{prenom}} {{nom}}</span>
        </div>
        <div class="user-id">{{user_id}}</div>
        <div class="qr-area">
            <img crossorigin="anonymous" src="https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={{user_id}}" alt="QR Code">
        </div>
    </div>
    <div class="actions">
        <button onclick="downloadCard()" class="btn" style="background:{{color}}; color:white;">📥 TÉLÉCHARGER LA CARTE (PNG)</button>
        <a href="/classement_{{discipline}}" class="btn" style="background:rgba(255,255,255,0.1); color:white; border:1px solid white;">VOIR LE CLASSEMENT</a>
        <a href="/" class="btn" style="color:white; opacity:0.6;">RETOUR ACCUEIL</a>
    </div>
    <script>
        function downloadCard() {
            html2canvas(document.getElementById('memberCard'), {useCORS: true, scale: 3}).then(canvas => {
                const link = document.createElement('a');
                link.download = 'Carte_{{prenom}}.png';
                link.href = canvas.toDataURL("image/png");
                link.click();
            });
        }
    </script>
</body>
</html>
"""


# =========================
# ROUTES PRINCIPALES
# =========================

@app.route('/')
def portal():
    return render_template_string(PORTAL_HTML)


# --- SECTION ECHECS ---

@app.route('/echecs', methods=['GET', 'POST'])
def index_echecs():
    if request.method == 'POST':
        nom = request.form['nom'].upper().strip()
        postnom = request.form['postnom'].upper().strip()
        prenom = request.form['prenom'].capitalize().strip()
        telephone = request.form['telephone'].strip()
        promotion = request.form['promotion']
        conn = get_db_connection(); c = conn.cursor()
        c.execute("SELECT user_id FROM users WHERE nom=%s AND postnom=%s AND prenom=%s", (nom, postnom, prenom))
        existing = c.fetchone()
        if existing:
            user_id = existing[0]
        else:
            c.execute("SELECT COUNT(*) FROM users WHERE promotion = %s", (promotion,))
            user_id = f"CHESS-{promotion}-{str(c.fetchone()[0] + 1).zfill(3)}"
            c.execute("INSERT INTO users (user_id, nom, postnom, prenom, telephone, promotion) VALUES (%s,%s,%s,%s,%s,%s)", (user_id, nom, postnom, prenom, telephone, promotion))
            conn.commit()
            notifier_activite("Nouveau Membre Échecs", f"{prenom} {nom} ({promotion})")
        conn.close()
        return render_template_string(SUCCESS_HTML, user_id=user_id, prenom=prenom, nom=nom, color="#1a2a6c", club_name="CLUB D'ÉCHECS ESI", discipline="echecs")
    return render_template('index.html', discipline='echecs', club_name="Club d'Échecs ESI")


@app.route('/classement_echecs')
def classement_echecs():
    conn = get_db_connection(); c = conn.cursor()
    c.execute("SELECT prenom, nom, promotion, points FROM users ORDER BY points DESC")
    members = c.fetchall(); conn.close()
    return render_template('classement.html', members=members, discipline='echecs', club_name="Club d'Échecs ESI")


# --- SECTION ORTHOGRAPHE ---

@app.route('/orthographe', methods=['GET', 'POST'])
def index_ortho():
    if request.method == 'POST':
        nom = request.form['nom'].upper().strip()
        postnom = request.form['postnom'].upper().strip()
        prenom = request.form['prenom'].capitalize().strip()
        telephone = request.form['telephone'].strip()
        promotion = request.form['promotion']
        conn = get_db_connection(); c = conn.cursor()
        c.execute("SELECT user_id FROM users_ortho WHERE nom=%s AND postnom=%s AND prenom=%s", (nom, postnom, prenom))
        existing = c.fetchone()
        if existing:
            user_id = existing[0]
        else:
            c.execute("SELECT COUNT(*) FROM users_ortho WHERE promotion = %s", (promotion,))
            user_id = f"ORTHO-{promotion}-{str(c.fetchone()[0] + 1).zfill(3)}"
            c.execute("INSERT INTO users_ortho (user_id, nom, postnom, prenom, telephone, promotion) VALUES (%s,%s,%s,%s,%s,%s)", (user_id, nom, postnom, prenom, telephone, promotion))
            conn.commit()
            notifier_activite("Nouveau Membre Ortho", f"{prenom} {nom} ({promotion})")
        conn.close()
        return render_template_string(SUCCESS_HTML, user_id=user_id, prenom=prenom, nom=nom, color="#2c5364", club_name="ESI ORTHOGRAPHE", discipline="ortho")
    return render_template('index.html', discipline='ortho', club_name="ESI Orthographe & Épellation")


@app.route('/classement_ortho')
def classement_ortho():
    conn = get_db_connection(); c = conn.cursor()
    c.execute("SELECT prenom, nom, promotion, points FROM users_ortho ORDER BY points DESC")
    members = c.fetchall(); conn.close()
    return render_template('classement.html', members=members, discipline='ortho', club_name="ESI Orthographe & Épellation")


# =========================
# ADMINISTRATION MIXTE
# =========================

@app.route('/admin_portal')
@auth.login_required
def admin_portal():
    return """
    <body style="background:#0f2027; color:white; font-family:sans-serif; text-align:center; padding:50px;">
        <h1>PANNEAU DE CONTRÔLE ADMIN</h1>
        <div style="display:flex; gap:20px; justify-content:center; margin-top:30px;">
            <a href="/admin_echecs" style="padding:30px; background:#1a2a6c; color:white; text-decoration:none; border-radius:15px; width:200px;">Gérer ÉCHECS</a>
            <a href="/admin_ortho" style="padding:30px; background:#2c5364; color:white; text-decoration:none; border-radius:15px; width:200px;">Gérer ORTHOGRAPHE</a>
        </div>
        <br><br><a href="/" style="color:#555;">Retour au site</a>
    </body>
    """

@app.route('/admin_echecs')
@auth.login_required
def admin_echecs():
    conn = get_db_connection(); c = conn.cursor()
    c.execute("SELECT id, user_id, nom, postnom, prenom, telephone, promotion, points FROM users ORDER BY points DESC")
    users = c.fetchall(); conn.close()
    return render_template('admin.html', users=users, title="Administration Échecs", discipline="echecs")

@app.route('/admin_ortho')
@auth.login_required
def admin_ortho():
    conn = get_db_connection(); c = conn.cursor()
    c.execute("SELECT id, user_id, nom, postnom, prenom, telephone, promotion, points FROM users_ortho ORDER BY points DESC")
    users = c.fetchall(); conn.close()
    return render_template('admin.html', users=users, title="Administration Orthographe", discipline="ortho")


# --- ACTIONS POINTS (ECHECS) ---
@app.route('/add_point/<int:id>')
@auth.login_required
def add_point(id):
    conn = get_db_connection(); c = conn.cursor()
    c.execute("UPDATE users SET points = points + 1 WHERE id = %s", (id,))
    conn.commit(); conn.close()
    return redirect('/admin_echecs')

@app.route('/remove_point/<int:id>')
@auth.login_required
def remove_point(id):
    conn = get_db_connection(); c = conn.cursor()
    c.execute("UPDATE users SET points = GREATEST(0, points - 1) WHERE id = %s", (id,))
    conn.commit(); conn.close()
    return redirect('/admin_echecs')

@app.route('/delete_echecs/<int:id>')
@auth.login_required
def delete_echecs(id):
    conn = get_db_connection(); c = conn.cursor()
    c.execute("DELETE FROM users WHERE id = %s", (id,))
    conn.commit(); conn.close()
    return redirect('/admin_echecs')


# --- ACTIONS POINTS (ORTHO) ---
@app.route('/add_point_ortho/<int:id>')
@auth.login_required
def add_point_ortho(id):
    conn = get_db_connection(); c = conn.cursor()
    c.execute("UPDATE users_ortho SET points = points + 1 WHERE id = %s", (id,))
    conn.commit(); conn.close()
    return redirect('/admin_ortho')

@app.route('/remove_point_ortho/<int:id>')
@auth.login_required
def remove_point_ortho(id):
    conn = get_db_connection(); c = conn.cursor()
    c.execute("UPDATE users_ortho SET points = GREATEST(0, points - 1) WHERE id = %s", (id,))
    conn.commit(); conn.close()
    return redirect('/admin_ortho')

@app.route('/delete_ortho/<int:id>')
@auth.login_required
def delete_ortho(id):
    conn = get_db_connection(); c = conn.cursor()
    c.execute("DELETE FROM users_ortho WHERE id = %s", (id,))
    conn.commit(); conn.close()
    return redirect('/admin_ortho')


# --- EXPORTS PDF ---

@app.route('/export_pdf_echecs')
@auth.login_required
def export_pdf_echecs():
    return generate_pdf_report("users", "CLUB D'ÉCHECS ESI")

@app.route('/export_pdf_ortho')
@auth.login_required
def export_pdf_ortho():
    return generate_pdf_report("users_ortho", "ESI ORTHOGRAPHE & EPELATION")

def generate_pdf_report(table_name, title):
    conn = get_db_connection(); c = conn.cursor()
    c.execute(f"SELECT user_id, nom, postnom, prenom, points, promotion FROM {table_name} ORDER BY points DESC")
    users = c.fetchall(); conn.close()
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()
    elements.append(Paragraph(f"LISTE DES MEMBRES - {title}", styles['Title']))
    data = [["ID UNIQUE", "NOM & PRÉNOM", "PROMO", "PTS"]]
    for u in users:
        data.append([u[0], f"{u[1]} {u[3]}", u[5], str(u[4])])
    t = Table(data, colWidths=[4 * cm, 8 * cm, 3 * cm, 2 * cm])
    t.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1a2a6c")), ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke), ('ALIGN', (0, 0), (-1, -1), 'CENTER'), ('GRID', (0, 0), (-1, -1), 1, colors.black)]))
    elements.append(t)
    doc.build(elements)
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name=f"membres_{table_name}.pdf", mimetype="application/pdf")


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)