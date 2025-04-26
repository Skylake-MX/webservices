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
        return decrypted_message.decode('utf-8')
    
    def encrypt(self, message):
        # Codificar el mensaje a bytes
        data = message.encode('utf-8')

        # Padding para asegurar múltiplos de 8 bytes
        padded_data = pad(data, DES3.block_size)

        # Crear el cifrador
        cipher = DES3.new(self.key, DES3.MODE_CBC, self.iv)

        # Cifrar y codificar en base64
        encrypted = cipher.encrypt(padded_data)
        return base64.b64encode(encrypted).decode('utf-8')
    
def process_soap_request(soap_request, decryptor):
    # Parsear el XML
    root = ET.fromstring(soap_request)

    # Definir un espacio de nombres para facilitar la búsqueda
    namespaces = {'soap': 'http://schemas.xmlsoap.org/soap/envelope/', 'xsi': 'http://www.w3.org/2001/XMLSchema-instance', 'xsd': 'http://www.w3.org/2001/XMLSchema'}

    # Función recursiva para procesar elementos y desencriptar valores
    def decrypt_elements(element):
        if element.text and element.text.strip():
            try:
                element.text = decryptor.decrypt(element.text.strip())
            except Exception as e:
                print(f"Error al desencriptar: {e}")
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
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:aol="http://wsAcredSitef.com.mx/types/AolSitef">
<soapenv:Header/>
<soapenv:Body>
<aol:tokenRequest>
<aol:Dispositivo>V7z5TsuT1Cc=</aol:Dispositivo>
<aol:idProveedor>/IuVeKR2OPGRheAZEf656ah292d5nQxPbMXMZxOUPnAubClxOmpi/A</aol:idProveedor>
</aol:tokenRequest>
</soapenv:Body>
</soapenv:Envelope>

   '''

    load_dotenv(override=True)
    key_to_encrypt = config("KEY_TO_ENCRYPT_WS_TRADICIONAL")
    
    decryptor = TripleDES(key_to_encrypt)

    decrypted_soap = process_soap_request(soap_request, decryptor)
    print(decrypted_soap)
