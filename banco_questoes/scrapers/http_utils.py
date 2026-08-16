"""Utilitários HTTP compartilhados: sessão com retry/backoff, rate-limiting.

Usado por todos os scrapers (PCI e futuras bancas: VUNESP, CESGRANRIO etc.).
"""
import random
import time

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def criar_sessao(timeout_s=30, max_retries=3):
    """Cria uma requests.Session com retry/backoff em 429/5xx.

    Args:
        timeout_s: timeout (segundos) guardado na sessão para uso pelo chamador
            (requests não aplica `session.timeout` automaticamente; passe
            `timeout=sessao.timeout` explicitamente em cada `.get()`).
        max_retries: número máximo de tentativas antes de desistir.
    """
    sessao = requests.Session()
    retry_strategy = Retry(
        total=max_retries,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS"],
        backoff_factor=1.0,  # 1s, 2s, 4s, ...
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    sessao.mount("http://", adapter)
    sessao.mount("https://", adapter)
    sessao.timeout = timeout_s
    return sessao


def aguardar(min_s=3, max_s=6):
    """Pausa de rate-limiting com jitter, para não sobrecarregar o servidor."""
    time.sleep(random.uniform(min_s, max_s))
