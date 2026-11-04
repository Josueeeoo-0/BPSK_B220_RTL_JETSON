# Referencia binaria: código, representación y utilidad

## Código original de generación

En una terminal Linux, el delimitador `<<'PY'` entrega las líneas siguientes a la entrada estándar de Python. Las comillas impiden que el shell sustituya variables o ejecute expresiones dentro del cuerpo; no forman parte de los datos generados.

```bash
python3 - <<'PY'
from pathlib import Path
import random

carpeta = Path.home() / "sdr-alertas" / "datos"
carpeta.mkdir(parents=True, exist_ok=True)

generador = random.Random(2026)
bits = bytes(generador.getrandbits(1) for _ in range(100000))

archivo = carpeta / "bpsk_tx.u8"
archivo.write_bytes(bits)

print("Archivo:", archivo)
print("Bits generados:", len(bits))
print("Primeros 32 bits:", list(bits[:32]))
PY
```

El [script del repositorio](../generar_bits.py) conserva ese algoritmo. Solo añade `argparse` para admitir `--salida` y una función `main()` que evita escribir datos al importar el módulo.

## 1. Rutas: `Path`, directorio personal y creación

`from pathlib import Path` importa una representación de rutas independiente del nombre de usuario. `Path.home()` obtiene el directorio personal; el operador `/` une componentes de ruta. En Linux el destino normal es `~/sdr-alertas/datos`, sin exigir que la cuenta se llame de una manera particular.

`mkdir(parents=True, exist_ok=True)` crea los directorios padres que falten y admite que el directorio ya exista. No borra su contenido. La posterior llamada `write_bytes` sí reemplaza un archivo del mismo nombre; por eso las capturas y referencias archivadas se mantienen dentro de sus experimentos, separadas de la carpeta de ejecución.

## 2. Secuencia pseudoaleatoria: `random.Random(2026)`

Se crea una instancia local del generador con una semilla fija. No depende de otras llamadas a `random` hechas por el programa. La secuencia es determinista: sirve para repetir una prueba y comparar archivos, no para proporcionar aleatoriedad criptográfica.

El número 2026 identifica la semilla; no es una frecuencia, un tamaño de palabra ni un parámetro BPSK. Para el experimento se busca una secuencia aproximadamente equilibrada, con transiciones frecuentes. La proporción de unos puede diferir de 0,5 en una muestra finita.

Si los bits fueran Bernoulli independientes ideales con $p=0,5$, el número esperado de unos sería $Np=50\,000$ y su desviación estándar $\sqrt{Np(1-p)}\simeq158,1$. Esta cuenta describe un modelo de referencia; no convierte el generador determinista en una fuente física independiente.

## 3. Construcción: `getrandbits(1)` y `bytes(...)`

`generador.getrandbits(1)` devuelve el entero 0 o 1. La expresión `for _ in range(100000)` lo evalúa 100 000 veces; `_` indica que el índice no se utiliza. `bytes(...)` almacena cada entero como un byte sin signo.

Hay que distinguir tres representaciones:

| Representación de cuatro bits lógicos 0, 1, 1, 0 | Bytes hexadecimales | Tamaño |
|---|---|---:|
| Un bit lógico por byte, como este proyecto | `00 01 01 00` | 4 bytes |
| Texto ASCII de los caracteres `0110` | `30 31 31 30` | 4 bytes |
| Bits empaquetados en un byte, completando con ceros | `60` si se ordenan MSB primero | 1 byte |

El `File Source` de tipo byte lee cada `00` o `01` como un índice válido del bloque `Chunks to Symbols`. Un TXT con caracteres `0`/`1` entregaría índices 48/49 y no es un reemplazo directo. Un archivo de bits empaquetados exigiría un desempaquetador antes del mapeador.

El almacenamiento usa ocho bits físicos por bit lógico para simplificar el flujo y la inspección. Esta redundancia de archivo no implica que se transmitan ocho símbolos por elemento: el mapeador recibe un byte y produce **un símbolo**.

## 4. Escritura y vista previa

`archivo.write_bytes(bits)` escribe los valores sin codificación de texto, encabezado ni salto de línea. `len(bits)` mide bytes almacenados, que en este formato coincide numéricamente con los bits lógicos. `list(bits[:32])` muestra sus primeros 32 valores como una lista de enteros; no imprime el archivo completo.

La escritura de 100 000 bytes no crea una señal RF. Solo prepara los índices. Las muestras IQ aparecen después de `Chunks to Symbols`, y la emisión ocurre cuando el flujo alcanza el sumidero UHD.

## 5. Relación con el enlace y el análisis

El mapeo es $a_k=2b_k-1$, con $b_k\in\{0,1\}$, por lo que los símbolos se sitúan en $-1+j0$ y $+1+j0$. Al transmitirse a $R_s=25\,000$ símbolos/s, una lectura del archivo dura nominalmente:

$$
T=\frac{100\,000}{25\,000}=4\ \mathrm{s}.
$$

Con `Repeat=Yes`, la referencia se recorre de nuevo cada cuatro segundos nominales. No se añade un encabezado ni se marca físicamente el inicio de cada vuelta. El receptor puede comenzar en cualquier fase del archivo repetido, por lo que la comparación RF usa índices circulares y un anclaje demostrado para esa captura.

En la simulación ideal no hay canal RF, error de reloj ni adquisición de lazo: se compara desde el primer elemento. En el receptor real se requiere localizar primero el desfase y la posible inversión global de BPSK. Esos pasos no cambian el formato de almacenamiento.

## Referencias

- [Python: `pathlib`](https://docs.python.org/3.10/library/pathlib.html), para rutas y lectura/escritura binaria.
- [Python: generadores pseudoaleatorios y `getrandbits`](https://docs.python.org/3.10/library/random.html), para semilla y reproducción.
- [GNU Radio: `Chunks to Symbols`](https://github.com/gnuradio/gnuradio/blob/v3.10.1.1/gr-digital/include/gnuradio/digital/chunks_to_symbols.h), para la conversión de índices en símbolos complejos.
