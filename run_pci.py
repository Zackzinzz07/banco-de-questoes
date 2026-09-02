#!/usr/bin/env python3
"""
PCI Coleta - Rodar coleta hierárquica do PCI Concursos
Uso: python run_pci.py
"""
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from banco_questoes.scrapers.pci.coletor_v2 import main

if __name__ == "__main__":
    main()
