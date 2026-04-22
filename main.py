from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import sqlite3
from pathlib import Path
from datetime import datetime

app = FastAPI()

DB_PATH = Path("data/historic_dhl.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def clean(x):
    if not x:
        return "non presente"
    return str(x).strip()


def fmt_date(x):
    if not x:
        return "non presente"
    try:
        return datetime.strptime(str(x)[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
    except:
        return x


def fmt_time(x):
    if not x:
        return "non presente"
    if " " in str(x):
        return str(x).split(" ")[1][:5]
    return x


def get_row(ddt):
    conn = get_connection()
    row = conn.execute("""
        SELECT * FROM pod_records WHERE ddt = ? LIMIT 1
    """, (ddt,)).fetchone()
    conn.close()
    return row


@app.get("/cert/{ddt}", response_class=HTMLResponse)
def cert(ddt: str):
    row = get_row(ddt)

    if not row:
        return "<h1>Non trovato</h1>"

    awb = clean(row["awb"])
    cliente = clean(row["cliente"])
    indirizzo = clean(row["consignee_address"])
    cap = clean(row["cap"])
    citta = clean(row["citta"])
    nazione = clean(row["nazione"])
    ritiro = fmt_date(row["data_ritiro"])
    consegna = fmt_date(row["data_consegna"])
    ora = fmt_time(row["delivery_datetime"])
    firma = clean(row["signatory"])
    esito = "Consegna avvenuta"

    return f"""
    <html>
    <head>
        <style>
            body {{
                font-family: Arial;
                background:#f3f3f3;
                padding:30px;
            }}
            .box {{
                background:white;
                padding:30px;
                border-radius:10px;
                max-width:900px;
                margin:auto;
            }}
            .header {{
                background:#ffcc00;
                padding:15px;
                border-bottom:4px solid #d40511;
                display:flex;
                justify-content:space-between;
                align-items:center;
            }}
            .title {{
                text-align:center;
                font-size:26px;
                font-weight:bold;
                margin-top:20px;
            }}
            .subtitle {{
                text-align:center;
                color:#444;
                margin-bottom:20px;
            }}
            .line {{
                margin:6px 0;
            }}
            .section {{
                margin-top:20px;
            }}
            hr {{
                margin:20px 0;
            }}
        </style>
    </head>

    <body>

    <div class="box">

        <div class="header">
            <img src="/dhl_logo_transparent.png" height="40">
            <b>POD MANAGER DHL</b>
        </div>

        <div class="title">CERTIFICAZIONE CONSEGNA</div>
        <div class="subtitle">Riepilogo da archivio storico DHL certificato</div>

        <div style="text-align:center;">
            Spedizione AWB <b>{awb}</b><br>
            La spedizione <b>{awb}</b> risulta consegnata.
        </div>

        <hr>

        <div class="section">
            <b>Stato consegna</b><br>
            <div class="line">Stato: {esito}</div>
            <div class="line">Ricevuto da: {firma}</div>
            <div class="line">Data consegna: {consegna}</div>
            <div class="line">Ora consegna: {ora}</div>
        </div>

        <div class="section">
            <b>Dati spedizione</b><br>

            <div class="line">Nome: {cliente}</div>
            <div class="line">Indirizzo: {indirizzo}</div>
            <div class="line">CAP / Città: {cap} / {citta}</div>
            <div class="line">Nazione: {nazione}</div>

            <br>

            <div class="line">AWB: {awb}</div>
            <div class="line">DDT: {ddt}</div>
            <div class="line">Riferimento mittente: {ddt}</div>

            <div class="line">Data ritiro: {ritiro}</div>
            <div class="line">Data consegna: {consegna}</div>
            <div class="line">Ora consegna: {ora}</div>

            <div class="line">Firma: {firma}</div>
            <div class="line">Esito consegna: {esito}</div>
        </div>

        <hr>

        <div style="font-size:12px;color:#444;">
            Certificazione riepilogativa derivata da archivio storico DHL.
        </div>

        <div style="margin-top:10px;font-size:12px;">
            Generato automaticamente dal sistema POD Manager
        </div>

    </div>

    </body>
    </html>
    """
