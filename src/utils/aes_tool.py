import base64
import argparse
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.padding import PKCS7
from cryptography.hazmat.backends import default_backend
import os
from decouple import config
from dotenv import load_dotenv

load_dotenv(override=True)

SECRET_KEY = config('SECRET_KEY') 
SALT = config('SALT').encode()  #b"SALT"

ITERATION_COUNT = 65536
KEY_LENGTH = 32
IV_LENGTH = 16

def derive_key(secret_key, salt):
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=KEY_LENGTH,
        salt=salt,
        iterations=ITERATION_COUNT,
        backend=default_backend()
    )
    return kdf.derive(secret_key.encode())

def encrypt(secret_key, value):
    key = derive_key(secret_key, SALT)
    iv = os.urandom(IV_LENGTH)
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    padder = PKCS7(algorithms.AES.block_size).padder()
    padded_data = padder.update(value.encode()) + padder.finalize()
    cipher_text = encryptor.update(padded_data) + encryptor.finalize()
    cipher_with_iv = iv + cipher_text
    return base64.b64encode(cipher_with_iv).decode()

def decrypt(secret_key, encrypted):
    key = derive_key(secret_key, SALT)
    cipher_with_iv = base64.b64decode(encrypted)
    iv = cipher_with_iv[:IV_LENGTH]
    cipher_text = cipher_with_iv[IV_LENGTH:]
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    decryptor = cipher.decryptor()
    padded_data = decryptor.update(cipher_text) + decryptor.finalize()
    unpadder = PKCS7(algorithms.AES.block_size).unpadder()
    data = unpadder.update(padded_data) + unpadder.finalize()
    return data.decode()

def main():
    parser = argparse.ArgumentParser(description="Encrypt or decrypt a message using AES-256-CBC.")
    parser.add_argument("mode", choices=["encrypt", "decrypt"], help="Mode of operation: encrypt or decrypt")
    parser.add_argument("input", help="Input text to encrypt or decrypt")
    args = parser.parse_args()

    if args.mode == "encrypt":
        result = encrypt(SECRET_KEY, args.input)
        print("Encrypted text:", result)
    elif args.mode == "decrypt":
        try:
            result = decrypt(SECRET_KEY, args.input)
            print("Decrypted text:", result)
        except Exception as e:
            print("Error during decryption:", e)

if __name__ == "__main__":
    main()