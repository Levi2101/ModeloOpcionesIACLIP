import numpy as np
import faiss
from pymongo import MongoClient
import random

# ==========================================
# 1. CONFIGURACIÓN DE MONGO DB
# ==========================================
MONGO_URI = "mongodb://pakarp11:27017/"
DB_NAME = "Opciones"
COLLECTION_NAME = "opcionesIA"

client = MongoClient(MONGO_URI)
db = client[DB_NAME]
coleccion = db[COLLECTION_NAME]

print("Cargando catálogo y embeddings desde MongoDB...")

# Proyectar los campos exactos de tu documento
cursor = coleccion.find(
    {"embedding": {"$exists": True}}, 
    {
        "_id": 1, 
        "codigo": 1, 
        "llave": 1,
        "talla": 1, 
        "marca": 1, 
        "modelo": 1, 
        "color": 1, 
        "precio_catalogo": 1,
        "precio_linea": 1,
        "url_imagen": 1, 
        "embedding": 1
    }
)

documentos = []
matriz_vectores = []
codigo_a_indices = {}  # Mapea un código a una lista de índices

for i, doc in enumerate(cursor):
    documentos.append(doc)
    matriz_vectores.append(doc["embedding"])
    
    # Mapear por campo 'codigo'
    cod = doc.get("codigo")
    if cod is not None:
        cod_str = str(cod).strip()
        if cod_str not in codigo_a_indices:
            codigo_a_indices[cod_str] = []
        codigo_a_indices[cod_str].append(i)

if not matriz_vectores:
    print("❌ Error: No se encontraron productos con embeddings en la colección.")
    exit()

# Convertir a matriz Numpy para FAISS
vectores_np = np.array(matriz_vectores, dtype=np.float32)

# Normalización L2 y construcción del índice FAISS
faiss.normalize_L2(vectores_np)
dimension = vectores_np.shape[1]
index = faiss.IndexFlatIP(dimension)
index.add(vectores_np)

print(f"¡Catálogo listo! {index.ntotal} registros cargados en el índice FAISS.\n")

# ==========================================
# 2. FUNCIÓN DE BÚSQUEDA
# ==========================================
def obtener_opciones_similares(codigo_buscar, top_k=5):
    codigo_str = str(codigo_buscar).strip()
    
    # Validar si el código existe
    if codigo_str not in codigo_a_indices:
        print(f"❌ Error: El código '{codigo_buscar}' no existe en la colección o no tiene embeddings.")
        return

    # Tomar el primer documento asociado a ese código para extraer su vector visual
    idx_objetivo = codigo_a_indices[codigo_str][0]
    prod_objetivo = documentos[idx_objetivo]
    
    vector_query = np.array([vectores_np[idx_objetivo]], dtype=np.float32)

    # 1. Traer un número amplio de candidatos iniciales (p. ej. 200) para saltar duplicados de tallas
    candidatos_a_buscar = min(200, index.ntotal)
    distancias, indices = index.search(vector_query, candidatos_a_buscar)

    codigos_vistos = {codigo_str}  # Ignorar el código original consultado
    recomendaciones = []

    # 2. Filtrar y seleccionar productos únicos hasta juntar top_k
    for rank, idx in enumerate(indices[0]):
        prod_similar = documentos[idx]
        cod_sim = str(prod_similar.get("codigo")).strip()

        if cod_sim not in codigos_vistos:
            codigos_vistos.add(cod_sim)
            score_similitud = float(distancias[0][rank]) * 100
            recomendaciones.append((score_similitud, prod_similar))

        if len(recomendaciones) == top_k:
            break

    # 3. Muestra de resultados en pantalla
    print("=" * 80)
    print("PRODUCTO CONSULTADO:")
    print(f"  * Código: {prod_objetivo.get('codigo')} | Llave: {prod_objetivo.get('llave')}")
    print(f"  * Marca: {prod_objetivo.get('marca')} | Modelo: {prod_objetivo.get('modelo')} | Color: {prod_objetivo.get('color')}")
    print(f"  * Precio Catálogo: ${prod_objetivo.get('precio_catalogo')} | Precio Línea: ${prod_objetivo.get('precio_linea')}")
    print(f"  * URL Imagen: {prod_objetivo.get('url_imagen')}")
    print("=" * 80)
    print(f"\n--- TOP {top_k} RECOMENDACIONES SIMILARES ---")

    for contador, (score, prod) in enumerate(recomendaciones, 1):
        print(f"\n#{contador} | Similitud Visual: {score:.2f}%")
        print(f"     Código: {prod.get('codigo')} | Llave: {prod.get('llave')}")
        print(f"     Marca: {prod.get('marca')} | Modelo: {prod.get('modelo')} | Color: {prod.get('color')}")
        print(f"     Precio Catálogo: ${prod.get('precio_catalogo')} | Precio Línea: ${prod.get('precio_linea')}")
        print(f"     URL Imagen: {prod.get('url_imagen')}")

    print("=" * 80)


# ==========================================
# 3. MODO INTERACTIVO DE PRUEBA
# ==========================================
if __name__ == "__main__":
    while True:
        print("\n" + "-" * 50)
        codigo_input = input("Ingresa un código de producto (o 'r' para aleatorio, 'salir' para terminar): ").strip()
        
        if codigo_input.lower() in ['salir', 'exit', 'q']:
            print("Saliendo de la prueba...")
            break

        if codigo_input.lower() == 'r':
            codigo_input = random.choice(list(codigo_a_indices.keys()))
            print(f"Probando con código aleatorio: {codigo_input}")

        if not codigo_input:
            continue

        obtener_opciones_similares(codigo_input, top_k=5)