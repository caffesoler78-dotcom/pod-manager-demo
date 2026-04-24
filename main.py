from fastapi import FastAPI
from fastapi.responses import HTMLResponse, FileResponse, Response
import sqlite3
from pathlib import Path
from datetime import datetime
import re
from io import BytesIO
import urllib.request
import urllib.error

from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import HexColor, black, white
from reportlab.pdfgen import canvas

app = FastAPI()

DB_STORICO = Path("data/historic_dhl.db")
DB_DRIVE = Path("data/pod_drive_index.db")
DB_EXCEL = Path("data/excel_index.db")
LOGO_PATH = Path("dhl_logo_transparent.png")


def clean(x, fallback="non presente"):
    if x is None:
        return fallback
    x = str(x).strip()
    return x if x else fallback


def fmt_date(x):
    if not x:
        return "non presente"

    x = str(x).strip()

    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(x[:19], fmt).strftime("%d/%m/%Y")
        except Exception:
            pass

    return x


def fmt_time(x):
    if not x:
        return "non presente"

    x = str(x).strip()

    if " " in x:
        return x.split(" ")[1][:5]

    if ":" in x:
        return x[:5]

    return "non presente"


def clean_cliente(text):
    value = clean(text, "")
    value = re.sub(r"^\d+\s*", "", value)
    value = re.sub(r"\s{2,}", " ", value).strip(" .,-")
    return value if value else "non presente"


def clean_address(text):
    value = clean(text, "")

    if not value:
        return "non presente"

    value = re.sub(r"RICEVIMENTO.*", "", value, flags=re.IGNORECASE)
    value = re.sub(r"\b\d{1,2}[:\.]\d{2}\b", "", value)
    value = re.sub(r"\s*-\s*", " ", value)
    value = re.sub(r"\s{2,}", " ", value).strip(" .,-")

    return value if value else "non presente"


def to_title_name(text):
    value = clean(text, "")
    if not value:
        return "non presente"
    return " ".join(p.capitalize() for p in value.split())


def get_connection_storico():
    conn = sqlite3.connect(DB_STORICO)
    conn.row_factory = sqlite3.Row
    return conn


def get_pod_drive(ddt: str):
    if not DB_DRIVE.exists():
        return None

    conn = sqlite3.connect(DB_DRIVE)
    cur = conn.cursor()

    row = cur.execute(
        """
        SELECT file_id, file_name, drive_path
        FROM pod_drive
        WHERE ddt = ?
        LIMIT 1
        """,
        (ddt,)
    ).fetchone()

    conn.close()

    if not row:
        return None

    return {
        "file_id": row[0],
        "file_name": row[1],
        "drive_path": row[2],
    }


def get_excel_data(ddt: str):
    if not DB_EXCEL.exists():
        return None

    conn = sqlite3.connect(DB_EXCEL)
    cur = conn.cursor()

    row = cur.execute(
        """
        SELECT ddt, awb, cliente, citta, data_ritiro, data_consegna, esito
        FROM excel_data
        WHERE ddt = ?
        LIMIT 1
        """,
        (ddt,)
    ).fetchone()

    conn.close()

    if not row:
        return None

    return {
        "ddt": row[0],
        "awb": row[1],
        "cliente": row[2],
        "citta": row[3],
        "data_ritiro": row[4],
        "data_consegna": row[5],
        "esito": row[6],
    }


def parse_drive_path(drive_path):
    """
    Esempio:
    pod/MASALA MARZO 2026/SPA – ROVERETO/803440854.pdf
    """
    if not drive_path:
        return {
            "cliente": "non presente",
            "citta": "non presente",
            "file_name": "",
        }

    parts = drive_path.replace("\\", "/").split("/")
    file_name = parts[-1] if parts else ""

    folder = parts[-2] if len(parts) >= 2 else ""

    cliente = folder
    citta = ""

    if "–" in folder:
        a, b = folder.split("–", 1)
        cliente = a.strip()
        citta = b.strip()
    elif "-" in folder:
        a, b = folder.split("-", 1)
        cliente = a.strip()
        citta = b.strip()

    return {
        "cliente": cliente or "non presente",
        "citta": citta or "non presente",
        "file_name": file_name,
    }


def search_drive_records(q: str, limit: int = 100):
    if not DB_DRIVE.exists():
        return []

    q = (q or "").strip()
    if not q:
        return []

    pattern = f"%{q}%"

    conn = sqlite3.connect(DB_DRIVE)
    cur = conn.cursor()

    rows = cur.execute(
        """
        SELECT ddt, file_id, file_name, drive_path
        FROM pod_drive
        WHERE
            COALESCE(ddt, '') LIKE ?
            OR COALESCE(file_name, '') LIKE ?
            OR COALESCE(drive_path, '') LIKE ?
        ORDER BY ddt
        LIMIT ?
        """,
        (pattern, pattern, pattern, limit)
    ).fetchall()

    conn.close()
    return rows


@app.get("/open-pod/{ddt}")
def open_pod(ddt: str):
    pod = get_pod_drive(ddt)

    if not pod:
        return HTMLResponse("POD non trovata su Google Drive", status_code=404)

    file_id = pod["file_id"]
    file_name = pod["file_name"] or f"{ddt}.pdf"

    drive_url = f"https://drive.google.com/uc?export=download&id={file_id}"

    try:
        req = urllib.request.Request(
            drive_url,
            headers={"User-Agent": "Mozilla/5.0"}
        )
        response = urllib.request.urlopen(req, timeout=60)
        pdf_bytes = response.read()

    except urllib.error.HTTPError as e:
        return HTMLResponse(f"Errore Google Drive HTTP {e.code}", status_code=502)
    except Exception as e:
        return HTMLResponse(f"Errore apertura POD: {e}", status_code=502)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{file_name}"'}
    )


@app.get("/dhl_logo_transparent.png")
def logo():
    if LOGO_PATH.exists():
        return FileResponse(LOGO_PATH)
    return HTMLResponse("Logo non trovato", status_code=404)


def search_dhl_records(q: str, limit: int = 100):
    if not DB_STORICO.exists():
        return [], "Database storico non trovato: data/historic_dhl.db"

    q = (q or "").strip()
    if not q:
        return [], None

    pattern = f"%{q}%"

    conn = get_connection_storico()
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
            delivery_datetime
        FROM pod_records
        WHERE
            COALESCE(ddt, '') LIKE ?
            OR COALESCE(awb, '') LIKE ?
            OR COALESCE(cliente, '') LIKE ?
            OR COALESCE(citta, '') LIKE ?
            OR COALESCE(signatory, '') LIKE ?
            OR COALESCE(consignee_address, '') LIKE ?
        ORDER BY COALESCE(data_consegna, '') DESC
        LIMIT ?
        """,
        (pattern, pattern, pattern, pattern, pattern, pattern, limit)
    ).fetchall()

    conn.close()
    return rows, None


def get_row(ddt: str):
    if not DB_STORICO.exists():
        return None

    conn = get_connection_storico()

    row = conn.execute(
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
            delivery_datetime
        FROM pod_records
        WHERE ddt = ?
        LIMIT 1
        """,
        (ddt,)
    ).fetchone()

    conn.close()
    return row


def compute_esito(row):
    if row["data_consegna"] or row["delivery_datetime"]:
        return "Consegna avvenuta"
    return clean(row["event_remark"])


def get_signatory(row):
    sign = clean(row["signatory"], "")
    if sign:
        return to_title_name(sign)

    remark = clean(row["event_remark"], "")
    return to_title_name(remark) if remark else "non presente"


def cert_view_data(row):
    return {
        "awb": clean(row["awb"]),
        "ddt": clean(row["ddt"]),
        "cliente": clean_cliente(row["cliente"]),
        "indirizzo": clean_address(row["consignee_address"]),
        "cap": clean(row["cap"]),
        "citta": clean(row["citta"]),
        "nazione": clean(row["nazione"]),
        "ritiro": fmt_date(row["data_ritiro"]),
        "consegna": fmt_date(row["data_consegna"] or row["delivery_datetime"]),
        "ora": fmt_time(row["delivery_datetime"]),
        "firma": get_signatory(row),
        "esito": compute_esito(row),
        "generated_on": datetime.now().strftime("%d/%m/%Y alle %H:%M"),
    }


def render_cert_html(row):
    data = cert_view_data(row)
    ddt = data["ddt"]

    pod_btn = ""
    if get_pod_drive(ddt):
        pod_btn = f'<a class="pod-btn" href="/open-pod/{ddt}" target="_blank">Apri POD reale</a>'

    return f"""
    <html>
    <head>
        <title>Certificazione DHL {ddt}</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                background: #efefef;
                margin: 0;
                padding: 32px;
                color: #111;
            }}
            .top-actions {{
                max-width: 1120px;
                margin: 0 auto 16px auto;
                display: flex;
                gap: 10px;
            }}
            .back-btn, .pdf-btn, .pod-btn {{
                display: inline-block;
                color: white;
                text-decoration: none;
                padding: 12px 18px;
                border-radius: 10px;
                font-weight: 700;
                font-size: 15px;
            }}
            .back-btn {{ background: #d40511; }}
            .pdf-btn {{ background: #444; }}
            .pod-btn {{ background: #0b57d0; }}
            .sheet {{
                background: white;
                max-width: 1120px;
                margin: 0 auto;
                border-radius: 12px;
                box-shadow: 0 2px 12px rgba(0,0,0,0.08);
                overflow: hidden;
            }}
            .header {{
                background: #ffcc00;
                padding: 16px 28px;
                border-bottom: 4px solid #d40511;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }}
            .header img {{ height: 44px; }}
            .content {{ padding: 34px 48px 40px 48px; }}
            .title {{
                text-align: center;
                font-size: 36px;
                font-weight: 800;
                margin-bottom: 8px;
            }}
            .subtitle {{
                text-align: center;
                color: #444;
                font-size: 15px;
                margin-bottom: 22px;
            }}
            .centerblock {{
                text-align: center;
                line-height: 1.65;
                margin-bottom: 28px;
                font-size: 18px;
            }}
            .rule {{
                border-top: 1px solid #d3d3d3;
                margin: 24px 0;
            }}
            .grid {{
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 56px;
                margin-bottom: 22px;
            }}
            .section-title {{
                font-size: 24px;
                font-weight: 800;
                margin-bottom: 18px;
            }}
            .line {{
                margin: 8px 0;
                font-size: 15.5px;
                line-height: 1.5;
            }}
            .line b {{
                display: inline-block;
                min-width: 180px;
            }}
            .badge {{
                display: inline-block;
                background: #e6f4ea;
                color: #137333;
                border: 1px solid #b7e1cd;
                border-radius: 6px;
                padding: 4px 10px;
                font-size: 12px;
                font-weight: 700;
                margin-left: 10px;
            }}
            .small {{
                font-size: 12px;
                color: #555;
                line-height: 1.55;
            }}
            .note-title {{
                font-weight: 700;
                font-size: 14px;
                margin: 16px 0 8px 0;
            }}
        </style>
    </head>

    <body>
        <div class="top-actions">
            <a class="back-btn" href="/">← Torna alla ricerca</a>
            <a class="pdf-btn" href="/cert/{ddt}/pdf">Scarica PDF</a>
            {pod_btn}
        </div>

        <div class="sheet">
            <div class="header">
                <img src="/dhl_logo_transparent.png" alt="DHL">
                <b>POD MANAGER DHL</b>
            </div>

            <div class="content">
                <div class="title">CERTIFICAZIONE CONSEGNA</div>
                <div class="subtitle">Riepilogo da archivio storico DHL certificato</div>

                <div class="centerblock">
                    Spedizione AWB <b>{data["awb"]}</b><br>
                    La spedizione <b>{data["awb"]}</b> risulta consegnata.
                </div>

                <div class="rule"></div>

                <div class="grid">
                    <div>
                        <div class="section-title">Consegna</div>
                        <div class="line"><b>Stato consegna</b> {data["esito"]}<span class="badge">Consegnato</span></div>
                        <div class="line"><b>Ricevuto da</b> {data["firma"]}</div>
                        <div class="line"><b>Data consegna</b> {data["consegna"]}</div>
                        <div class="line"><b>Ora consegna</b> {data["ora"]}</div>
                        <div class="line"><b>Firmatario</b> {data["firma"]}</div>
                    </div>

                    <div>
                        <div class="section-title">Destinatario</div>
                        <div class="line"><b>Nome</b> {data["cliente"]}</div>
                        <div class="line"><b>Indirizzo</b> {data["indirizzo"]}</div>
                        <div class="line"><b>CAP / Città</b> {data["cap"]} / {data["citta"]}</div>
                        <div class="line"><b>Nazione</b> {data["nazione"]}</div>
                    </div>
                </div>

                <div class="rule"></div>

                <div class="section-title">Dati spedizione</div>
                <div class="line"><b>AWB</b> {data["awb"]}</div>
                <div class="line"><b>DDT</b> {data["ddt"]}</div>
                <div class="line"><b>Riferimento mittente</b> {data["ddt"]}</div>
                <div class="line"><b>Data ritiro</b> {data["ritiro"]}</div>
                <div class="line"><b>Data consegna</b> {data["consegna"]}</div>
                <div class="line"><b>Ora consegna</b> {data["ora"]}</div>
                <div class="line"><b>Firma</b> {data["firma"]}</div>
                <div class="line"><b>Esito consegna</b> {data["esito"]}</div>

                <div class="rule"></div>

                <div class="small">
                    Certificazione riepilogativa derivata da archivio storico DHL. Il presente documento riporta i dati disponibili nei file certificati DHL forniti per il recupero archivio 2024-2025 e non sostituisce una POD PDF originale.
                </div>

                <div class="note-title">Nota</div>
                <div class="small">Generato il {data["generated_on"]}</div>
                <div class="small">Sistema: POD Manager DHL</div>
            </div>
        </div>
    </body>
    </html>
    """


@app.get("/cert/{ddt}/pdf")
def certificazione_pdf(ddt: str):
    row = get_row(ddt)

    if not row:
        return HTMLResponse("Certificazione non trovata", status_code=404)

    data = cert_view_data(row)

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    c.setFillColor(HexColor("#efefef"))
    c.rect(0, 0, width, height, fill=1, stroke=0)

    c.setFillColor(white)
    c.rect(28, 28, width - 56, height - 56, fill=1, stroke=0)

    c.setFillColor(HexColor("#ffcc00"))
    c.rect(28, height - 80, width - 56, 52, fill=1, stroke=0)

    c.setFillColor(HexColor("#d40511"))
    c.rect(28, height - 83, width - 56, 3, fill=1, stroke=0)

    if LOGO_PATH.exists():
        c.drawImage(str(LOGO_PATH), 46, height - 62, width=72, height=18, mask="auto")

    c.setFillColor(black)
    c.setFont("Helvetica-Bold", 11)
    c.drawRightString(width - 46, height - 48, "POD MANAGER DHL")

    y = height - 125

    c.setFont("Helvetica-Bold", 26)
    c.drawCentredString(width / 2, y, "CERTIFICAZIONE CONSEGNA")
    y -= 24

    c.setFont("Helvetica", 11)
    c.drawCentredString(width / 2, y, "Riepilogo da archivio storico DHL certificato")
    y -= 35

    c.setFont("Helvetica", 14)
    c.drawCentredString(width / 2, y, f"Spedizione AWB {data['awb']}")
    y -= 18
    c.drawCentredString(width / 2, y, f"La spedizione {data['awb']} risulta consegnata.")
    y -= 35

    left = 62

    c.setFont("Helvetica-Bold", 16)
    c.drawString(left, y, "Consegna")
    c.drawString(left + 260, y, "Destinatario")
    y -= 24

    def line(x, y_pos, label, value):
        c.setFont("Helvetica-Bold", 9)
        c.drawString(x, y_pos, label)
        c.setFont("Helvetica", 9)
        c.drawString(x + 90, y_pos, str(value))

    y0 = y

    line(left, y, "Stato", data["esito"])
    y -= 14
    line(left, y, "Ricevuto da", data["firma"])
    y -= 14
    line(left, y, "Data", data["consegna"])
    y -= 14
    line(left, y, "Ora", data["ora"])

    y = y0
    line(left + 260, y, "Nome", data["cliente"])
    y -= 14
    line(left + 260, y, "Indirizzo", data["indirizzo"])
    y -= 14
    line(left + 260, y, "CAP / Città", f"{data['cap']} / {data['citta']}")
    y -= 14
    line(left + 260, y, "Nazione", data["nazione"])

    y -= 40

    c.setFont("Helvetica-Bold", 16)
    c.drawString(left, y, "Dati spedizione")
    y -= 24

    for label, value in [
        ("AWB", data["awb"]),
        ("DDT", data["ddt"]),
        ("Riferimento mittente", data["ddt"]),
        ("Data ritiro", data["ritiro"]),
        ("Data consegna", data["consegna"]),
        ("Ora consegna", data["ora"]),
        ("Firma", data["firma"]),
        ("Esito consegna", data["esito"]),
    ]:
        line(left, y, label, value)
        y -= 14

    c.showPage()
    c.save()

    pdf_bytes = buffer.getvalue()
    buffer.close()

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="certificazione_{ddt}.pdf"'}
    )


@app.get("/", response_class=HTMLResponse)
def home(q: str = ""):
    storico_rows, db_error = search_dhl_records(q)
    drive_rows = search_drive_records(q)

    storico_ddt = set()
    risultati = ""

    if q and not db_error:
        for row in storico_rows:
            ddt = clean(row["ddt"], "")
            storico_ddt.add(ddt)

            awb = clean(row["awb"], "")
            destinatario = clean_cliente(row["cliente"])
            citta = clean(row["citta"], "-")
            ritiro = fmt_date(row["data_ritiro"])
            consegna = fmt_date(row["data_consegna"] or row["delivery_datetime"])
            esito = compute_esito(row)

            pod_btn = ""
            if get_pod_drive(ddt):
                pod_btn = f'<a class="pod-btn" href="/open-pod/{ddt}" target="_blank">POD</a>'

            risultati += f"""
            <tr>
                <td>DHL Certificata</td>
                <td>{ddt}</td>
                <td>{awb}</td>
                <td>{destinatario}</td>
                <td>{citta}</td>
                <td>{ritiro}</td>
                <td>{consegna}</td>
                <td>{esito}</td>
                <td>
                    <a class="open-btn" href="/cert/{ddt}">Certificazione</a>
                    {pod_btn}
                </td>
            </tr>
            """

    if q:
        for ddt, file_id, file_name, drive_path in drive_rows:
            if ddt in storico_ddt:
                continue

            excel = get_excel_data(ddt)
            parsed = parse_drive_path(drive_path)

            awb = clean(excel["awb"], "-") if excel else "-"
            cliente = clean_cliente(excel["cliente"]) if excel and excel["cliente"] else parsed["cliente"]
            citta = clean(excel["citta"], parsed["citta"]) if excel else parsed["citta"]
            ritiro = fmt_date(excel["data_ritiro"]) if excel and excel["data_ritiro"] else "-"
            consegna = fmt_date(excel["data_consegna"]) if excel and excel["data_consegna"] else "-"
            esito = clean(excel["esito"], "POD disponibile") if excel else "POD disponibile"

            risultati += f"""
            <tr>
                <td>POD Drive</td>
                <td>{ddt}</td>
                <td>{awb}</td>
                <td>{cliente}</td>
                <td>{citta}</td>
                <td>{ritiro}</td>
                <td>{consegna}</td>
                <td>{esito}</td>
                <td>
                    <a class="pod-btn" href="/open-pod/{ddt}" target="_blank">POD</a>
                </td>
            </tr>
            """

    msg = ""
    if db_error:
        msg = f"<p style='color:red'><b>{db_error}</b></p>"
    elif q and not risultati:
        msg = "<p>Nessun risultato trovato.</p>"

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
                max-width: 1450px;
                margin: auto;
                box-shadow: 0 2px 10px rgba(0,0,0,0.08);
            }}
            .header {{
                background: #ffcc00;
                padding: 16px 24px;
                border-bottom: 4px solid #d40511;
                border-radius: 10px 10px 0 0;
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin: -20px -20px 20px -20px;
            }}
            .header img {{ height: 36px; }}
            h1 {{
                font-size: 42px;
                margin: 20px 0;
            }}
            form {{
                display: flex;
                gap: 10px;
            }}
            input {{
                flex: 1;
                padding: 14px;
                border: 1px solid #ccc;
                border-radius: 8px;
                font-size: 16px;
            }}
            button {{
                background: #d40511;
                color: white;
                border: 0;
                border-radius: 8px;
                padding: 14px 22px;
                font-weight: bold;
                cursor: pointer;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 25px;
            }}
            th, td {{
                border-bottom: 1px solid #ddd;
                padding: 12px;
                text-align: left;
                font-size: 14px;
            }}
            th {{
                background: #f1f1f1;
            }}
            .open-btn, .pod-btn {{
                display: inline-block;
                color: white;
                text-decoration: none;
                padding: 9px 13px;
                border-radius: 8px;
                font-weight: 700;
                font-size: 13px;
                margin-right: 6px;
            }}
            .open-btn {{ background: #d40511; }}
            .pod-btn {{ background: #0b57d0; }}
            .note {{
                color: #666;
                margin-top: 12px;
            }}
        </style>
    </head>

    <body>
        <div class="box">
            <div class="header">
                <img src="/dhl_logo_transparent.png" alt="DHL">
                <b>POD MANAGER DHL</b>
            </div>

            <h1>POD Manager</h1>

            <form>
                <input name="q" value="{q}" placeholder="Inserisci DDT, AWB, cliente, città o firmatario">
                <button type="submit">Cerca</button>
            </form>

            <div class="note">
                Ricerca su archivio storico DHL + POD reali Drive + dati Excel.
            </div>

            {msg}

            <h2>DHL Certificata / POD Drive</h2>

            <table>
                <tr>
                    <th>Fonte</th>
                    <th>DDT</th>
                    <th>AWB</th>
                    <th>Destinatario</th>
                    <th>Città</th>
                    <th>Ritiro</th>
                    <th>Consegna</th>
                    <th>Esito</th>
                    <th>Documento</th>
                </tr>
                {risultati}
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
