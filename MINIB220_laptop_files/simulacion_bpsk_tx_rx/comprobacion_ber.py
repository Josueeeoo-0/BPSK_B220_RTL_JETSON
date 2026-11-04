#!/usr/bin/env python3
"""Compara archivos de bits binarios y calcula la tasa de error (BER)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parent / "archivos_de_simulacion"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Valida y compara dos archivos byte por bit (valores 0/1)."
    )
    parser.add_argument("--tx", type=Path, default=DATA_DIR / "bpsk_tx.u8",
                        help="archivo de bits transmitidos (predeterminado: referencia local)")
    parser.add_argument("--rx", type=Path, default=DATA_DIR / "bpsk_rx.u8",
                        help="archivo de bits recibidos (predeterminado: referencia local)")
    parser.add_argument("--expected-bits", type=int, default=100_000,
                        help="longitud exigida para ambos archivos (predeterminado: 100000)")
    return parser.parse_args()


def read_binary_bits(path: Path) -> bytes:
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise ValueError(f"no se pudo leer {path}: {exc}") from exc
    if any(value not in (0, 1) for value in data):
        invalid = next(value for value in data if value not in (0, 1))
        raise ValueError(f"{path} contiene el valor no binario {invalid}")
    return data


def main() -> int:
    args = parse_args()
    if args.expected_bits <= 0:
        print("ERROR: --expected-bits debe ser mayor que cero.", file=sys.stderr)
        return 2

    try:
        tx = read_binary_bits(args.tx)
        rx = read_binary_bits(args.rx)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    print(f"Bits transmitidos: {len(tx)}")
    print(f"Bits recibidos:    {len(rx)}")
    if len(tx) != len(rx):
        print("FALLO: las longitudes de TX y RX no coinciden.")
        return 1
    if len(tx) != args.expected_bits:
        print(f"FALLO: se esperaban {args.expected_bits} bytes/bit por archivo.")
        return 1

    errors = sum(a != b for a, b in zip(tx, rx))
    ber = errors / len(tx)
    print(f"Errores:           {errors}")
    print(f"BER observada:      {ber:.8g}")
    if errors:
        print("FALLO: se detectaron errores de bit.")
        return 1
    print("PRUEBA CORRECTA: sin errores de bit.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
