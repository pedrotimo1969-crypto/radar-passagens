# 🌴 Radar de passagens · Punta Cana 2027

Todo dia às 7h busca no Google Flights o preço das duas opções de data
(19–23/jul e 26–30/jul de 2027) para 6 pessoas, guarda o histórico,
atualiza a página da família e manda um email. Para sozinho depois da viagem.

## O que tem na página
Melhor preço do dia, comparação das duas datas, gráfico da evolução, oscilações
(mínimo, máximo, quedas), previsão para 7 dias, melhores voos (marcando os que
chegam cedinho e voltam à noite) e um resumo geral.

## Ajustes
Tudo em `config.toml`: aeroporto de saída, datas, nº de pessoas, horários e metas
(por pessoa: alerta R$ 4.000, bom R$ 4.500, ok R$ 5.000).

## Configuração no GitHub (uma vez só)
Em **Settings → Secrets and variables → Actions → New repository secret**:
| Secret | O que é |
|---|---|
| `SERPAPI_KEY` | chave grátis de serpapi.com |
| `EMAIL_USUARIO` | Gmail que vai enviar (ex.: o seu) |
| `EMAIL_SENHA_APP` | "senha de app" do Gmail (myaccount.google.com/apppasswords) |
| `EMAIL_DESTINO` | quem recebe (pode ser vários, separados por vírgula) |

E em **Settings → Pages → Source: GitHub Actions**. Depois, em **Actions → Radar diário → Run workflow** para rodar a primeira vez.

## Rodar no computador
```bash
python buscar.py --demo 40   # dados fictícios, só para ver o visual (abre site/index.html)
SERPAPI_KEY=xxx python buscar.py --sem-email
```
Python 3.11+, sem bibliotecas extras.

## Arquivos
- `buscar.py` busca e orquestra · `analise.py` oscilações e previsão
- `site_relatorio.py` página · `email_diario.py` email · `dados/historico.json` histórico
