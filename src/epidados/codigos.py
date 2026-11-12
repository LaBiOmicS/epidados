"""Rótulos dos códigos das fichas do SINAN usados nas saídas.

Fontes: dicionários de dados e fichas de notificação/investigação do SINAN Net.
"""

SEXO = {"M": "Masculino", "F": "Feminino", "I": "Ignorado"}

RACA = {"1": "Branca", "2": "Preta", "3": "Amarela", "4": "Parda", "5": "Indígena", "9": "Ignorado"}

SIM_NAO = {"1": "Sim", "2": "Não", "9": "Ignorado"}

FAIXAS_ETARIAS = [
    (0, 4, "0-4"), (5, 9, "5-9"), (10, 19, "10-19"), (20, 39, "20-39"),
    (40, 59, "40-59"), (60, 79, "60-79"), (80, 200, "80+"),
]

# Leishmaniose visceral
LEIV_EVOLUCAO = {
    "1": "Cura", "2": "Abandono", "3": "Óbito por LV", "4": "Óbito por outras causas",
    "5": "Transferência", "6": "Mudança de diagnóstico", "9": "Ignorado",
}
LEIV_ENTRADA = {"1": "Caso novo", "2": "Recidiva", "3": "Transferência", "9": "Ignorado"}
LEIV_HIV = SIM_NAO

# Leptospirose: situações de risco nos 30 dias antes dos sintomas (campos ANT_CB_*)
LEPT_EXPOSICAO = {
    "ANT_CB_LAM": "Água ou lama de enchente",
    "ANT_CB_CRI": "Criação de animais",
    "ANT_CB_CAI": "Caixa d'água",
    "ANT_CB_FOS": "Fossa, caixa de gordura ou esgoto",
    "ANT_CB_SIN": "Local com sinais de roedores",
    "ANT_CB_PLA": "Plantio ou colheita",
    "ANT_CB_COR": "Rio, córrego, lagoa ou represa",
    "ANT_CB_ROE": "Contato direto com roedores",
    "ANT_CB_GRA": "Armazenamento de grãos ou alimentos",
    "ANT_CB_TER": "Terreno baldio",
    "ANT_CB_LIX": "Lixo ou entulho",
}
LEPT_EVOLUCAO = {"1": "Cura", "2": "Óbito por leptospirose", "3": "Óbito por outras causas", "9": "Ignorado"}

# Atendimento antirrábico humano
ANTR_ANIMAL = {
    "1": "Cão", "2": "Gato", "3": "Morcego", "4": "Primata (macaco)",
    "5": "Raposa", "6": "Herbívoro doméstico", "7": "Outro",
}
ANTR_ANIMAL_CHAVE = {
    "1": "cao", "2": "gato", "3": "morcego", "4": "primata",
    "5": "raposa", "6": "herbivoro", "7": "outro",
}
ANTR_CONDICAO = {
    "1": "Sadio", "2": "Suspeito", "3": "Raivoso", "4": "Morto ou desaparecido", "9": "Ignorado",
}
ANTR_CONDUTA = {
    "1": "Pré-exposição",
    "2": "Dispensa de tratamento",
    "3": "Observação do animal",
    "4": "Observação do animal + vacina",
    "5": "Vacina",
    "6": "Soro + vacina",
    "7": "Esquema de reexposição",
}


def sql_case(coluna: str, mapa: dict[str, str], padrao: str = "Ignorado") -> str:
    ramos = " ".join(f"WHEN {coluna} = '{k}' THEN '{v.replace(chr(39), chr(39) * 2)}'" for k, v in mapa.items())
    return f"(CASE {ramos} ELSE '{padrao}' END)"


def sql_faixa(coluna: str = "idade_anos") -> str:
    ramos = " ".join(f"WHEN {coluna} BETWEEN {a} AND {b} THEN '{r}'" for a, b, r in FAIXAS_ETARIAS)
    return f"(CASE {ramos} ELSE 'Ignorado' END)"
