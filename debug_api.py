#!/usr/bin/env python
import requests
import json

print("=" * 60)
print("TESTANDO API")
print("=" * 60)

try:
    # 1. Órgãos
    print("\n1. GET /api/orgaos")
    resp = requests.get("http://localhost:8000/api/orgaos")
    print(f"   Status: {resp.status_code}")
    data = resp.json()
    print(f"   Órgãos: {data.get('orgaos')}")

    # 2. Cargos
    print("\n2. GET /api/cargos/sedes_df")
    resp = requests.get("http://localhost:8000/api/cargos/sedes_df")
    print(f"   Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print(f"   Cargos: {data.get('cargos')}")
        cargo = data['cargos'][0] if data.get('cargos') else None

        if cargo:
            # 3. Materias
            print(f"\n3. GET /api/materias/sedes_df/{cargo}")
            resp = requests.get(f"http://localhost:8000/api/materias/sedes_df/{cargo}")
            print(f"   Status: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                print(f"   Materias: {list(data.get('materias', {}).keys())[:3]}...")

                # 4. Stats
                print(f"\n4. GET /api/stats/cargo/sedes_df/{cargo}")
                resp = requests.get(f"http://localhost:8000/api/stats/cargo/sedes_df/{cargo}")
                print(f"   Status: {resp.status_code}")
                if resp.status_code == 200:
                    data = resp.json()
                    print(f"   Stats: {json.dumps(data, indent=2)}")
                else:
                    print(f"   Error: {resp.text}")
            else:
                print(f"   Error: {resp.text}")
    else:
        print(f"   Error: {resp.text}")

except Exception as e:
    print(f"Erro: {e}")
    import traceback
    traceback.print_exc()
