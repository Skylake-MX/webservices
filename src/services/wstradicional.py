import requests
import sys
import datetime
import pandas as pd
import xml.etree.ElementTree as ET
from decouple import config
from dotenv import load_dotenv
from src.utils.tripleDES import TripleDES, process_soap_request

load_dotenv(override=True)
tdes = TripleDES(config("KEY_TO_ENCRYPT_WS_TRADICIONAL"))

df=pd.read_csv("DepositoMXN.csv", encoding="latin1")
lista=df.to_dict(orient="records")

def seleccionar_registro(lista):
    id_dep = input("Ingrese el Id Dispositivo: ")
    print(f"Los siguientes depositos estan pendientes de envio en el archivo DepositoMXN para el id: {id_dep}\n")

    resultados = [r for r in lista if str(r.get("ID_DEP"))==str(id_dep)]
    if not resultados:
        print("\nNo se encontraron coincidencias")
        return None

    for i, item in enumerate(resultados):
        print(f"[{i}],{item}")

    seleccion = int(input("\nSeleccione un deposito a transmitir por [numero]: "))
    return resultados[seleccion]

def limpiar_cadena(valor):
    if pd.isna(valor):
        return ""
    if isinstance(valor, float) and valor.is_integer():
        valor = int(valor)  # elimina el .0
    valor = str(valor).strip()
    valor = valor.lstrip("'")  # quita comilla simple al inicio si la hay
    if valor == "-":
        return "0"
    return valor

def construir_datos_para_request(fila, mapeo):
    datos = {}
    for tag_xml, origen in mapeo.items():
        if callable(origen):
            datos[tag_xml] = origen(fila)
        else:
            datos[tag_xml] = fila.get(origen, "")
    return datos

registro = seleccionar_registro(lista)

#### SOLCITUD DE TOKEN #####

def request_token(soap_request_token, tdes):
    root = ET.fromstring(soap_request_token) # Parsear el XML

    # Definir un espacio de nombres para facilitar la búsqueda
    namespaces = {'soap': 'http://schemas.xmlsoap.org/soap/envelope/', 'xsi': 'http://www.w3.org/2001/XMLSchema-instance', 'xsd': 'http://www.w3.org/2001/XMLSchema'}

    # Función recursiva para procesar elementos y cifrar valores
    def encrypt_elements(element):
        if element.text and element.text.strip():
            try:
                element.text = tdes.encrypt(element.text.strip())
            except Exception as e:
                print(f"Error al cifrar: {e}")
        for child in element:
            encrypt_elements(child)

    # Buscar el cuerpo SOAP
    body = root.find("soap:Body", namespaces)
    if body is not None:
        encrypt_elements(body)

    # Devolver el XML modificado
    return ET.tostring(root, encoding='unicode')

# Enviar la solicitud
def send_request_token(soap_request_token, tdes):
    # Cifrar el cuerpo SOAP
    encrypted_soap = request_token(soap_request_token, tdes)

    # URL del servicio SOAP (asegúrate de que sea la correcta)
    url = 'http://187.174.109.62:8777/wsAcredSitef/AcredSitef/ws/AOL_SITEF.wsdl'  # Cambia esto por el endpoint real

    # Encabezados SOAP
    headers = {
        'Content-Type': 'text/xml;charset=UTF-8',
        'SOAPAction': 'http://wsAcredSitef.com.mx/types/AolSitef/tokenRequest',  # Asegúrate de usar la acción SOAP correcta
    }

    # Realizar la solicitud POST
    response = requests.post(url, data=encrypted_soap, headers=headers)
    return response

mapeo_personalizado_sin_encriptar = {
    "Dispositivo": lambda fila: limpiar_cadena(fila["ID_DEP"]),
    "idProveedor": lambda fila: limpiar_cadena(fila["PROVEEDOR"]),
}

valores_sin_encriptar = mapeo_personalizado_sin_encriptar
dispositivo = valores_sin_encriptar["Dispositivo"](registro)
id_proveedor = limpiar_cadena(valores_sin_encriptar["idProveedor"](registro))
#print(dispositivo)
#print(id_proveedor)

# Ejemplo de uso
if __name__ == "__main__":
    soap_request_token = f'''
    <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:aol="http://wsAcredSitef.com.mx/types/AolSitef">
        <soapenv:Header/>
        <soapenv:Body>
            <aol:tokenRequest>
                <aol:Dispositivo>{dispositivo}</aol:Dispositivo>
                <aol:idProveedor>{id_proveedor}</aol:idProveedor>
            </aol:tokenRequest>
        </soapenv:Body>
    </soapenv:Envelope>
    '''
    # Enviar la solicitud SOAP cifrada
    response = send_request_token(soap_request_token, tdes)

    # Verificar la respuesta
    if response.status_code == 200:
        print("\nRespuesta recibida correctamente.")
        print("Respuesta Cifrada:", response.text)

        # Registrar el namespace para buscar correctamente
        namespaces = {'ns2': 'http://wsAcredSitef.com.mx/types/AolSitef'}

        # Parsear el XML
        root = ET.fromstring(response.text)

        # Buscar el elemento y obtener el texto
        token = root.find('.//ns2:Stoken', namespaces).text

        # Mostrar o usar el token
        #print("Token:", token)

    else:
        print(f"\nError al realizar la solicitud: {response.status_code}")
        print(response.text)

##### RequestDeposito #####

mapeo_personalizado_encrypt= {
    "Token": lambda fila: token,
    "Dispositivo": lambda fila: tdes.encrypt(limpiar_cadena(fila["ID_DEP"])),
    "Cuenta": lambda fila: tdes.encrypt(limpiar_cadena(fila["CUENTA_CHEQUES"])),
    "Secuencia": lambda fila: tdes.encrypt(limpiar_cadena(fila["OPERACION"])),
    "fechaDispositivo": lambda fila: tdes.encrypt(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
    "usuario": lambda fila: tdes.encrypt(limpiar_cadena(fila["USUARIO"])),
    "montoDeposito": lambda fila: tdes.encrypt(limpiar_cadena(fila["TOTAL"])),
    "Divisa": lambda fila: tdes.encrypt("1" if str(fila.get("DIVISA", "")).upper() == "MXN" else "2"),
    "comprobante": lambda fila: tdes.encrypt(limpiar_cadena(fila["FOLIOENVASE"])),
    "referencia1": lambda fila: tdes.encrypt(limpiar_cadena(fila["REFERENCIA_1"])),
    "referencia2": lambda fila: tdes.encrypt(limpiar_cadena(fila["REFERENCIA_2"])),
    "banco": lambda fila: tdes.encrypt(limpiar_cadena(fila["BANCO"])),
    "totalSobre": lambda fila: tdes.encrypt(limpiar_cadena("0")),
    "codigoSobre": lambda fila: tdes.encrypt(limpiar_cadena("0")),
    "totalDocumentos": lambda fila: tdes.encrypt(limpiar_cadena("0")),
    "diferenciaContable": lambda fila: tdes.encrypt(limpiar_cadena("0")),
    "diferenciaFisica": lambda fila: tdes.encrypt(limpiar_cadena("0")),
    "horaTransaccionInicia": lambda fila: tdes.encrypt(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
    "importeCodigoBarras": lambda fila: tdes.encrypt(limpiar_cadena(fila["IMPORTE CODIGO BARRAS"])),
    "importeWS": lambda fila: tdes.encrypt(limpiar_cadena(fila["TOTAL"])),
    "porDepositarTicket": lambda fila: tdes.encrypt(limpiar_cadena("0")),
    "ticket": lambda fila: tdes.encrypt(limpiar_cadena("0")),
    "tipo": lambda fila: tdes.encrypt(limpiar_cadena("0")),
    "totalDepositado": lambda fila: tdes.encrypt(limpiar_cadena(fila["TOTAL"])),
    "validacion": lambda fila: tdes.encrypt(limpiar_cadena("0")),
    "AreaVenta": lambda fila: tdes.encrypt(limpiar_cadena("0")),
    "idProveedor": lambda fila: tdes.encrypt(limpiar_cadena(fila["PROVEEDOR"])),
    "noSerie": lambda fila: tdes.encrypt(limpiar_cadena(fila["NO DE SERIE"])),
    "ipCofre": lambda fila: tdes.encrypt(limpiar_cadena("127.0.0.1")),
    "cf1": lambda fila: tdes.encrypt(limpiar_cadena(fila["CAMPO REFERENCIA 1"])),
    "cf2": lambda fila: tdes.encrypt(limpiar_cadena(fila["CAMPO REFERENCIA 2"])),
    "operacion": lambda fila: tdes.encrypt(limpiar_cadena("14")),
}

if registro:
    datos_mapeados = construir_datos_para_request(registro, mapeo_personalizado_encrypt)
    
    #print("\nDatos mapeados:")
    for clave, valor in datos_mapeados.items():
        #print(f"{clave}: {valor}")
        pass

    denominaciones_tags = []

    for col in registro:
        if col.startswith(('B_', 'M_')):
            cantidad = registro[col]
            if pd.isna(cantidad) or int(cantidad) == 0:
                continue  # ignorar si no hay piezas

            tipo = '0' if col.startswith('B_') else '1'
            denominacion = col.split('_')[1]

            # Crear elemento Denominaciones correctamente con namespaces
            denom_elem = ET.Element("{http://wsAcredSitef.com.mx/types/AolSitef}Denominaciones")
            ET.SubElement(denom_elem, "{http://wsAcredSitef.com.mx/types/AolSitef}tipo").text = tdes.encrypt(tipo)
            ET.SubElement(denom_elem, "{http://wsAcredSitef.com.mx/types/AolSitef}denominacion").text = tdes.encrypt(denominacion)
            ET.SubElement(denom_elem, "{http://wsAcredSitef.com.mx/types/AolSitef}cantidad").text = tdes.encrypt(str(int(cantidad)))

            denominaciones_tags.append(denom_elem)


def generar_xml(data, denominaciones_tags):
    NS_SOAP = "http://schemas.xmlsoap.org/soap/envelope/"
    NS_AOL = "http://wsAcredSitef.com.mx/types/AolSitef"

    ET.register_namespace("soapenv", NS_SOAP)
    ET.register_namespace("aol", NS_AOL)

    envelope = ET.Element(f"{{{NS_SOAP}}}Envelope")
    ET.SubElement(envelope, f"{{{NS_SOAP}}}Header")
    body = ET.SubElement(envelope, f"{{{NS_SOAP}}}Body")
    deposito_request = ET.SubElement(body, f"{{{NS_AOL}}}depositoRequest")

    # Insertar los elementos en orden, y agregar denominaciones justo después de <aol:banco>
    insert_after = "banco"
    insert_index = None

    for idx, (tag, valor) in enumerate(data.items()):
        elem = ET.SubElement(deposito_request, f"{{{NS_AOL}}}{tag}")
        elem.text = str(valor)

        if tag == insert_after:
            insert_index = idx  # Guardamos la posición donde insertar denominaciones

    if insert_index is not None:
        # Reorganizar elementos: primero extraemos los existentes
        elements = list(deposito_request)
        deposito_request.clear()

        for i, el in enumerate(elements):
            deposito_request.append(el)
            if i == insert_index:
                # Insertamos después del <banco>
                for denom_element in denominaciones_tags:
                    deposito_request.append(denom_element)
    else:
        # Si no se encuentra <banco>, simplemente los agregamos al final
        for denom_element in denominaciones_tags:
            deposito_request.append(denom_element)

    xml_str = ET.tostring(envelope, encoding="unicode")
    print("\nXML Generado:\n")
    print(xml_str)
    return xml_str

request = generar_xml(datos_mapeados, denominaciones_tags)

def depositoRequest(request):
    # URL del servicio SOAP (asegúrate de que sea la correcta)
    url = 'http://187.174.109.62:8777/wsAcredSitef/AcredSitef/ws/AOL_SITEF.wsdl'  # Cambia esto por el endpoint real

    # Encabezados SOAP
    headers = {
        'Content-Type': 'text/xml;charset=UTF-8',
        'SOAPAction': 'http://wsAcredSitef.com.mx/types/AolSitef/depositoRequest',  # Asegúrate de usar la acción SOAP correcta
    }

    # Realizar la solicitud POST
    response = requests.post(url, data=request, headers=headers)

    return response

enviar = input("\n¿Desea enviar el depósito a SITEF? [S/N]: ").strip().upper()

if enviar == 'S':
    print("Enviando depósito a SITEF...")

    response = depositoRequest(request)
    # Verificar la respuesta
    if response.status_code == 200:
        print("\nRespuesta recibida correctamente")
        print("Respuesta Cifrada:", response.text)

    else:
        print(f"\nError al realizar la solicitud: {response.status_code}")
        print(response.text)

    decrypted_soap = process_soap_request(response.text, tdes)
    print("\nRespuesta Decifrada", decrypted_soap)
elif enviar == 'N':
    print("Operación cancelada. Saliendo del programa.")
    sys.exit()
else:
    print("Opción no válida. Saliendo del programa.")
    sys.exit()