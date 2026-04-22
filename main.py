from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()

@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <html>
        <head>
            <title>POD Manager</title>
            <style>
                body { font-family: Arial; background:#f4f4f4; padding:40px; }
                .box { background:white; padding:20px; border-radius:10px; max-width:800px; margin:auto; }
                input { width:80%; padding:10px; }
                button { padding:10px; }
            </style>
        </head>
        <body>
            <div class="box">
                <h1>POD Manager</h1>
                <p>Ricerca POD (demo)</p>
                <input placeholder="Inserisci DDT o AWB">
                <button>Cerca</button>
                <hr>
                <p>Risultati appariranno qui</p>
            </div>
        </body>
    </html>
    """
