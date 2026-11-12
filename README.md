# EpiDados

**Site:** https://labiomics.github.io/epidados

Plataforma aberta de ensino com dados reais do DATASUS:

- **Estudos de caso** interprofissionais (veterinária, medicina, enfermagem, farmácia, odontologia), com mapas, séries históricas e perguntas por profissão;
- **Datasets para IA**, prontos para scikit-learn, com ficha técnica e notebook de linha de base.

O site é estático (GitHub Pages). O processamento roda em Python no GitHub Actions, uma vez por mês.

```
DATASUS (FTP) + IBGE (APIs)
        │  GitHub Actions, mensal
        ▼
pipeline Python + DuckDB  ──►  site/dados/*.csv  ──►  Quarto  ──►  GitHub Pages
        │
        └── testes contra os totais oficiais do TabNet
```

## Conteúdo da versão atual

| Tipo | Item | Fonte |
|---|---|---|
| Estudo de caso | Zoonoses e Saúde Única | SINAN: leishmaniose visceral, leptospirose, atendimento antirrábico |
| Dataset de IA | Óbito por leishmaniose visceral | SINAN: leishmaniose visceral |

## Rodar localmente

Requer [uv](https://docs.astral.sh/uv/). O Quarto é instalado como dependência Python.

```bash
uv sync --all-groups
uv run epidados            # baixa (~1 GB na primeira vez), converte, agrega e gera os datasets
uv run pytest -q                 # valida contra o TabNet
uv run quarto preview site       # abre o site em http://localhost:xxxx
```

Etapas separadas: `uv run epidados preparar | malhas | agregar | ml`.
Para baixar só alguns agravos: `uv run epidados preparar --agravos LEIV LEPT`.

A primeira execução leva cerca de 25 minutos, quase todo o tempo no atendimento antirrábico (cerca de 750 mil registros por ano). As seguintes são incrementais: só arquivos novos ou alterados no FTP são reprocessados.

## Publicar no GitHub Pages

O workflow `.github/workflows/publicar.yml` baixa os dados, roda os testes, gera o site e publica no GitHub Pages (Settings → Pages → Source: GitHub Actions). Ele roda todo dia 5, a cada push na branch `main` e manualmente em **Actions → Atualizar dados e publicar site → Run workflow**.

As APIs do IBGE (`servicodados` e `apisidra`) costumam recusar conexões de fora do Brasil, como as dos runners do GitHub. Por isso o repositório guarda em `referencia/ibge/` uma cópia comprimida (~2,6 MB) de municípios, malhas e população, usada quando a API não responde. Quando o IBGE publicar novas estimativas, rode localmente (no Brasil) `uv run epidados agregar` e depois `uv run epidados referencia` e faça commit de `referencia/`.


## Estrutura

```
src/epidados/
  config.py      agravos, colunas e caminhos
  baixar.py      FTP do DATASUS e APIs do IBGE, com cache e fallback
  sinan.py       .dbc → Parquet; view harmonizada no DuckDB
  ibge.py        municípios, população anual, malhas
  codigos.py     rótulos dos códigos das fichas
  agregar.py     CSVs do site
  ml.py          datasets de machine learning
notebooks/       notebooks de linha de base (gerados por _gerar_notebooks.py)
site/            projeto Quarto
referencia/ibge/ cópia versionada das bases do IBGE (fallback da API)
tests/           validação contra o TabNet e regras de privacidade
docs/            decisões de tratamento e armadilhas dos dados
```

## Como adicionar um agravo

1. Descubra o prefixo do arquivo no FTP (`ftp.datasus.gov.br/dissemin/publicos/SINAN/DADOS/FINAIS`).
2. Acrescente um `Agravo` em `config.py`, com as colunas necessárias.
3. Escreva as agregações em `agregar.py` e os rótulos em `codigos.py`.
4. Consulte os totais no TabNet e acrescente-os em `tests/test_validacao.py`.

## Licenças

Código: MIT. Textos e dados derivados: CC BY 4.0. Dados originais: Ministério da Saúde (SINAN/DATASUS) e IBGE.

Material didático. Não usar para decisões clínicas.
