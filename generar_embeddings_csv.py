import os
import json
import requests
import torch
import pandas as pd
import numpy as np
from io import BytesIO
from PIL import Image
from sentence_transformers import SentenceTransformer
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor

# ==========================================
# 1. OPTIMIZACIÓN DE RECURSOS DE CPU Y GPU
# ==========================================
# Limitar los hilos de CPU que PyTorch usa en segundo plano para evitar saturar la CPU
torch.set_num_threads(4)

device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"--- Dispositivo de cómputo: {device.upper()} ---")

if device == "cuda":
    print(f"GPU activa: {torch.cuda.get_device_name(0)}")
else:
    print("ATENCIÓN: No se detectó CUDA. Se ejecutará en CPU.")

# ==========================================
# 2. CONFIGURACIÓN DEL PROCESAMIENTO
# ==========================================
CSV_ENTRADA = "productos_prueba.csv"      # Nombre de tu archivo CSV de origen
CSV_SALIDA = "embeddings_prueba_resultado.csv"

COLUMNA_URL = "URLs"                      # Nombre de la columna con las URLs de las fotos
COLUMNA_ID = "CodigoUnico"                # Nombre de la columna de identificación

BATCH_SIZE = 128                          # Lote grande enviado directamente a la GPU
NUM_WORKERS = 4                           # Reducido a 4 para no saturar tu Intel Ultra 7

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

# ==========================================
# 3. CARGAR MODELO Y LEER ARCHIVO
# ==========================================
print("\nCargando modelo CLIP (ViT-B/32) en memoria GPU...")
model = SentenceTransformer('clip-ViT-B-32', device=device)

if not os.path.exists(CSV_ENTRADA):
    print(f"❌ Error: No se encontró el archivo '{CSV_ENTRADA}'.")
    exit()

df = pd.read_csv(CSV_ENTRADA)

if COLUMNA_URL not in df.columns:
    print(f"❌ Error: La columna '{COLUMNA_URL}' no existe en el CSV.")
    print(f"Columnas detectadas: {list(df.columns)}")
    exit()

print(f"Se cargaron {len(df)} filas desde '{CSV_ENTRADA}'.")

# ==========================================
# 4. FUNCIÓN AUXILIAR DE DESCARGA
# ==========================================
def descargar_imagen(row_tuple):
    idx, url = row_tuple
    if pd.isna(url) or not str(url).startswith("http"):
        return (idx, None)
    
    try:
        res = requests.get(str(url).strip(), timeout=4, headers=HEADERS)
        if res.status_code == 200:
            img = Image.open(BytesIO(res.content)).convert("RGB")
            return (idx, img)
    except Exception:
        pass
    return (idx, None)

# ==========================================
# 5. GENERACIÓN DE EMBEDDINGS EN GPU
# ==========================================
embeddings_dict = {}
filas_lista = list(df[COLUMNA_URL].items())
total_filas = len(filas_lista)

print("\nIniciando procesamiento de imágenes...")
pbar = tqdm(total=total_filas, desc="Generando embeddings")

for i in range(0, total_filas, BATCH_SIZE):
    lote_filas = filas_lista[i:i + BATCH_SIZE]
    
    lote_indices = []
    lote_imagenes = []
    
    # Descarga de imágenes limitada a 4 hilos de CPU
    with ThreadPoolExecutor(max_workers=NUM_WORKERS) as executor:
        resultados = list(executor.map(descargar_imagen, lote_filas))
        
    for idx, img in resultados:
        if img is not None:
            lote_indices.append(idx)
            lote_imagenes.append(img)
            
    # Proceso matricial directo en la GPU RTX 5070
    if lote_imagenes:
        with torch.no_grad():
            vectores = model.encode(
                lote_imagenes, 
                batch_size=len(lote_imagenes), 
                show_progress_bar=False, 
                convert_to_numpy=True
            )
            
        for idx, emb in zip(lote_indices, vectores):
            embeddings_dict[idx] = json.dumps(emb.tolist())

    pbar.update(len(lote_filas))

pbar.close()

# ==========================================
# 6. GUARDAR RESULTADOS
# ==========================================
df['embedding'] = df.index.map(embeddings_dict)
df.to_csv(CSV_SALIDA, index=False)

procesados = df['embedding'].notna().sum()
print("\n" + "=" * 60)
print(f" ¡Proceso completado con éxito!")
print(f" Imágenes procesadas correctamente: {procesados} / {total_filas}")
print(f" Archivo guardado en: {CSV_SALIDA}")
print("=" * 60)

# Muestra de validación del vector de 512 dimensiones
ejemplo = df[df['embedding'].notna()].head(1)
if not ejemplo.empty:
    id_ej = ejemplo[COLUMNA_ID].values[0] if COLUMNA_ID in df.columns else "N/A"
    emb_list = json.loads(ejemplo['embedding'].values[0])
    print(f"\nEjemplo para producto ID '{id_ej}':")
    print(f"Dimensión del vector generado: {len(emb_list)}")
    print(f"Primeros 5 valores: {emb_list[:5]}...")