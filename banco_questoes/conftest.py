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
