# backend/main.py
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import io
import pandas as pd
import psycopg2
import json
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuración desde .env
DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"),
    "database": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD")
}

def get_connection():
    return psycopg2.connect(**DB_CONFIG)

@app.post("/export_excel")
async def export_excel(request: Request):
    data = await request.json()
    selected_tables = data.get("tables", [])
    if not selected_tables:
        return {"error": "No tables selected"}

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        conn = get_connection()
        for table in selected_tables:
            df = pd.read_sql_query(f"SELECT * FROM {table}", conn)
            df.to_excel(writer, sheet_name=table[:31], index=False)
        conn.close()

    output.seek(0)
    return StreamingResponse(output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=datos_auditoria.xlsx"}
    )




@app.get("/controles")
def get_controles():
    def calcular_estado(cantidad):
        if cantidad > 15:
            return "Crítico"
        elif cantidad > 0:
            return "Atención"
        else:
            return "Cumpliendo"

    conn = get_connection()
    cur = conn.cursor()

    # Obtener todos los controles
    cur.execute("SELECT * FROM controles")
    rows = cur.fetchall()
    columns = [desc[0] for desc in cur.description]
    controles = [dict(zip(columns, row)) for row in rows]

    # Para cada control, contar anomalías en su tabla correspondiente
    for control in controles:
        control_id = control["id"]
        tabla_resultado = f"resultados_control{control_id}"

        try:
            cur.execute(f"SELECT COUNT(*) FROM {tabla_resultado}")
            cantidad_anomalias = cur.fetchone()[0]
        except Exception:
            cantidad_anomalias = 0  # Si la tabla no existe o hay error

        # Guardamos el conteo
        control["cantidadAnomalias"] = cantidad_anomalias

        # Si hay anomalías, recalculamos el estado
        if cantidad_anomalias > 0:
            control["estado"] = calcular_estado(cantidad_anomalias)
        else:
            control["estado"] = "Cumpliendo"
            control["accion_requerida"] = None  # Limpia el texto si no hay anomalías

    cur.close()
    conn.close()
    return controles

"""
@app.get("/controles")
def get_controles():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM controles")
    rows = cur.fetchall()
    columns = [desc[0] for desc in cur.description]
    data = [dict(zip(columns, row)) for row in rows]
    cur.close()
    conn.close()
    return data

"""
