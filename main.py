# backend/main.py
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import io
import pandas as pd
import psycopg2
import json
import os
from playwright.sync_api import sync_playwright
import requests
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

app = FastAPI()

API_KEY = os.getenv("OPENSANCTIONS_API_KEY")
MATCH_URL = "https://api.opensanctions.org/match/sanctions?algorithm=best"

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
            return "Cumpliendo" # sin anomalias detectadas

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
            control["accion_requerida"] = None  # Si esta cumpliendo no deberian existir anomalias

    cur.close()
    conn.close()
    return controles


@app.get("/normativas")
def get_normativas():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM normativas")
    rows = cur.fetchall()
    columns = [desc[0] for desc in cur.description]
    cur.close()
    conn.close()
    return [dict(zip(columns, row)) for row in rows]


@app.get("/procesos")
def get_procesos():
    conn = get_connection()
    cur = conn.cursor()

    # Obtener todos los procesos
    cur.execute("SELECT * FROM procesos")
    procesos_raw = cur.fetchall()
    procesos_columns = [desc[0] for desc in cur.description]

    procesos = []
    for row in procesos_raw:
        proceso = dict(zip(procesos_columns, row))
        
        # Buscar normativas asociadas a este proceso
        cur.execute("""
            SELECT normativa_id 
            FROM normativa_proceso 
            WHERE proceso_id = %s
        """, (proceso["id"],))
        normativa_ids = [r[0] for r in cur.fetchall()]
        proceso["normativas"] = normativa_ids

        procesos.append(proceso)

    cur.close()
    conn.close()
    return procesos


@app.get("/controles/{control_id}/normativas")
def get_normativas_por_control(control_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT n.id, n.nombre, n.descripcion
        FROM control_normativa cn
        JOIN normativas n ON cn.normativa_id = n.id
        WHERE cn.control_id = %s
    """, (control_id,))
    rows = cur.fetchall()
    columns = [desc[0] for desc in cur.description]
    cur.close()
    conn.close()
    return [dict(zip(columns, row)) for row in rows]
