import requests
from io import BytesIO
from PIL import Image
import torch
from sentence_transformers import SentenceTransformer
from pymongo import MongoClient, UpdateOne
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor

# ==========================================
# 1. CONTROL DE RECURSOS DE CPU Y GPU
# ==========================================
# Evita que PyTorch consuma todos los núcleos de la CPU en segundo plano
torch.set_num_threads(4)

# 2. Configuración de Conexión a MongoDB Local
MONGO_URI = "mongodb://pakarp11:27017/"
DB_NAME = "Opciones"
COLLECTION_NAME = "opcionesIA"

client = MongoClient(MONGO_URI)
db = client[DB_NAME]
coleccion = db[COLLECTION_NAME]

# 3. Detección y Configuración de GPU
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"--- Dispositivo de cómputo: {device.upper()} ---")

if device == "cuda":
    print(f"GPU activa: {torch.cuda.get_device_name(0)}")
else:
    print("ATENCIÓN: No se detectó CUDA. Se ejecutará en CPU.")

# 4. Cargar Modelo CLIP en VRAM
print("\nCargando modelo CLIP (ViT-B/32) en memoria GPU...")
model = SentenceTransformer('clip-ViT-B-32', device=device)

# 5. Función auxiliar para descargar imágenes en paralelo
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

def descargar_imagen(doc):
    # CORREGIDO: Usamos "url_imagen" que fue como lo guardaste en MongoDB
    url = doc.get("url_imagen") or doc.get("URLs")
    if not url or not str(url).startswith("http"):
        return (doc["_id"], None)
        
    try:
        res = requests.get(str(url).strip(), timeout=4, headers=HEADERS)
        if res.status_code == 200:
            img = Image.open(BytesIO(res.content)).convert("RGB")
            return (doc["_id"], img)
    except Exception:
        pass
    return (doc["_id"], None)

# 6. Proceso por lotes (Batching) para GPU
# Leemos los documentos que tengan una URL de imagen válida
documentos = list(coleccion.find(
    {"$or": [{"url_imagen": {"$ne": None}}, {"URLs": {"$ne": None}}]}, 
    {"_id": 1, "url_imagen": 1, "URLs": 1}
))

total_docs = len(documentos)
print(f"\nIniciando generación de embeddings para {total_docs} productos en MongoDB...")

BATCH_SIZE = 128     # Lote adecuado para enviar directo a la VRAM de tu RTX 5070
NUM_WORKERS = 4      # CORREGIDO: Reducido a 4 para no saturar tu CPU

pbar = tqdm(total=total_docs, desc="Procesando imágenes")

for i in range(0, total_docs, BATCH_SIZE):
    lote_docs = documentos[i:i + BATCH_SIZE]
    
    lote_imagenes = []
    lote_ids = []
    
    # Descargar imágenes usando hilos controlados de CPU
    with ThreadPoolExecutor(max_workers=NUM_WORKERS) as executor:
        resultados = list(executor.map(descargar_imagen, lote_docs))
        
    for doc_id, img in resultados:
        if img is not None:
            lote_ids.append(doc_id)
            lote_imagenes.append(img)
            
    if not lote_imagenes:
        pbar.update(len(lote_docs))
        continue

    # Generar embeddings usando la RTX 5070
    with torch.no_grad():
        embeddings = model.encode(
            lote_imagenes, 
            batch_size=len(lote_imagenes), 
            show_progress_bar=False, 
            convert_to_numpy=True
        )

    # Preparar actualización masiva en MongoDB
    operaciones_bulk = []
    for doc_id, emb in zip(lote_ids, embeddings):
        operaciones_bulk.append(
            UpdateOne(
                {"_id": doc_id},
                {"$set": {"embedding": emb.tolist()}}
            )
        )

    if operaciones_bulk:
        coleccion.bulk_write(operaciones_bulk, ordered=False)

    pbar.update(len(lote_docs))

pbar.close()
print("\n¡Proceso finalizado! Embeddings guardados directamente en la colección de MongoDB.")