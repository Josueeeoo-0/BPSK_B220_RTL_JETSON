# Teoría y bloques de la simulación BPSK

El grafo real, tanto en `../bpsk_simulation.grc` como en `../tx_usrp.py`, es `file_source(byte) → chunks_to_symbols(complex) → constellation_decoder(byte) → file_sink(byte)`. A continuación se explica cada bloque y qué permite concluir esta configuración.

## Entrada de bytes (`blocks.file_source`)

El bloque lee un archivo binario de una sola pasada (`repeat=False`) con tipo GNU Radio `byte` —un elemento de 8 bits por elemento de flujo— y entrega sus valores numéricos. En este ejemplo se espera que cada valor sea 0 o 1, de modo que un byte representa un bit. No existe un bloque explícito de empaquetado o despaquetado.

El generador del repositorio crea 100 000 bits binarios deterministas en `~/sdr-alertas/datos/bpsk_tx.u8`. Es importante generar este archivo antes de iniciar GRC o el script; la fuente lee la ruta de datos acordada para la máquina.

Cada elemento del archivo es un byte almacenado físicamente, pero representa un solo bit lógico: `0x00` para el bit 0 y `0x01` para el bit 1. Esto no es un formato binario compactado como el empaquetamiento de ocho bits por byte. Por tanto, 100 000 bits lógicos ocupan aquí 100 000 bytes. Si un programa escribe caracteres ASCII `'0'` y `'1'`, sus valores serían 48 y 49, que el mapeador interpretaría como índices de símbolo fuera de la tabla; de ahí la validación estricta del comprobador BER.

## Mapeador (`digital.chunks_to_symbols_bc`)

La tabla configurada es `[-1+0j, +1+0j]`, dimensión 1. Para el byte de entrada `b ∈ {0,1}` produce el símbolo complejo:

$$
s(b)=\begin{cases}-1+j0,&b=0\\+1+j0,&b=1\end{cases}
=2b-1.
$$

Son dos puntos antipodales sobre el eje real del plano I/Q, con energía unitaria por símbolo. La distancia euclídea entre puntos es 2. La tabla asigna 0 a −1 y 1 a +1; esa convención de polaridad importa si se conecta otro transmisor o receptor.

En general, el bloque implementa la búsqueda de tabla `y[n]=table[u[n]]`, con `dimension=1`, de modo que consume un byte por elemento y genera un número complejo por elemento. Si el byte no está en el rango de la tabla (0 o 1), el acceso no describe un símbolo válido; el flujo presupone entrada binaria, y no contiene un bloque que valide o recodifique esos valores.

Aunque el nombre sugiera transmisión, el grafo no lleva estos símbolos a un canal ni a una salida de radio. Los conecta directamente a un decodificador.

## Decisor BPSK (`digital.constellation_decoder_cb`)

El decodificador recibe la constelación BPSK de GNU Radio (`digital.constellation_bpsk().base()`) y toma la decisión de símbolo más cercano. Para una entrada real ideal `r`, la frontera está a mitad de camino entre −1 y +1, es decir en cero: si `Re(r)<0`, decide 0; si `Re(r)>0`, decide 1 (el tratamiento exacto de un empate depende de la implementación). Aquí la salida del mapeador es exactamente −1 o +1, por lo que el bloque debe devolver el byte original en ausencia de alteraciones.

La decisión más cercana minimiza la distancia cuadrática `|r−s_i|²`. Para `r=I+jQ` y puntos `s_0=−1`, `s_1=+1`, las distancias son `(I+1)²+Q²` y `(I−1)²+Q²`; restarlas cancela `Q²` y da la regla `I<0 ⇒ 0`, `I>0 ⇒ 1`. En una frontera exacta `I=0`, ambas distancias empatan, y la asignación concreta queda determinada por la función de decisión de GNU Radio. El código de este flujo solo entrega puntos con `I=±1`, así que no hay empate.

En un canal AWGN real, la observación sería `r=s+n`; ruido suficientemente grande puede cruzar el umbral y generar errores. Esta gráfica no agrega `n`, por lo que no simula una curva BER en función de Eb/N0 ni modela sincronización, filtrado de pulsos o desvanecimiento.

El bloque `constellation_decoder_cb` emite una etiqueta de punto de constelación (byte) y consume un elemento complejo por salida. Aquí las etiquetas de la constelación BPSK predeterminada están alineadas con la tabla del mapeador: el punto −1 corresponde a la etiqueta 0 y +1 a 1. Así se obtiene la identidad `decode(map(b))=b` para `b∈{0,1}`. El grafo no tiene codificación diferencial; una inversión completa de polaridad en un canal real intercambiaría todos los bits.

## Archivo de salida (`blocks.file_sink`)

El sumidero escribe la secuencia de bytes recuperados en `bpsk_rx.u8`; no repite la entrada ni añade muestras de relleno. La pareja de archivos de referencia del repositorio tiene 100 000 bytes cada una. El programa de comprobación compara contenido elemento a elemento y define:

$$
\mathrm{BER}=\frac{N_{\mathrm{errores}}}{N_{\mathrm{bits}}},\qquad
N_{\mathrm{errores}}=\sum_i [b_i^{(tx)}\ne b_i^{(rx)}].
$$

El cálculo es válido porque el flujo prescribe un byte con valor 0 o 1 por bit. El programa falla si falta un archivo, las longitudes no coinciden con el tamaño esperado, hay valores distintos de 0/1 o se encuentra cualquier error. El tamaño esperado es ajustable mediante `--expected-bits`.

El comprobador lee los ficheros como `bytes` sin conversiones de texto, valida el dominio `{0,1}`, valida que TX y RX tengan la misma longitud y que cada uno mida exactamente el tamaño pedido, después suma comparaciones distintas con `zip`. Al exigir longitud idéntica antes de comparar, evita truncar silenciosamente un archivo largo al tamaño del corto; el tamaño por omisión (100 000) reproduce la longitud de los archivos de referencia y `--expected-bits` permite otra captura. El cálculo tiene complejidad lineal `O(N)` y memoria `O(N)` por cargar ambos ficheros completos, algo razonable para los 100 kB de este ejemplo.

Sus códigos de salida distinguen fallas de datos/uso (`2`, por ejemplo archivo ausente o byte no binario) de fallas de comparación (`1`, longitudes o cuenta incorrectas, o BER mayor que cero); solo devuelve `0` si pasan las validaciones y no hay discrepancias. Un tamaño válido de 100 000 no garantiza por sí mismo que los bits provengan de una ejecución reciente: la ruta se especifica por CLI, y el valor predeterminado apunta a las muestras archivadas del repositorio.

## Tipos, tasas y límites

| Etapa | Tipo de elemento | Cantidad por bit | Tasa configurada |
|---|---|---:|---|
| Fuente de archivo | Byte sin signo | 1 | No configurada |
| Mapeador | Complejo (`complex`) | 1 símbolo | No configurada |
| Decodificador | Byte | 1 | No configurada |
| Sumidero de archivo | Byte sin signo | 1 | No configurada |

GNU Radio programa los bloques según disponibilidad y capacidad del host. Como no hay `samp_rate`, reloj ni bloques de interpolación, no se puede asignar una tasa física de símbolos. No hay forma de onda sobremuestreada ni conformación de pulsos en este modelo. `file_source` es una fuente finita y `file_sink` consume tan rápido como los bloques y disco lo permiten: la duración no equivale a 100 000/R_b a una tasa de bit `R_b` configurada, porque esa tasa no existe. Tampoco hay un bloque `Throttle`; el flujo está limitado por lectura, planificación y escritura, no por un reloj simulado. Por ello no es una medición de rendimiento de enlace.

## Lectura del flujo Python generado

El script `tx_usrp.py` instancia `blocks.file_source(gr.sizeof_char, ..., False, 0, 0)`: cada elemento tiene tamaño de char (un byte), se empieza en offset cero y no se repite el archivo. `set_begin_tag(PMT_NIL)` impide depender de una etiqueta de comienzo de ráfaga. Luego `digital.chunks_to_symbols_bc([-1+0j, 1+0j], 1)` convierte cada byte en un complejo con amplitud unitaria. `digital.constellation_decoder_cb(digital.constellation_bpsk().base())` recupera la etiqueta del punto más próximo. `blocks.file_sink(gr.sizeof_char, ..., False)` escribe un byte de salida por decisión, con `append=False`, por lo que comienza un archivo nuevo en vez de anexar la ejecución anterior. No se configura una tasa de salida ni un throttle. `tb.start(); tb.wait()` inicia el grafo y espera a que termine la fuente finita.

El GRC produce la misma cadena y parámetros. La etiqueta `tx_usrp` del script/nombre de archivo es heredada y puede sugerir un USRP, pero no hay fuente o sumidero UHD/USRP en el grafo. Tampoco hay etapa de transmisión RF: el nombre no describe el comportamiento actual.

## Qué sería necesario para una BER de canal

Una experiencia BER de BPSK sobre ruido requeriría, al menos, una fuente de bits, mapeo, modelado temporal de pulsos y tasa de muestras, un canal con AWGN calibrado por energía por bit y `E_b/N_0`, sincronización/recuperación si procede, decisor y comparación alineada. Para muestras sobremuestreadas, el receptor debe filtrar e integrar o muestrear en el instante de símbolo. Este grafo omite todos esos elementos deliberadamente; solo comprueba coherencia entre una tabla de símbolos y su decisor ideal.

## Fuentes primarias

- [GNU Radio 3.10.12.0: tabla y mapeo de `chunks_to_symbols`](https://github.com/gnuradio/gnuradio/blob/v3.10.12.0/gr-digital/lib/chunks_to_symbols_impl.cc)
- [GNU Radio 3.10.12.0: `constellation_decoder_cb` llama al decisor de la constelación](https://github.com/gnuradio/gnuradio/blob/v3.10.12.0/gr-digital/lib/constellation_decoder_cb_impl.cc)
- [GNU Radio 3.10.12.0: constelaciones y decisiones BPSK](https://github.com/gnuradio/gnuradio/blob/v3.10.12.0/gr-digital/lib/constellation.cc)
- [GNU Radio 3.10.12.0: fuente de archivo](https://github.com/gnuradio/gnuradio/blob/v3.10.12.0/gr-blocks/lib/file_source_impl.cc)
- [GNU Radio 3.10.12.0: sumidero de archivo](https://github.com/gnuradio/gnuradio/blob/v3.10.12.0/gr-blocks/lib/file_sink_impl.cc)
- [GNU Radio 3.10.12.0: esquema GRC del decisor BPSK](https://github.com/gnuradio/gnuradio/blob/v3.10.12.0/gr-digital/grc/digital_constellation_decoder_cb.block.yml)
