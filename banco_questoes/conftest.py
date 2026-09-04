"""Marca a raiz do projeto para o pytest.

A presença deste arquivo é o que coloca esta pasta no `sys.path`, permitindo
que os testes façam `import db`, `import config` etc. (o pacote `tests/` tem
`__init__.py`, então o import parte daqui).

A fixture de banco de teste vive em `tests/conftest.py`, e só lá: ela existia
duplicada aqui, numa versão antiga que isentava `test_gerador_multibanca` do
redirecionamento — o que fez testes gravarem no banco de PRODUÇÃO. Duas
fixtures autouse de mesmo nome não somam: a mais próxima do teste vence e a
outra vira código morto silencioso.
"""


# O pytest varre a pasta inteira do projeto atras de testes. O perfil do Chrome
# do scraper tem milhares de arquivos de cache que o navegador cria e apaga em
# tempo real; quando o coletor do QC esta rodando, um deles some no meio da
# varredura e a coleta de testes aborta com AssertionError. Os PDFs arquivados
# da Cebraspe sao so peso morto na varredura.
collect_ignore_glob = [
    "perfil_chrome_scraper/*",
    "provas_pdf/*",
    ".venv/*",
]
