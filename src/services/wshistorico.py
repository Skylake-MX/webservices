from decouple import config
from dotenv import load_dotenv
from src.utils.aes_tool import encrypt
import requests
import xml.etree.ElementTree as ET
import json
import pandas as pd
import os
from tabulate import tabulate

def save_registros(xml_response):

    with open("data/output/registros.xml", "w", encoding="utf-8") as f:
        f.write(xml_response)
    print("Exportado a data/output/registros.xml")

    # Parsear XML
    root = ET.fromstring(xml_response)

    # Buscar todos los registros
    registros = []
    for registro in root.findall('.//{http://wsSitef_reporteador.com.mx/types/AolSitef_Reporteador}registro'):
        try:
            json_data = json.loads(registro.text)
            registros.append(json_data)
        except json.JSONDecodeError:
            print("Error al parsear el JSON de un registro")

    # Crear DataFrame
    if registros:
        df = pd.DataFrame(registros)
        pd.set_option('display.max_columns', None)

        # Crear carpeta de salida si no existe
        os.makedirs("data/output", exist_ok=True)

        # Exportar a CSV
        df.to_csv("data/output/registros.csv", index=False, encoding='utf-8-sig')
        print("\nExportado a data/output/registros.csv")

        # Exportar a JSON
        df.to_json("data/output/registros.json", orient='records', indent=4, force_ascii=False)
        print("Exportado a data/output/registros.json")

    else:
        print("No se encontraron registros.")


load_dotenv(override=True)

usuario = config('USER')
contrasena = config('PASS')

id=input("Digita su ID Dispositivo: ")
id_encrypt = encrypt(config('SECRET_KEY'),id)

date=input("Captura la fecha a consultar: ")
date_encrypt = encrypt(config('SECRET_KEY'),date)

headers = {
    "Content-Type": "text/xml; charset=utf-8",
    "SOAPAction": ""
}

soap_body_token = f"""<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
                  xmlns:aol="http://wsSitef_reporteador.com.mx/types/AolSitef_Reporteador">
   <soapenv:Header/>
   <soapenv:Body>
      <aol:tokenClienteRq>
         <aol:usuario>{usuario}</aol:usuario>
         <aol:contrasena>{contrasena}</aol:contrasena>
      </aol:tokenClienteRq>
   </soapenv:Body>
</soapenv:Envelope>"""

#print("Codigo Response: ", response.status_code)
#print("Response XML:")
#print(response.text)

response_token= requests.post(config('ENDPOINT'), data=soap_body_token, headers=headers)
tree = ET.fromstring(response_token.text)
token_element = tree.find(".//{http://wsSitef_reporteador.com.mx/types/AolSitef_Reporteador}Stoken")
token = token_element.text if token_element is not None else None

if not token:
    print("No se pudo extraer el token")
    print(response_token.text)
    exit()

# print("Token obtenido:\n", token)

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

response_registros = requests.post(config('ENDPOINT'), data=soap_body_registros, headers=headers)

print("Código de respuesta:", response_registros.status_code)
print("Respuesta XML:")
print(response_registros.text)

save_registros(response_registros.text)