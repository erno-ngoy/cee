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
    if username in users_auth and \
            check_password_hash(users_auth.get(username), password):
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
        body { background: linear-gradient(135deg, #0f2027, #2c5364); font-family: 'Segoe UI', sans-serif; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; padding: 20px; }
        .card { background: white; padding: 30px; border-radius: 20px; text-align: center; box-shadow: 0 20px 40px rgba(0,0,0,0.5); max-width: 450px; width: 100%; animation: pop 0.4s ease-out; border-top: 8px solid #1a2a6c; }
        @keyframes pop { from { transform: scale(0.8); opacity: 0; } to { transform: scale(1); opacity: 1; } }
        .badge { background: #e8f5e9; color: #2e7d32; padding: 5px 15px; border-radius: 50px; font-size: 0.8em; font-weight: bold; margin-bottom: 15px; display: inline-block; }
        .badge.already { background: #fff3e0; color: #ef6c00; }
        .icon { font-size: 50px; margin: 10px 0; }
        h2 { color: #1a2a6c; margin: 10px 0; font-size: 1.8em; }
        .id-label { font-size: 0.9em; color: #777; margin-top: 20px; text-transform: uppercase; letter-spacing: 1px; }
        .id-box { background: #1a2a6c; color: #ffd700; padding: 20px; margin: 10px 0; border-radius: 12px; font-size: 1.5em; font-weight: bold; font-family: 'Courier New', monospace; box-shadow: inset 0 2px 10px rgba(0,0,0,0.2); }
        .info { color: #555; margin-bottom: 25px; font-size: 1.1em; line-height: 1.4; }
        .btn { display: block; text-decoration: none; background: #1a2a6c; color: white; padding: 15px; border-radius: 12px; font-weight: bold; transition: 0.3s; margin-top: 10px; }
        .btn:hover { background: #2c5364; transform: translateY(-2px); }
    </style>
</head>
<body>
    <div class="card">
        {% if is_already %}
            <div class="badge already">MEMBER DÉJÀ INSCRIT</div>
        {% else %}
            <div class="badge">NOUVELLE INSCRIPTION</div>
        {% endif %}
        <div class="icon">♟️</div>
        <h2>Bienvenue, {{prenom}} !</h2>
        <p class="info">Tes données sont sécurisées dans le registre du <b>Club d'Échecs ESI</b>.</p>

        <div class="id-label">Ton Identifiant Unique</div>
        <div class="id-box">{{user_id}}</div>

        <p style="font-size: 0.85em; color: #999;">Promotion : {{promotion}}</p>
        <a href="/" class="btn">RETOUR À L'ACCUEIL</a>
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

            # 1. VÉRIFIER SI LA PERSONNE EXISTE DÉJÀ
            c.execute("""
                SELECT user_id, prenom FROM users 
                WHERE nom=%s AND postnom=%s AND prenom=%s
            """, (nom, postnom, prenom))
            existing_user = c.fetchone()

            if existing_user:
                # Si elle existe, on récupère ses infos sans ré-ajouter
                user_id = existing_user[0]
                is_already = True
            else:
                # 2. SI NOUVELLE PERSONNE, ON L'AJOUTE
                c.execute("SELECT COUNT(*) FROM users WHERE promotion = %s", (promotion,))
                count = c.fetchone()[0] + 1
                user_id = f"{promotion}-{nom}-{str(count).zfill(3)}"

                c.execute("""
                    INSERT INTO users (user_id, nom, postnom, prenom, telephone, promotion)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (user_id, nom, postnom, prenom, telephone, promotion))
                conn.commit()
                is_already = False

            conn.close()
            return render_template_string(SUCCESS_HTML, user_id=user_id, prenom=prenom, promotion=promotion,
                                          is_already=is_already)

        except Exception as e:
            return f"Erreur critique : {e}"

    return render_template('index.html')


# --- CONSERVEZ VOS AUTRES ROUTES (admin, delete, export_pdf) ICI ---
@app.route('/admin')
@auth.login_required
def admin():
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM users ORDER BY promotion ASC, nom ASC")
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
    c.execute("SELECT user_id, nom, postnom, prenom, telephone, promotion FROM users ORDER BY promotion, nom ASC")
    users = c.fetchall()
    conn.close()

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=1.5 * cm, leftMargin=1.5 * cm, topMargin=2 * cm,
                            bottomMargin=2 * cm)
    elements = []
    styles = getSampleStyleSheet()

    def draw_background(canvas, doc):
        canvas.saveState()
        canvas.setFillColorRGB(0.9, 0.9, 0.9)
        canvas.setFillAlpha(0.05)
        pieces = "♟ ♜ ♞ ♝ ♚ ♛  " * 6
        for i in range(0, 900, 70):
            canvas.drawString(15, i, pieces)
        canvas.setFont("Helvetica", 9)
        canvas.setFillColor(colors.grey)
        canvas.drawRightString(A4[0] - 1.5 * cm, 0.8 * cm, f"Page {canvas.getPageNumber()}")
        canvas.restoreState()

    title_style = styles['Title']
    title_style.textColor = colors.HexColor('#1a2a6c')
    elements.append(Paragraph("<b>♜ CLUB D'ÉCHECS ESI ♜</b>", title_style))
    elements.append(Paragraph("<center>LISTE OFFICIELLE DES MEMBRES - 2025</center>", styles['Normal']))
    elements.append(Spacer(1, 1 * cm))

    data = [["N°", "ID MEMBRE", "NOM & PRÉNOM", "PROMOTION", "CONTACT"]]
    for i, u in enumerate(users, 1):
        full_name = f"{u[1]} {u[2]} {u[3]}"
        data.append([i, u[0], full_name, u[5], u[4]])

    table = Table(data, colWidths=[1 * cm, 4.5 * cm, 6.5 * cm, 3 * cm, 3 * cm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f6f6f6')])
    ]))
    elements.append(table)
    doc.build(elements, onFirstPage=draw_background, onLaterPages=draw_background)
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name="Membres_Club_Echecs.pdf", mimetype="application/pdf")


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)