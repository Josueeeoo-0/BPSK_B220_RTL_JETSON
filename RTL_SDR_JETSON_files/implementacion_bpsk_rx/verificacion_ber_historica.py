#!/usr/bin/env python3
"""Reproduce el cálculo histórico únicamente con la captura que lo originó."""

import argparse
from pathlib import Path

import numpy as np


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--datos", type=Path, default=Path.home() / "sdr-alertas" / "datos")
    args = parser.parse_args()
    try:
        tx = np.fromfile(args.datos / "bpsk_tx.u8", dtype=np.uint8)
        rx = np.fromfile(args.datos / "bpsk_rx_rf_USRP_tx.u8", dtype=np.uint8)
    except OSError as exc:
        raise SystemExit(f"No se pudo leer la captura: {exc}")
    if len(tx) != 100000 or len(rx) != 1250113:
        raise SystemExit("Los tamaños cambiaron. Este anclaje corresponde a la captura histórica.")
    if np.any(tx > 1) or np.any(rx > 1):
        raise SystemExit("Se esperaban bytes de valor 0 o 1.")

    inicio_anclaje_rx = 65536
    posicion_anclaje_tx = 57716
    invertida = False
    excluir = 8192
    inicio_medicion = inicio_anclaje_rx + excluir
    indices_anclaje = (posicion_anclaje_tx + np.arange(excluir)) % len(tx)
    anclaje_rx = rx[inicio_anclaje_rx:inicio_medicion] ^ int(invertida)
    if np.any(anclaje_rx != tx[indices_anclaje]):
        raise SystemExit("El anclaje no coincide. No aplicar estos índices a otra captura.")

    recibidos = rx[inicio_medicion:] ^ int(invertida)
    indices_tx = (posicion_anclaje_tx + excluir + np.arange(len(recibidos))) % len(tx)
    diferencias = recibidos != tx[indices_tx]
    comparados = len(recibidos)
    errores = int(np.count_nonzero(diferencias))
    ber = errores / comparados
    print("RESULTADO DEL TRAMO CONTINUO")
    print("Primer bit RX analizado:", inicio_medicion)
    print("Bits iniciales excluidos:", inicio_medicion)
    print("Bits comparados:", comparados)
    print("Errores:", errores)
    print(f"BER observada: {ber:.10g}")
    print(f"Porcentaje de errores: {100 * ber:.8f} %")
    if errores:
        posiciones = np.flatnonzero(diferencias)
        print("Primeros errores, posiciones absolutas en RX:", (posiciones[:10] + inicio_medicion).tolist())
    else:
        print("Límite superior aproximado de BER al 95 %:", f"{3 / comparados:.3g}",
              "(suponiendo errores independientes y estacionarios)")


if __name__ == "__main__":
    main()
