# Plano — Buscador de Vagas na nuvem (GitHub Actions + Pages)

Aprovado por Ygor em 2026-09-10 (Processo Normal; vencedor: GitHub Actions + Pages, link público grátis).

## Arquitetura
- **Agendamento + execução:** GitHub Actions (cron 1x/dia + botão manual). Roda `python buscar_vagas.py`.
- **Chaves:** GitHub Secrets `ADZUNA_APP_ID` e `ADZUNA_APP_KEY`. O workflow escreve um `.env` efêmero no runner a partir dos secrets (o script lê `.env` via `ler_env`); nunca commitado.
- **Hospedagem:** GitHub Pages servindo a pasta `site/` (link fixo público).
- Repo PÚBLICO (Pages grátis exige público). `.env` no `.gitignore`.

## Etapas (MVP, uma por vez)
1. **E1** — `git init` + `.gitignore` (ignora `.env`, `__pycache__/`, `*.xlsx`) + commit inicial (sem `.env`).
2. **E2** — Criar repo público no GitHub (kenobii/buscador-vagas) e `git push`.
3. **E3** — Guardar as 2 chaves como GitHub Secrets (lidas do `.env` local; não passam pelo chat).
4. **E4** — Criar `.github/workflows/atualiza-vagas.yml`: cron diário 12:00 UTC (09:00 BRT) + `workflow_dispatch`; monta `.env` dos secrets; instala `requests openpyxl`; roda o script; publica `site/` no Pages (`upload-pages-artifact` + `deploy-pages`).
5. **E5** — Ligar o GitHub Pages (source = GitHub Actions).
6. **E6 (prova)** — Disparar o workflow na mão, aguardar verde, abrir o link e confirmar as vagas.

## Riscos conhecidos (do juiz)
- Cron do Actions pausa se o repo ficar 60 dias sem atividade (1 clique reativa).
- Código fica visível (repo público); chaves NÃO (ficam nos Secrets).
- Cron pode atrasar minutos/horas — irrelevante para 1x/dia.
