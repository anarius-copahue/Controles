from cryptography.fernet import Fernet
import sys

def encrypt_file(file_path, key=None):
    # Read the file content
    with open(file_path, 'rb') as file:
        file_data = file.read()

    # Generate a key if not provided
    if key is None:
        key = Fernet.generate_key()
        print(f"Generated Key: {key.decode()} (store this key to decrypt the file later)")

    # Create a Fernet object with the provided key
    fernet = Fernet(key)

    # Encrypt the file data
    encrypted_data = fernet.encrypt(file_data)

    # Write the encrypted data back to the file
    # Add .encrypted extension
    if not file_path.endswith('.encrypted'):
        file_path += '.encrypted'

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

    # Remove the .encrypted extension if it exists
    if file_path.endswith('.encrypted'):
        file_path = file_path[:-10]  # Remove the last 10 characters ('.encrypted')

    # Write the decrypted data back to the file
    with open(file_path, 'wb') as file:
        file.write(decrypted_data)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python encrypt.py <file_path> <key>")
        sys.exit(1)

    file_path = sys.argv[1]
    key = sys.argv[2] if len(sys.argv) > 2 else None

    if file_path.endswith('.encrypted'):
        if key is None:
            print("Key is required for decryption.")
            sys.exit(1)
        decrypt_file(file_path, key.encode())
        print(f"Archivo {file_path} desencriptado.")

    else:
        encrypt_file(file_path, key.encode() if key else None)
        print(f"Archivo {file_path} encriptado.")