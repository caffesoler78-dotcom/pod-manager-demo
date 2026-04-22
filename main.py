from fastapi import FastAPI
from fastapi.responses import HTMLResponse, Response
from weasyprint import HTML

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

def genera_html(cert):
    return f"""
    <html>
    <body style="font-family:Arial; padding:40px;">

        <h1 style="text-align:center;">CERTIFICAZIONE CONSEGNA</h1>
        <p style="text-align:center;">Riepilogo da archivio storico DHL certificato</p>

        <hr>

        <h2>Stato consegna</h2>
        <p><b>Stato:</b> {cert['esito']}</p>
        <p><b>Ricevuto da:</b> {cert['firmatario']}</p>
        <p><b>Data consegna:</b> {cert['consegna']}</p>
        <p><b>Ora consegna:</b> {cert['ora']}</p>

        <hr>

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

        <hr>

        <p style="font-size:12px;">
        Certificazione riepilogativa derivata da archivio storico DHL.
        Il presente documento riporta i dati disponibili nei file certificati DHL.
        </p>

        <hr>

        <p style="font-size:12px;">
        Generato automaticamente dal sistema POD Manager
        </p>

    </body>
    </html>
    """

@app.get("/cert/{ddt}", response_class=HTMLResponse)
def certificazione(ddt: str):
    cert = next((c for c in CERTIFICATE if c["ddt"] == ddt), None)
    return genera_html(cert)

@app.get("/pdf/{ddt}")
def pdf(ddt: str):
    cert = next((c for c in CERTIFICATE if c["ddt"] == ddt), None)

    html = genera_html(cert)
    pdf = HTML(string=html).write_pdf()

    return Response(
        pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=certificazione_{ddt}.pdf"}
    )
