from cryptography.fernet import Fernet

def encrypt_file(file_path, key=None):
    # Read the file content
    with open(file_path, 'rb') as file:
        file_data = file.read()

    # Create a Fernet object with the provided key
    fernet = Fernet(key)

    # Encrypt the file data
    encrypted_data = fernet.encrypt(file_data)

    # Write the encrypted data back to the file
    with open(file_path, 'wb') as file:
        file.write(encrypted_data)

def decrypt_file(file_path, key):
    # Read the encrypted file content
    with open(file_path, 'rb') as file:
        encrypted_data = file.read()

    # Create a Fernet object with the provided key
    fernet = Fernet(key)

    # Decrypt the file data
    decrypted_data = fernet.decrypt(encrypted_data)

    # Write the decrypted data back to the file
    with open(file_path, 'wb') as file:
        file.write(decrypted_data)

def encrypt_data():
    import sys

    ARCHIVOS = ["data/diccionario.xlsx", "data/representante.xlsx", "data/SELL_IN_OUT.csv"]

    key = sys.argv[1] if len(sys.argv) > 1 else None

    if key is None:
        # Generate a key if not provided
        key = Fernet.generate_key()
        print(f"Generated key: {key.decode()}")

    for archivo in ARCHIVOS:
        encrypt_file(archivo, key)
        print(f"Archivo {archivo} encriptado.")

encrypt_data()
