from fastapi import FastAPI, HTTPException
import requests
from bs4 import BeautifulSoup
import re

app = FastAPI(
    title="API de Razas de Perros",
    description="Consulta características de perros a través de Experto Animal"
)

def formatear_nombre_raza(nombre: str) -> str:
    """Transforma 'Pastor Alemán' en 'pastor-aleman' para la URL."""
    nombre = nombre.lower().strip()
    # Reemplazar acentos
    remplazos = {"á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u", "ñ": "n"}
    for origen, destino in remplazos.items():
        nombre = nombre.replace(origen, destino)
    # Reemplazar espacios y caracteres raros por guiones
    nombre = re.sub(r'[\s_]+', '-', nombre)
    return nombre

@app.get("/raza/{nombre_raza}")
def obtener_raza(nombre_raza: str):
    slug = formatear_nombre_raza(nombre_raza)
    url = f"https://www.expertoanimal.com/razas-de-perros/{slug}.html"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        respuesta = requests.get(url, headers=headers, timeout=10)
        
        if respuesta.status_code == 404:
            raise HTTPException(
                status_code=404, 
                detail=f"No se encontró la raza '{nombre_raza}'. Intenta con nombres comunes (ej: 'beagle', 'pastor-aleman', 'golden-retriever')."
            )
        elif respuesta.status_code != 200:
            raise HTTPException(status_code=respuesta.status_code, detail="Error al conectar con la web de origen.")
            
    except requests.exceptions.RequestException:
        raise HTTPException(status_code=500, detail="Error de conexión con el servidor externo.")

    soup = BeautifulSoup(respuesta.text, 'html.parser')
    
    # 1. Extraer el Título
    titulo = soup.find('h1')
    titulo_texto = titulo.text.strip() if titulo else nombre_raza.capitalize()
    
    # 2. Extraer las Características de la Ficha Técnica
    caracteristicas = {}
    
    # Experto Animal organiza sus datos clave en un bloque con la clase 'propiedades' o listas específicas
    ficha = soup.find('div', class_='propiedades')
    if ficha:
        items = ficha.find_all('div', class_='propiedad')
        for item in items:
            # Intentamos extraer el nombre del atributo y su valor
            label = item.find('span', class_='label')
            value = item.text.replace(label.text if label else "", "").strip()
            if label:
                clave = label.text.replace(":", "").strip()
                caracteristicas[clave] = value
    
    # Método alternativo si el diseño cambia ligeramente
    if not caracteristicas:
        for li in soup.find_all('li'):
            texto = li.get_text().strip()
            if any(k in texto for k in ["Tamaño", "Peso", "Esperanza de vida", "Actividad física"]):
                if ":" in texto:
                    clave, valor = texto.split(":", 1)
                    caracteristicas[clave.strip()] = valor.strip()

    # 3. Extraer la introducción / resumen
    resumen_nodo = soup.find('div', class_='introduccion') or soup.find('p', class_='intro')
    if not resumen_nodo:
        resumen_nodo = soup.find('p') # Primer párrafo por defecto
        
    resumen_texto = resumen_nodo.text.strip() if resumen_nodo else "Sin resumen disponible."

    return {
        "raza": titulo_texto,
        "url_origen": url,
        "resumen": resumen_texto,
        "caracteristicas_principales": caracteristicas
    }
