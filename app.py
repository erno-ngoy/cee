from flask import Flask, render_template, request, redirect, send_file, render_template_string
import psycopg2
import io
import os
import smtplib
from email.mime.text import MIMEText
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
auth = HTTPBasicAuth()

# =========================
# CONFIGURATION EMAIL
# =========================
EMAIL_EXPEDITEUR = "ton-email@gmail.com"
MOT_DE_PASSE_APP = "ogaipenscpoebifz"
DESTINATAIRES = ["ernongoy@gmail.com", "ernoerno226@gmail.com"]

def notifier_activite(sujet, message_corps):
    try:
        msg = MIMEText(message_corps)
        msg['Subject'] = f"♟️ ESI ECHECS : {sujet}"
        msg['From'] = EMAIL_EXPEDITEUR
        msg['To'] = ", ".join(DESTINATAIRES)
        serveur = smtplib.SMTP('smtp.gmail.com', 587, timeout=10)
        serveur.starttls()
        serveur.login(EMAIL_EXPEDITEUR, MOT_DE_PASSE_APP)
        serveur.sendmail(EMAIL_EXPEDITEUR, DESTINATAIRES, msg.as_string())
        serveur.quit()
    except Exception as e:
        print(f"ERREUR EMAIL : {e}")

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
# PAGE DE RÉUSSITE + CARTE DE MEMBRE
# =========================
SUCCESS_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
    <style>
        body { background: #0f2027; font-family: 'Segoe UI', sans-serif; display: flex; flex-direction: column; align-items: center; min-height: 100vh; margin: 0; padding: 20px; color: white; }
        #memberCard { 
            background: white; color: #333; width: 350px; padding: 25px; border-radius: 20px; 
            box-shadow: 0 15px 35px rgba(0,0,0,0.5); text-align: center; position: relative;
            border-top: 12px solid #1a2a6c;
        }
        .card-header h3 { margin: 0; color: #1a2a6c; font-size: 20px; letter-spacing: 1px; }
        .card-header p { margin: 5px 0 20px; font-size: 12px; color: #666; font-weight: bold; }
        .info-group { text-align: left; margin-bottom: 12px; }
        .label { font-size: 10px; text-transform: uppercase; color: #999; font-weight: bold; display: block; }
        .value { font-size: 16px; color: #1a2a6c; font-weight: bold; }
        .user-id { background: #1a2a6c; color: #ffd700; padding: 12px; border-radius: 10px; font-family: monospace; font-size: 20px; font-weight: bold; margin: 20px 0; }
        .qr-area { display: flex; justify-content: center; margin-top: 10px; }
        .qr-area img { width: 120px; height: 120px; border: 1px solid #eee; padding: 5px; background: white; }
        .footer-text { font-size: 9px; color: #aaa; margin-top: 15px; font-style: italic; }
        .actions { margin-top: 30px; display: flex; flex-direction: column; gap: 12px; width: 350px; }
        .btn { padding: 15px; border-radius: 12px; font-weight: bold; text-align: center; cursor: pointer; border: none; text-decoration: none; font-size: 14px; transition: 0.3s; }
        .btn-download { background: #ffd700; color: #000; }
        .btn-home { background: rgba(255,255,255,0.1); color: white; border: 1px solid white; }
    </style>
</head>
<body>
    <div id="memberCard">
        <div class="card-header">
            <h3>CLUB D'ÉCHECS ESI</h3>
            <p>CARTE OFFICIELLE DE MEMBRE</p>
        </div>
        <div class="info-group">
            <span class="label">Nom Complet</span>
            <span class="value">{{prenom}} {{nom}}</span>
        </div>
        <div class="info-group">
            <span class="label">Promotion</span>
            <span class="value">{{promotion}}</span>
        </div>
        <div class="user-id">{{user_id}}</div>
        <div class="qr-area">
            <img crossorigin="anonymous" src="https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={{user_id}}" alt="QR Code">
        </div>
        <div class="footer-text">Présentez cette carte lors des tournois officiels.</div>
    </div>
    <div class="actions">
        <button onclick="downloadCard()" class="btn btn-download">📥 TÉLÉCHARGER MA CARTE (PNG)</button>
        <a href="/classement" class="btn btn-home">VOIR LE CLASSEMENT</a>
    </div>
    <script>
        function downloadCard() {
            const card = document.getElementById('memberCard');
            html2canvas(card, { useCORS: true, scale: 3 }).then(canvas => {
                const link = document.createElement('a');
                link.download = 'Carte_Club_Echecs_{{prenom}}.png';
                link.href = canvas.toDataURL("image/png");
                link.click();
            });
        }
    </script>
</body>
</html>
"""

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        nom = request.form['nom'].upper().strip()
        postnom = request.form['postnom'].upper().strip()
        prenom = request.form['prenom'].capitalize().strip()
        telephone = request.form['telephone'].strip()
        promotion = request.form['promotion']
        try:
            conn = get_db_connection(); c = conn.cursor()
            c.execute("SELECT user_id FROM users WHERE nom=%s AND postnom=%s AND prenom=%s", (nom, postnom, prenom))
            existing = c.fetchone()
            if existing:
                user_id, is_already = existing[0], True
            else:
                c.execute("SELECT COUNT(*) FROM users WHERE promotion = %s", (promotion,))
                user_id = f"{promotion}-{nom}-{str(c.fetchone()[0] + 1).zfill(3)}"
                c.execute("INSERT INTO users (user_id, nom, postnom, prenom, telephone, promotion) VALUES (%s,%s,%s,%s,%s,%s)", (user_id, nom, postnom, prenom, telephone, promotion))
                conn.commit(); is_already = False
                notifier_activite("Nouveau Membre", f"{prenom} {nom} ({promotion}) s'est inscrit.")
            conn.close()
            return render_template_string(SUCCESS_HTML, user_id=user_id, prenom=prenom, nom=nom, promotion=promotion)
        except Exception as e: return f"Erreur : {e}"
    return render_template('index.html')

@app.route('/admin')
@auth.login_required
def admin():
    conn = get_db_connection(); c = conn.cursor()
    c.execute("SELECT id, user_id, nom, postnom, prenom, telephone, promotion, points FROM users ORDER BY points DESC")
    users = c.fetchall(); conn.close()
    return render_template('admin.html', users=users)

@app.route('/add_point/<int:id>')
@auth.login_required
def add_point(id):
    conn = get_db_connection(); c = conn.cursor()
    c.execute("UPDATE users SET points = points + 1 WHERE id = %s", (id,))
    conn.commit(); conn.close()
    return redirect('/admin')

@app.route('/remove_point/<int:id>')
@auth.login_required
def remove_point(id):
    conn = get_db_connection(); c = conn.cursor()
    c.execute("UPDATE users SET points = GREATEST(0, points - 1) WHERE id = %s", (id,))
    conn.commit(); conn.close()
    return redirect('/admin')

@app.route('/delete/<int:id>')
@auth.login_required
def delete(id):
    conn = get_db_connection(); c = conn.cursor()
    c.execute("DELETE FROM users WHERE id = %s", (id,))
    conn.commit(); conn.close()
    return redirect('/admin')

@app.route('/classement')
def classement():
    conn = get_db_connection(); c = conn.cursor()
    c.execute("SELECT prenom, nom, promotion, points FROM users ORDER BY points DESC")
    members = c.fetchall(); conn.close()
    return render_template('classement.html', members=members)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))