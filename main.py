from fastapi import FastAPI
from fastapi.responses import HTMLResponse, FileResponse
import sqlite3
from pathlib import Path
from datetime import datetime
import re

app = FastAPI()

DB_PATH = Path("data/historic_dhl.db")
LOGO_PATH = Path("dhl_logo_transparent.png")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def clean(x, fallback="non presente"):
    if x is None:
        return fallback
    text = str(x).strip()
    return text if text else fallback


# 🔥 PULIZIA NOME CLIENTE
def clean_cliente(text):
    value = clean(text, "")

    if not value:
        return "non presente"

    # elimina codici tipo 4513 davanti
    value = re.sub(r"^\d+\s*", "", value)

    # elimina duplicazioni strane
    value = re.sub(r"\s{2,}", " ", value)

    return value.strip()


# 🔥 PULIZIA INDIRIZZO (rimuove orari)
def clean_address(text):
    value = clean(text, "")

    if not value:
        return "non presente"

    # rimuove orari tipo 9 11.30 14
    value = re.sub(r"\b\d{1,2}(\.\d{2})?\b", "", value)

    # rimuove roba tipo RICEVIMENTO
    value = re.sub(r"RICEVIMENTO.*", "", value, flags=re.IGNORECASE)

    # pulizia spazi
    value = re.sub(r"\s{2,}", " ", value).strip(" .,-")

    return value if value else "non presente"


def fmt_date(x):
    if not x:
        return "non presente"

    text = str(x).strip()

    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y"):
        try:
            dt = datetime.strptime(text[:19], fmt)
            return dt.strftime("%d/%m/%Y")
        except:
            pass

    return text


def fmt_time(x):
    if not x:
        return "non presente"

    text = str(x).strip()

    if " " in text:
        try:
            return text.split(" ")[1][:5]
        except:
            return "non presente"

    return text[:5] if ":" in text else "non presente"


def compute_esito(row):
    if row["data_consegna"] or row["delivery_datetime"]:
        return "Consegna avvenuta"
    return clean(row["event_remark"])


def get_signatory(row):
    sign = clean(row["signatory"], "")
    if sign:
        return sign
    return clean(row["event_remark"])


def search_dhl_records(q: str):
    if not DB_PATH.exists():
        return [], "Database non trovato"

    pattern = f"%{q}%"

    conn = get_connection()
    rows = conn.execute("""
        SELECT * FROM pod_records
        WHERE
            COALESCE(ddt, '') LIKE ?
            OR COALESCE(awb, '') LIKE ?
            OR COALESCE(cliente, '') LIKE ?
    """, (pattern, pattern, pattern)).fetchall()

    conn.close()
    return rows, None


def get_row(ddt: str):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM pod_records WHERE ddt = ?",
        (ddt,)
    ).fetchone()
    conn.close()
    return row


@app.get("/dhl_logo_transparent.png")
def logo():
    return FileResponse(LOGO_PATH)


# 🔥 CERTIFICAZIONE
def render_cert_html(row):

    cliente = clean_cliente(row["cliente"])
    indirizzo = clean_address(row["consignee_address"])

    awb = clean(row["awb"])
    ddt = clean(row["ddt"])
    cap = clean(row["cap"])
    citta = clean(row["citta"])
    nazione = clean(row["nazione"])

    ritiro = fmt_date(row["data_ritiro"])
    consegna = fmt_date(row["data_consegna"])
    ora = fmt_time(row["delivery_datetime"])

    firma = get_signatory(row)
    esito = compute_esito(row)

    generated = datetime.now().strftime("%d/%m/%Y %H:%M")

    return f"""
    <html>
    <body style="font-family:Arial;background:#efefef;padding:30px;">

    <a href="/" style="background:#d40511;color:white;padding:10px 15px;border-radius:8px;text-decoration:none;">← Torna alla ricerca</a>

    <div style="background:white;max-width:1000px;margin:20px auto;border-radius:10px;overflow:hidden;">

        <div style="background:#ffcc00;padding:15px;border-bottom:4px solid #d40511;">
            <img src="/dhl_logo_transparent.png" style="height:40px;">
            <span style="float:right;font-weight:bold;">POD MANAGER DHL</span>
        </div>

        <div style="padding:30px;">
            <h1 style="text-align:center;">CERTIFICAZIONE CONSEGNA</h1>

            <p style="text-align:center;">
                Spedizione AWB <b>{awb}</b><br>
                Consegnata con successo
            </p>

            <hr>

            <h3>Consegna</h3>
            Stato: {esito}<br>
            Ricevuto da: {firma}<br>
            Data: {consegna}<br>
            Ora: {ora}

            <h3>Destinatario</h3>
            Nome: {cliente}<br>
            Indirizzo: {indirizzo}<br>
            CAP/Città: {cap} {citta}<br>
            Nazione: {nazione}

            <h3>Dati spedizione</h3>
            AWB: {awb}<br>
            DDT: {ddt}<br>
            Data ritiro: {ritiro}<br>

            <hr>

            <small>Generato il {generated}</small>
        </div>

    </div>
    </body>
    </html>
    """


@app.get("/", response_class=HTMLResponse)
def home(q: str = ""):
    rows, _ = search_dhl_records(q)

    results = ""
    for r in rows:
        results += f"""
        <tr>
            <td>{r['ddt']}</td>
            <td>{r['awb']}</td>
            <td>{r['cliente']}</td>
            <td><a href="/cert/{r['ddt']}">Apri</a></td>
        </tr>
        """

    return f"""
    <html>
    <body style="font-family:Arial;padding:30px;">
        <h1>POD Manager</h1>

        <form>
            <input name="q" value="{q}">
            <button>Cerca</button>
        </form>

        <table border="1" style="margin-top:20px;">
        {results}
        </table>
    </body>
    </html>
    """


@app.get("/cert/{ddt}", response_class=HTMLResponse)
def cert(ddt: str):
    row = get_row(ddt)
    return render_cert_html(row)
