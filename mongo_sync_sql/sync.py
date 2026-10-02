import json
import pandas as pd
import pyodbc
from pymongo import MongoClient, UpdateOne

# ==========================================
# 1. CONFIGURACIÓN DE CONEXIONES
# ==========================================

# Conexión a tu SQL Server
SQL_CONN_STR = (
    "DRIVER={SQL Server};"
    "SERVER=PAKARP12;"         # O el IP / Nombre de tu servidor SQL
    "DATABASE=opcionesIA;" 
    "Trusted_Connection=yes;"
)

# Conexión Local para MongoDB Compass
# Si tu MongoDB en Compass no tiene usuario/contraseña:
MONGO_URI = "mongodb://pakarp11:27017"

# Si tu MongoDB local requiere usuario y contraseña, usa este formato:
# MONGO_URI = "mongodb://usuario:password@localhost:27017/?authSource=admin"

MONGO_DB_NAME = "Opciones"
MONGO_COLLECTION_NAME = "opcionesIA"

# ==========================================
# 2. PROCESO DE MIGRACIÓN
# ==========================================
def migrar_exacto_sql_a_mongo():
    print("Conectando a SQL Server y MongoDB...")
    
    conn_sql = pyodbc.connect(SQL_CONN_STR)
    client_mongo = MongoClient(MONGO_URI)
    db_mongo = client_mongo[MONGO_DB_NAME]
    coleccion = db_mongo[MONGO_COLLECTION_NAME]

    # 1. Eliminar datos e índices previos que causaban el choque
    print("Eliminando datos e índices antiguos en MongoDB...")
    coleccion.delete_many({})
    coleccion.drop_indexes()

    query = """
    SELECT Llave, Talla, Marca, Modelo, Color, Codigo, Unidades, PrecioCatalogo, PrecioLinea, Departamento, UrlImagen
    FROM producto
    """

    print("Cargando las 207,509 filas desde SQL Server...")
    
    chunk_size = 5000
    total_procesados = 0

    for chunk in pd.read_sql(query, conn_sql, chunksize=chunk_size):
        lote_documentos = []

        for idx, row in chunk.iterrows():
            doc_producto = {
                "llave": str(row["Llave"]).strip() if pd.notna(row["Llave"]) else None,
                "talla": str(row["Talla"]).strip() if pd.notna(row["Talla"]) else None,
                "marca": str(row["Marca"]).strip() if pd.notna(row["Marca"]) else None,
                "modelo": str(row["Modelo"]).strip() if pd.notna(row["Modelo"]) else None,
                "color": str(row["Color"]).strip() if pd.notna(row["Color"]) else None,
                "codigo": str(row["Codigo"]).strip() if pd.notna(row["Codigo"]) else None,
                "unidades": int(row["Unidades"]) if pd.notna(row["Unidades"]) else 0,
                "precio_catalogo": float(row["PrecioCatalogo"]) if pd.notna(row["PrecioCatalogo"]) else 0.0,
                "precio_linea": float(row["PrecioLinea"]) if pd.notna(row["PrecioLinea"]) else 0.0,
                "departamento": str(row["Departamento"]).strip() if pd.notna(row["Departamento"]) else None,
                "url_imagen": str(row["UrlImagen"]).strip() if pd.notna(row["UrlImagen"]) else None
            }
            lote_documentos.append(doc_producto)

        if lote_documentos:
            coleccion.insert_many(lote_documentos, ordered=False)
            total_procesados += len(lote_documentos)
            print(f"Progreso: {total_procesados} / 207,509 registros insertados...")

    total_mongo = coleccion.count_documents({})
    print(f"\n✅ Migración completada exitosamente.")
    print(f"📌 Total de documentos final en MongoDB: {total_mongo}")

    # 2. Crear índice NORMAL (no único) para optimizar consultas por llave sin bloquear duplicados
    coleccion.create_index("llave", unique=False)
    print("📌 Índice estándar en 'llave' creado correctamente.")

if __name__ == "__main__":
    migrar_exacto_sql_a_mongo()