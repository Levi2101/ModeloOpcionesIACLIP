import numpy as np
import faiss
from pymongo import MongoClient
from sentence_transformers import SentenceTransformer
import torch

# 1. CARGAR MODELO Y BASE DE DATOS
print("Cargando modelo semántico...")
device = "cuda" if torch.cuda.is_available() else "cpu"
model = SentenceTransformer('intfloat/multilingual-e5-base', device=device)

MONGO_URI = "mongodb://pakarp11:27017/"
DB_NAME = "Opciones"
COLLECTION_NAME = "opcionesIA"

client = MongoClient(MONGO_URI)
db = client[DB_NAME]
coleccion = db[COLLECTION_NAME]

print("Cargando vectores de texto desde MongoDB...")
cursor = coleccion.find(
    {"embedding_texto": {"$exists": True}},
    {
        "_id": 1,
        "codigo": 1,
        "marca": 1,
        "modelo": 1,
        "color": 1,
        "precio_linea": 1,
        "departamento": 1,
        "url_imagen": 1,
        "texto_consolidado": 1,
        "embedding_texto": 1
    }
)

documentos = []
matriz_vectores = []

for doc in cursor:
    documentos.append(doc)
    matriz_vectores.append(doc["embedding_texto"])

if not matriz_vectores:
    print("❌ Error: No se encontraron documentos con 'embedding_texto'. Ejecuta primero el paso 1.")
    exit()

# Crear Índice FAISS
vectores_np = np.array(matriz_vectores, dtype=np.float32)
dimension = vectores_np.shape[1]
index = faiss.IndexFlatIP(dimension)  # Productos normalizados -> Producto Interno = Cosine Similarity
index.add(vectores_np)

print(f"¡Sistema listo! {index.ntotal} productos cargados en memoria.\n")


# 2. FUNCIÓN DE BÚSQUEDA SEMÁNTICA
def buscar_producto(consulta_usuario, top_k=5):
    # El modelo e5 requiere el prefijo 'query: ' para la consulta de búsqueda
    texto_query = f"query: {consulta_usuario}"
    
    # Vectorizar la consulta del usuario
    query_vector = model.encode([texto_query], normalize_embeddings=True)
    query_vector = np.array(query_vector, dtype=np.float32)

    # Buscar en FAISS
    distancias, indices = index.search(query_vector, top_k * 5)

    codigos_vistos = set()
    resultados = []

    for rank, idx in enumerate(indices[0]):
        prod = documentos[idx]
        cod = str(prod.get("codigo")).strip()

        if cod not in codigos_vistos:
            codigos_vistos.add(cod)
            # Similitud coseno en porcentaje (de 0% a 100%)
            score = float(distancias[0][rank]) * 100
            resultados.append((score, prod))

        if len(resultados) == top_k:
            break

    # Imprimir Resultados
    print("=" * 80)
    print(f"--- RESULTADOS SEMÁNTICOS PARA: '{consulta_usuario}' ---")
    
    for contador, (score, prod) in enumerate(resultados, 1):
        print(f"\n#{contador} | Coincidencia Semántica: {score:.2f}%")
        print(f"     Código: {prod.get('codigo')} | Marca: {prod.get('marca')} | Modelo: {prod.get('modelo')}")
        print(f"     Color: {prod.get('color')} | Depto: {prod.get('departamento')}")
        print(f"     Texto Base: {prod.get('texto_consolidado')}")
        print(f"     URL Imagen: {prod.get('url_imagen')}")

    print("=" * 80)


# 3. CONSOLA INTERACTIVA
if __name__ == "__main__":
    while True:
        print("\n" + "-" * 50)
        entrada = input("Escribe tu búsqueda (o 'salir'): ").strip()
        
        if entrada.lower() in ['salir', 'exit', 'q']:
            break
            
        if entrada:
            buscar_producto(entrada, top_k=5)