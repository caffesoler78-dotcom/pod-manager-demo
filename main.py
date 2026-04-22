from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()

PODS = [
    {
        "ddt": "803401182",
        "cliente": "ALSTOM",
        "citta": "VADO LIGURE",
        "url": "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf"
    },
    {
        "ddt": "803414507",
        "cliente": "TRENITALIA",
        "citta": "NAPOLI",
        "url": "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf"
    }
]

CERTIFICATE = [
    {
        "ddt": "803128294",
        "awb": "7021037354",
        "nome": "ALSTOM SERVICES ITALIA SPA",
        "indirizzo": "VIA DANDALO 18/C IMC",
        "citta": "TREVISO",
        "cap": "31100",
        "nazione": "ITALY",
        "ritiro": "07/10/2025",
        "consegna": "08/10/2025",
        "ora": "10:11",
        "firmatario": "Roberto fantin",
        "esito": "Consegna avvenuta",
        "destinatario": "ALSTOM VADO LIGURE"
    },
    {
        "ddt": "803414507",
        "awb": "8253987654",
        "nome": "TRENITALIA SPA",
        "indirizzo": "NAPOLI CENTRALE",
        "citta": "NAPOLI",
        "cap": "80100",
        "nazione": "ITALY",
        "ritiro": "16/04/2026",
        "consegna": "17/04/2026",
        "ora": "09:45",
        "firmatario": "Mario Rossi",
        "esito": "Consegna avvenuta",
        "destinatario": "TRENITALIA NAPOLI"
    }
]

def render_cert_html(cert):
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
                <div class="row"><b>Stato:</b> {cert['esito']}</div>
                <div class="row"><b>Ricevuto da:</b> {cert['firmatario']}</div>
                <div class="row"><b>Data consegna:</b> {cert['consegna']}</div>
                <div class="row"><b>Ora consegna:</b> {cert['ora']}</div>

                <div class="line"></div>

                <div class="section-title">Dati spedizione</div>
                <div class="row"><b>Nome:</b> {cert['nome']}</div>
                <div class="row"><b>Indirizzo:</b> {cert['indirizzo']}</div>
                <div class="row"><b>CAP / Città:</b> {cert['cap']} / {cert['citta']}</div>
                <div class="row"><b>Nazione:</b> {cert['nazione']}</div>
                <div class="row"><b>AWB:</b> {cert['awb']}</div>
                <div class="row"><b>DDT:</b> {cert['ddt']}</div>
                <div class="row"><b>Riferimento mittente:</b> {cert['ddt']}</div>
                <div class="row"><b>Data ritiro:</b> {cert['ritiro']}</div>
                <div class="row"><b>Data consegna:</b> {cert['consegna']}</div>
                <div class="row"><b>Ora consegna:</b> {cert['ora']}</div>
                <div class="row"><b>Firma:</b> {cert['firmatario']}</div>
                <div class="row"><b>Esito consegna:</b> {cert['esito']}</div>

                <div class="line"></div>

                <div class="small">
                    Certificazione riepilogativa derivata da archivio storico DHL. Il presente
                    documento riporta i dati disponibili nei file certificati DHL.
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
    risultati_pod = ""
    risultati_cert = ""

    if q:
        q_lower = q.lower()

        for pod in PODS:
            testo = f"{pod['ddt']} {pod['cliente']} {pod['citta']}".lower()
            if q_lower in testo:
                risultati_pod += f"""
                <tr>
                    <td>{pod['ddt']}</td>
                    <td>{pod['cliente']}</td>
                    <td>{pod['citta']}</td>
                    <td>
                        <a href="{pod['url']}" target="_blank">
                            <button>Apri POD</button>
                        </a>
                    </td>
                </tr>
                """

        for cert in CERTIFICATE:
            testo = f"{cert['ddt']} {cert['awb']} {cert['destinatario']} {cert['esito']}".lower()
            if q_lower in testo:
                risultati_cert += f"""
                <tr>
                    <td>{cert['ddt']}</td>
                    <td>{cert['awb']}</td>
                    <td>{cert['destinatario']}</td>
                    <td>{cert['ritiro']}</td>
                    <td>{cert['consegna']}</td>
                    <td>{cert['esito']}</td>
                    <td>
                        <a href="/cert/{cert['ddt']}">
                            <button>Apri Certificazione</button>
                        </a>
                    </td>
                </tr>
                """

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
            </style>
        </head>
        <body>
            <div class="box">
                <h1>POD Manager</h1>

                <form>
                    <input name="q" value="{q}" placeholder="Inserisci DDT, AWB, cliente o città">
                    <button type="submit">Cerca</button>
                </form>

                <h2>POD</h2>
                <table>
                    <tr>
                        <th>DDT</th>
                        <th>Cliente</th>
                        <th>Città</th>
                        <th>POD</th>
                    </tr>
                    {risultati_pod}
                </table>

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
    cert = next((c for c in CERTIFICATE if c["ddt"] == ddt), None)

    if not cert:
        return HTMLResponse("<h1>Certificazione non trovata</h1>", status_code=404)

    return render_cert_html(cert)
