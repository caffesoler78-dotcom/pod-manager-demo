from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()

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
        "esito": "Consegna avvenuta"
    }
]

@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <html>
        <body style="font-family:Arial;padding:40px;">
            <h1>POD Manager</h1>
            <a href="/cert/803128294">Apri certificazione esempio</a>
        </body>
    </html>
    """

@app.get("/cert/{ddt}", response_class=HTMLResponse)
def certificazione(ddt: str):
    cert = next((c for c in CERTIFICATE if c["ddt"] == ddt), None)

    if not cert:
        return "Certificazione non trovata"

    return f"""
    <html>
        <head>
            <style>
                body {{ font-family: Arial; padding:40px; background:white; }}
                .container {{ max-width:800px; margin:auto; }}
                h1 {{ text-align:center; }}
                h2 {{ margin-top:30px; }}
                .line {{ border-top:1px solid #ccc; margin:20px 0; }}
                p {{ margin:5px 0; }}
            </style>
        </head>

        <body>
            <div class="container">

                <h1>CERTIFICAZIONE CONSEGNA</h1>
                <p style="text-align:center;">Riepilogo da archivio storico DHL certificato</p>

                <div class="line"></div>

                <h2>Stato consegna</h2>
                <p><b>Stato:</b> {cert['esito']}</p>
                <p><b>Ricevuto da:</b> {cert['firmatario']}</p>
                <p><b>Data consegna:</b> {cert['consegna']}</p>
                <p><b>Ora consegna:</b> {cert['ora']}</p>

                <div class="line"></div>

                <h2>Dati spedizione</h2>
                <p><b>Nome:</b> {cert['nome']}</p>
                <p><b>Indirizzo:</b> {cert['indirizzo']}</p>
                <p><b>CAP / Città:</b> {cert['cap']} / {cert['citta']}</p>
                <p><b>Nazione:</b> {cert['nazione']}</p>

                <p><b>AWB:</b> {cert['awb']}</p>
                <p><b>DDT:</b> {cert['ddt']}</p>
                <p><b>Riferimento mittente:</b> {cert['ddt']}</p>

                <p><b>Data ritiro:</b> {cert['ritiro']}</p>
                <p><b>Data consegna:</b> {cert['consegna']}</p>
                <p><b>Ora consegna:</b> {cert['ora']}</p>

                <p><b>Firma:</b> {cert['firmatario']}</p>
                <p><b>Esito consegna:</b> {cert['esito']}</p>

                <div class="line"></div>

                <p style="font-size:12px;">
                Certificazione riepilogativa derivata da archivio storico DHL.
                Il presente documento riporta i dati disponibili nei file certificati DHL.
                </p>

                <div class="line"></div>

                <p style="font-size:12px;">
                Generato automaticamente dal sistema POD Manager
                </p>

            </div>
        </body>
    </html>
    """
