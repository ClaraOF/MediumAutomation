# Compatibilidad hacia atrás: re-exporta run() desde main.py
# Este archivo ya no contiene lógica — ver main.py para el entry point con CLI.
from main import run

__all__ = ["run"]
