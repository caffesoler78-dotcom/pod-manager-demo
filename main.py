from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import sqlite3
from pathlib import Path
from datetime import datetime

app = FastAPI()

DB_PATH = Path("data/historic_dhl.db")

# Logo DHL incorporato direttamente nel codice, così non devi caricare file extra
DHL_LOGO_BASE64 = "iVBORw0KGgoAAAANSUhEUgAAAMgAAABkCAYAAADDhn8LAAAJzklEQVR4nO3dfYwUZx0H8O/Mvt7d3O3sTQqFBo3SQrqgFJQWHwq2tK0h8VDb0C6V0IQmKkYQxV9FQYlNK1J7aC3q0m5a0Wm1p1C1BqM2WJrQ2kQ3iE5sAqg6JQmEoW0d5u7u7s7uzPzP7N7u7OzO7M7s2f+M5kzZ87M7MzM+f8z3zP8zwAAMhHk1QAAABg2o0AAADYhQIAANiFAgAA2IUCAADYhQIAANiFAgAA2IUCAADYhQIAANiFAgAA2IUCAADYhQIAANiFAgAA2IUCAADYhQIAANiFAgAA2IUCAADYhQIAANiFAgAA2IUCAADYhQIAANiFAgAA2IUCAADYhQIAANiFAgAA2IUCAADYhQIAANiFAgAA2IUCAADYhQIAANiFAgAA2IUCAADYhQIAANiFAgAA2IUCAADYhQIAANiFAgAA2IUCAADYhQIAANiFAgAA2IUCAADYhQIAANiFAgAA2IUCAPB9Wbdu3a5du3a9e/fu6dOnT58+fXr16tWrV69evXr16tWrV69evXr16tWrV68eX1J3rV27dt26dZs2bdo0b968efPmzZs3b968efPmzZs3b968efPmzZs3b968efPmzZs3b9583d7e3r59+3b16tW7du3atWvXrl27du3atWvXrl27du3atWvXrl27du3atWvXrv1Z8n4zMzNzc3O7du3atWvXrl27du3atWvXrl27du3atWvXrl27du3atWvXrl27dv0v8n8AAJQ1g6kAAACwCwUAALALBQAA sAsFAACwCwUAALALBQAA sAsFAACwCwUAALALBQAA sAsFAACwCwUAALALBQAA sAsFAACwCwUAALALBQAA sAsFAACwCwUAALALBQAA sAsFAACwCwUAALALBQAA sAsFAACwCwUAALALBQAA sAsFAACwCwUAALALBQAA sAsFAACwCwUAALALBQAA sAsFAACwCwUAALALBQAA sAsFAACwCwUAALALBQAA sAsFAACwCwUAALALBQAA sAsFAACwCwUAALALBQAA sAsFAACwCwUAALALBQAA sAsFAACwCwUAALALBQAA sAsFAACwCwUAALALBQAA sAsFAACwCwUAALALBQAA sAsFAACwCwUAALALBQAA sAsFAACwCwUAALALBQAA sAsFAACwCwUAALALBQAA sAsFAACwCwUAALALBQAA sAsFAACwCwUAALALBQAA sAsFAACwCwUAALALBQAA sAsFAACwCwUAALALBQAA sAsFAACwCwUAALALBQAA sAsFAACwCwUAALALBQAA sAsFAACwCwUAALALBQAA sAsFAACwCwUAALALBQAA sAsFAADw/9wTzTQAAABJRU5ErkJggg==".replace(" ", "")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def db_exists():
    return DB_PATH.exists()


def fmt_date(value):
    if not value:
        return "non presente"
    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y"):
        try:
            dt = datetime.strptime(text[:19], fmt)
            return dt.strftime("%d/%m/%Y")
        except Exception:
            pass
    return text


def fmt_time(value):
    if not value:
        return "non presente"
    text = str(value).strip()
    if " " in text:
        try:
            return text.split(" ")[1][:5]
        except Exception:
            return "non presente"
    if len(text) >= 5 and ":" in text:
        return text[:5]
    return "non presente"


def clean_text(value, fallback="non presente"):
    if value is None:
        return fallback
    text = str(value).strip()
    return text if text else fallback


def compute_delivery_status(row):
    # Nel DB certificato spesso event_remark contiene il firmatario, non l'esito.
    # Per coerenza con il PDF modello, se esiste una data consegna consideriamo "Consegna avvenuta".
    if row["data_consegna"] or row["delivery_datetime"]:
        return "Consegna avvenuta"
    return clean_text(row["event_remark"])


def get_signatory(row):
    # signatory è il campo più affidabile; se manca usiamo event_remark come fallback.
    sign = clean_text(row["signatory"], "")
    if sign:
        return sign
    return clean_text(row["event_remark"])


def get_record_by_ddt(ddt: str):
    if not db_exists():
        return None

    conn = get_connection()
    cur = conn.cursor()

    row = cur.execute(
        """
        SELECT
            ddt,
            awb,
            cliente,
            citta,
            nazione,
            cap,
            file_path,
            file_name,
            cliente_origine,
            data_elaborazione,
            anno_archivio,
            mese_archivio,
            data_ritiro,
            data_consegna,
            transit_days,
            source_type,
            source_file,
            signatory,
            event_remark,
            consignee_address,
            delivery_datetime
        FROM pod_records
        WHERE ddt = ?
        LIMIT 1
        """,
        (ddt,)
    ).fetchone()

    conn.close()
    return row


def search_dhl_records(q: str, limit: int = 100):
    if not db_exists():
        return [], "Database non trovato: data/historic_dhl.db"

    q = (q or "").strip()
    if not q:
        return [], None

    pattern = f"%{q}%"

    conn = get_connection()
    cur = conn.cursor()

    rows = cur.execute(
        """
        SELECT
            ddt,
            awb,
            cliente,
            citta,
            nazione,
            cap,
            data_ritiro,
            data_consegna,
            signatory,
            event_remark,
            consignee_address,
            delivery_datetime,
            source_type
        FROM pod_records
        WHERE
            COALESCE(ddt, '') LIKE ?
            OR COALESCE(awb, '') LIKE ?
            OR COALESCE(cliente, '') LIKE ?
            OR COALESCE(citta, '') LIKE ?
            OR COALESCE(signatory, '') LIKE ?
            OR COALESCE(consignee_address, '') LIKE ?
        ORDER BY
            CASE
                WHEN COALESCE(ddt, '') = ? THEN 0
                WHEN COALESCE(awb, '') = ? THEN 1
                ELSE 2
            END,
            COALESCE(data_consegna, '') DESC
        LIMIT ?
        """,
        (pattern, pattern, pattern, pattern, pattern, pattern, q, q, limit)
    ).fetchall()

    conn.close()
    return rows, None


def render_cert_html(row):
    awb = clean_text(row["awb"])
    ddt = clean_text(row["ddt"])
    cliente = clean_text(row["cliente"])
    indirizzo = clean_text(row["consignee_address"])
    cap = clean_text(row["cap"])
    citta = clean_text(row["citta"])
    nazione = clean_text(row["nazione"])
    ritiro = fmt_date(row["data_ritiro"])
    consegna = fmt_date(row["data_consegna"] or row["delivery_datetime"])
    ora_consegna = fmt_time(row["delivery_datetime"])
    firmatario = get_signatory(row)
    esito = compute_delivery_status(row)
    generated_on = datetime.now().strftime("%d/%m/%Y alle %H:%M")

    return f"""
    <html>
        <head>
            <title>Certificazione DHL {ddt}</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    background: #f3f3f3;
                    margin: 0;
                    padding: 28px;
                    color: #111;
                }}
                .actions {{
                    max-width: 940px;
                    margin: 0 auto 14px auto;
                }}
                .back-btn {{
                    display: inline-block;
                    background: #d40511;
                    color: white;
                    text-decoration: none;
                    padding: 10px 14px;
                    border-radius: 8px;
                    font-weight: 700;
                }}
                .sheet {{
                    max-width: 940px;
                    margin: auto;
                    background: white;
                    border-radius: 10px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.08);
                    overflow: hidden;
                }}
                .topbar {{
                    background: #ffcc00;
                    padding: 14px 24px;
                    border-bottom: 4px solid #d40511;
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    gap: 16px;
                }}
                .topbar img {{
                    height: 42px;
                }}
                .topbar-right {{
                    font-size: 12px;
                    font-weight: 700;
                    color: #444;
                    text-transform: uppercase;
                    letter-spacing: 0.5px;
                }}
                .content {{
                    padding: 28px 34px 30px 34px;
                }}
                .title {{
                    font-size: 28px;
                    font-weight: 800;
                    text-align: center;
                    margin: 0 0 6px 0;
                }}
                .subtitle {{
                    text-align: center;
                    font-size: 15px;
                    color: #444;
                    margin-bottom: 18px;
                }}
                .awb-line {{
                    text-align: center;
                    font-size: 18px;
                    margin-bottom: 6px;
                }}
                .shipment-line {{
                    text-align: center;
                    font-size: 17px;
                    margin-bottom: 26px;
                }}
                .divider {{
                    border-top: 1px solid #cfcfcf;
                    margin: 18px 0 22px 0;
                }}
                .two-col-head {{
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    gap: 20px;
                    font-size: 18px;
                    font-weight: 700;
                    margin-bottom: 8px;
                }}
                .section-title {{
                    font-size: 22px;
                    font-weight: 800;
                    margin: 0 0 14px 0;
                }}
                .row {{
                    margin: 7px 0;
                    font-size: 16px;
                    line-height: 1.4;
                }}
                .small {{
                    font-size: 12px;
                    color: #444;
                    line-height: 1.45;
                }}
                .footer {{
                    margin-top: 10px;
                    font-size: 12px;
                    color: #444;
                }}
                .mono {{
                    letter-spacing: 0.2px;
                }}
            </style>
        </head>
        <body>
            <div class="actions">
                <a class="back-btn" href="/">← Torna alla ricerca</a>
            </div>

            <div class="sheet">
                <div class="topbar">
                    <img src="data:image/png;base64,{DHL_LOGO_BASE64}" alt="DHL Logo">
                    <div class="topbar-right">POD Manager DHL</div>
                </div>

                <div class="content">
                    <div class="title">CERTIFICAZIONE CONSEGNA</div>
                    <div class="subtitle">Riepilogo da archivio storico DHL certificato</div>

                    <div class="awb-line">Spedizione AWB <b class="mono">{awb}</b></div>
                    <div class="shipment-line">La spedizione <b class="mono">{awb}</b> risulta consegnata.</div>

                    <div class="divider"></div>

                    <div class="two-col-head">
                        <div>Consegna</div>
                        <div>Destinatario</div>
                    </div>

                    <div class="section-title">Dati spedizione</div>

                    <div class="row"><b>Stato consegna</b> {esito}</div>
                    <div class="row"><b>Ricevuto da</b> {firmatario}</div>
                    <div class="row"><b>Data consegna</b> {consegna}</div>
                    <div class="row"><b>Ora consegna</b> {ora_consegna}</div>
                    <div class="row"><b>Firmatario</b> {firmatario}</div>

                    <div class="row"><b>Nome</b> {cliente}</div>
                    <div class="row"><b>Indirizzo</b> {indirizzo}</div>
                    <div class="row"><b>CAP / Città</b> {cap} / {citta}</div>
                    <div class="row"><b>Nazione</b> {nazione}</div>

                    <div class="row"><b>AWB</b> {awb}</div>
                    <div class="row"><b>DDT</b> {ddt}</div>
                    <div class="row"><b>Riferimento mittente</b> {ddt}</div>
                    <div class="row"><b>Data ritiro</b> {ritiro}</div>
                    <div class="row"><b>Data consegna</b> {consegna}</div>
                    <div class="row"><b>Ora consegna</b> {ora_consegna}</div>
                    <div class="row"><b>Firma</b> {firmatario}</div>
                    <div class="row"><b>Esito consegna</b> {esito}</div>

                    <div class="divider"></div>

                    <div class="small">
                        Certificazione riepilogativa derivata da archivio storico DHL. Il presente documento riporta i dati disponibili nei file
                        certificati DHL forniti per il recupero archivio 2024-2025 e non sostituisce una POD PDF originale.
                    </div>

                    <div class="row" style="margin-top:16px;"><b>Nota</b></div>
                    <div class="footer">Generato il {generated_on}</div>
                    <div class="footer">Sistema: POD Manager DHL</div>
                </div>
            </div>
        </body>
    </html>
    """


@app.get("/", response_class=HTMLResponse)
def home(q: str = ""):
    rows, db_error = search_dhl_records(q)

    risultati_cert = ""
    if q and not db_error:
        for row in rows:
            esito = compute_delivery_status(row)
            destinatario = clean_text(row["cliente"], "")
            risultati_cert += f"""
            <tr>
                <td>{clean_text(row["ddt"], "")}</td>
                <td>{clean_text(row["awb"], "")}</td>
                <td>{destinatario}</td>
                <td>{fmt_date(row["data_ritiro"])}</td>
                <td>{fmt_date(row["data_consegna"] or row["delivery_datetime"])}</td>
                <td>{esito}</td>
                <td>
                    <a href="/cert/{clean_text(row["ddt"], "")}">
                        <button>Apri Certificazione</button>
                    </a>
                </td>
            </tr>
            """

    messaggio = ""
    if db_error:
        messaggio = f"<p style='color:red;'><b>{db_error}</b></p>"
    elif q and not risultati_cert:
        messaggio = "<p>Nessun risultato trovato.</p>"

    return f"""
    <html>
        <head>
            <title>POD Manager</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    background: #f4f4f4;
                    padding: 40px;
                }}
                .box {{
                    background: white;
                    padding: 20px;
                    border-radius: 10px;
                    max-width: 1200px;
                    margin: auto;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.08);
                }}
                input {{
                    width: 80%;
                    padding: 10px;
                }}
                button {{
                    padding: 10px;
                }}
                table {{
                    width: 100%;
                    margin-top: 20px;
                    border-collapse: collapse;
                }}
                td, th {{
                    border-bottom: 1px solid #ccc;
                    padding: 8px;
                    text-align: left;
                }}
                h2 {{
                    margin-top: 40px;
                }}
                .note {{
                    color: #666;
                    font-size: 13px;
                    margin-top: 10px;
                }}
            </style>
        </head>
        <body>
            <div class="box">
                <h1>POD Manager</h1>

                <form>
                    <input name="q" value="{q}" placeholder="Inserisci DDT, AWB, cliente, città o firmatario">
                    <button type="submit">Cerca</button>
                </form>

                <div class="note">
                    Ricerca su archivio DHL certificato reale (database SQLite).
                </div>

                {messaggio}

                <h2>DHL Certificata</h2>
                <table>
                    <tr>
                        <th>DDT</th>
                        <th>AWB</th>
                        <th>Destinatario</th>
                        <th>Ritiro</th>
                        <th>Consegna</th>
                        <th>Esito</th>
                        <th>Documento</th>
                    </tr>
                    {risultati_cert}
                </table>
            </div>
        </body>
    </html>
    """


@app.get("/cert/{ddt}", response_class=HTMLResponse)
def certificazione(ddt: str):
    row = get_record_by_ddt(ddt)

    if not row:
        return HTMLResponse("<h1>Certificazione non trovata</h1>", status_code=404)

    return render_cert_html(row)
