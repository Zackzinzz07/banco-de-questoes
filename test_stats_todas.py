#!/usr/bin/env python
import requests
import json

try:
    print("GET /api/stats/todas")
    resp = requests.get("http://localhost:8000/api/stats/todas")
    print(f"Status: {resp.status_code}")
    data = resp.json()
    print(f"\nTotal: {data['total']}")
    print(f"\nTop órgãos:")
    for orgao, count in list(data['por_orgao'].items())[:5]:
        print(f"  {orgao}: {count}")
    print(f"\nTop matérias:")
    for materia, count in list(data['por_materia'].items())[:5]:
        print(f"  {materia}: {count}")

except Exception as e:
    print(f"Erro: {e}")
