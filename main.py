from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()

# dati demo con link PDF
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

@app.get("/", response_class=HTMLResponse)
def home(q: str = ""):
    risultati = ""

    if q:
        for pod in PODS:
            if q in pod["ddt"]:
                risultati += f"""
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

    return f"""
    <html>
        <head>
            <title>POD Manager</title>
            <style>
                body {{ font-family: Arial; background:#f4f4f4; padding:40px; }}
                .box {{ background:white; padding:20px; border-radius:10px; max-width:900px; margin:auto; }}
                input {{ width:80%; padding:10px; }}
                button {{ padding:10px; }}
                table {{ width:100%; margin-top:20px; border-collapse: collapse; }}
                td, th {{ border-bottom:1px solid #ccc; padding:8px; text-align:left; }}
            </style>
        </head>
        <body>
            <div class="box">
                <h1>POD Manager</h1>

                <form>
                    <input name="q" value="{q}" placeholder="Inserisci DDT">
                    <button type="submit">Cerca</button>
                </form>

                <table>
                    <tr>
                        <th>DDT</th>
                        <th>Cliente</th>
                        <th>Città</th>
                        <th>POD</th>
                    </tr>
                    {risultati}
                </table>
            </div>
        </body>
    </html>
    """
