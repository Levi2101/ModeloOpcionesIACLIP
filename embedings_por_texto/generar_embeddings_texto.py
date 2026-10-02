from pymongo import MongoClient
from sentence_transformers import SentenceTransformer
import torch

# 1. CARGAR MODELO MULTILINGÜE
print("Cargando modelo semántico multilingüe (e5-base)...")
device = "cuda" if torch.cuda.is_available() else "cpu"
model = SentenceTransformer('intfloat/multilingual-e5-base', device=device)

# 2. CONEXIÓN A MONGOBD
MONGO_URI = "mongodb://pakarp11:27017/"
DB_NAME = "Opciones"
COLLECTION_NAME = "opcionesIA"

client = MongoClient(MONGO_URI)
db = client[DB_NAME]
coleccion = db[COLLECTION_NAME]

print("Obteniendo productos de MongoDB...")
cursor = coleccion.find({}, {
    "_id": 1,
    "codigo": 1,
    "marca": 1,
    "modelo": 1,
    "color": 1,
    "departamento": 1,
    "talla": 1
})

documentos = list(cursor)
total = len(documentos)
print(f"Total de productos a procesar: {total}")

# 3. GENERACIÓN EN BATCHES (Para máxima velocidad)
BATCH_SIZE = 256
batch_docs = []
batch_textos = []

for i, doc in enumerate(documentos, 1):
    # Formatear datos limpios
    marca = str(doc.get("marca", "") or "").strip()
    modelo = str(doc.get("modelo", "") or "").strip()
    color = str(doc.get("color", "") or "").strip()
    depto = str(doc.get("departamento", "") or "").strip()
    
    # Construcción de la frase descriptiva (Consolidación)
    # Nota: El modelo e5 requiere el prefijo 'passage: ' para los documentos
    texto_producto = f"passage: Producto {depto} marca {marca} modelo {modelo} color {color}"
    
    batch_docs.append((doc["_id"], texto_producto))
    batch_textos.append(texto_producto)

    if len(batch_textos) == BATCH_SIZE or i == total:
        # Generar embeddings de texto
        embeddings = model.encode(batch_textos, normalize_embeddings=True, show_progress_bar=False)
        
        # Actualizar en MongoDB
        for (doc_id, txt), emb in zip(batch_docs, embeddings):
            coleccion.update_one(
                {"_id": doc_id},
                {
                    "$set": {
                        "texto_consolidado": txt.replace("passage: ", ""),
                        "embedding_texto": emb.tolist()
                    }
                }
            )
            
        print(f"Procesados {i}/{total} productos...")
        batch_docs = []
        batch_textos = []

print("✅ Generación de embeddings de texto completada con éxito.")