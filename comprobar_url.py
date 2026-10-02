import requests
from pymongo import MongoClient, InsertOne
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed

# 1. Configuración de MongoDB
MONGO_URI = "mongodb://pakarp11:27017/"
DB_NAME = "Opciones"

ORIGIN_COLLECTION = "productos_opciones_ia"
TARGET_COLLECTION = "opciones_ia"

client = MongoClient(MONGO_URI)
db = client[DB_NAME]

col_origen = db[ORIGIN_COLLECTION]
col_destino = db[TARGET_COLLECTION]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

documentos = list(col_origen.find({"URLs": {"$exists": True, "$ne": ""}}))
print(f"Se encontraron {len(documentos)} productos para verificar.")

# 2. Función para comprobar accesibilidad
def verificar_y_procesar(doc):
    url = doc.get("URLs")
    if not url:
        return None

    es_valida = False
    try:
        res = requests.head(url, timeout=3, allow_redirects=True, headers=HEADERS)
        if res.status_code == 200:
            es_valida = True
        else:
            res = requests.get(url, timeout=3, stream=True, headers=HEADERS)
            if res.status_code == 200:
                es_valida = True
    except Exception:
        es_valida = False

    if es_valida:
        doc_nuevo = doc.copy()
        
        # CORRECCIÓN CLAVE: Eliminar _id para que no cause conflicto en la nueva colección
        doc_nuevo.pop("_id", None)
        
        # Conversión de precio
        try:
            doc_nuevo["PrecioLineaNum"] = float(doc.get("PrecioLinea", "0.00"))
        except (ValueError, TypeError):
            doc_nuevo["PrecioLineaNum"] = 0.0
            
        return doc_nuevo
    
    return None

# 3. Procesamiento en paralelo
validos = 0
invalidos = 0
buffer_insert = []
BATCH_SIZE = 1000  # Insertar en lotes de 1,000 documentos a la vez

# Limpiar colección destino antes de poblarla (Opcional)
col_destino.delete_many({})

print("Comprobando accesibilidad e insertando en lotes...")

MAX_WORKERS = 30  # Ajusta según tu velocidad de internet (20-50 hilos)

with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
    futures = [executor.submit(verificar_y_procesar, doc) for doc in documentos]
    
    for future in tqdm(as_completed(futures), total=len(documentos), desc="Verificando URLs"):
        resultado = future.result()
        if resultado is not None:
            buffer_insert.append(resultado)
            validos += 1
            
            # Guardado masivo por lotes (súper rápido)
            if len(buffer_insert) >= BATCH_SIZE:
                col_destino.insert_many(buffer_insert)
                buffer_insert = []
        else:
            invalidos += 1

# Insertar el resto que haya quedado en el buffer
if buffer_insert:
    col_destino.insert_many(buffer_insert)

print("\n--- RESUMEN DEL PROCESO ---")
print(f" Total analizados   : {len(documentos)}")
print(f" URLs Válidas        : {validos} (guardados en '{TARGET_COLLECTION}')")
print(f" URLs Inaccesibles   : {invalidos} (omitidos)")