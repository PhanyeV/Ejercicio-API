from fastapi import FastAPI, HTTPException
import requests
from bs4 import BeautifulSoup
import re

app = FastAPI(
    title="Consulta de Razas de Perros (EGVO)",
    description="Consulta las características de razas de perros directamente desde Purina España"
)

def formatear_nombre_raza(nombre: str) -> str:
    """Transforma 'Golden Retriever' en 'golden-retriever' para la URL."""
    nombre = nombre.lower().strip()
    # Reemplazar espacios y caracteres especiales comunes por guiones
    nombre = re.sub(r'[\s_]+', '-', nombre)
    # Eliminar acentos básicos si es necesario
    remplazos = {"á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u", "ñ": "n"}
    for origen, destino in remplazos.items():
        nombre = nombre.replace(origen, destino)
    return nombre

@app.get("/raza/{nombre_raza}")
def obtener_caracteristicas_raza(nombre_raza: str):
    # 1. Formatear el nombre para construir la URL correcta
    slug = formatear_nombre_raza(nombre_raza)
    url = f"https://www.purina.es/encuentra-mascota/razas-de-perro/{slug}"
    
    # User-Agent para evitar que el servidor nos bloquee pensando que somos un bot malicioso
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        respuesta = requests.get(url, headers=headers, timeout=10)
        
        if respuesta.status_code == 404:
            raise HTTPException(
                status_code=404, 
                detail=f"No se encontró la raza '{nombre_raza}'. Verifica si está escrita correctamente o si existe en Purina."
            )
        elif respuesta.status_code != 200:
            raise HTTPException(status_code=respuesta.status_code, detail="Error al conectar con el sitio de Purina.")
            
    except requests.exceptions.RequestException:
        raise HTTPException(status_code=500, detail="Error de conexión con el servidor externo.")

    # 2. Parsear el HTML con BeautifulSoup
    soup = BeautifulSoup(respuesta.text, 'html.parser')
    
    # 3. Extraer los datos (Buscamos el título principal y los bloques de características)
    titulo = soup.find('h1')
    titulo_texto = titulo.text.strip() if titulo else nombre_raza.capitalize()
    
    # Estructura para almacenar las características
    caracteristicas = {}
    
    # Purina suele organizar los datos clave en listas o bloques dentro de la ficha de la raza
    # Buscamos elementos comunes de especificaciones (clases habituales o etiquetas de lista)
    bloques_info = soup.find_all('div', class_='breed-key-facts') or soup.find_all('ul', class_='breed-characteristics')
    
    # En caso de que usen una estructura de "Título: Valor" genérica:
    for item in soup.find_all(['li', 'div'], class_=lambda x: x and 'characteristic' in x.lower() or 'fact' in x.lower()):
        text = item.get_text(separator=": ").strip()
        if ":" in text:
            clave, valor = text.split(":", 1)
            caracteristicas[clave.strip()] = valor.strip()

    # Si la web usa tablas o listas de especificaciones estándar en sus artículos:
    if not caracteristicas:
        for li in soup.find_all('li'):
            # Buscar patrones clave como "Tamaño:", "Esperanza de vida:", etc.
            texto_li = li.get_text().strip()
            if any(keyword in texto_li for keyword in ["Tamaño", "Pelaje", "Necesidad de ejercicio", "Esperanza de vida", "Carácter"]):
                if ":" in texto_li:
                    clave, valor = texto_li.split(":", 1)
                    caracteristicas[clave.strip()] = valor.strip()

    # Extraer el resumen introductorio si existe
    resumen = soup.find('div', class_='breed-profile__introduction') or soup.find('p')
    resumen_texto = resumen.text.strip() if resumen else "Sin resumen disponible."

    # 4. Devolver la respuesta en formato JSON limpio
    return {
        "raza": titulo_texto,
        "url_origen": url,
        "resumen": resumen_texto,
        "caracteristicas_principales": caracteristicas if caracteristicas else "Consulta la URL de origen para ver las barras de atributos personalizadas."
    }
