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
DESTINATAIRES = ["ernongoy@gmail.com", "arnoerno226@gmail.com"]


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
# DESIGN CARTE DE MEMBRE
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
            background: white; color: #333; width: 340px; padding: 25px; border-radius: 20px; 
            box-shadow: 0 15px 35px rgba(0,0,0,0.5); text-align: center; border-top: 12px solid #1a2a6c;
        }
        .user-id { background: #1a2a6c; color: #ffd700; padding: 10px; border-radius: 8px; font-family: monospace; font-size: 18px; font-weight: bold; margin: 15px 0; }
        .qr-area img { width: 120px; height: 120px; }
        .actions { margin-top: 25px; display: flex; flex-direction: column; gap: 10px; width: 340px; }
        .btn { padding: 15px; border-radius: 12px; font-weight: bold; text-align: center; cursor: pointer; text-decoration: none; border: none; }
    </style>
</head>
<body>
    <div id="memberCard">
        <h3 style="color:#1a2a6c; margin:0;">CLUB D'ÉCHECS ESI</h3>
        <p style="font-size:12px; color:#666;">CARTE OFFICIELLE</p>
        <div style="text-align:left; margin-top:15px;">
            <small style="color:#999; font-weight:bold;">NOM COMPLET</small><br>
            <span style="font-weight:bold; color:#1a2a6c;">{{prenom}} {{nom}}</span>
        </div>
        <div class="user-id">{{user_id}}</div>
        <div class="qr-area">
            <img crossorigin="anonymous" src="https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={{user_id}}" alt="QR Code">
        </div>
    </div>
    <div class="actions">
        <button onclick="downloadCard()" class="btn" style="background:#ffd700; color:#000;">📥 TÉLÉCHARGER LA CARTE (PNG)</button>
        <a href="/classement" class="btn" style="background:rgba(255,255,255,0.1); color:white; border:1px solid white;">VOIR LE CLASSEMENT</a>
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
            conn = get_db_connection();
            c = conn.cursor()
            c.execute("SELECT user_id FROM users WHERE nom=%s AND postnom=%s AND prenom=%s", (nom, postnom, prenom))
            existing = c.fetchone()
            if existing:
                user_id = existing[0]
            else:
                c.execute("SELECT COUNT(*) FROM users WHERE promotion = %s", (promotion,))
                user_id = f"{promotion}-{nom}-{str(c.fetchone()[0] + 1).zfill(3)}"
                c.execute(
                    "INSERT INTO users (user_id, nom, postnom, prenom, telephone, promotion) VALUES (%s,%s,%s,%s,%s,%s)",
                    (user_id, nom, postnom, prenom, telephone, promotion))
                conn.commit()
                notifier_activite("Nouveau Membre", f"{prenom} {nom} ({promotion}) s'est inscrit.")
            conn.close()
            return render_template_string(SUCCESS_HTML, user_id=user_id, prenom=prenom, nom=nom, promotion=promotion)
        except Exception as e:
            return f"Erreur : {e}"
    return render_template('index.html')


@app.route('/admin')
@auth.login_required
def admin():
    conn = get_db_connection();
    c = conn.cursor()
    c.execute("SELECT id, user_id, nom, postnom, prenom, telephone, promotion, points FROM users ORDER BY points DESC")
    users = c.fetchall();
    conn.close()
    return render_template('admin.html', users=users)


@app.route('/add_point/<int:id>')
@auth.login_required
def add_point(id):
    conn = get_db_connection();
    c = conn.cursor()
    c.execute("UPDATE users SET points = points + 1 WHERE id = %s", (id,))
    conn.commit();
    conn.close()
    return redirect('/admin')


@app.route('/remove_point/<int:id>')
@auth.login_required
def remove_point(id):
    conn = get_db_connection();
    c = conn.cursor()
    c.execute("UPDATE users SET points = GREATEST(0, points - 1) WHERE id = %s", (id,))
    conn.commit();
    conn.close()
    return redirect('/admin')


# --- ROUTE PDF RÉINTÉGRÉE ---
@app.route('/export_pdf')
@auth.login_required
def export_pdf():
    try:
        conn = get_db_connection();
        c = conn.cursor()
        c.execute("SELECT user_id, nom, postnom, prenom, points, promotion FROM users ORDER BY points DESC")
        users = c.fetchall();
        conn.close()

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        elements = []
        styles = getSampleStyleSheet()

        elements.append(Paragraph("LISTE DES MEMBRES - CLUB D'ÉCHECS ESI", styles['Title']))

        data = [["ID UNIQUE", "NOM & PRÉNOM", "PROMO", "PTS"]]
        for u in users:
            data.append([u[0], f"{u[1]} {u[3]}", u[5], str(u[4])])

        t = Table(data, colWidths=[4 * cm, 8 * cm, 3 * cm, 2 * cm])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1a2a6c")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ]))
        elements.append(t)
        doc.build(elements)
        buffer.seek(0)
        return send_file(buffer, as_attachment=True, download_name="membres_echecs_esi.pdf", mimetype="application/pdf")
    except Exception as e:
        return f"Erreur lors de la génération du PDF : {e}"


@app.route('/delete/<int:id>')
@auth.login_required
def delete(id):
    conn = get_db_connection();
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE id = %s", (id,))
    conn.commit();
    conn.close()
    return redirect('/admin')


@app.route('/classement')
def classement():
    conn = get_db_connection();
    c = conn.cursor()
    c.execute("SELECT prenom, nom, promotion, points FROM users ORDER BY points DESC")
    members = c.fetchall();
    conn.close()
    return render_template('classement.html', members=members)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))