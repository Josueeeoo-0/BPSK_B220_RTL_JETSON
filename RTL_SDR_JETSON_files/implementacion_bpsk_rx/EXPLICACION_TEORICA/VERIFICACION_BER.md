# Verificación de BER con la captura de referencia

Este documento explica línea por línea el método implementado en [verificacion_ber_historica.py](../verificacion_ber_historica.py). El código aplica una alineación fija validada por un bloque inicial de anclaje, luego cuenta discrepancias bit a bit. Es una verificación de una captura ya alineada, no un estimador automático de retardo, no un detector de trama y no una garantía sobre otra corrida.

## 1. Qué es la BER observada

Para secuencias TX y RX alineadas de longitud `N`, con `E` posiciones diferentes:

`BER_obs = E/N`.

La tasa solo tiene sentido si ambas cadenas representan los mismos bits en el mismo orden, con polaridad resuelta y con las regiones de inicio/transitorio tratadas de manera explícita. Una comparación de arrays sin sincronización puede reportar muchos errores aunque la forma de onda sea buena; elegir un desplazamiento arbitrario hasta lograr cero errores sesga la medición.

## 2. Qué hace el código histórico

1. Importa `Path` y NumPy. Lee TX y RX con `np.fromfile(..., dtype=np.uint8)`, es decir, cada octeto del archivo se interpreta como una etiqueta de bit/byte sin signo.
2. Comprueba tamaños exactos: TX de 100 000 bytes y RX de 1 250 113 bytes. Ese control evita aplicar las posiciones elegidas a archivos de otras longitudes. **La RX presente en el repositorio es 1 252 730 bytes**, por lo que el propio control debe detener el método histórico para esta captura.
3. Verifica que todos los valores sean 0 o 1; si el archivo contiene otro valor, el supuesto de un byte por decisión binaria no se cumple.
4. Define el anclaje histórico: índice RX 65 536 corresponde al índice TX 57 716, sin invertir polaridad. Ese emparejamiento se identificó anteriormente y se debe verificar, no presumir universal.
5. Reserva `excluir=8192` posiciones de RX desde el inicio del anclaje. Con la relación de índices, los primeros 8192 bits RX del anclaje deben coincidir con TX desde 57 716, envolviendo al final de TX si es necesario.
6. Construye `indices_anclaje = (57716 + arange(8192)) % len(tx)`. El módulo implementa repetición cíclica del patrón TX de 100 000 bits.
7. Extrae `rx[65536:73728]` y aplica XOR con `int(False)`, que no altera los datos. Si esta secuencia no es idéntica a TX en los índices calculados, aborta. Es la defensa esencial contra reutilizar el desplazamiento cuando no corresponde.
8. La medición empieza en `inicio_medicion = 65536 + 8192 = 73 728`. Se comparan todas las decisiones RX desde ahí hasta el fin del archivo con el segmento TX que continúa desde el índice 65 908 (`57 716 + 8 192`), también en repetición cíclica.
9. Cuenta `E = count_nonzero(recibidos != esperados)`, calcula `N = len(recibidos)` y `BER_obs = E/N`. Imprime la posición de inicio, cantidad comparada, errores, BER y porcentaje.
10. Si hubo discrepancias, muestra las primeras diez posiciones absolutas de RX. Si no hubo discrepancias, imprime `3/N` como límite superior aproximado al 95 %, sujeto a las hipótesis estadísticas indicadas abajo.

El mensaje `Bits iniciales excluidos` imprime `inicio_medicion`, un índice absoluto RX (73 728), aunque su etiqueta sugiere que imprimiría el tamaño de la exclusión (8 192). Para no confundir medidas, deben leerse por separado: el inicio RX es 73 728; lo excluido desde el inicio del archivo son 73 728; los bits descartados después del comienzo del anclaje son 8 192.

El apunte `comandos_comparacion_BER.assert` enlaza ahora los comandos de ejecución. Se corrigió el uso original de una cadena como ruta: la versión ejecutable usa `Path` y admite `--datos`. El algoritmo histórico conserva las comprobaciones de tamaño, valores binarios y anclaje antes de contar errores.

## 3. Resultado histórico y alcance

Para la captura histórica exacta de RX de 1 250 113 bytes, el anclaje citado en el archivo produce un tramo continuo desde RX 73 728 de longitud 1 176 385 bits. El resultado histórico comunicado fue cero diferencias, `BER_obs = 0/1 176 385 = 0`, equivalente a 0 % observado. Bajo el modelo binomial de errores independientes con probabilidad constante, cero errores no demuestra BER verdadera igual a cero. La aproximación «regla de 3» da límite superior unilateral cercano al 95 %:

`BER ≲ 3/N = 3/1 176 385 ≈ 2.55×10⁻⁶`.

Con cero errores observados, la cota binomial unilateral exacta satisface $(1-p)^N=0,05$: $p_{95}=1-0,05^{1/N}$. Para $N$ grande se aproxima por $-\ln(0,05)/N \simeq 3/N$. No es una medida directa de una BER no nula ni una cota garantizada sin esos supuestos.

La captura actualmente incluida (`archivos_tx_y_rx/bpsk_rx_rf_USRP_tx.u8`) tiene 1 252 730 bytes y SHA-256 `87c3a6fde9775ad95077565f9f2d73ad0da3cead1d4cb8054cbf15a8fed6a922`. El control de tamaño del `.assert` debe fallar antes de medir. Además, al intentar validar el anclaje histórico RX 65 536 → TX 57 716 sobre los primeros 8192 bits de ese anclaje, aparecen 4107 diferencias; por tanto, la asociación antigua es inválida para esta captura.

Una búsqueda de anclajes exactos de 8192 bits sobre bloques de búsqueda de 4096 bits identificó como primer anclaje RX 475 136 → TX 70 727, sin inversión. Se reservaron los 4096 bits de búsqueda y los 4096 siguientes de validación; ambos bloques se excluyeron del conteo, de modo que la medición continua comienza en RX 483 328, asociado a TX 78 919. Desde ese punto hasta el final se compararon 769 402 decisiones: 145 590 diferencias, `BER_obs = 0.18922487854203654` (18.9224878542 %). La primera diferencia del tramo se encuentra en la posición absoluta RX 961 192. Este es el resultado para la comparación continua especificada sobre esta captura; no es una BER nula ni una cifra de rendimiento RF universal.

La búsqueda por bloques es una etapa para proponer una correspondencia; el bloque de validación posterior comprueba un tramo distinto al usado para hallarla. Después de fijar ese desplazamiento, el conteo abarca el segmento restante completo. Aunque haya una larga región inicial con coincidencias, no debe recortarse el análisis justo antes del primer error para declarar BER cero: seleccionar el segmento por su resultado observado introduce sesgo y descarta evidencia de pérdida de correspondencia. El primer error ocurre en RX 961 192, pero no identifica por sí mismo la causa física. Una discrepancia sostenida podría ser compatible con deslizamiento/pérdida de sincronismo, diferencia entre flujos o estructura de captura distinta; no se puede concluir cuál ocurrió solo a partir del byte comparado.

El análisis reproducible actual está implementado en `../verificacion_ber_rf.py`; desde la raíz del repositorio se ejecuta con `python3 RTL_SDR_JETSON_files/implementacion_bpsk_rx/verificacion_ber_rf.py`. El análisis histórico queda protegido por sus comprobaciones de longitud y anclaje y se conserva por separado. No se debe eliminar ese guard ni reutilizar el resultado histórico en la captura actual.

## 4. Por qué se excluyen 8192 bits y qué no resuelve

El bloque de 8192 bits funciona como prueba del anclaje y se excluye del conteo para que la validación no sea también parte de la cifra de BER. No es detección de preámbulo ni de límites de trama. En el método descrito, el resto se compara con una sola correspondencia que continúa desde el anclaje; el código no busca el retardo que minimiza errores a cada instante.

La exclusión inicial no prueba que el receptor opere sin errores desde el arranque ni valida la región excluida como rendimiento. Tampoco resuelve pérdida de sincronismo posterior: un solo deslizamiento de bit vuelve incorrecto el alineamiento de todo el resto y puede elevar enormemente la BER calculada.

## 5. Límites estadísticos y de interpretación

- La regla de 3 asume ensayos Bernoulli aproximadamente independientes y una probabilidad de error estacionaria en el segmento medido. Ráfagas de error, desvanecimiento, deriva o ciclos de pérdida/recaptura violan esa simplificación.
- Una repetición cíclica de TX con módulo conserva el alineamiento si el transmisor repite exactamente el patrón y no hay encabezados, pausas u otros bytes que cambien la relación de flujo. No representa por sí sola una trama de protocolo.
- El archivo de salida es un byte por decisión binaria, no bits empaquetados. Las longitudes de archivo se cuentan en bytes/decisiones.
- Cero discrepancias en el segmento analizado no significa que toda captura, cada paquete, el receptor en tiempo real o cualquier enlace RF tenga BER cero.
- La comparación necesita confirmar polaridad BPSK (la fase ambigua de π puede invertir todas las etiquetas), mapeo del decoder, origen de los datos y correcta sincronización.
- Un valor de BER no caracteriza por sí solo sensibilidad, margen de enlace ni desempeño en diferentes SNR. Para una curva BER vs. Eb/N0 hace falta controlar el canal/ruido, medir energía por bit y realizar corridas independientes y suficientes.

Para un resultado publicable conviene registrar por cada captura su hash, tamaño, parámetros RF, índices de inicio, polaridad, bloque de anclaje validado, cantidad comparada, errores y reglas de exclusión. No se debe reutilizar un desplazamiento en otra captura salvo que vuelva a pasar una prueba objetiva de anclaje.

## 6. Correspondencia matemática y operaciones NumPy

Si RX en el índice $i_0$ corresponde a TX en $p_0$, la predicción para cualquier índice posterior $i$ es:

$$
\hat b_{TX}[i]=TX[(p_0+i-i_0)\bmod L],
$$

donde $L=100\,000$ es la longitud de la referencia y el transmisor la repite sin insertar otros elementos. Para una polaridad global $v\in\{0,1\}$, el error de posición es $e_i=\mathbf{1}\{(RX[i]\oplus v)\ne\hat b_{TX}[i]\}$. La BER observada es la suma de esos indicadores dividida por la cantidad medida.

`np.arange(N)` crea los desplazamientos enteros `0, 1, ..., N-1`. Sumar la posición de referencia y aplicar `% len(tx)` construye los índices circulares; `tx[indices_tx]` selecciona el valor esperado para cada decisión RX. Esa operación de indexación no altera TX ni busca una nueva coincidencia en cada punto.

El XOR `^ int(invertida)` cambia todos los bits únicamente si la orientación global es inversa: `x ^ 0 = x` y `x ^ 1 = 1-x` para valores 0/1. No se decide una inversión distinta por bloque para ocultar errores. La operación `recibidos != esperados` produce un array booleano y `count_nonzero` cuenta sus `True`; por eso mide discrepancias lógicas y no distancias IQ. `flatnonzero` identifica índices de errores dentro del tramo; sumar `inicio_medicion` los convierte en posiciones absolutas del archivo RX.

## 7. Búsqueda reproducible para una captura diferente

El [comparador RF actual](../verificacion_ber_rf.py) conserva el cálculo anterior después del anclaje, pero sustituye las posiciones históricas por una búsqueda explícita:

1. `leer_bits` rechaza archivos vacíos y valores distintos de 0/1 antes de cualquier correlación.
2. `buscar_anclaje` transforma las etiquetas a números con signo mediante `astype(float)*2-1`. Convertir antes de restar evita el desbordamiento de `uint8` que convertiría −1 en 255.
3. Extiende circularmente TX para poder buscar ventanas que atraviesen el final de la referencia repetida. Recorre RX cronológicamente en bloques de 4096, no elige el mejor resultado de BER final.
4. `correlate(..., mode="valid", method="fft")` calcula las coincidencias de cada ventana con las fases posibles de TX. Para secuencias bipolares, $C/N=1-2E/N$ si están alineadas; el valor negativo indica posible inversión. Se usa la magnitud para proponer fase y polaridad.
5. La correlación en coma flotante solo propone el candidato. La aceptación exige `array_equal` sobre los bits enteros de la ventana de búsqueda y de otra ventana consecutiva de 4096 bits. No se decide validez únicamente por una aproximación FFT cercana a uno.
6. Excluye esos 8192 bits, fija una sola fase/polaridad y compara hasta EOF. No realinea cuando encuentra discrepancias y no termina en el primer error.
7. El informe incluye SHA-256 de ambos archivos, tamaños, anclaje, exclusiones, errores, BER y primeras posiciones de error. `--json RUTA` conserva ese informe. La finalización correcta del programa significa que la medición se completó; una BER no nula se informa como resultado, no como un error de ejecución.

La exigencia de dos ventanas exactas es una elección conservadora para esta demostración, no una solución universal de adquisición. Una captura con errores dispersos en todas las ventanas puede contener señal BPSK y aun así no superar esa búsqueda. En ese caso el programa indica que no calculó BER; hace falta otro procedimiento de alineación validado, no relajar silenciosamente la condición hasta obtener una cifra deseada.

Referencia de la operación numérica: [SciPy `signal.correlate`](https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.correlate.html). Los índices, longitudes y resultados del informe proceden de los archivos incluidos, no de esa documentación.
