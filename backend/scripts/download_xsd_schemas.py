#!/usr/bin/env python3
"""Descarga XSD v4.4 oficiales del CDN de Hacienda."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fiscal.xsd_validator import SCHEMA_PATHS, ensure_schema_downloaded

def main():
    for tipo in SCHEMA_PATHS:
        path = ensure_schema_downloaded(tipo)
        print('OK', tipo, path)
    print('\nEsquemas listos en fiscal/schemas/')


if __name__ == '__main__':
    main()
