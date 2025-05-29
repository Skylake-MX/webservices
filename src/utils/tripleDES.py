from Crypto.Cipher import DES3
from Crypto.Hash import MD5
from Crypto.Util.Padding import pad, unpad
from dotenv import load_dotenv
from decouple import config

import base64
import xml.etree.ElementTree as ET

class TripleDES:
    def __init__(self, key_to_encrypt):
        self.key_to_encrypt = key_to_encrypt
        self.key = self._generate_key()
        self.iv = bytes(8)  # Vector de inicialización de 8 bytes (todo ceros)

    def _generate_key(self):
        # Crear una clave de 24 bytes a partir del hash MD5 de la clave proporcionada
        md5 = MD5.new()
        md5.update(self.key_to_encrypt.encode('utf-8'))
        digest = md5.digest()
        key_bytes = digest + digest[:8]  # Expandir a 24 bytes
        return key_bytes

    def decrypt(self, base64_message):
        cipher = DES3.new(self.key, DES3.MODE_CBC, self.iv)
        encrypted_message = base64.b64decode(base64_message)
        decrypted_message = unpad(cipher.decrypt(encrypted_message), DES3.block_size)
        #print(decrypted_message.decode('utf-8'))
        return decrypted_message.decode('utf-8')

    
    def encrypt(self, message):
        #print(f"Encrypting: '{message}'")
        #print(f"Key (hex): {self.key.hex()}")
        #print(f"IV (hex):  {self.iv.hex()}")
        
        cipher = DES3.new(self.key, DES3.MODE_CBC, self.iv)
        padded = pad(message.encode('utf-8'), DES3.block_size)
        encrypted = cipher.encrypt(padded)
        encrypted_b64 = base64.b64encode(encrypted).decode('utf-8')
        #print(f"Encrypted (base64): {encrypted_b64}")
        return encrypted_b64
    
def process_soap_request(soap_request, decryptor):
    # Parsear el XML
    root = ET.fromstring(soap_request)

    # Definir un espacio de nombres para facilitar la búsqueda
    namespaces = {'soap': 'http://schemas.xmlsoap.org/soap/envelope/', 
                  'xsi': 'http://www.w3.org/2001/XMLSchema-instance', 
                  'xsd': 'http://www.w3.org/2001/XMLSchema', 
                  'aol': 'http://wsAcredSitef.com.mx/types/AolSitef'}

    # Función recursiva para procesar elementos y desencriptar valores
    def decrypt_elements(element):
        if element.text and element.text.strip():
            try:
                element.text = decryptor.decrypt(element.text.strip())
                print(element.text, "=", decryptor.decrypt(element.text.strip()))
            except Exception as e:
                #print(f"Error al desencriptar: {e}")
                pass
            
        for child in element:
            decrypt_elements(child)

    # Buscar el cuerpo SOAP
    body = root.find("soap:Body", namespaces)
    if body is not None:
        decrypt_elements(body)

    # Devolver el XML modificado
    return ET.tostring(root, encoding='unicode')

# Ejemplo de uso
if __name__ == "__main__":
    soap_request = '''

    <s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"><s:Header><autorizacion xmlns="gsi">jU0Al0YYwDoKrmDTkv2IOZ4jg2iIvxsB</autorizacion></s:Header><s:Body xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema"><depositoCuenta xmlns="http://citySitef.com.mx/types/CitySitef"><DepositoInput><ContractNumber>GCww1aVrokfVbfloY0bzEw==</ContractNumber><CPAE>b0i5Q8l9Sso=</CPAE><UnitNumber>GsLSVNblLHs=</UnitNumber><AccountNumber>a2Q5RnFuUfQxTM8GMyN3MA==</AccountNumber><DeviceID>jziE6FQJ/r4=</DeviceID><Sequence>GChCwUiMWNfKTJzHGWi54w==</Sequence><DepositAmount>w8eyU+O0SkU=</DepositAmount><Currency>azhiH8/Y7PI=</Currency><ArchivoCorpo>cXVniXkFQJk=</ArchivoCorpo><StatusTicket>cXVniXkFQJk=</StatusTicket><StatusServicio>cXVniXkFQJk=</StatusServicio><DiferenciaFisica>cXVniXkFQJk=</DiferenciaFisica><AreaVenta>YKu8P60iADY=</AreaVenta><DiferenciaContable>wvHiwKGx2m4=</DiferenciaContable><Version>0/TwGrSsDqgeiBHB0762rA==</Version><FechaDispositivo>uQfzFSBQWV1O0hBjzffFoK1WbVPZFa/m</FechaDispositivo><Denominaciones><Type>TCfeuxsMGvw=</Type><Amount>YmXNFTsdAag=</Amount><Count>2U6jTMrEolo=</Count><Currency>azhiH8/Y7PI=</Currency></Denominaciones><Reference1>3wbme/TS4f4=</Reference1><Reference2>K724NL93aK31+UNg2DReywVpVdHtGG6I</Reference2><ProcessorID>JYtdP2MHdb8Bge6wWPgulQ==</ProcessorID><PackageID>hxlImSrOp84=</PackageID><CounterfeitAmount>TCfeuxsMGvw=</CounterfeitAmount><MissingAmount>TCfeuxsMGvw=</MissingAmount><SurplusAmount>TCfeuxsMGvw=</SurplusAmount></DepositoInput></depositoCuenta></s:Body></s:Envelope>
   
   '''

    load_dotenv(override=True)
    key_to_encrypt = config("KEY_TO_ENCRYPT_WS_TRADICIONAL")
    decryptor = TripleDES(key_to_encrypt)

    decrypted_soap = process_soap_request(soap_request, decryptor)
    print(decrypted_soap)
