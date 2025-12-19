from flask import Flask, render_template, request, redirect, send_file
import psycopg2
import io
import os
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import generate_password_hash, check_password_hash

# Imports spécifiques pour le beau PDF
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
        print("Base de données initialisée.")
    except Exception as e:
        print(f"Erreur DB : {e}")


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
            return f"Erreur : {e}"

    return render_template('index.html')


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


# =========================
# ROUTE EXPORT PDF (DESIGN AMÉLIORÉ)
# =========================
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

    # Fonction pour le background et numérotation
    def draw_background(canvas, doc):
        canvas.saveState()
        # Filigrane échecs
        canvas.setFillColorRGB(0.9, 0.9, 0.9)
        canvas.setFillAlpha(0.05)
        pieces = "♟ ♜ ♞ ♝ ♚ ♛  " * 6
        for i in range(0, 900, 70):
            canvas.drawString(15, i, pieces)

        # Numérotation de page
        canvas.setFont("Helvetica", 9)
        canvas.setFillColor(colors.grey)
        canvas.drawRightString(A4[0] - 1.5 * cm, 0.8 * cm, f"Page {canvas.getPageNumber()}")
        canvas.restoreState()

    # Titre
    title_style = styles['Title']
    title_style.textColor = colors.HexColor('#1a2a6c')
    elements.append(Paragraph("<b>♜ CLUB D'ÉCHECS ESI ♜</b>", title_style))
    elements.append(Paragraph("<center>LISTE OFFICIELLE DES MEMBRES - 2025</center>", styles['Normal']))
    elements.append(Spacer(1, 1 * cm))

    # Tableau
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