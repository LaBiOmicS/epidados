# Plano do projeto: Saúde em Dados (nome provisório)

Plataforma aberta de ensino com dados reais do DATASUS, com duas portas de entrada:

- **Saúde**: estudos de caso interprofissionais (veterinária, medicina, farmácia, enfermagem, odontologia)
- **Dados/IA**: datasets prontos para machine learning (scikit-learn) para TI, estatística e ciência de dados

Tudo gratuito: GitHub Pages (site), GitHub Actions (atualização), OpenML (datasets) e Zenodo (DOI).

---

## 1. Escopo da v1

### Estudos de caso (saúde)

| # | Caso | Bases | Cursos |
|---|---|---|---|
| 1 | Sífilis congênita | SINAN (SIFG, SIFC), SINASC, SIM | Med, Farm, Enf, Odonto |
| 2 | Intoxicações exógenas | SINAN (IEXO), SIM | Vet, Med, Farm, Enf |
| 3 | Acidentes com material biológico | SINAN (ACBI), CNES | Med, Farm, Enf, Odonto |
| 4 | Zoonoses e Saúde Única | SINAN (LEIV, LEPT, ANTR), SIM | Vet, Med, Farm, Enf |
| 5 | Violência | SINAN (VIOL), SIM | Med, Enf, Odonto |
| T | Onde estão os profissionais? (transversal) | CNES | Todos |

Cada caso traz um tronco comum (contexto, mapa, série, conceitos), lentes por profissão (perguntas), um quadro "Limites do dado" e um gabarito para o professor (separado).

### Datasets de ML

| Dataset | Base | Tarefa |
|---|---|---|
| Baixo peso ao nascer | SINASC | Classificação binária (vazamento, categóricas) |
| Óbito por leishmaniose visceral | SINAN LEIV | Classificação desbalanceada |
| Dengue semanal por UF | SINAN DENG | Séries temporais |

Cada dataset traz uma versão mini (≤10 mil linhas) e uma completa, uma ficha técnica (*Datasheets for Datasets*), um notebook de linha de base no Colab e publicação no OpenML (`fetch_openml`).

### Fora da v1

MCP, SIH/SIA, dados de doença animal, análises espaciais avançadas no site.

---

## 2. Arquitetura

```
ftp.datasus.gov.br ─┐
IBGE (pop., malhas) ─┤
                     ▼
        pipeline/ (Python + DuckDB)
        baixa .dbc → descompacta → harmoniza → agrega → valida
                     │
       ┌─────────────┼──────────────────┐
       ▼             ▼                  ▼
  site/dados/   datasets/ml/        testes contra TabNet
  (CSV/JSON)    (Parquet/CSV)       (totais oficiais)
       │             │
       ▼             ├──► OpenML
  site/ (Quarto) ────┴──► GitHub Pages
       │
       └──► Zenodo (DOI por versão anual)
```

### Escolhas técnicas

| Item | Escolha | Motivo |
|---|---|---|
| Pipeline | Python 3.12, `uv`, DuckDB, pandas | DuckDB agrega milhões de linhas em segundos, sem servidor |
| Leitura `.dbc` | `pyreaddbc` (ou PySUS) | Bibliotecas maduras para o formato |
| Site | **Quarto** + Observable JS / Plotly | Feito para conteúdo acadêmico; páginas com texto, gráficos e exercícios; exporta PDF para o professor; publica direto no GitHub Pages |
| Mapas | Malha municipal do IBGE (GeoJSON simplificado) | Pública; simplificada para carregar rápido |
| Automação | GitHub Actions (cron mensal) | Gratuito; reexecuta o pipeline e republica |
| ML | `openml-python` para publicar | Integração nativa com `sklearn.datasets.fetch_openml` |

### Estrutura do repositório

```
epidados/
├── pipeline/
│   ├── baixar.py          # FTP DATASUS + IBGE, com cache
│   ├── harmonizar/        # um módulo por sistema (sinan.py, sim.py, sinasc.py, cnes.py)
│   ├── agregar.py         # recortes para o site
│   ├── ml/                # um script por dataset de ML
│   └── validar.py         # compara totais com o TabNet
├── site/                  # projeto Quarto
│   ├── casos/             # um .qmd por estudo de caso
│   ├── dados-ia/          # páginas dos datasets
│   └── professor/         # gabaritos (fora da navegação pública)
├── notebooks/             # linhas de base no Colab
├── docs/armadilhas.md     # decisões de tratamento e armadilhas dos dados
└── .github/workflows/
```

---

## 3. Regras de tratamento (valem para tudo)

1. **Casos confirmados** por padrão (`CLASSI_FIN`), declarado em cada página.
2. **Município de residência** para epidemiologia; o de notificação só quando o caso for sobre o serviço.
3. **Código IBGE com 7 dígitos** em todas as saídas (o SINAN usa 6).
4. **Final × preliminar** marcado em todo dado, com a data de extração.
5. **Supressão de células com menos de 5 casos** em recortes de perfil.
6. **Datasets individuais de ML**: município vira UF ou região, datas viram ano ou mês, idades extremas são agrupadas. **Violência e HIV nunca entram em nível individual.**
7. **Validação**: os totais por UF e ano precisam bater com o TabNet (tolerância documentada).

---

## 4. Fases

A estratégia é uma **fatia vertical primeiro**: um caso e um dataset completos, publicados de ponta a ponta, antes de expandir. Assim os riscos técnicos aparecem cedo.

### Fase 0: Verificação (semana 1)
- Baixar 1 ano de LEIV, LEPT, ANTR, SINASC, SIM e CNES; inspecionar os campos reais
- Confirmar as fontes de população e malha do IBGE
- Identificar o arquivo `ESPOBR`
- Medir tamanhos e tempos de processamento (cabem no GitHub Actions?)
- **Entrega:** `docs/armadilhas.md` (1ª versão) e decisão de seguir ou ajustar o escopo

### Fase 1: Fatia vertical (semanas 2–4)
- Pipeline completo para **zoonoses** (LEIV, LEPT, ANTR) e **SIM**
- Site Quarto com **Caso 4 (Zoonoses)**: mapa, série, lentes, limites do dado
- Dataset de ML **Óbito por leishmaniose visceral** com ficha e notebook
- Publicação no GitHub Pages + automação mensal
- **Entrega:** link público funcionando, que você mostra a um colega

### Fase 2: Saúde materno-infantil (semanas 5–7)
- SINASC + SINAN sífilis
- **Caso 1 (Sífilis congênita)**
- Datasets **Baixo peso ao nascer** (classificação + versão de regressão)

### Fase 3: Restante dos casos (semanas 8–10)
- **Casos 2 (Intoxicações), 3 (Material biológico), 5 (Violência)** e **módulo CNES**
- Dataset **Dengue semanal por UF**

### Fase 4: Acabamento e publicação (semanas 11–12)
- Revisão das lentes por docentes de cada área
- Gabaritos do professor, exportação em PDF
- Publicação no OpenML; release v1.0 com DOI no Zenodo
- Página "Como citar" e "Como usar em aula"

### Fase 5: Piloto e artigos (semestre seguinte)
- Uso em pelo menos uma disciplina de saúde e uma de dados/IA
- Coleta de avaliação (**requer aprovação no CEP antes**)
- Artigos: data paper (datasets) e relato de experiência (ensino)

---

## 5. Divisão de trabalho

| Quem | O quê |
|---|---|
| **Claude** | Pipeline, site, datasets, notebooks, validação, rascunho dos textos e das perguntas |
| **Você** | Validar conteúdo, escolher a ordem dos casos, recrutar docentes revisores, piloto, CEP, conta GitHub |
| **Docentes revisores** | Revisar as lentes da sua profissão (1 por área) |

---

## 6. Riscos

| Risco | Mitigação |
|---|---|
| DATASUS fora do ar ou mudança de formato | Cache dos arquivos brutos; versões congeladas no Zenodo |
| Pipeline estoura o tempo do GitHub Actions | Medir na Fase 0; processar só os anos novos (incremental) |
| Números divergem do TabNet | Testes automáticos de validação; divergências documentadas |
| Conteúdo de uma área fica raso | Revisão obrigatória por docente da área antes do piloto |
| Reidentificação nos datasets de ML | Regras da seção 3.6; revisão antes de publicar no OpenML |

---

## 7. Decisões pendentes

1. Nome do projeto
2. Conta/organização no GitHub onde ficará o repositório
3. Disciplina(s) do piloto (define a ordem dos casos; hoje a Fase 1 começa por Zoonoses)
4. Docentes revisores por área
5. Coautores e afiliação institucional (para Zenodo e artigos)

---

## 8. Situação em 2026-11-12

### Decisões já tomadas

| Decisão | Resultado |
|---|---|
| Nome | **EpiDados** (pacote Python `epidados`, comando `uv run epidados`) |
| Repositório | https://github.com/LaBiOmicS/epidados, **público, com tudo** (inclusive `professor/`) |
| Site | https://labiomics.github.io/epidados (GitHub Pages via Actions) |
| MCP | **Adiado.** Os CSVs publicados no Pages já servem de "API" quando for retomado |
| Licenças | Código MIT; textos e dados CC BY 4.0 (`LICENSE`) |

### Fases 0 e 1 concluídas (fatia vertical)

- **Pipeline** (`src/epidados/`): SINAN (LEIV, LEPT, ANTR, 2007–2026) + IBGE (municípios, população anual, malhas)
- **Validação**: casos confirmados de LEIV e LEPT **idênticos ao TabNet** em todos os anos; 9 testes em `tests/`
- **Site**: caso *Zoonoses e Saúde Única* (mapas, séries, perfis, lentes de vet/med/enf/farm), Metodologia, Dados para IA
- **Dataset de IA**: óbito por leishmaniose visceral (45 mil casos), versão mini, ficha técnica, notebook com botão do Colab
- **Roteiro do professor**: `professor/gabarito-zoonoses.qmd` → PDF via Typst (`cd professor && uv run quarto render gabarito-zoonoses.qmd`)
- **Automação**: `.github/workflows/publicar.yml` (todo dia 5, push na `main` e manual)

Mudança de rumo registrada: os dados de 2007–2025 **não** mostram a leishmaniose migrando para o Sudeste. A história real é "menos casos, mais mortes" (casos em adultos e coinfecção por HIV).

Verificar na retomada: se a **primeira execução do workflow** (run 43128906461) publicou o site sem erro.

---

## 9. Como retomar

```bash
cd /home/dayhoff/workdir/informatics/mcp/vet
uv sync --all-groups
uv run epidados                 # usa o cache local; só baixa o que mudou no FTP
uv run pytest -q
uv run quarto preview site
```

Para um agravo novo do SINAN: acrescentar em `config.py` (colunas), `codigos.py` (rótulos), `agregar.py` (saídas) e os totais do TabNet em `tests/test_validacao.py`. O TabNet pode ser consultado por POST em `tabnet.datasus.gov.br/cgi/tabcgi.exe?sinannet/cnv/<def>.def` (ver o histórico da Fase 1).

---

## 10. Próximas fases (detalhadas)

### Antes da Fase 2: preparar o pipeline para volumes grandes

As próximas bases são muito maiores que as da Fase 1 (medido no FTP em 2026-11-12):

| Base | Tamanho (.dbc) | Observação |
|---|---|---|
| SINAN dengue (DENG) | ~1,1 GB | 2024 tem milhões de registros |
| SINASC (DNRES, todas as UFs e anos) | ~6,6 GB | 1 arquivo por UF e ano; SP ≈ 25 MB/ano |
| SINAN violência (VIOL) | ~330 MB | Só agregados, nunca individual |
| SINAN intoxicação (IEXO) | ~210 MB | |
| CNES (PF, profissionais) | grande | 1 arquivo por UF e **mês**; usar uma competência por ano |

O `dbfread` converte cerca de 12 mil linhas/s: a dengue sozinha levaria mais de uma hora. Tarefas:

1. **Leitor de DBF rápido**: DBF tem registros de largura fixa; ler com `numpy.frombuffer` só as colunas necessárias (meta: 10× mais rápido). Manter `dbfread` como referência nos testes.
2. **Cache do Actions**: o pipeline já pula arquivos convertidos pelo `.meta` sem baixar de novo, então guardar só `cache/parquet` e `cache/raw/ibge` no cache (limite de 10 GB por repositório).
3. **Conversão em paralelo** (vários arquivos ao mesmo tempo; o runner tem 4 núcleos).
4. **Medir** o tempo total no Actions; o `timeout-minutes: 180` pode precisar subir ou a primeira carga ser feita por partes.

### Fase 2: Saúde materno-infantil

- **Dados**: SINASC (`SINASC/1996_/Dados/DNRES/DN<UF><ANO>.dbc`), SINAN sífilis em gestante (SIFG) e congênita (SIFC), SIM (óbitos infantis, se couber).
- **Atenção**: SIFG, SIFC e SIFA só existem como **preliminares** no FTP (nenhum ano final). O site deve deixar isso explícito.
- **Caso 1, Sífilis congênita**: lentes de Med, Farm, Enf, Odonto. Ganchos: falhas de pré-natal, desabastecimento de penicilina benzatina em meados dos anos 2010 (confirmar datas em fonte oficial antes de afirmar), manifestações orais.
- **Datasets de IA**: baixo peso ao nascer (classificação) e peso ao nascer (regressão). Armadilha didática: semanas de gestação "entregam" a resposta (vazamento).
- **Validação**: nascidos vivos por UF e ano contra o TabNet do SINASC.

### Fase 3: Demais casos

- **Caso 2, Intoxicações** (IEXO + SIM): Vet, Med, Farm, Enf. Agentes (medicamentos, agrotóxicos, raticidas), circunstância, evolução.
- **Caso 3, Acidentes com material biológico** (ACBI + CNES): Med, Farm, Enf, Odonto. Categoria profissional exposta, tipo de exposição, profilaxia.
- **Caso 5, Violência** (VIOL + SIM): Med, Enf, Odonto. **Somente agregados**; revisar com cuidado ético.
- **Módulo transversal CNES**: profissionais do SUS por categoria e município ("Onde estão os profissionais?").
- **Dataset de IA**: dengue semanal por UF (séries temporais).
- **Odontologia** ainda não tem lente no caso de zoonoses: ela entra nos casos 1, 3 e 5.

### Fase 4: Acabamento e publicação

- Revisão das lentes por um docente de cada área
- Publicar os datasets no **OpenML** (`openml-python`; exige chave de API da conta)
- Ligar o repositório ao **Zenodo** e criar a release v1.0 (DOI)
- Página "Como usar em aula" e "Como citar" com o DOI
- Testar o notebook no Colab de verdade (pandas 2.x)

### Fase 5: Piloto e artigos

- Uso em uma disciplina de saúde e uma de dados/IA
- **CEP antes** de qualquer coleta de avaliação com alunos
- Artigos: data paper (datasets) e relato de experiência (ensino)

### Depois: MCP

Retomar quando o site estiver estável. O MCP leria os CSVs publicados em `labiomics.github.io/epidados/dados/`.

---

## 11. Pendências técnicas conhecidas

- O SIM ainda não é usado (o plano original previa óbitos do SIM no caso de zoonoses; hoje a letalidade vem da evolução no SINAN).
- O arquivo `ESPOBR` do SINAN continua sem identificação (talvez esporotricose).
- A página de zoonoses carrega cerca de 10 MB de dados (malha municipal de 3 MB + CSVs). Avaliar TopoJSON e arquivos por agravo se ficar lenta.
- Armadilhas do site, já resolvidas, que voltarão nos novos casos:
  - `${...}` em texto ou HTML do Quarto vira fórmula matemática: usar células `{ojs}` com `md` ou `html`;
  - malhas do IBGE precisam de reorientação dos polígonos para o d3 (`ibge._orientar_para_d3`);
  - no pandas 3, colunas de texto não são `object`: usar `select_dtypes(exclude="number")`;
  - antes de publicar, verificar as páginas com `scripts/verificar_site.js` (instruções no cabeçalho do arquivo). Neste computador há um Chromium em `~/.cache/ms-playwright/chromium_headless_shell-1254/`.

## 12. Decisões ainda pendentes

1. Disciplina(s) do piloto
2. Docentes revisores por área
3. Coautores e afiliação (Zenodo e artigos)
4. Se o roteiro do professor continua público (hoje está no repositório, por decisão de 2026-11-12)
