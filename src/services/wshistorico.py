from decouple import config
from dotenv import load_dotenv
from src.utils.aes_tool import encrypt
import requests
import xml.etree.ElementTree as ET
import json
import pandas as pd
import os
import sys
from tabulate import tabulate

def save_registros(xml_response):
    # Ruta base compatible con ejecución desde .exe o .py
    if getattr(sys, 'frozen', False):
        BASE_DIR = os.path.dirname(sys.executable)
    else:
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))

    output_dir = os.path.join(BASE_DIR, "data", "output")
    os.makedirs(output_dir, exist_ok=True)

    # Guardar XML
    xml_path = os.path.join(output_dir, "registros.xml")
    with open(xml_path, "w", encoding="utf-8") as f:
        f.write(xml_response)
    print(f"Exportado a {xml_path}")

    # Parsear XML
    try:
        root = ET.fromstring(xml_response)
    except ET.ParseError:
        print("❌ Error al parsear el XML.")
        return

    # Buscar registros
    registros = []
    for registro in root.findall('.//{http://wsSitef_reporteador.com.mx/types/AolSitef_Reporteador}registro'):
        try:
            json_data = json.loads(registro.text)
            registros.append(json_data)
        except json.JSONDecodeError:
            print("⚠️ Error al parsear el JSON de un registro.")

    # Crear DataFrame y exportar si hay registros válidos
    if registros:
        df = pd.DataFrame(registros)
        pd.set_option('display.max_columns', None)

        # Exportar a CSV
        csv_path = os.path.join(output_dir, "registros.csv")
        df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        print(f"Exportado a {csv_path}")

        # Exportar a JSON
        json_path = os.path.join(output_dir, "registros.json")
        df.to_json(json_path, orient='records', indent=4, force_ascii=False)
        print(f"Exportado a {json_path}")
    else:
        print("⚠️ No se encontraron registros.")

load_dotenv(override=True)

usuario = config('USER')
contrasena = config('PASS')

registros=""

contrasena_encrypt=encrypt(config('SECRET_KEY'),contrasena)

def datos_consulta():
    id=input("\nDigita su ID Dispositivo: ")
    id_encrypt = encrypt(config('SECRET_KEY'),id)
    print("ID Dispositivo encryptado", id_encrypt)

    date=input("\nCaptura la fecha a consultar: ")
    date_encrypt = encrypt(config('SECRET_KEY'),date)
    print("Fecha Encriptada: ", date_encrypt)
    return id_encrypt, date_encrypt

headers = {
    "Content-Type": "text/xml; charset=utf-8",
    "SOAPAction": ""
    }

def peticionToken():
    soap_body_token = f"""<?xml version="1.0" encoding="UTF-8"?>
    <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
                    xmlns:aol="http://wsSitef_reporteador.com.mx/types/AolSitef_Reporteador">
    <soapenv:Header/>
    <soapenv:Body>
        <aol:tokenClienteRq>
            <aol:usuario>{usuario}</aol:usuario>
            <aol:contrasena>{contrasena_encrypt}</aol:contrasena>
        </aol:tokenClienteRq>
    </soapenv:Body>
    </soapenv:Envelope>"""

    print("\nRequest tokenClienteRq: ", soap_body_token)
    #print("Response XML:")

    response_token= requests.post(config('ENDPOINT'), data=soap_body_token, headers=headers)
    tree = ET.fromstring(response_token.text)
    token_element = tree.find(".//{http://wsSitef_reporteador.com.mx/types/AolSitef_Reporteador}Stoken")
    token = token_element.text if token_element is not None else None

    if not token:
        print("No se pudo extraer el token")
        print(response_token.text)
        exit()

    print("\nResponse tokenClienteRq: ", response_token.text)

    print("\nToken obtenido: ", token)
    return token

def peticionRegistros(token, date_encrypt, id_encrypt):

    soap_body_registros = f"""<?xml version="1.0" encoding="UTF-8"?>
    <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
                    xmlns:aol="http://wsSitef_reporteador.com.mx/types/AolSitef_Reporteador">
    <soapenv:Header/>
    <soapenv:Body>
        <aol:peticionRegistros>
            <aol:usuario>{usuario}</aol:usuario>
            <aol:token>{token}</aol:token>
            <aol:fechaCorte>{date_encrypt}</aol:fechaCorte>
            <aol:claveDispositivo>{id_encrypt}</aol:claveDispositivo>
        </aol:peticionRegistros>
    </soapenv:Body>
    </soapenv:Envelope>"""

    print("\nRequest peticionRegistros: ", soap_body_registros)

    response_registros = requests.post(config('ENDPOINT'), data=soap_body_registros, headers=headers)

    print("Código de respuesta:", response_registros.status_code)
    print("Respuesta XML:")
    print(response_registros.text)

    # save_registros(response_registros.text)

    root = ET.fromstring(response_registros.text)

    # Namespace usado en el XML
    ns = {
        'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
        'ns2': 'http://wsSitef_reporteador.com.mx/types/AolSitef_Reporteador'
    }

    # Buscar todos los nodos <ns2:registro>
    registros = root.findall('.//ns2:registro', ns)

    # Lista para guardar los folios
    folios = []

    # Extraer cada JSON del texto y sacar el folio
    for r in registros:
        contenido = r.text.strip()
        data = json.loads(contenido)
        folios.append(data.get('folio'))

    print("Folios encontrados:", folios)

    return folios

def peticionPunteo(token, registros):
    # Encriptar cada folio
    registros_encrypted = [
        encrypt(config('SECRET_KEY'), folio) for folio in registros
    ]

    # Crear bloque XML con <aol:operacion><aol:folio>...</aol:folio></aol:operacion>
    operaciones_xml = ""
    for folio in registros_encrypted:
        # Construir el cuerpo SOAP completo
        soap_body_punteo = f"""<?xml version="1.0" encoding="UTF-8"?>
        <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:aol="http://wsSitef_reporteador.com.mx/types/AolSitef_Reporteador">
        <soapenv:Header/>
        <soapenv:Body>
            <aol:punteoRegistroRq>
                <aol:usuario>{usuario}</aol:usuario>
                <aol:token>{token}</aol:token>
                <aol:operacion>
                    <aol:folio>{folio}</aol:folio>
                </aol:operacion>
            </aol:punteoRegistroRq>
        </soapenv:Body>
        </soapenv:Envelope>"""

        print("\nRequest punteoRegistroRq:\n", soap_body_punteo)

        # Enviar peticións
        response = requests.post(config('ENDPOINT'), data=soap_body_punteo, headers=headers)

        # Mostrar respuesta
        print("Código de respuesta:", response.status_code)
        print("Respuesta XML:\n", response.text)

while True:
    print("\n[1] Petición de Registros.")
    print("[2] Punteo de Operaciones.")
    print("[0] Salir.")
    metodo = input("Seleccione una de las opciones anteriores []: ")

    if metodo == "1":
        id_encrypt, date_encrypt = datos_consulta()
        token = peticionToken()
        registros = peticionRegistros(token, date_encrypt, id_encrypt)

    elif metodo == "2":
        print("¿Desea insertar algún folio específico? [Y/N]")
        opcion2 = input()

        if opcion2.upper() == "Y":
            entrada = input("\nLos registros para realizar el punteo son (separe mediante comas):\n> ")
            registros = [folio.strip() for folio in entrada.split(",") if folio.strip()]
            print("Registros cargados:", registros)
            
            id_encrypt, date_encrypt = datos_consulta()
            token = peticionToken()
            peticionPunteo(token, registros)
            input("Pulse una tecla para continuar...")

        elif registros and opcion2.upper() == "N":
            print("Se procesarán los registros de la última consulta peticionRegistros")
            print("Registros a puntear:", registros)
           
            token = peticionToken()
            peticionPunteo(token, registros)
            input("Pulse una tecla para continuar...")

        else:
            print("No se encontraron folios para realizar el punteo. Regresando...")

    elif metodo == "0":
        print("Saliendo del programa.")
        sys.exit()

    else:
        print("Opción inválida. Intenta nuevamente.")