# Controles

## Encriptar y Desencriptar Archivos

### Uso

El script se ejecuta desde la terminal de la siguiente manera:

```bash
python encrypt.py <ruta_archivo> <clave>
```

### 1. Encriptar un archivo

* Si el archivo **no** termina con `.encrypted`, el script lo encriptará.
* Se puede proporcionar la **clave Fernet** que se usará para el cifrado.
* Si no se pasa clave, el script genera una nueva clave y la muestra en pantalla. **Hay que guardala en un lugar seguro**, ya que se necesita para desencriptar el archivo después.
* El archivo encriptado se guardará con la extensión `.encrypted`.

Ejemplo:

```bash
python encrypt.py documento.txt MI_CLAVE_FERNET
```

Resultado:
`documento.txt` → `documento.txt.encrypted`

### 2. Desencriptar un archivo

* Si el archivo **termina con `.encrypted`**, el script intentará desencriptarlo.
* Es obligatorio pasar la misma clave Fernet que se usó para cifrarlo.
* El archivo resultante se guardará sin la extensión `.encrypted`.

Ejemplo:

```bash
python encrypt.py documento.txt.encrypted MI_CLAVE_FERNET
```

Resultado:
`documento.txt.encrypted` → `documento.txt`