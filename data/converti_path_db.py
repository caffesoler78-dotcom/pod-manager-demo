import sqlite3

DB_PATH = "pod_attuali_index.db"
BASE_PREFIX = r"C:\Users\domenico.rizzo\OneDrive - BCube spa\POD\pod\"

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# aggiunge la colonna path se non esiste già
cols = [r[1] for r in cur.execute("PRAGMA table_info(pod_attuali)").fetchall()]
if "path" not in cols:
    cur.execute("ALTER TABLE pod_attuali ADD COLUMN path TEXT")

rows = cur.execute("SELECT ddt, full_path FROM pod_attuali").fetchall()

aggiornati = 0

for ddt, full_path in rows:
    if not full_path:
        continue

    rel = full_path
    if rel.startswith(BASE_PREFIX):
        rel = rel[len(BASE_PREFIX):]

    rel = rel.replace("\\", "/")

    cur.execute(
        "UPDATE pod_attuali SET path = ? WHERE ddt = ?",
        (rel, ddt)
    )
    aggiornati += 1

conn.commit()
conn.close()

print("FINE")
print("Record aggiornati:", aggiornati)
