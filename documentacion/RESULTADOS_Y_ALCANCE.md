# Resultados, procedencia y límites de la evidencia

## Datos de referencia

Los archivos `bpsk_tx.u8` incluidos en transmisión, simulación y recepción son idénticos, contienen 100 000 elementos y solo utilizan los valores 0/1. Coinciden con el generador `random.Random(2026)` seguido de 100 000 llamadas a `getrandbits(1)`. La salida ideal `bpsk_rx.u8` también coincide byte por byte.

En este formato cada byte representa una decisión binaria. La igualdad de archivos demuestra igualdad de esa secuencia digital, no una calibración del nivel RF ni una tasa de error fuera del intervalo observado.

## Simulación ideal

La comprobación incluida valida tipo de datos, longitud esperada e igualdad de todas las posiciones. Resultado de los archivos archivados:

```text
Bits transmitidos: 100000
Bits recibidos:    100000
Errores:          0
BER observada:    0
```

No se modelan ruido, desfase de reloj ni canal RF en este diagrama. Por eso la simulación comprueba principalmente la representación y la compatibilidad entre mapeador y decoder.

## Medición RF histórica

Durante el desarrollo se comunicó el siguiente resultado, con un archivo RX de **1 250 113** elementos:

```text
Anclaje RX:                   65536
Posición correspondiente TX:  57716
Inversión global:             False
Bits del anclaje excluidos:   8192
Inicio de medición RX:        73728
Bits comparados:              1176385
Errores:                      0
BER observada:                0
Límite superior aproximado:   2.55e-06 (95 %, con hipótesis)
```

La captura que produjo esa salida no está presente en la copia actual. Se conserva el cálculo en `verificacion_ber_historica.py`, con las comprobaciones de longitud y de anclaje que impiden reutilizarlo accidentalmente con otros datos. El resultado histórico es una referencia de desarrollo; no se presenta como recalculado a partir del archivo incluido.

## Auditoría de la captura RF incluida

El archivo actual `RTL_SDR_JETSON_files/implementacion_bpsk_rx/archivos_tx_y_rx/bpsk_rx_rf_USRP_tx.u8` tiene **1 252 730** elementos. El anclaje histórico falla en **4107 de sus 8192 posiciones**, por lo que ni el tamaño ni la relación temporal corresponden a la medición anterior.

Para medir el archivo disponible se recorre la captura cronológicamente en ventanas de 4096 bits. La primera ventana de coincidencia exacta que además supera otra ventana consecutiva de validación fija la relación RX/TX. Ambas ventanas se excluyen del cálculo. Después se compara todo el resto de la captura con una única alineación y sin corregir desplazamientos posteriores.

| Campo | Resultado |
|---|---:|
| Inicio del anclaje RX | 475 136 |
| Posición correspondiente en TX repetida | 70 727 |
| Inversión global | No |
| Longitud de búsqueda más validación excluida | 8 192 bits |
| Inicio de medición RX | 483 328 |
| Bits comparados hasta el final | 769 402 |
| Errores | 145 590 |
| BER observada del tramo | 0,18922487854203654 |
| Primer error, índice absoluto RX | 961 192 |

La región inicial de esa medición coincide hasta que aparecen diferencias; esa observación no justifica detener el conteo justo antes del primer error. El resultado íntegro se conserva en [auditoria_captura_incluida.json](../RTL_SDR_JETSON_files/implementacion_bpsk_rx/resultados/auditoria_captura_incluida.json).

El método mide discrepancias bajo el alineamiento inicial. Si el transmisor deja de emitir mientras RX continúa guardando ruido, o si se pierde la sincronización o se produce un deslizamiento, esa región también contará como diferencias. El archivo no incluye marcas temporales de encendido/apagado que permitan resolver esas posibilidades. Por eso este valor no debe presentarse como BER de un canal estacionario aislado sin describir cómo se obtuvo la captura.

## Qué se ha demostrado

- El RTL-SDR V4 funciona en la Jetson ARM64 del montaje y permitió recepción FM.
- El mapeo y decisión ideal conservan los 100 000 bits del archivo de referencia.
- El enlace RF entre Mini B220 y RTL-SDR recupera la secuencia conocida en regiones de recepción sincronizada.
- La herramienta de evaluación rechaza anclajes ajenos y permite detectar que una captura posterior deja de coincidir.

La evidencia no proporciona una curva BER frente a $E_b/N_0$, sensibilidad calibrada, alcance máximo, potencia radiada, eficiencia energética ni tasa de entrega de paquetes. Esas magnitudes requieren experimentos adicionales con condiciones y registros propios.
