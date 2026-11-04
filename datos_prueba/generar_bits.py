#!/usr/bin/env python3
"""Genera la referencia binaria de 100 000 bits usada por los flujos BPSK."""

import argparse
import random
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--salida", type=Path,
        default=Path.home() / "sdr-alertas" / "datos" / "bpsk_tx.u8",
    )
    args = parser.parse_args()
    args.salida.parent.mkdir(parents=True, exist_ok=True)
    generador = random.Random(2026)
    bits = bytes(generador.getrandbits(1) for _ in range(100000))
    args.salida.write_bytes(bits)
    print("Archivo:", args.salida)
    print("Bits generados:", len(bits))
    print("Primeros 32 bits:", list(bits[:32]))


if __name__ == "__main__":
    main()
