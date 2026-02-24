import os
import requests
import pdfplumber
import io
import json
import urllib.parse
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
import google.generativeai as genai

# 1. Configuración de la API Key de Gemini
genai.configure(api_key=os.environ["GEMINI_API_KEY"])

# Configuración para forzar a Gemini a responder SIEMPRE en formato JSON válido
configuracion_json = genai.GenerationConfig(response_mime_type="application/json")
modelo = genai.GenerativeModel('gemini-2.5-flash', generation_config=configuracion_json)

# 2. Diccionario de los 32 Congresos Estatales
CONGRESOS = {
    "Aguascalientes": "https://www.congresoags.gob.mx/",
    "Baja California": "https://www.congresobc.gob.mx/",
    "Baja California Sur": "https://www.cbcs.gob.mx/",
    "Campeche": "https://www.congresocam.gob.mx/",
    "Chiapas": "https://www.congresochiapas.gob.mx/",
    "Chihuahua": "https://www.congresochihuahua.gob.mx/",
    "Ciudad de México": "https://www.congresocdmx.gob.mx/",
    "Coahuila": "https://www.congresocoahuila.gob.mx/",
    "Colima": "https://congresocol.gob.mx/",
    "Durango": "https://congresodurango.gob.mx/",
    "Estado de México": "https://www.legislaturaedomex.gob.mx/",
    "Guanajuato": "https://www.congresogto.gob.mx/",
    "Guerrero": "https://congresogro.gob.mx/",
    "Hidalgo": "https://www.congreso-hidalgo.gob.mx/",
    "Jalisco": "https://www.congresojal.gob.mx/",
    "Michoacán": "https://congresomich.gob.mx/",
    "Morelos": "https://congresomorelos.gob.mx/",
    "Nayarit": "https://www.congresonayarit.mx/",
    "Nuevo León": "https://www.hcnl.gob.mx/",
    "Oaxaca": "https://www.congresooaxaca.gob.mx/",
    "Puebla": "https://www.congresopuebla.gob.mx/",
    "Querétaro": "https://legislaturaqueretaro.gob.mx/",
    "Quintana Roo": "https://www.congresoqroo.gob.mx/",
    "San Luis Potosí": "https://congresosanluis.gob.mx/",
    "Sinaloa": "https://www.congresosinaloa.gob.mx/",
    "Sonora": "https://www.congresoson.gob.mx/",
    "Tabasco": "https://congresotabasco.gob.mx/",
    "Tamaulipas": "https://www.congresotamaulipas.gob.mx/",
    "Tlaxcala": "https://congresotlaxcala.gob.mx/",
    "Veracruz": "https://www.legisver.gob.mx/",
    "Yucatán": "https://www.congresoyucatan.gob.mx/",
    "Zacatecas": "https://www.congresozac.gob.mx/"
}

def obtener_texto_web(url):
    """Extrae texto, links a PDFs y busca el canal de YouTube del congreso"""
    try:
        # Usamos un User-Agent para evitar que algunas páginas bloqueen la petición
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        text = soup.get_text(separator=' ', strip=True)
        
        pdf_links = []
        youtube_links = set() # Usamos un set para no tener canales duplicados
        
        for a in soup.find_all('a', href=True):
            href = a['href'].lower()
            
            # Buscar PDFs
            if '.pdf' in href:
                link = a['href']
                if not link.startswith('http'):
                    link = url.rstrip('/') + '/' + link.lstrip('/')
                pdf_links.append(link)
                
            # Buscar links de YouTube (canal oficial o transmisiones)
            elif 'youtube.com' in href or 'youtu.be' in href:
                youtube_links.add(a['href'])
                
        # Tomamos el primer link de YouTube si existe
        yt_link = list(youtube_links)[0] if youtube_links else None
                
        return text[:4000], pdf_links, yt_link
    except Exception as e:
        return f"Error accediendo a la web: {e}", [], None

def extraer_texto_pdf(pdf_url):
    """Descarga y lee las primeras páginas de un PDF"""
    try:
        response = requests.get(pdf_url, timeout=10)
        with pdfplumber.open(io.BytesIO(response.content)) as pdf:
            texto_pdf = ""
            for page in pdf.pages[:2]: 
                texto_pdf += page.extract_text() + "\n"
        return texto_pdf
    except Exception as e:
        return ""

def buscar_noticia_google(estado, tema):
    """Busca el tema en Google News y devuelve el link de la mejor coincidencia"""
    query = urllib.parse.quote(f'"{tema}" congreso {estado} noticias')
    url = f"https://news.google.com/rss/search?q={query}&hl=es-419&gl=MX&ceid=MX:es-419"
    
    try:
        response = requests.get(url, timeout=5)
        root = ET.fromstring(response.content)
        
        primer_item = root.find('.//item')
        if primer_item is not None:
            link = primer_item.find('link').text
            return link
    except Exception:
        pass 
        
    return None

def generar_newsletter(estado, texto_crudo, yt_link):
    """Pide a Gemini los datos, busca noticias y arma el formato de WhatsApp"""
    
    prompt = f"""
    Eres un analista legislativo experto de México. Analiza el texto del congreso de {estado}.
    Identifica las 1 a 3 iniciativas legislativas más relevantes.
    
    Devuelve tu respuesta ESTRICTAMENTE como una lista de objetos JSON con las siguientes claves exactas:
    "iniciativa": "El nombre corto y claro de la iniciativa o tema clave",
    "noticia": "Estatus actual y detalles breves (usa emojis como ✅, 🛑, ⏳, 🏛️)"
    
    Si el texto indica errores de página (ej. 404, Access Denied) o no hay información relevante, devuelve una lista vacía: []
    
    Texto extraído para analizar:
    {texto_crudo}
    """
    try:
        respuesta = modelo.generate_content(prompt)
        # Como forzamos el output a JSON, podemos cargarlo directamente
        datos = json.loads(respuesta.text)
        
        texto_whatsapp = f"📍 *{estado}*\n"
        
        if not datos or len(datos) == 0:
            texto_whatsapp += "- 📭 Sin actividad legislativa relevante reportada esta semana.\n"
        else:
            for item in datos:
                tema = item.get("iniciativa", "Tema no especificado")
                noticia = item.get("noticia", "Sin detalles")
                
                texto_whatsapp += f"*Iniciativa:* {tema}\n"
                texto_whatsapp += f"- 🏛️ *Noticia:* {noticia}\n"
                
                link_noticia = buscar_noticia_google(estado, tema)
                if link_noticia:
                    texto_whatsapp += f"- 📰 *Fuente en medios:* {link_noticia}\n"
                
                texto_whatsapp += "\n" 
        
        # Agregamos el link de YouTube al final del bloque del estado si se encontró uno
        if yt_link:
            texto_whatsapp += f"📺 *Transmisiones del Congreso:* {yt_link}\n"
            
        return texto_whatsapp.strip()
        
    except Exception as e:
        return f"📍 *{estado}*\n- ⚠️ Error procesando datos: {e}"

def ejecutar_agente():
    boletin_semanal = []
    
    print("Iniciando escaneo de los 32 congresos (Versión con YouTube y Google News)...\n")
    
    for estado, url in CONGRESOS.items():
        print(f"Analizando Congreso de {estado}...")
        texto_web, pdf_links, yt_link = obtener_texto_web(url)
        
        texto_pdfs = ""
        for pdf_link in pdf_links[:1]:
            texto_pdfs += extraer_texto_pdf(pdf_link)
            
        texto_completo = f"--- TEXTO WEB ---\n{texto_web}\n--- TEXTO PDFs ---\n{texto_pdfs}"
        
        resultado = generar_newsletter(estado, texto_completo, yt_link)
        boletin_semanal.append(resultado)
        
    print("\n\n" + "="*40)
    print("📱 BOLETÍN LEGISLATIVO SEMANAL 📱")
    print("="*40 + "\n")
    
    texto_final = "\n\n".join(boletin_semanal)
    print(texto_final)

if __name__ == "__main__":
    ejecutar_agente()
