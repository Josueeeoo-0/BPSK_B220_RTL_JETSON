# Entorno y ejecución de los experimentos

## Plataformas registradas

| Componente | Entorno registrado durante el desarrollo |
|---|---|
| Laptop TX | DragonOS Resolute R1; GNU Radio exportado 3.10.12.0; UHD 4.9.0.1 |
| SDR TX | Mini B220 LibreSDR; UHD informa B210; USB 3 |
| Jetson RX | Orin Nano Developer Kit Super, 8 GB; Ubuntu 22.04.5 LTS aarch64 |
| Jetson Linux | L4T 36.4.7; kernel 5.15.148-tegra |
| Python Jetson | 3.10.12 |
| SDR RX | RTL-SDR Blog V4, sintonizador R828D; librtlsdr 2.0.3 compatible con V4 |
| GNU Radio Jetson | 3.10.1.1 en los flujos exportados; Gqrx 2.15.8 |

No todas las plataformas usan la misma versión de GRC. Los `.grc` son la fuente editable y los `.py` son exportaciones acompañantes. Al abrir en otra versión, revisar los avisos y generar de nuevo desde GRC antes de interpretar un problema como fallo del hardware.

## Preparación

Clonar o copiar el repositorio en cada equipo. Todos los comandos siguientes parten de su directorio raíz. Para los programas de análisis, instalar NumPy y SciPy en el entorno Python elegido. En Ubuntu/DragonOS con los módulos del sistema:

```bash
sudo apt install python3-numpy python3-scipy
```

El generador y la comprobación ideal usan solamente la biblioteca estándar. `requirements-analisis.txt` ofrece los requisitos para un entorno de análisis separado; no contiene GNU Radio ni controladores SDR. Una instalación de GNU Radio del sistema debe ejecutarse con el Python que tenga disponibles sus módulos.

## Compatibilidad del RTL-SDR V4 en ARM64

La arquitectura ARM64 no exige Zadig. Zadig corresponde al entorno Windows; Linux utiliza el acceso USB y los permisos de dispositivo de su propia instalación. El V4 requiere una librería que reconozca su hardware, además de reglas de acceso USB apropiadas. La [guía del fabricante](https://www.rtl-sdr.com/v4/) describe sus controladores y las alternativas Linux. No se debe confundir el reconocimiento USB del RTL2832U con soporte completo del sintonizador V4.

En el entorno del proyecto se compiló e instaló librtlsdr compatible con V4 como paquetes ARM64. La comprobación funcional reconoció `RTL-SDR Blog V4 Detected`, trabajó sin `sudo` y no informó pérdida de muestras durante la prueba a 2,048 MS/s. Esa observación corresponde al equipo del desarrollo, no a una prueba automática efectuada en cualquier máquina que clone el repositorio.

Comprobaciones antes de abrir una aplicación:

```bash
lsusb
rtl_test -d 0 -s 2048000
```

Detener `rtl_test` con `Ctrl+C` antes de iniciar Gqrx o GNU Radio. El RTL-SDR debe estar libre: dos aplicaciones no pueden usarlo a la vez. En una instalación nueva, resolver permisos USB, conflictos con el controlador DVB y soporte V4 siguiendo la documentación del controlador instalado.

## Preparar la referencia en ambos equipos

```bash
python3 datos_prueba/generar_bits.py
```

Este paso crea `~/sdr-alertas/datos/`. Los flujos normalizados usan ese directorio mediante `Path.home()`; no dependen del usuario original ni de la ruta donde se clone el repositorio. La generación reemplaza solo `bpsk_tx.u8` en la carpeta de ejecución. Los archivos archivados dentro del repositorio se conservan.

## Orden de ejecución

1. **Jetson, FM:** abrir `RTL_SDR_JETSON_files/fm_rx/fm_rx_jetson.grc`, ejecutar y comprobar espectro y audio. La estación inicial del archivo es 96,7 MHz; adaptar la sintonía a una emisora local.
2. **Simulación ideal:** abrir `MINIB220_laptop_files/simulacion_bpsk_tx_rx/bpsk_simulation.grc`, ejecutar hasta su finalización y comprobar el archivo nuevo con:

   ```bash
   python3 MINIB220_laptop_files/simulacion_bpsk_tx_rx/comprobacion_ber.py \
       --tx "$HOME/sdr-alertas/datos/bpsk_tx.u8" \
       --rx "$HOME/sdr-alertas/datos/bpsk_rx.u8"
   ```

3. **Laptop, tono:** abrir `MINIB220_laptop_files/prueba_pulso_tx/tx_usrp.grc`. Verificar el canal UHD seleccionado y observar en Gqrx de la Jetson la frecuencia nominal 923,1 MHz. No ejecutar todavía el receptor BPSK sobre el mismo RTL.
4. **Laptop, BPSK:** abrir `MINIB220_laptop_files/implementacion_bpsk_tx/tx_bpsk_usrp_base.grc`. La referencia se transmite continuamente en bucle; no es una ráfaga única.
5. **Jetson, recepción:** cerrar Gqrx y abrir `RTL_SDR_JETSON_files/implementacion_bpsk_rx/bpsk_rx_usrp_a_jetsonRTL_base.grc`. Ejecutar, inspeccionar las pestañas, capturar y detener el flujo antes de analizar su archivo.
6. **Evaluación de la nueva captura:** ejecutar el comparador con las rutas de la carpeta de ejecución:

   ```bash
   python3 RTL_SDR_JETSON_files/implementacion_bpsk_rx/verificacion_ber_rf.py \
       --tx "$HOME/sdr-alertas/datos/bpsk_tx.u8" \
       --rx "$HOME/sdr-alertas/datos/bpsk_rx_rf_USRP_tx.u8"
   ```

El comparador exige localizar dos ventanas consecutivas exactas para fijar un anclaje. Si no las encuentra, no entrega una BER: no es un estimador general para señales extremadamente degradadas. Una vez aceptado el anclaje, conserva el alineamiento hasta el final, incluyendo cualquier región posterior que deje de coincidir.

## Canales UHD y diagnóstico

Los archivos incluidos seleccionan explícitamente `[0]` para un canal de transmisión. En el desarrollo también se obtuvo recepción al seleccionar `[1]`. El índice debe corresponder al puerto físico y al dispositivo identificado por UHD; no hay evidencia para afirmar que el canal 0 esté averiado.

Si no aparece la señal, comprobar la asignación de canal, puerto `TX/RX`, continuidad de streaming y frecuencia nominal desplazada. Una gráfica TX solo confirma muestras digitales internas. El LED de transmisión o el bloqueo del oscilador tampoco sustituye observar la RF en el receptor. La [documentación de UHD](https://files.ettus.com/manual/page_configuration.html) explica la selección de dispositivos y canales.

No se añade `Throttle` en las rutas de hardware: los SDR establecen el ritmo. La simulación ideal es finita y sin GUI; procesa su archivo hasta EOF, sin constituir una medición de rendimiento de CPU ni de tasa física.

## Preservación de las mediciones

Al detener una nueva prueba, copiar sus archivos a una carpeta de resultados con fecha y configuración propias. No reemplazar la captura incluida sin actualizar su informe, hash, alineación y capturas de pantalla. El File Sink del receptor está configurado para sobrescribir al iniciar el flujo y usa buffering, por lo que el cierre normal es necesario antes de comparar.
