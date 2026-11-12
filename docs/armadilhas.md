# Armadilhas dos dados e decisões de tratamento

Registro do que foi medido nos dados reais. Atualize sempre que uma decisão mudar.

## Validação (2026-11-12)

Casos confirmados por ano de notificação, comparados com o TabNet:

- Leishmaniose visceral 2007–2025: **idêntico** em todos os anos (total 58.794).
- Leptospirose 2007–2026: **idêntico** em todos os anos (total 69.231, incluindo preliminares).

Ao atribuir os casos ao município de residência, perdem-se de 0 a 4 casos por ano: pessoas que moram fora do Brasil ou com código de município inválido. Por isso os totais do site ficam ligeiramente abaixo do TabNet.

## SINAN

| Armadilha | O que fazemos |
|---|---|
| Arquivos `.dbc` (DBF compactado) | `pyreaddbc.dbc2dbf` + `dbfread`, convertidos para Parquet |
| Fichas mudam entre anos | Lista fixa de colunas por agravo; colunas ausentes num ano ficam nulas e são registradas no log |
| Antes de 2007 o sistema era outro (SINAN Windows) | Usamos só de 2007 em diante |
| `NU_IDADE_N` codificado: 1º dígito é a unidade (1 hora, 2 dia, 3 mês, 4 ano) | Convertido para anos; menores de 1 ano = 0 |
| Código de município com 6 dígitos | Ligado ao código IBGE de 7 dígitos pelos 6 primeiros |
| `NU_ANO` vazio em alguns registros | O ano vem do nome do arquivo (ano de notificação), como no TabNet |
| `DT_SIN_PRI` às vezes absurda | Para séries mensais: usada se cair no ano do arquivo ou no anterior; senão, `DT_NOTIFIC` |
| Mesmo ano em `FINAIS` e `PRELIM` | Usamos o final |
| Preliminares mudam a cada extração | Marcados como `preliminar` em todas as saídas |
| `NDUPLIC_N` (duplicidade) quase sempre vazio | Não deduplicamos; o TabNet também não |

### Códigos verificados

- **Leishmaniose visceral, `EVOLUCAO`**: 1 cura, 2 abandono, 3 óbito por LV, 4 óbito por outras causas, 5 transferência, 6 mudança de diagnóstico. Letalidade de 2023 (148/1.720 = 8,6%) coerente com o Ministério.
- **Leptospirose, `EVOLUCAO`**: 1 cura, 2 óbito por leptospirose, 3 óbito por outras causas, 9 ignorado.
- **Atendimento antirrábico, `ANIMAL`**: 1 cão, 2 gato, 3 morcego, 4 primata, 5 raposa, 6 herbívoro doméstico, 7 outro (cão = 78% em 2023).
- **Atendimento antirrábico, `TRAT_ATUAL`**: 1 pré-exposição, 2 dispensa, 3 observação do animal, 4 observação + vacina, 5 vacina, 6 soro + vacina, 7 reexposição.

## IBGE

| Armadilha | O que fazemos |
|---|---|
| SIDRA limita 100 mil valores por consulta | Uma consulta por ano |
| Tabela 6579 não tem 2007, 2010, 2022 e 2023 | 2010: Censo (tabela 202). 2022: Censo (tabela 4709). 2007 e 2023: interpolação linear |
| Censo 2022 ficou cerca de 10 milhões abaixo da estimativa de 2021 | Documentado no site; a incidência "pula" entre 2021 e 2022 |
| Municípios criados depois de 2007 | Ficam sem população nos anos anteriores |

## Privacidade

- Tabelas de perfil: células com 1 a 4 casos são suprimidas.
- Datasets de IA: sem município, UF ou datas; idade limitada a 90.
- Violência e HIV nunca em nível individual.
