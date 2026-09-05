"""Catálogo bruto das disciplinas do QConcursos: nome -> id.

Dado, não lógica. Fica separado de `disciplinas.py` porque uma tabela de 232
entradas ocupa espaço sem ser complexidade, e o módulo de regras precisa caber
no limite de 250 linhas de `scrapers/**`.

Levantado na interface logada em 04/09/2026 por DOIS agentes independentes:
244 IDs coincidiram nos dois com nome idêntico, zero divergência. O catálogo
real vai até o ID 623 — 267 disciplinas válidas.

Dez IDs ficaram de fora: devolvem 2.657.288 questões, que é o total do site
inteiro — sinal de que o filtro não aplica. Dois deles nem são matéria
("Como estudar para concursos", "Entenda o seu edital"). Coletar por eles
traria o acervo inteiro rotulado errado.

O comentário de cada linha é o tamanho do acervo daquela disciplina no QC.
"""

CATALOGO: dict[str, int] = {
    "Medicina": 177,  # 160.160 questoes
    "Pedagogia": 182,  # 141.916 questoes
    "Matemática": 13,  # 89.956 questoes
    "Enfermagem": 172,  # 83.574 questoes
    "Psicologia": 178,  # 51.039 questoes
    "Engenharia Civil": 171,  # 47.691 questoes
    "Odontologia": 176,  # 45.140 questoes
    "Segurança e Saúde no Trabalho": 28,  # 42.740 questoes
    "Contabilidade Geral": 35,  # 35.068 questoes
    "Nutrição": 186,  # 34.559 questoes
    "Saúde Pública": 575,  # 33.427 questoes
    "Farmácia": 262,  # 30.410 questoes
    "Contabilidade Pública": 36,  # 29.141 questoes
    "Educação Física": 326,  # 28.643 questoes
    "Legislação Federal": 53,  # 26.059 questoes
    "Inglês": 16,  # 24.873 questoes
    "Fisioterapia": 185,  # 24.530 questoes
    "Geografia": 73,  # 23.865 questoes
    "Redes de Computadores": 95,  # 23.854 questoes
    "Biologia": 244,  # 23.477 questoes
    "Direito Tributário": 18,  # 22.954 questoes
    "Biblioteconomia": 169,  # 21.112 questoes
    "História": 550,  # 20.129 questoes
    "Veterinária": 239,  # 20.034 questoes
    "Direito Civil": 8,  # 19.522 questoes
    "Arquitetura": 168,  # 19.406 questoes
    "Legislação de Trânsito": 200,  # 19.221 questoes
    "Engenharia Elétrica": 180,  # 18.781 questoes
    "Química": 208,  # 18.666 questoes
    "Banco de Dados": 96,  # 18.459 questoes
    "Economia": 191,  # 17.574 questoes
    "Engenharia Mecânica": 181,  # 17.553 questoes
    "Fonoaudiologia": 263,  # 16.876 questoes
    "Gestão de Pessoas": 112,  # 16.499 questoes
    "Engenharia Agronômica (Agronomia)": 256,  # 16.142 questoes
    "Direito Sanitário": 211,  # 15.752 questoes
    "Engenharia Ambiental e Sanitária": 259,  # 15.684 questoes
    "Atualidades": 56,  # 15.579 questoes
    "Direito Ambiental": 76,  # 15.148 questoes
    "Programação": 160,  # 14.502 questoes
    "Engenharia de Software": 100,  # 14.266 questoes
    "Segurança da Informação": 97,  # 14.265 questoes
    "História e Geografia de Estados e Municípios": 521,  # 14.077 questoes
    "Estatística": 40,  # 13.898 questoes
    "Conhecimentos Gerais": 24,  # 13.765 questoes
    "Sistemas Operacionais": 94,  # 13.445 questoes
    "Direito Processual Civil - Novo Código de Processo Civil - CPC 2015": 560,  # 12.463 questoes
    "Radiologia": 437,  # 11.794 questoes
    "Psiquiatria": 189,  # 11.432 questoes
    "Comunicação Social": 170,  # 11.208 questoes
    "Física": 198,  # 11.109 questoes
    "Terapia Ocupacional": 183,  # 10.459 questoes
    "Direito do Trabalho": 7,  # 10.106 questoes
    "Jornalismo": 206,  # 10.032 questoes
    "Direito Financeiro": 14,  # 9.769 questoes
    "Biomedicina - Análises Clínicas": 299,  # 9.520 questoes
    "Técnicas em Laboratório": 465,  # 9.360 questoes
    "Auditoria": 34,  # 9.347 questoes
    "Educação Artística": 325,  # 8.966 questoes
    "Libras": 371,  # 8.660 questoes
    "Meio Ambiente": 417,  # 8.232 questoes
    "Matemática Financeira": 39,  # 8.120 questoes
    "Ética na Administração Pública": 25,  # 7.721 questoes
    "Governança de TI": 99,  # 7.532 questoes
    "Direito Processual Civil - CPC 1973": 12,  # 7.360 questoes
    "Edificações": 323,  # 7.242 questoes
    "Mecânica": 413,  # 7.011 questoes
    "Sociologia": 252,  # 6.945 questoes
    "Geologia": 358,  # 6.761 questoes
    "Legislação dos Municípios do Estado do Rio Grande do Sul": 599,  # 6.450 questoes
    "Direito Previdenciário": 19,  # 6.356 questoes
    "Direito Empresarial (Comercial)": 166,  # 6.195 questoes
    "Eletricidade": 327,  # 6.062 questoes
    "Gerência de Projetos": 118,  # 6.053 questoes
    "Segurança e Transporte": 207,  # 6.006 questoes
    "Medicina Legal": 104,  # 5.219 questoes
    "Direito Processual do Trabalho": 11,  # 5.029 questoes
    "Design Gráfico": 501,  # 4.872 questoes
    "Áudio e Vídeo": 523,  # 4.811 questoes
    "Direitos Humanos": 214,  # 4.772 questoes
    "Contabilidade de Custos": 107,  # 4.693 questoes
    "Noções de Primeiros Socorros": 199,  # 4.528 questoes
    "Direito do Consumidor": 89,  # 4.382 questoes
    "Filosofia": 546,  # 4.382 questoes
    "Estatuto da Pessoa com Deficiência - Lei nº 13.146 de 2015": 579,  # 4.349 questoes
    "Agropecuária": 564,  # 4.328 questoes
    "Legislação dos Municípios do Estado de São Paulo": 596,  # 4.317 questoes
    "Espanhol": 17,  # 4.306 questoes
    "Engenharia Eletrônica": 275,  # 4.268 questoes
    "Legislação dos Municípios do Estado de Santa Catarina": 600,  # 4.118 questoes
    "Mecânica de Autos": 414,  # 4.095 questoes
    "Auditoria Governamental": 502,  # 3.954 questoes
    "Relações Públicas": 265,  # 3.883 questoes
    "Artes Visuais": 302,  # 3.867 questoes
    "Direito Urbanístico": 519,  # 3.766 questoes
    "Conhecimentos de Serviços Gerais": 577,  # 3.467 questoes
    "Conhecimentos Bancários": 57,  # 3.401 questoes
    "Música": 423,  # 3.343 questoes
    "Engenharia Química e Química Industrial": 260,  # 3.309 questoes
    "Direito Digital": 593,  # 3.288 questoes
    "Ciências": 566,  # 3.270 questoes
    "Regimento Interno": 92,  # 3.147 questoes
    "Direito Notarial e Registral": 497,  # 3.104 questoes
    "Direito Eleitoral": 6,  # 3.077 questoes
    "Eletrotécnica": 332,  # 2.883 questoes
    "Engenharia de Produção": 274,  # 2.877 questoes
    "Legislação dos Municípios do Estado de Minas Gerais": 597,  # 2.767 questoes
    "Engenharia Florestal": 258,  # 2.702 questoes
    "Legislação Municipal": 179,  # 2.655 questoes
    "Secretariado": 440,  # 2.563 questoes
    "Artes Cênicas": 283,  # 2.556 questoes
    "Patologia": 148,  # 2.552 questoes
    "Legislação do Ministério Público": 276,  # 2.437 questoes
    "Telecomunicações": 47,  # 2.324 questoes
    "Marketing": 229,  # 2.323 questoes
    "Literatura": 408,  # 2.191 questoes
    "Engenharia de Telecomunicações": 184,  # 2.145 questoes
    "Legislação dos Tribunais de Justiça (TJs)": 43,  # 2.088 questoes
    "Eletrônica": 331,  # 2.038 questoes
    "Legislação dos Municípios do Estado do Paraná": 598,  # 2.034 questoes
    "Turismo": 484,  # 1.936 questoes
    "Engenharia Hidráulica": 344,  # 1.888 questoes
    # 1.866 questoes
    "Legislação dos Tribunais de Contas (TCU, TCEs e TCMs) e Ministérios Públicos de Contas": 581,
    "Artes Plásticas": 301,  # 1.863 questoes
    "Engenharia Cartográfica": 578,  # 1.825 questoes
    "Legislação dos Municípios do Estado do Rio de Janeiro": 595,  # 1.744 questoes
    "Modelagem de Processos de Negócio (BPM)": 489,  # 1.526 questoes
    "Auditoria de Obras Públicas": 225,  # 1.465 questoes
    "Museologia": 422,  # 1.456 questoes
    "Engenharia de Transportes e Trânsito": 343,  # 1.444 questoes
    "Legislação dos TRFs, STJ, STF e CNJ": 558,  # 1.444 questoes
    "Engenharia Naval": 269,  # 1.405 questoes
    "Engenharia de Petróleo": 341,  # 1.392 questoes
    "Criminalística": 530,  # 1.351 questoes
    "Linguística": 591,  # 1.308 questoes
    "Legislação dos Municípios do Estado de Goiás": 601,  # 1.283 questoes
    "Sistemas de Informação": 238,  # 1.267 questoes
    "Engenharia de Agrimensura": 339,  # 1.264 questoes
    "Controle Externo": 66,  # 1.224 questoes
    "Agrimensura": 281,  # 1.133 questoes
    "Engenharia Agrícola": 255,  # 1.120 questoes
    "Antropologia": 273,  # 1.084 questoes
    "Direito Internacional Público": 42,  # 1.034 questoes
    "Braille": 589,  # 1.028 questoes
    "Engenharia Aeronáutica": 518,  # 1.004 questoes
    "Meteorologia": 419,  # 1.001 questoes
    "Engenharia de Pesca": 266,  # 935 questoes
    "Legislação dos Municípios do Estado do Espírito Santo": 617,  # 930 questoes
    "Legislação da Defensoria Pública": 246,  # 905 questoes
    "Ciência Política": 253,  # 860 questoes
    "Criminologia": 554,  # 855 questoes
    "Relações Internacionais": 585,  # 847 questoes
    "Legislação dos Municípios do Estado do Mato Grosso": 602,  # 837 questoes
    "Legislação dos Municípios do Estado do Pará": 606,  # 804 questoes
    "Segurança Pública": 532,  # 801 questoes
    "Direito Econômico": 551,  # 784 questoes
    "Relações Humanas": 51,  # 782 questoes
    "Gestão de Saúde e Administração Hospitalar": 592,  # 768 questoes
    "Comércio Internacional (Exterior)": 152,  # 760 questoes
    "Desenho Industrial": 318,  # 722 questoes
    "Engenharia de Automação": 498,  # 715 questoes
    "Direito Agrário": 232,  # 691 questoes
    "Eletroeletrônica": 329,  # 666 questoes
    "Legislação dos Municípios do Estado de Pernambuco": 608,  # 665 questoes
    "Francês": 354,  # 664 questoes
    "Atuária": 245,  # 640 questoes
    "Alemão": 561,  # 566 questoes
    "Legislação dos Tribunais do Trabalho (TST e TRTs)": 557,  # 548 questoes
    "Legislação dos Tribunais Eleitorais (TSE e TREs)": 580,  # 537 questoes
    "Arqueologia": 272,  # 513 questoes
    "Engenharia de Qualidade": 499,  # 511 questoes
    "Direito Marítimo": 78,  # 507 questoes
    "Engenharia Biomédica": 336,  # 507 questoes
    "Publicidade e Propaganda": 594,  # 479 questoes
    "Legislação dos Municípios do Estado da Bahia": 604,  # 479 questoes
    "Oceanografia Geológica": 205,  # 475 questoes
    "Engenharia Mecatrônica": 346,  # 399 questoes
    "Filosofia do Direito": 216,  # 396 questoes
    "Legislação da PRF": 559,  # 384 questoes
    "Italiano": 586,  # 361 questoes
    "Legislação dos Municípios do Estado do Ceará": 605,  # 357 questoes
    "Vestuário, Moda e Estilismo": 485,  # 337 questoes
    "Legislação dos Municípios do Estado da Paraíba": 607,  # 316 questoes
    "Artes Gráficas": 82,  # 307 questoes
    "Legislação dos Municípios do Estado de Rondônia": 616,  # 298 questoes
    "Astronomia": 587,  # 297 questoes
    "Legislação dos Municípios do Estado de Alagoas": 619,  # 293 questoes
    "Direito Internacional Privado": 90,  # 273 questoes
    "Legislação dos Municípios do Estado do Rio Grande do Norte": 610,  # 251 questoes
    "Legislação dos Municípios do Estado do Maranhão": 618,  # 244 questoes
    "Metodologia da Investigação Policial": 524,  # 215 questoes
    "Legislação dos Municípios do Estado do Amazonas": 614,  # 205 questoes
    "Gastronomia": 356,  # 203 questoes
    "Zootecnia": 487,  # 203 questoes
    "Matemática Atuarial": 226,  # 193 questoes
    "Legislação de Seguros": 222,  # 192 questoes
    "Legislação da Justiça Militar": 556,  # 191 questoes
    "Legislação dos Municípios do Estado de Tocantins": 613,  # 190 questoes
    "Zoologia": 576,  # 182 questoes
    "Legislação dos Municípios do Estado do Acre": 620,  # 158 questoes
    "Legislação dos Municípios do Estado do Mato Grosso do Sul": 603,  # 154 questoes
    "Atendimento (Escriturário)": 58,  # 152 questoes
    "Legislação dos Municípios do Estado do Piauí": 609,  # 151 questoes
    "Legislação dos Municípios do Estado de Roraima": 611,  # 129 questoes
    # 127 questoes
    "Estatuto da Advocacia e da OAB, Regulamento Geral e Código de Ética e Disciplina da OAB": 500,
    "Técnicas em Topografia": 471,  # 122 questoes
    "Ciência e Tecnologia": 293,  # 111 questoes
    "Mecatrônica": 416,  # 107 questoes
    "Legislação das Procuradorias Gerais dos Estados - PGE's": 583,  # 106 questoes
    "Enologia": 350,  # 88 questoes
    "Tratados Internacionais": 588,  # 88 questoes
    "Legislação dos Municípios do Estado de Sergipe": 612,  # 85 questoes
    "Teologia": 483,  # 80 questoes
    "Legislação da AGU": 250,  # 76 questoes
    "Técnicas Administrativas": 447,  # 61 questoes
    "Automação": 305,  # 47 questoes
    "Taquigrafia": 590,  # 33 questoes
    "Instrumentação Industrial": 370,  # 32 questoes
    "Órtese e Prótese": 427,  # 27 questoes
    "Desenho Técnico": 317,  # 25 questoes
    "Tecnologia Educacional": 475,  # 25 questoes
    "Sistemas de Gás": 442,  # 23 questoes
    "Ciências Humanas": 567,  # 14 questoes
    "Hidrologia": 367,  # 10 questoes
    "Hemoterapia": 366,  # 9 questoes
    "Legislação dos Municípios do Estado do Amapá": 615,  # 9 questoes
    "Mineração": 573,  # 6 questoes
    "Metrologia": 420,  # 5 questoes
    "Mandarim": 622,  # 4 questoes
    "Segurança": 388,  # 1 questoes
    "Ciências Navais": 562,  # 1 questoes
    "Cartografia": 565,  # 1 questoes
}
