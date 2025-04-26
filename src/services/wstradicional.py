from decouple import config
from dotenv import load_dotenv
from src.utils.tripleDES import TripleDES

load_dotenv(override=True)

tdes = TripleDES(config("KEY_TO_ENCRYPT_WS_TRADICIONAL"))

dispositivo = input("Ingresa el dispositivo: ")

