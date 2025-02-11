from __future__ import annotations
from pathlib import Path
import argparse
import sys


def init() -> argparse.ArgumentParser:
    """Возвращает объект для разбора входных параметров."""
    parser = argparse.ArgumentParser()

    parser.add_argument ('file', type=str, help='xml file for handling')

    return parser


def prepare_prks(file_path: Path):
    """."""

def prepare_ozps(file_path: Path):
    """."""

if __name__ == '__main__':
    parser = init()
    args = parser.parse_args()

    file_path = Path(args.file)

    if not file_path.exists():
        print(f'handling file not found in path "{file_path}"')
        sys.exit()

    if file_path.is_dir():
        print(f'handling file not found, current path "{file_path}" is directory.')
        sys.exit()

    if file_path.name.lower() == 'prks':
        prepare_prks(file_path)

    elif file_path.name.lower() == 'ozps':
        prepare_ozps(file_path)
