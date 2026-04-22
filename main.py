from fastapi import FastAPI
from fastapi.responses import HTMLResponse, FileResponse
import sqlite3
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import io

app = FastAPI()

DB_PATH = "data/historic_dhl.db"


def get_connection():
    return sqlite3.connect(DB_PATH)


@app.get("/")
def home():
    return HTMLResponse("""
    <h1>POD Manager</h1>
    <form action="/search">
        <input name="q" placeholder="DDT o AWB">
        <button>Cerca</button>
    </form>
    """)


@app.get("/search", response_class=HTMLResponse)
def search(q: str):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT ddt, awb, destinatario
        FROM spedizioni
        WHERE ddt LIKE ? OR awb LIKE ?
        LIMIT 20
    """, (f"%{q}%", f"%{q}%"))

    rows = cur.fetchall()
    conn.close()

    html = "<h2>Risultati</h2><table border=1>"

    for r in rows:
        html += f"""
        <tr>
            <td>{r[0]}</td>
            <td>{r[1]}</td>
            <td>{r[2]}</td>
            <td><a href="/cert/{r[0]}">Apri</a></td>
        </tr>
        """

    html += "</table>"
    return HTMLResponse(html)


@app.get("/cert/{ddt}", response_class=HTMLResponse)
def cert(ddt: str):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT *
        FROM spedizioni
        WHERE ddt = ?
    """, (ddt,))

    row = cur.fetchone()
    conn.close()

    if not row:
        return HTMLResponse("Non trovato")

    data = {
        "ddt": row[0],
        "awb": row[1],
        "destinatario": row[2],
        "indirizzo": row[3],
        "citta": row[4],
        "nazione": row[5],
        "ritiro": row[6],
        "consegna": row[7],
        "firma": row[8],
        "esito": row[9]
    }

    return HTMLResponse(f"""
    <a href="/">← Torna alla ricerca</a>
    <a href="/cert/{ddt}/pdf" style="margin-left:20px;">📄 Scarica PDF</a>

    <h1>CERTIFICAZIONE CONSEGNA</h1>

    <p>AWB: {data["awb"]}</p>
    <p>DDT: {data["ddt"]}</p>

    <h3>Destinatario</h3>
    <p>{data["destinatario"]}</p>
    <p>{data["indirizzo"]}</p>
    <p>{data["citta"]}</p>

    <h3>Dettagli</h3>
    <p>Ritiro: {data["ritiro"]}</p>
    <p>Consegna: {data["consegna"]}</p>
    <p>Firma: {data["firma"]}</p>
    <p>Esito: {data["esito"]}</p>
    """)


# 🔥 ROUTE PDF
@app.get("/cert/{ddt}/pdf")
def download_pdf(ddt: str):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM spedizioni WHERE ddt = ?", (ddt,))
    row = cur.fetchone()
    conn.close()

    if not row:
        return {"error": "not found"}

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)

    pdf.drawString(100, 800, "CERTIFICAZIONE CONSEGNA")
    pdf.drawString(100, 770, f"DDT: {row[0]}")
    pdf.drawString(100, 750, f"AWB: {row[1]}")
    pdf.drawString(100, 730, f"Destinatario: {row[2]}")
    pdf.drawString(100, 710, f"Indirizzo: {row[3]}")
    pdf.drawString(100, 690, f"Città: {row[4]}")
    pdf.drawString(100, 670, f"Nazione: {row[5]}")
    pdf.drawString(100, 650, f"Ritiro: {row[6]}")
    pdf.drawString(100, 630, f"Consegna: {row[7]}")
    pdf.drawString(100, 610, f"Firma: {row[8]}")
    pdf.drawString(100, 590, f"Esito: {row[9]}")

    pdf.save()

    buffer.seek(0)

    return FileResponse(
        buffer,
        media_type="application/pdf",
        filename=f"certificazione_{ddt}.pdf"
    )
