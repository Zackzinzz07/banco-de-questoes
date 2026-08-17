#!/usr/bin/env python
import requests
import json

try:
    # Testa /api/orgaos
    print("1. Testando /api/orgaos...")
    resp = requests.get("http://localhost:8000/api/orgaos")
    print(f"   Status: {resp.status_code}")
    print(f"   Response: {json.dumps(resp.json(), indent=2)}")

    # Testa /api/cargos
    print("\n2. Testando /api/cargos/SEDES%2FDF...")
    resp = requests.get("http://localhost:8000/api/cargos/SEDES%2FDF")
    print(f"   Status: {resp.status_code}")
    if resp.status_code == 200:
        print(f"   Response: {json.dumps(resp.json(), indent=2)}")
    else:
        print(f"   Error: {resp.text}")

except Exception as e:
    print(f"Erro: {e}")
