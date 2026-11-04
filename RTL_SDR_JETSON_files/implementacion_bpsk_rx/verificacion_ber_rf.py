#!/usr/bin/env python3
"""Busca un anclaje y mide una sola alineación hasta el final de la captura.

La búsqueda y validación se excluyen de la medición. No se realinea el resto
del archivo ni se eliminan sus errores. Una BER distinta de cero no impide
completar la medición: no es una prueba que deba forzarse a pasar.
"""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.signal import correlate


DATA = Path(__file__).resolve().parent / "archivos_tx_y_rx"


def leer_bits(path):
    data = np.fromfile(path, dtype=np.uint8)
    if not len(data) or np.any(data > 1):
        raise ValueError(f"{path}: se requiere un archivo no vacío de bytes 0/1")
    return data


def buscar_anclaje(tx, rx, bloque):
    # Extender circularmente permite que una ventana cruce el final de TX.
    circular = tx[np.arange(len(tx) + bloque - 1) % len(tx)].astype(float) * 2 - 1
    examinadas = 0
    for inicio in range(0, len(rx) - 2 * bloque + 1, bloque):
        ventana = rx[inicio:inicio + bloque].astype(float) * 2 - 1
        correlacion = correlate(circular, ventana, mode="valid", method="fft")
        fase = int(np.argmax(np.abs(correlacion)))
        invertida = bool(correlacion[fase] < 0)
        examinadas += 1
        # El filtro numérico acelera la búsqueda; la aceptación usa igualdad
        # exacta sobre enteros, incluyendo una segunda ventana no buscada.
        if abs(correlacion[fase]) < bloque - 0.5:
            continue
        esperado = tx[(fase + np.arange(2 * bloque)) % len(tx)]
        if np.array_equal(rx[inicio:inicio + 2 * bloque] ^ int(invertida), esperado):
            return inicio, fase, invertida, examinadas
    raise ValueError("No se encontró un anclaje exacto con validación independiente")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tx", type=Path, default=DATA / "bpsk_tx.u8")
    parser.add_argument("--rx", type=Path, default=DATA / "bpsk_rx_rf_USRP_tx.u8")
    parser.add_argument("--bloque", type=int, default=4096)
    parser.add_argument("--json", type=Path, help="Guardar un informe de la medición")
    args = parser.parse_args()
    if args.bloque <= 0:
        parser.error("--bloque debe ser positivo")
    try:
        tx, rx = leer_bits(args.tx), leer_bits(args.rx)
        inicio, fase, invertida, examinadas = buscar_anclaje(tx, rx, args.bloque)
        excluir = 2 * args.bloque
        inicio_medicion = inicio + excluir
        if inicio_medicion >= len(rx):
            raise ValueError("No quedan bits independientes para medir")
        recibidos = rx[inicio_medicion:] ^ int(invertida)
        indices = (fase + excluir + np.arange(len(recibidos))) % len(tx)
        diferencias = recibidos != tx[indices]
        errores = int(np.count_nonzero(diferencias))
        comparados = len(recibidos)
        informe = {
            "metodo": "primer anclaje exacto de dos ventanas; una alineacion hasta EOF",
            "sha256_tx": hashlib.sha256(tx.tobytes()).hexdigest(),
            "sha256_rx": hashlib.sha256(rx.tobytes()).hexdigest(),
            "bits_tx": len(tx), "bits_rx": len(rx),
            "bloque_busqueda_bits": args.bloque, "ventanas_examinadas": examinadas,
            "inicio_anclaje_rx": inicio, "posicion_anclaje_tx": fase,
            "invertida": invertida, "bits_excluidos_anclaje": excluir,
            "inicio_medicion_rx": inicio_medicion,
            "bits_comparados": comparados, "errores": errores,
            "ber_observada": errores / comparados,
            "primeras_posiciones_error_rx": (
                np.flatnonzero(diferencias)[:10] + inicio_medicion
            ).tolist(),
        }
        if not errores:
            informe["limite_ber_95_aproximado"] = 3 / comparados
        print(json.dumps(informe, indent=2, ensure_ascii=False))
        print("Medición completada. La alineación no cambia dentro del tramo medido.")
        if args.json:
            args.json.parent.mkdir(parents=True, exist_ok=True)
            args.json.write_text(json.dumps(informe, indent=2, ensure_ascii=False) + "\n", encoding="utf8")
        return 0
    except (OSError, ValueError) as exc:
        print(f"No se calculó BER: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
