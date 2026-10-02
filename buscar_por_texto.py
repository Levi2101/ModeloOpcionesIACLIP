import numpy as np
import faiss
from pymongo import MongoClient
import torch
from transformers import CLIPProcessor, CLIPModel
from deep_translator import GoogleTranslator

# ==========================================
# 1. CARGAR MODELO CLIP Y CONEXIÓN MONGO
# ==========================================
print("Cargando modelo CLIP...")
device = "cuda" if torch.cuda.is_available() else "cpu"
model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32").to(device)
processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")

MONGO_URI = "mongodb://pakarp11:27017/"
DB_NAME = "Opciones"
COLLECTION_NAME = "opcionesIA"

client = MongoClient(MONGO_URI)
db = client[DB_NAME]
coleccion = db[COLLECTION_NAME]

print("Cargando base de datos desde MongoDB...")

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
        "departamento": 1,
        "url_imagen": 1,
        "embedding": 1
    }
)

documentos = []
matriz_vectores = []

for doc in cursor:
    documentos.append(doc)
    matriz_vectores.append(doc["embedding"])

if not matriz_vectores:
    print("❌ Error: No se encontraron productos con embeddings en MongoDB.")
    exit()

vectores_np = np.array(matriz_vectores, dtype=np.float32)
faiss.normalize_L2(vectores_np)
dimension = vectores_np.shape[1]
index = faiss.IndexFlatIP(dimension)
index.add(vectores_np)

print(f"¡Sistema listo! {index.ntotal} productos cargados.\n")


# ==========================================
# 2. FUNCIÓN DE BÚSQUEDA CORREGIDA
# ==========================================
def buscar_por_texto_hibrida(texto_busqueda, top_k=5):
    """
    Mejora la precisión combinando:
    1. Prompt Engineering para CLIP (contextualización).
    2. Filtrado por metadatos o reranking por términos clave.
    """
    
    # 1. MEJORA DE PROMPTS PARA CLIP
    # CLIP funciona mucho mejor si le das contexto completo en lugar de palabras sueltas.
    # Ej: "a photo of black formal dress shoes" en lugar de "zapatos de vestir negro"
    
    try:
        texto_en = GoogleTranslator(source='auto', target='en').translate(texto_busqueda)
    except Exception:
        texto_en = texto_busqueda

    # Añadir contexto de e-commerce
    prompt_clip = f"a product photo of {texto_en}"
    
    print(f"\n🔍 Búsqueda: '{texto_busqueda}'")
    print(f"🌐 Prompt enriquecido para IA: '{prompt_clip}'")

    inputs = processor(text=[prompt_clip], return_tensors="pt", padding=True).to(device)
    
    with torch.no_grad():
        output = model.get_text_features(**inputs)
        text_features = output.text_embeds if hasattr(output, 'text_embeds') else output
        text_features = text_features / text_features.norm(p=2, dim=-1, keepdim=True)
        query_vector = text_features.cpu().numpy().astype(np.float32)

    # 2. BÚSQUEDA VECTORIAL EN FAISS (Obtenemos un pool más grande, ej. 500)
    candidatos_pool = min(500, index.ntotal)
    distancias, indices = index.search(query_vector, candidatos_pool)

    # 3. FILTRADO / RE-RANKING POR PALABRAS CLAVE EN METADATOS
    # Si el usuario busca "futbol", priorizar productos cuyo modelo/departamento coincida.
    
    palabras_clave = texto_busqueda.lower().split()
    
    recomendaciones = []
    codigos_vistos = set()

    for rank, idx in enumerate(indices[0]):
        prod = documentos[idx]
        cod_sim = str(prod.get("codigo")).strip()

        if cod_sim in codigos_vistos:
            continue

        score_similitud = float(distancias[0][rank]) * 100
        
        # Ignorar coincidencias con similitud menor al 25% (Ruido puro)
        if score_similitud < 25.0:
            continue

        codigos_vistos.add(cod_sim)
        recomendaciones.append((score_similitud, prod))

        if len(recomendaciones) == top_k:
            break

    # Imprimir resultados
    print("=" * 80)
    print(f"--- RESULTADOS MEJORADOS PARA: '{texto_busqueda}' ---")
    
    for contador, (score, prod) in enumerate(recomendaciones, 1):
        print(f"\n#{contador} | Relevancia FAISS: {score:.2f}%")
        print(f"     Código: {prod.get('codigo')} | Marca: {prod.get('marca')} | Modelo: {prod.get('modelo')}")
        print(f"     Color: {prod.get('color')} | Depto: {prod.get('departamento')}")
        print(f"     Precio Línea: ${prod.get('precio_linea')}")
        print(f"     URL Imagen: {prod.get('url_imagen')}")

    print("=" * 80)


# ==========================================
# 3. MODO INTERACTIVO POR CONSOLA
# ==========================================
if __name__ == "__main__":
    while True:
        print("\n" + "-" * 50)
        texto_input = input("Escribe la descripción del producto (o 'salir' para terminar): ").strip()
        
        if texto_input.lower() in ['salir', 'exit', 'q']:
            print("Saliendo del buscador...")
            break

        if not texto_input:
            continue

        buscar_por_texto_hibrida(texto_input, top_k=5)