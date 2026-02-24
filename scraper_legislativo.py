import os
import requests
import pdfplumber
import io
from bs4 import BeautifulSoup
import google.generativeai as genai

# 1. Configurar la API Key de Gemini
# El script buscará la variable de entorno que configuramos en GitHub o en tu computadora
genai.configure(api_key=os.environ["GEMINI_API_KEY"])
modelo = genai.GenerativeModel('gemini-2.5-flash') # Modelo rápido y eficiente para texto

# 2. AQUÍ VAN LOS 32 CONGRESOS
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
    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        text = soup.get_text(separator=' ', strip=True)
        
        pdf_links = []
        for a in soup.find_all('a', href=True):
            if '.pdf' in a['href'].lower():
                link = a['href']
                if not link.startswith('http'):
                    link = url.rstrip('/') + '/' + link.lstrip('/')
                pdf_links.append(link)
                
        return text[:5000], pdf_links
    except Exception as e:
        return f"Error accediendo a la web: {e}", []

def extraer_texto_pdf(pdf_url):
    try:
        response = requests.get(pdf_url, timeout=10)
        with pdfplumber.open(io.BytesIO(response.content)) as pdf:
            texto_pdf = ""
            for page in pdf.pages[:3]: 
                texto_pdf += page.extract_text() + "\n"
        return texto_pdf
    except Exception as e:
        return ""

def generar_newsletter(estado, texto_crudo):
    prompt = f"""
    Eres un analista legislativo experto de México. Analiza el siguiente texto extraído de la página web 
    y la agenda del congreso del estado de {estado}.
    
    Tu trabajo es identificar las noticias e iniciativas legislativas más relevantes y estructurarlas 
    estrictamente en el siguiente formato para un newsletter:
    
    - Estado: {estado}
    - Iniciativa legislativa en cuestión: [Nombre de la iniciativa]
    - Noticia: [Estado actual: Ej. Se aprobó, se desechó, se votará esta semana, etc.]
    
    Si hay varias iniciativas, lístalas todas bajo el mismo formato. Si no hay información clara, 
    indica que no hubo actividad relevante reportada en la página principal.
    
    Texto extraído:
    {texto_crudo}
    """
    try:
        respuesta = modelo.generate_content(prompt)
        return respuesta.text
    except Exception as e:
        return f"- Estado: {estado}\n- Error al procesar con Gemini: {e}"

def ejecutar_agente():
    boletin_semanal = []
    
    for estado, url in CONGRESOS.items():
        print(f"Analizando Congreso de {estado}...")
        texto_web, pdf_links = obtener_texto_web(url)
        
        texto_pdfs = ""
        for pdf_link in pdf_links[:2]:
            texto_pdfs += extraer_texto_pdf(pdf_link)
            
        texto_completo = f"--- TEXTO WEB ---\n{texto_web}\n--- TEXTO PDFs ---\n{texto_pdfs}"
        
        resultado = generar_newsletter(estado, texto_completo)
        boletin_semanal.append(resultado)
        
    print("\n\n" + "="*40)
    print("BOLETÍN LEGISLATIVO SEMANAL")
    print("="*40 + "\n")
    for nota in boletin_semanal:
        print(nota)
        print("-" * 20)

if __name__ == "__main__":
    ejecutar_agente()
