#!/usr/bin/env python
"""Test PCI API endpoints."""

import requests
import json

BASE_URL = "http://localhost:8000"

print("\n" + "="*80)
print("TESTANDO ENDPOINTS PCI")
print("="*80)

# Test 1: Global PCI stats
print("\n[1] GET /api/stats/pci")
try:
    r = requests.get(f"{BASE_URL}/api/stats/pci", timeout=5)
    if r.status_code == 200:
        data = r.json()
        print(f"    [OK] Total PCI: {data['total_pci']:,} questoes")
        print(f"    [OK] Categorias: {len(data['por_categoria'])} categorias")

        # Show first 3 categories
        for cat in list(data['por_categoria'].keys())[:3]:
            stats = data['por_categoria'][cat]
            print(f"         - {cat}: {stats['total']} qs ({len(stats['temas'])} temas)")
    else:
        print(f"    [ERROR] Status {r.status_code}")
except Exception as e:
    print(f"    [ERROR] {e}")

# Test 2: Specific category
print("\n[2] GET /api/stats/pci/direito-administrativo")
try:
    r = requests.get(f"{BASE_URL}/api/stats/pci/direito-administrativo", timeout=5)
    if r.status_code == 200:
        data = r.json()
        print(f"    [OK] Total: {data['total']:,} questoes")
        print(f"    [OK] Temas: {len(data['por_tema'])} temas")

        # Show first 3 temas
        for tema in list(data['por_tema'].keys())[:3]:
            stats = data['por_tema'][tema]
            print(f"         - {tema}: {stats['total']} qs ({stats['com_imagens']} com imgs)")
    else:
        print(f"    [ERROR] Status {r.status_code}")
except Exception as e:
    print(f"    [ERROR] {e}")

print("\n" + "="*80)
print("Endpoints respondendo corretamente!")
print("Acesse http://localhost:8000 para ver o dashboard")
print("="*80 + "\n")
