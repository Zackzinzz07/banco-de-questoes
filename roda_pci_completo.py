#!/usr/bin/env python
"""Coleta COMPLETA do PCI: todas as 42 categorias com mapeamento expandido."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    from banco_questoes.scrapers.pci import coletor
except ImportError:
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "coletor",
        Path(__file__).parent / "banco_questoes/scrapers/pci/coletor.py"
    )
    coletor = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(coletor)

print("\n" + "="*80)
print("🚀 COLETA COMPLETA DO PCI CONCURSOS - TODAS AS 42 CATEGORIAS")
print("="*80)
print("\n📊 Estimativa:")
print("  - ~200K questões disponíveis")
print("  - Rate limit: 1-3 segundos entre páginas")
print("  - Tempo estimado: ~9 horas (resumível)\n")

try:
    coletor.coletar_multiplas_categorias(coletor.config.listar_categorias())
    print("\n" + "="*80)
    print("✅ Coleta completa!")
    print("="*80 + "\n")
except KeyboardInterrupt:
    print("\n\n⚠️  Coleta interrompida (é seguro - tem checkpoint)")
except Exception as e:
    print(f"\n\n❌ Erro: {e}")
    import traceback
    traceback.print_exc()
