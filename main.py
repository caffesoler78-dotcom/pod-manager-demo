from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import sqlite3
from pathlib import Path

app = FastAPI()

DB_PATH = Path("data/historic_dhl.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def search_dhl_records(q: str, limit: int = 100):
    if not DB_PATH.exists():
        return [], "Database non trovato: data/historic_dhl.db"

    q = (q or "").strip()
    if not q:
        return [], None

    pattern = f"%{q}%"

    conn = get_connection()
    cur = conn.cursor()

    sql = """
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
            delivery_datetime,
            source_type
        FROM pod_records
        WHERE
            COALESCE(ddt, '') LIKE ?
            OR COALESCE(awb, '') LIKE ?
            OR COALESCE(cliente, '') LIKE ?
            OR COALESCE(citta, '') LIKE ?
            OR COALESCE(signatory, '') LIKE ?
            OR COALESCE(event_remark, '') LIKE ?
        ORDER BY
            CASE
                WHEN COALESCE(ddt, '') = ? THEN 0
                WHEN COALESCE(awb, '') = ? THEN 1
                ELSE 2
            END,
            COALESCE(data_consegna, '') DESC
        LIMIT ?
    """

    rows = cur.execute(
        sql,
        (pattern, pattern, pattern, pattern, pattern, pattern, q, q, limit)
    ).fetchall()

    conn.close()
    return rows, None


def get_record_by_ddt(ddt: str):
    if not DB_PATH.exists():
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
            data_ritiro,
            data_consegna,
            signatory,
            event_remark,
            delivery_datetime,
            source_type
        FROM pod_records
        WHERE ddt = ?
        LIMIT 1
        """,
        (ddt,)
    ).fetchone()

    conn.close()
    return row


def render_cert_html(cert):
    firmatario = cert["signatory"] or "non presente"
    esito = cert["event_remark"] or "Consegna avvenuta"
    consegna = cert["data_consegna"] or "non presente"
    ritiro = cert["data_ritiro"] or "non presente"
    ora = "non presente"

    if cert["delivery_datetime"]:
        dt = str(cert["delivery_datetime"]).strip()
        if " " in dt:
            parts = dt.split(" ")
            if len(parts) >= 2:
                ora = parts[1][:5]

    return f"""
    <html>
        <head>
            <title>Certificazione DHL</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    background: #f4f4f4;
                    margin: 0;
                    padding: 30px;
                }}
                .sheet {{
                    max-width: 980px;
                    margin: auto;
                    background: white;
                    padding: 36px 44px;
                    border-radius: 10px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.08);
                }}
                .title {{
                    text-align: center;
                    font-size: 28px;
                    font-weight: 700;
                    margin-bottom: 8px;
                }}
                .subtitle {{
                    text-align: center;
                    font-size: 15px;
                    color: #444;
                    margin-bottom: 28px;
                }}
                .line {{
                    border-top: 1px solid #cfcfcf;
                    margin: 22px 0;
                }}
                .section-title {{
                    font-size: 20px;
                    font-weight: 700;
                    margin-bottom: 14px;
                }}
                .row {{
                    margin: 8px 0;
                    font-size: 16px;
                    line-height: 1.45;
                }}
                .small {{
                    font-size: 12px;
                    color: #444;
                    line-height: 1.45;
                }}
                .actions {{
                    max-width: 980px;
                    margin: 0 auto 16px auto;
                }}
                .btn {{
                    display: inline-block;
                    padding: 10px 14px;
                    background: #d40511;
                    color: white;
                    text-decoration: none;
                    border-radius: 8px;
                    font-weight: 700;
                }}
            </style>
        </head>
        <body>
            <div class="actions">
                <a class="btn" href="/">← Torna alla ricerca</a>
            </div>

            <div class="sheet">
                <div class="title">CERTIFICAZIONE CONSEGNA</div>
                <div class="subtitle">Riepilogo da archivio storico DHL certificato</div>

                <div class="line"></div>

                <div class="section-title">Stato consegna</div>
                <div class="row"><b>Stato:</b> {esito}</div>
                <div class="row"><b>Ricevuto da:</b> {firmatario}</div>
                <div class="row"><b>Data consegna:</b> {consegna}</div>
                <div class="row"><b>Ora consegna:</b> {ora}</div>

                <div class="line"></div>

                <div class="section-title">Dati spedizione</div>
                <div class="row"><b>Nome:</b> {cert["cliente"] or "non presente"}</div>
                <div class="row"><b>Indirizzo:</b> non presente</div>
                <div class="row"><b>CAP / Città:</b> {(cert["cap"] or "non presente")} / {(cert["citta"] or "non presente")}</div>
                <div class="row"><b>Nazione:</b> {cert["nazione"] or "non presente"}</div>
                <div class="row"><b>AWB:</b> {cert["awb"] or "non presente"}</div>
                <div class="row"><b>DDT:</b> {cert["ddt"] or "non presente"}</div>
                <div class="row"><b>Riferimento mittente:</b> {cert["ddt"] or "non presente"}</div>
                <div class="row"><b>Data ritiro:</b> {ritiro}</div>
                <div class="row"><b>Data consegna:</b> {consegna}</div>
                <div class="row"><b>Ora consegna:</b> {ora}</div>
                <div class="row"><b>Firma:</b> {firmatario}</div>
                <div class="row"><b>Esito consegna:</b> {esito}</div>

                <div class="line"></div>

                <div class="small">
                    Certificazione riepilogativa derivata da archivio storico DHL. Il presente
                    documento riporta i dati disponibili nei file certificati DHL forniti per il recupero archivio.
                </div>

                <div class="line"></div>

                <div class="small">
                    Generato automaticamente dal sistema POD Manager
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
        for cert in rows:
            esito = cert["event_remark"] or "Consegna avvenuta"
            destinatario = cert["cliente"] or ""
            risultati_cert += f"""
            <tr>
                <td>{cert["ddt"] or ""}</td>
                <td>{cert["awb"] or ""}</td>
                <td>{destinatario}</td>
                <td>{cert["data_ritiro"] or ""}</td>
                <td>{cert["data_consegna"] or ""}</td>
                <td>{esito}</td>
                <td>
                    <a href="/cert/{cert["ddt"]}">
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
    cert = get_record_by_ddt(ddt)

    if not cert:
        return HTMLResponse("<h1>Certificazione non trovata</h1>", status_code=404)

    return render_cert_html(cert)
