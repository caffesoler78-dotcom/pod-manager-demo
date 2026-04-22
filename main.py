from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()

# POD demo con link PDF
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
    },
    {
        "ddt": "802049535",
        "cliente": "ALSTOM",
        "citta": "SESTO S.GIOVANNI",
        "url": "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf"
    },
]

# DHL certificata demo
CERTIFICATE = [
    {
        "ddt": "803401182",
        "awb": "8253912345",
        "destinatario": "ALSTOM VADO LIGURE",
        "ritiro": "24/02/2026",
        "consegna": "25/02/2026",
        "esito": "Consegnato"
    },
    {
        "ddt": "803414507",
        "awb": "8253987654",
        "destinatario": "TRENITALIA NAPOLI",
        "ritiro": "16/04/2026",
        "consegna": "17/04/2026",
        "esito": "Consegnato"
    },
    {
        "ddt": "802049535",
        "awb": "8253977777",
        "destinatario": "ALSTOM SESTO S.GIOVANNI",
        "ritiro": "10/01/2024",
        "consegna": "15/01/2024",
        "esito": "Consegnato"
    },
]

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
                    <td><button disabled>Certificazione PDF</button></td>
                </tr>
                """

    return f"""
    <html>
        <head>
            <title>POD Manager</title>
            <style>
                body {{ font-family: Arial; background:#f4f4f4; padding:40px; }}
                .box {{ background:white; padding:20px; border-radius:10px; max-width:1200px; margin:auto; }}
                input {{ width:80%; padding:10px; }}
                button {{ padding:10px; }}
                table {{ width:100%; margin-top:20px; border-collapse: collapse; }}
                td, th {{ border-bottom:1px solid #ccc; padding:8px; text-align:left; }}
                h2 {{ margin-top:40px; }}
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
                        <th>PDF</th>
                    </tr>
                    {risultati_cert}
                </table>
            </div>
        </body>
    </html>
    """
