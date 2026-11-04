# Fundamento del receptor FM

Este documento describe el flujo que implementan `../fm_rx_jetson.grc` y `../fm_rx_jetson.py`. El grafo es: RTL-SDR → (espectro Qt GUI y remuestreador complejo) → receptor WFM → control de nivel → salida de audio. El espectro está conectado en paralelo antes del remuestreo.

## Fuente RTL-SDR (`osmosdr.source`)

El sintonizador entrega muestras complejas I/Q centradas en `freq = 96.7e6` Hz a `samp_rate = 2,048,000` muestras/s. La componente I representa la proyección en fase y Q la cuadratura; juntas describen amplitud y fase de la señal recibida. `rtl=0` selecciona el primer dispositivo RTL disponible. El GRC fija un canal, corrección de frecuencia 0, ganancia automática desactivada y ganancias RF/IF/baseband de 20 dB; el ancho de banda del dispositivo queda en 0 (selección automática del backend). Son valores configurados, no una calibración garantizada.

La tasa de muestreo determina el ancho de banda complejo observado: idealmente abarca aproximadamente ±1.024 MHz respecto del centro, con limitaciones prácticas de filtros y hardware. Un modelo de la traslación de RF a banda base compleja es `x(t)=I(t)+jQ(t)≈A(t)e^{jφ(t)}`. El sintonizador mezcla la portadora sintonizada a cero; la fase `φ(t)` conserva la variación instantánea alrededor de ese centro. Aquí `T_s=1/F_s≈488.28 ns`. Nyquist fija un intervalo ideal de `[-F_s/2,+F_s/2)`, no una respuesta plana de hardware: filtros, reloj, interferencia y backend delimitan la zona útil.

## Analizador Qt GUI (`qtgui.freq_sink_c`)

La rama de visualización toma las muestras I/Q directamente de la fuente. Una FFT de `N=1024` puntos representa el espectro en torno a 96.7 MHz. El espaciado nominal entre bins es `Δf=F_s/N=2,000 Hz` (Hz, no muestras/s). La resolución efectiva de un pico depende además de la ventana: Blackman-Harris reduce lóbulos laterales, pero ensancha el lóbulo principal frente a una ventana rectangular. Así, 2 kHz es el espaciado de la rejilla FFT, no una garantía de resolución de 2 kHz. El sink se actualiza cada 0.10 s, usa escala de −140 a 10 dB, y promedio 1.0 (sin promedio temporal adicional). No altera la rama de demodulación. `fc=freq` y `bw=samp_rate` fijan el centro y span de presentación; esto no es una medición calibrada de potencia RF, que depende también de la normalización FFT, ganancias, antena y pérdidas.

## Remuestreo racional (`filter.rational_resampler_ccc`)

Para convertir 2.048 MS/s a la tasa que espera el demodulador, el bloque interpola por `L=15` y diezma por `M=128`. La tasa de salida es:

$$
F_{out}=F_{in}\frac{L}{M}=2{,}048{,}000\frac{15}{128}=240{,}000\;\text{muestras/s}.
$$

Conceptualmente, el remuestreo interpola insertando `L−1` ceros, filtra y conserva cada `M`-ésima muestra. Una implementación polifásica divide los coeficientes FIR entre fases y evita calcular todas las muestras que se descartarían. El filtrado limita imágenes de interpolación y atenúa componentes que se plegarían al diezmar (aliasing). `taps=[]`, `fractional_bw=0` hacen que GNU Radio 3.10.1.1 diseñe automáticamente un FIR de paso bajo con su fracción de banda predeterminada. No se especificó un ancho de canal manual.

El objetivo de 240 kS/s es alimentar el WFM con su `quad_rate` nominal. La banda compleja ideal de Nyquist en la salida es ±120 kHz; la banda que realmente queda útil depende del filtro diseñado y no debe tomarse como garantía de separación de canales. La relación de tasas no compensa una frecuencia central mal ajustada, ni asegura que el canal RF deseado quepa sin interferencia. En esta cadena se reduce el ritmo de cálculo 8.533:1 sin modificar el desplazamiento central.

## Demodulador FM de banda ancha (`analog.wfm_rcv`)

El receptor está configurado con `quad_rate=240000` y `audio_decimation=5`. Para un mensaje `m(t)`, FM ideal en banda base se expresa como `s(t)=A exp(jφ(t))`, donde `φ(t)=φ₀+2πk_f∫m(τ)dτ`; por tanto, la frecuencia instantánea `f_i(t)=(1/2π)dφ/dt=k_f m(t)`. La amplitud ideal permanece fija y el audio está en la pendiente temporal de fase.

En tiempo discreto, un discriminador estima el giro de fase entre muestras consecutivas: `f̂_i[n]=(F_s/2π) arg{x[n]x*[n−1]}`. El argumento principal está entre −π y π, de modo que el giro no ambiguo por muestra es menor que Fs/2. El bloque WFM multiplica este resultado por `quad_rate/(2π·75 kHz)`: 75 kHz es su desviación máxima predeterminada, y el factor produce una señal proporcional al audio normalizado por esa desviación.

`analog.wfm_rcv` es un bloque jerárquico: en GNU Radio 3.10.1.1 enlaza discriminador en cuadratura → FIR pasa bajo de audio con decimación → deénfasis FM. El filtro calcula corte `F_audio/2−F_audio/32` y transición `F_audio/32`; para 48 kHz son 21.75 kHz y 1.5 kHz, respectivamente. La decimación da `240000/5=48000` muestras/s, que coincide con `audio_rate` y el sink. El deénfasis usa el valor predeterminado `τ=75 μs` de GNU Radio. El GRC no muestra este parámetro; emisoras con otra constante regional pueden sonar con respuesta tonal distinta.

## Nivel y sumidero de audio

`blocks.multiply_const_ff(0.2)` multiplica cada muestra real por 0.2. En amplitud esto equivale a −13.98 dB (`20 log10(0.2)`), y reduce el nivel para evitar una salida excesiva; no cambia la frecuencia ni la tasa. `audio.sink(48000, '', True)` envía muestras flotantes a la salida de audio predeterminada a 48 kS/s y permite bloqueo para acompasar el flujo al dispositivo.

El sumidero de audio aporta un límite de tiempo real: el `ok_to_block=True` permite que el planificador espere al dispositivo. No se necesita un bloque `Throttle` en una cadena con hardware de radio y salida de audio, porque esos dispositivos marcan el ritmo. Sobreutilización de CPU, USB o buffers puede causar cortes aunque las tasas nominales del diagrama cuadren.

## Alcance real del receptor

El grafo produce una salida WFM mono y muestra el espectro de la entrada. No tiene decodificador estéreo, piloto de 19 kHz, separación L−R, RDS, squelch ni controles de AGC. La frecuencia de partida es 96.7 MHz y `rtl=0` elige un dispositivo según el orden del backend. La recepción depende de la cobertura, la antena, el error de frecuencia del oscilador, los niveles de RF y el dispositivo. El multiplicador `0.2` solo ajusta nivel; no corrige distorsión, ruido o clipping anterior.

## Tipos y tasas por etapa

| Tramo | Tipo de muestra | Tasa |
|---|---|---:|
| Fuente RTL-SDR | Complejo (I/Q) | 2,048,000 sps |
| Espectro | Complejo | 2,048,000 sps |
| Remuestreador | Complejo | 240,000 sps |
| `analog.wfm_rcv` | Flotante real de audio | 48,000 sps |
| Multiplicador y audio sink | Flotante real | 48,000 sps |

## Fuentes primarias

- [GNU Radio 3.10.1.1: WFM jerárquico, desviación máxima, filtro y decimación](https://github.com/gnuradio/gnuradio/blob/v3.10.1.1/gr-analog/python/analog/wfm_rcv.py)
- [GNU Radio 3.10.1.1: deénfasis FM y tau predeterminado](https://github.com/gnuradio/gnuradio/blob/v3.10.1.1/gr-analog/python/analog/fm_emph.py)
- [GNU Radio 3.10.1.1: FIR del remuestreador racional](https://github.com/gnuradio/gnuradio/blob/v3.10.1.1/gr-filter/lib/rational_resampler_impl.cc)
- [GNU Radio 3.10.1.1: definición GRC del receptor WFM](https://github.com/gnuradio/gnuradio/blob/v3.10.1.1/gr-analog/grc/analog_wfm_rcv.block.yml)
- [GNU Radio 3.10.1.1: código de los sinks Qt](https://github.com/gnuradio/gnuradio/tree/v3.10.1.1/gr-qtgui)
