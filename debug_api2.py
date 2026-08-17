#!/usr/bin/env python
import requests
import json

print("=" * 60)
print("DEBUG: BD → BACKEND → FRONTEND")
print("=" * 60)

try:
    cargo = "Técnico de Atendimento Direto ao Cidadão"

    # 4. Stats
    print(f"\nGET /api/stats/cargo/sedes_df/{cargo}")
    url = f"http://localhost:8000/api/stats/cargo/sedes_df/{cargo}"
    print(f"URL: {url}")
    resp = requests.get(url)
    print(f"Status: {resp.status_code}")
    print(f"Response: {json.dumps(resp.json(), indent=2)}")

except Exception as e:
    print(f"Erro: {e}")
    import traceback
    traceback.print_exc()
