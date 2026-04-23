from fastapi import FastAPI
from fastapi.responses import HTMLResponse, FileResponse, Response
import sqlite3
from pathlib import Path
from datetime import datetime
import re
from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import HexColor, black, white
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas

app = FastAPI()

DB_PATH = Path("data/historic_dhl.db")
POD_ATTUALI_DB = Path("data/pod_attuali_index.db")
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


def to_title_name(text):
    value = clean(text, "")
    if not value:
        return "non presente"
    return " ".join(part.capitalize() for part in value.split())


def get_signatory(row):
    sign = clean(row["signatory"], "")
    if sign:
        return to_title_name(sign)
    fallback = clean(row["event_remark"], "")
    return to_title_name(fallback) if fallback else "non presente"


def clean_cliente(text):
    value = clean(text, "")
    if not value:
        return "non presente"

    value = re.sub(r"^\d+\s*", "", value)
    value = re.sub(r"\s{2,}", " ", value).strip(" .,-")
    return value if value else "non presente"


def clean_address(text):
    value = clean(text, "")
    if not value:
        return "non presente"

    value = re.sub(r"RICEVIMENTO.*", "", value, flags=re.IGNORECASE)
    value = re.sub(r"\b\d{1,2}[:\.]\d{2}\b", "", value)
    value = re.sub(r"\b\d{1,2}\b(?=\s+\d{1,2}[:\.]?\d*)", "", value)
    value = re.sub(r"\s*-\s*", " ", value)
    value = re.sub(r"\s{2,}", " ", value).strip(" .,-")

    return value if value else "non presente"


def search_dhl_records(q: str, limit: int = 100):
    if not DB_PATH.exists():
        return [], "Database storico non trovato: data/historic_dhl.db"

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


def get_pod_reale(ddt: str):
    if not POD_ATTUALI_DB.exists():
        return None

    conn = sqlite3.connect(POD_ATTUALI_DB)
    cur = conn.cursor()

    row = cur.execute(
        """
        SELECT full_path
        FROM pod_attuali
        WHERE ddt = ?
        LIMIT 1
        """,
        (ddt,)
    ).fetchone()

    conn.close()

    if row and row[0]:
        return row[0]

    return None


@app.get("/open-pod/{ddt}")
def open_pod(ddt: str):
    path = get_pod_reale(ddt)

    if not path:
        return HTMLResponse("POD non trovata nell'indice attuale", status_code=404)

    file_path = Path(path)

    if not file_path.exists():
        return HTMLResponse("File POD non trovato sul percorso salvato", status_code=404)

    return FileResponse(file_path, filename=file_path.name)


@app.get("/dhl_logo_transparent.png")
def logo():
    if LOGO_PATH.exists():
        return FileResponse(LOGO_PATH)
    return HTMLResponse("Logo non trovato", status_code=404)


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
    if get_pod_reale(ddt):
        pod_btn = f'<a class="pod-btn" href="/open-pod/{ddt}" target="_blank">Apri POD reale</a>'

    return f"""
    <html>
    <head>
        <title>Certificazione DHL {data["ddt"]}</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                background: #efefef;
                padding: 32px;
                margin: 0;
                color: #111;
            }}

            .top-actions {{
                max-width: 1120px;
                margin: 0 auto 16px auto;
                display: flex;
                gap: 10px;
                flex-wrap: wrap;
            }}

            .back-btn, .pdf-btn, .pod-btn {{
                display: inline-block;
                color: white;
                text-decoration: none;
                padding: 12px 18px;
                border-radius: 10px;
                font-weight: 700;
                font-size: 15px;
                box-shadow: 0 2px 6px rgba(0,0,0,0.12);
            }}

            .back-btn {{
                background: #d40511;
            }}

            .pdf-btn {{
                background: #444;
            }}

            .pod-btn {{
                background: #0b57d0;
            }}

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

            .header img {{
                height: 44px;
            }}

            .header-right {{
                font-weight: 800;
                font-size: 15px;
                letter-spacing: 0.2px;
            }}

            .content {{
                padding: 34px 48px 40px 48px;
            }}

            .title {{
                text-align: center;
                font-size: 36px;
                font-weight: 800;
                margin: 0 0 8px 0;
                letter-spacing: 0.5px;
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
                color: #333;
                font-weight: 700;
            }}

            .shipment-title {{
                font-size: 24px;
                font-weight: 800;
                margin: 6px 0 18px 0;
            }}

            .rows {{
                max-width: 820px;
            }}

            .rows .line b {{
                min-width: 190px;
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
                vertical-align: middle;
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

            @media (max-width: 900px) {{
                .content {{
                    padding: 28px 24px 30px 24px;
                }}

                .grid {{
                    grid-template-columns: 1fr;
                    gap: 18px;
                }}

                .line b,
                .rows .line b {{
                    display: block;
                    min-width: 0;
                    margin-bottom: 2px;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="top-actions">
            <a class="back-btn" href="/">← Torna alla ricerca</a>
            <a class="pdf-btn" href="/cert/{data["ddt"]}/pdf">Scarica PDF</a>
            {pod_btn}
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

                <div class="shipment-title">Dati spedizione</div>

                <div class="rows">
                    <div class="line"><b>AWB</b> {data["awb"]}</div>
                    <div class="line"><b>DDT</b> {data["ddt"]}</div>
                    <div class="line"><b>Riferimento mittente</b> {data["ddt"]}</div>
                    <div class="line"><b>Data ritiro</b> {data["ritiro"]}</div>
                    <div class="line"><b>Data consegna</b> {data["consegna"]}</div>
                    <div class="line"><b>Ora consegna</b> {data["ora"]}</div>
                    <div class="line"><b>Firma</b> {data["firma"]}</div>
                    <div class="line"><b>Esito consegna</b> {data["esito"]}</div>
                </div>

                <div class="rule"></div>

                <div class="small">
                    Certificazione riepilogativa derivata da archivio storico DHL. Il presente documento riporta i dati disponibili nei file
                    certificati DHL forniti per il recupero archivio 2024-2025 e non sostituisce una POD PDF originale.
                </div>

                <div class="note-title">Nota</div>
                <div class="small">Generato il {data["generated_on"]}</div>
                <div class="small">Sistema: POD Manager DHL</div>
            </div>
        </div>
    </body>
    </html>
    """


def draw_wrapped_text(c, text, x, y, max_width, font_name="Helvetica", font_size=10, leading=11):
    c.setFont(font_name, font_size)
    words = str(text).split()
    line = ""
    current_y = y

    for word in words:
        trial = f"{line} {word}".strip()
        if stringWidth(trial, font_name, font_size) <= max_width:
            line = trial
        else:
            c.drawString(x, current_y, line)
            current_y -= leading
            line = word

    if line:
        c.drawString(x, current_y, line)
        current_y -= leading

    return current_y


@app.get("/cert/{ddt}/pdf")
def certificazione_pdf(ddt: str):
    row = get_row(ddt)
    if not row:
        return HTMLResponse("Certificazione non trovata", status_code=404)

    data = cert_view_data(row)

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    yellow = HexColor("#ffcc00")
    red = HexColor("#d40511")
    gray_line = HexColor("#d3d3d3")
    gray_text = HexColor("#555555")

    card_x = 28
    card_y = 28
    card_w = width - 56
    card_h = height - 56

    c.setFillColor(HexColor("#efefef"))
    c.rect(0, 0, width, height, fill=1, stroke=0)

    c.setFillColor(white)
    c.roundRect(card_x, card_y, card_w, card_h, 10, fill=1, stroke=0)

    header_h = 52
    c.setFillColor(yellow)
    c.roundRect(card_x, height - card_y - header_h, card_w, header_h, 10, fill=1, stroke=0)
    c.setFillColor(yellow)
    c.rect(card_x, height - card_y - header_h, card_w, header_h - 10, fill=1, stroke=0)

    c.setFillColor(red)
    c.rect(card_x, height - card_y - header_h - 3, card_w, 3, fill=1, stroke=0)

    if LOGO_PATH.exists():
        c.drawImage(str(LOGO_PATH), card_x + 18, height - card_y - 34, width=72, height=18, mask="auto")

    c.setFillColor(black)
    c.setFont("Helvetica-Bold", 11)
    c.drawRightString(card_x + card_w - 18, height - card_y - 20, "POD MANAGER DHL")

    left = card_x + 34
    right = card_x + card_w - 34
    y = height - card_y - header_h - 38

    c.setFont("Helvetica-Bold", 26)
    c.drawCentredString(width / 2, y, "CERTIFICAZIONE CONSEGNA")
    y -= 20

    c.setFillColor(gray_text)
    c.setFont("Helvetica", 11)
    c.drawCentredString(width / 2, y, "Riepilogo da archivio storico DHL certificato")
    y -= 28

    c.setFillColor(black)
    c.setFont("Helvetica", 14)
    c.drawCentredString(width / 2, y, f"Spedizione AWB {data['awb']}")
    y -= 18
    c.drawCentredString(width / 2, y, f"La spedizione {data['awb']} risulta consegnata.")
    y -= 22

    c.setStrokeColor(gray_line)
    c.line(left, y, right, y)
    y -= 26

    col_gap = 36
    col_w = (right - left - col_gap) / 2
    col1_x = left
    col2_x = left + col_w + col_gap
    col_y_top = y

    c.setFillColor(black)
    c.setFont("Helvetica-Bold", 18)
    c.drawString(col1_x, col_y_top, "Consegna")
    c.drawString(col2_x, col_y_top, "Destinatario")

    y1 = col_y_top - 24
    y2 = col_y_top - 24

    def draw_label_value(x, y_pos, label, value, label_w=110, max_w=col_w - 110):
        c.setFont("Helvetica-Bold", 10)
        c.drawString(x, y_pos, label)
        return draw_wrapped_text(c, value, x + label_w, y_pos, max_w, "Helvetica", 10, 11)

    y1 = draw_label_value(col1_x, y1, "Stato consegna", data["esito"])
    y1 = draw_label_value(col1_x, y1 - 2, "Ricevuto da", data["firma"])
    y1 = draw_label_value(col1_x, y1 - 2, "Data consegna", data["consegna"])
    y1 = draw_label_value(col1_x, y1 - 2, "Ora consegna", data["ora"])
    y1 = draw_label_value(col1_x, y1 - 2, "Firmatario", data["firma"])

    y2 = draw_label_value(col2_x, y2, "Nome", data["cliente"], 80, col_w - 80)
    y2 = draw_label_value(col2_x, y2 - 2, "Indirizzo", data["indirizzo"], 80, col_w - 80)
    y2 = draw_label_value(col2_x, y2 - 2, "CAP / Città", f"{data['cap']} / {data['citta']}", 80, col_w - 80)
    y2 = draw_label_value(col2_x, y2 - 2, "Nazione", data["nazione"], 80, col_w - 80)

    y = min(y1, y2) - 14
    c.setStrokeColor(gray_line)
    c.line(left, y, right, y)
    y -= 24

    c.setFillColor(black)
    c.setFont("Helvetica-Bold", 18)
    c.drawString(left, y, "Dati spedizione")
    y -= 22

    y = draw_label_value(left, y, "AWB", data["awb"], 120, 500)
    y = draw_label_value(left, y - 2, "DDT", data["ddt"], 120, 500)
    y = draw_label_value(left, y - 2, "Riferimento mittente", data["ddt"], 120, 500)
    y = draw_label_value(left, y - 2, "Data ritiro", data["ritiro"], 120, 500)
    y = draw_label_value(left, y - 2, "Data consegna", data["consegna"], 120, 500)
    y = draw_label_value(left, y - 2, "Ora consegna", data["ora"], 120, 500)
    y = draw_label_value(left, y - 2, "Firma", data["firma"], 120, 500)
    y = draw_label_value(left, y - 2, "Esito consegna", data["esito"], 120, 500)

    y -= 8
    c.setStrokeColor(gray_line)
    c.line(left, y, right, y)
    y -= 18

    c.setFillColor(gray_text)
    y = draw_wrapped_text(
        c,
        "Certificazione riepilogativa derivata da archivio storico DHL. Il presente documento riporta i dati disponibili nei file certificati DHL forniti per il recupero archivio 2024-2025 e non sostituisce una POD PDF originale.",
        left,
        y,
        right - left,
        "Helvetica",
        8.5,
        11,
    )

    c.setFillColor(black)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(left, y - 4, "Nota")
    y -= 18

    c.setFillColor(gray_text)
    c.setFont("Helvetica", 8.5)
    c.drawString(left, y, f"Generato il {data['generated_on']}")
    y -= 12
    c.drawString(left, y, "Sistema: POD Manager DHL")

    c.showPage()
    c.save()

    pdf_bytes = buffer.getvalue()
    buffer.close()

    filename = f"certificazione_{data['ddt']}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@app.get("/", response_class=HTMLResponse)
def home(q: str = ""):
    rows, db_error = search_dhl_records(q)

    risultati_cert = ""
    if q and not db_error:
        for row in rows:
            ddt = clean(row["ddt"], "")
            awb = clean(row["awb"], "")
            destinatario = clean_cliente(row["cliente"])
            ritiro = fmt_date(row["data_ritiro"])
            consegna = fmt_date(row["data_consegna"] or row["delivery_datetime"])
            esito = compute_esito(row)

            pod_btn = ""
            if get_pod_reale(ddt):
                pod_btn = f'<a class="pod-btn" href="/open-pod/{ddt}" target="_blank">POD</a>'

            risultati_cert += f"""
            <tr>
                <td>{ddt}</td>
                <td>{awb}</td>
                <td>{destinatario}</td>
                <td>{ritiro}</td>
                <td>{consegna}</td>
                <td>{esito}</td>
                <td>
                    <a class="open-btn" href="/cert/{ddt}">Certificazione</a>
                    {pod_btn}
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

                .header img {{
                    height: 36px;
                }}

                .header-right {{
                    font-weight: 800;
                    font-size: 15px;
                }}

                .search-title {{
                    font-size: 34px;
                    font-weight: 800;
                    margin: 0 0 16px 0;
                }}

                .search-bar {{
                    display: flex;
                    gap: 10px;
                    margin-bottom: 10px;
                }}

                input {{
                    flex: 1;
                    padding: 12px;
                    font-size: 15px;
                    border: 1px solid #ccc;
                    border-radius: 8px;
                }}

                button {{
                    padding: 12px 16px;
                    border: 0;
                    border-radius: 8px;
                    background: #d40511;
                    color: white;
                    font-weight: 700;
                    cursor: pointer;
                }}

                table {{
                    width: 100%;
                    margin-top: 20px;
                    border-collapse: collapse;
                }}

                td, th {{
                    border-bottom: 1px solid #ddd;
                    padding: 10px 8px;
                    text-align: left;
                    font-size: 14px;
                }}

                h2 {{
                    margin-top: 34px;
                    font-size: 24px;
                }}

                .note {{
                    color: #666;
                    font-size: 13px;
                    margin-top: 10px;
                }}

                .open-btn, .pod-btn {{
                    display: inline-block;
                    color: white;
                    text-decoration: none;
                    padding: 8px 12px;
                    border-radius: 8px;
                    font-weight: 700;
                    font-size: 13px;
                    margin-right: 6px;
                }}

                .open-btn {{
                    background: #d40511;
                }}

                .pod-btn {{
                    background: #0b57d0;
                }}
            </style>
        </head>
        <body>
            <div class="box">
                <div class="header">
                    <img src="/dhl_logo_transparent.png" alt="DHL">
                    <div class="header-right">POD MANAGER DHL</div>
                </div>

                <div class="search-title">POD Manager</div>

                <form>
                    <div class="search-bar">
                        <input name="q" value="{q}" placeholder="Inserisci DDT, AWB, cliente, città o firmatario">
                        <button type="submit">Cerca</button>
                    </div>
                </form>

                <div class="note">
                    Ricerca su archivio DHL certificato reale (database storico) + POD attuali indicizzate.
                </div>

                {messaggio}

                <h2>DHL Certificata / POD Attuali</h2>
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
