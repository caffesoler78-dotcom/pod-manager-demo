from fastapi import FastAPI
from fastapi.responses import HTMLResponse, FileResponse
import sqlite3
from pathlib import Path
from datetime import datetime

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


def fmt_date(x):
    if not x:
        return "non presente"

    text = str(x).strip()

    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y"):
        try:
            dt = datetime.strptime(text[:19], fmt)
            return dt.strftime("%d/%m/%Y")
        except Exception:
            pass

    return text


def fmt_time(x):
    if not x:
        return "non presente"

    text = str(x).strip()

    if " " in text:
        try:
            return text.split(" ")[1][:5]
        except Exception:
            return "non presente"

    if ":" in text:
        return text[:5]

    return "non presente"


def compute_esito(row):
    if row["data_consegna"] or row["delivery_datetime"]:
        return "Consegna avvenuta"
    return clean(row["event_remark"])


def get_signatory(row):
    sign = clean(row["signatory"], "")
    if sign:
        return sign
    fallback = clean(row["event_remark"], "")
    return fallback if fallback else "non presente"


def search_dhl_records(q: str, limit: int = 100):
    if not DB_PATH.exists():
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


def get_row(ddt: str):
    if not DB_PATH.exists():
        return None

    conn = get_connection()
    row = conn.execute(
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


@app.get("/dhl_logo_transparent.png")
def logo():
    if LOGO_PATH.exists():
        return FileResponse(LOGO_PATH)
    return HTMLResponse("Logo non trovato", status_code=404)


def render_cert_html(row):
    awb = clean(row["awb"])
    ddt = clean(row["ddt"])
    cliente = clean(row["cliente"])
    indirizzo = clean(row["consignee_address"])
    cap = clean(row["cap"])
    citta = clean(row["citta"])
    nazione = clean(row["nazione"])
    ritiro = fmt_date(row["data_ritiro"])
    consegna = fmt_date(row["data_consegna"] or row["delivery_datetime"])
    ora = fmt_time(row["delivery_datetime"])
    firma = get_signatory(row)
    esito = compute_esito(row)
    generated_on = datetime.now().strftime("%d/%m/%Y alle %H:%M")

    return f"""
    <html>
    <head>
        <title>Certificazione DHL {ddt}</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                background: #efefef;
                padding: 32px;
                margin: 0;
                color: #111;
            }}
            .top-actions {{
                max-width: 1080px;
                margin: 0 auto 16px auto;
            }}
            .back-btn {{
                display: inline-block;
                background: #d40511;
                color: white;
                text-decoration: none;
                padding: 12px 18px;
                border-radius: 10px;
                font-weight: 700;
                font-size: 15px;
            }}
            .sheet {{
                background: white;
                max-width: 1080px;
                margin: 0 auto;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.08);
                overflow: hidden;
            }}
            .header {{
                background: #ffcc00;
                padding: 18px 28px;
                border-bottom: 3px solid #d40511;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }}
            .header img {{
                height: 34px;
            }}
            .header-right {{
                font-weight: 700;
                font-size: 14px;
                letter-spacing: 0.2px;
            }}
            .content {{
                padding: 34px 48px 36px 48px;
            }}
            .title {{
                text-align: center;
                font-size: 34px;
                font-weight: 800;
                margin: 0 0 8px 0;
                letter-spacing: 0.3px;
            }}
            .subtitle {{
                text-align: center;
                color: #444;
                font-size: 15px;
                margin-bottom: 22px;
            }}
            .centerblock {{
                text-align: center;
                line-height: 1.6;
                margin-bottom: 28px;
                font-size: 18px;
            }}
            .rule {{
                border-top: 1px solid #cfcfcf;
                margin: 22px 0 24px 0;
            }}
            .columns-head {{
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 30px;
                font-size: 19px;
                font-weight: 700;
                margin-bottom: 14px;
            }}
            .section-title {{
                font-size: 22px;
                font-weight: 800;
                margin-bottom: 18px;
            }}
            .rows {{
                max-width: 760px;
            }}
            .line {{
                margin: 10px 0;
                font-size: 17px;
                line-height: 1.5;
            }}
            .line b {{
                display: inline-block;
                min-width: 190px;
                font-weight: 700;
            }}
            .spacer {{
                height: 10px;
            }}
            .small {{
                font-size: 12px;
                color: #444;
                line-height: 1.5;
            }}
            .note-title {{
                font-weight: 700;
                font-size: 14px;
                margin: 14px 0 8px 0;
            }}
        </style>
    </head>
    <body>
        <div class="top-actions">
            <a class="back-btn" href="/">← Torna alla ricerca</a>
        </div>

        <div class="sheet">
            <div class="header">
                <img src="/dhl_logo_transparent.png" alt="DHL">
                <div class="header-right">POD MANAGER DHL</div>
            </div>

            <div class="content">
                <div class="title">CERTIFICAZIONE CONSEGNA</div>
                <div class="subtitle">Riepilogo da archivio storico DHL certificato</div>

                <div class="centerblock">
                    Spedizione AWB <b>{awb}</b><br>
                    La spedizione <b>{awb}</b> risulta consegnata.
                </div>

                <div class="rule"></div>

                <div class="columns-head">
                    <div>Consegna</div>
                    <div>Destinatario</div>
                </div>

                <div class="section-title">Dati spedizione</div>

                <div class="rows">
                    <div class="line"><b>Stato consegna</b> {esito}</div>
                    <div class="line"><b>Ricevuto da</b> {firma}</div>
                    <div class="line"><b>Data consegna</b> {consegna}</div>
                    <div class="line"><b>Ora consegna</b> {ora}</div>
                    <div class="line"><b>Firmatario</b> {firma}</div>

                    <div class="spacer"></div>

                    <div class="line"><b>Nome</b> {cliente}</div>
                    <div class="line"><b>Indirizzo</b> {indirizzo}</div>
                    <div class="line"><b>CAP / Città</b> {cap} / {citta}</div>
                    <div class="line"><b>Nazione</b> {nazione}</div>

                    <div class="spacer"></div>

                    <div class="line"><b>AWB</b> {awb}</div>
                    <div class="line"><b>DDT</b> {ddt}</div>
                    <div class="line"><b>Riferimento mittente</b> {ddt}</div>
                    <div class="line"><b>Data ritiro</b> {ritiro}</div>
                    <div class="line"><b>Data consegna</b> {consegna}</div>
                    <div class="line"><b>Ora consegna</b> {ora}</div>
                    <div class="line"><b>Firma</b> {firma}</div>
                    <div class="line"><b>Esito consegna</b> {esito}</div>
                </div>

                <div class="rule"></div>

                <div class="small">
                    Certificazione riepilogativa derivata da archivio storico DHL. Il presente documento riporta i dati disponibili nei file
                    certificati DHL forniti per il recupero archivio 2024-2025 e non sostituisce una POD PDF originale.
                </div>

                <div class="note-title">Nota</div>
                <div class="small">Generato il {generated_on}</div>
                <div class="small">Sistema: POD Manager DHL</div>
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
            ddt = clean(row["ddt"], "")
            awb = clean(row["awb"], "")
            destinatario = clean(row["cliente"], "")
            ritiro = fmt_date(row["data_ritiro"])
            consegna = fmt_date(row["data_consegna"] or row["delivery_datetime"])
            esito = compute_esito(row)

            risultati_cert += f"""
            <tr>
                <td>{ddt}</td>
                <td>{awb}</td>
                <td>{destinatario}</td>
                <td>{ritiro}</td>
                <td>{consegna}</td>
                <td>{esito}</td>
                <td>
                    <a href="/cert/{ddt}">
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
    row = get_row(ddt)

    if not row:
        return HTMLResponse("<h1>Certificazione non trovata</h1>", status_code=404)

    return render_cert_html(row)
