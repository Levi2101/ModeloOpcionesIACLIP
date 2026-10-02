import os
import json
import numpy as np
import faiss
import pandas as pd

# 1. Configuración de archivos y columnas
CSV_ENTRADA = "embeddings_prueba_resultado.csv"
COLUMNA_ID = "CodigoUnico"
COLUMNA_URL = "URLs"
COLUMNA_EMBEDDING = "embedding"

if not os.path.exists(CSV_ENTRADA):
    print(f"❌ Error: El archivo '{CSV_ENTRADA}' no existe. Ejecuta primero 'generar_embeddings_csv.py'.")
    exit()

print(f"Cargando datos desde '{CSV_ENTRADA}'...")

# Forzamos a leer la columna del ID como string para evitar el conversion a float (.0)
df = pd.read_csv(CSV_ENTRADA, dtype={COLUMNA_ID: str})

# Filtrar únicamente filas que tengan embedding generado
df = df[df[COLUMNA_EMBEDDING].notna()].reset_index(drop=True)

if df.empty:
    print("❌ Error: No se encontraron embeddings válidos en el archivo CSV.")
    exit()

# Función auxiliar para limpiar cualquier residuo de float
def normalizar_codigo(codigo):
    val_str = str(codigo).strip()
    if val_str.endswith(".0"):
        val_str = val_str[:-2]
    return val_str

# Aplicar limpieza a toda la columna
df[COLUMNA_ID] = df[COLUMNA_ID].apply(normalizar_codigo)

# 2. Reconstruir la matriz de vectores para FAISS
print("Parseando vectores e inicializando índice FAISS...")
matriz_vectores = []
id_a_indice = {}

for idx, row in df.iterrows():
    vector = json.loads(row[COLUMNA_EMBEDDING])
    matriz_vectores.append(vector)
    
    # Mapear el CodigoUnico limpio a su posición en la matriz
    codigo_u = row[COLUMNA_ID]
    id_a_indice[codigo_u] = idx

vectores_np = np.array(matriz_vectores, dtype=np.float32)

# Normalizar los vectores para calcular similitud coseno
faiss.normalize_L2(vectores_np)

# Crear el índice FAISS en memoria
dimension = vectores_np.shape[1]
index = faiss.IndexFlatIP(dimension)
index.add(vectores_np)

print(f"¡Listo! {index.ntotal} productos cargados en el índice de búsqueda.\n")

# 3. Función de búsqueda por Código Único
def buscar_opciones_similares_csv(codigo_unico, top_k=5):
    codigo_str = normalizar_codigo(codigo_unico)
    
    if codigo_str not in id_a_indice:
        print(f"❌ Error: El CodigoUnico '{codigo_unico}' (normalizado: '{codigo_str}') no fue encontrado en el CSV.")
        return

    idx_objetivo = id_a_indice[codigo_str]
    prod_objetivo = df.iloc[idx_objetivo]
    
    # Extraer el vector del producto consultado
    vector_query = np.array([vectores_np[idx_objetivo]], dtype=np.float32)

    # Aumentamos el margen de búsqueda para tener suficientes candidatos al filtrar duplicados
    distancias, indices = index.search(vector_query, top_k * 10)

    print("=" * 75)
    print(f"PRODUCTO CONSULTADO -> CodigoUnico: {prod_objetivo[COLUMNA_ID]}")
    print(f"URL: {prod_objetivo[COLUMNA_URL]}")
    print("=" * 75)
    print(f"\n--- TOP {top_k} OPCIONES SIMILARES ENCONTRADAS (ÚNICAS) ---")

    contador = 1
    codigos_vistas = set()
    codigos_vistas.add(codigo_str)  # Evita mostrar el producto consultado

    for rank, idx in enumerate(indices[0]):
        prod_similar = df.iloc[idx]
        codigo_sim = prod_similar[COLUMNA_ID]
        
        # Omitir si ya mostramos este CodigoUnico previamente
        if codigo_sim in codigos_vistas:
            continue
            
        codigos_vistas.add(codigo_sim)
        score_similitud = distancias[0][rank]
        print(f"#{contador} | Similitud: {score_similitud * 100:.2f}% | CodigoUnico: {prod_similar[COLUMNA_ID]} | URL: {prod_similar[COLUMNA_URL]}")
        
        contador += 1
        if contador > top_k:
            break
            
    print("=" * 75)

# --- PRUEBA ---
if __name__ == "__main__":
    CODIGO_A_BUSCAR = "55033"
    
    buscar_opciones_similares_csv(CODIGO_A_BUSCAR, top_k=5)