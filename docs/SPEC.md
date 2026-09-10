# SPEC — Buscador Central de Vagas (Fase 2)

**Objetivo:** reunir, de forma LEGAL, o máximo de vagas de Analista/Coordenador
Administrativo em Brasília-DF; pontuar contra o currículo do Ygor; salvar Excel
ordenado. Iniciante, Windows, Python, rodar 1x/dia.

**Abordagem escolhida (B):** buscador em 3 camadas legais, entregue em 2 ondas.
Decidido via Processo Normal (Fable+Opus+Qwen+Codex; Gemini juiz) em 2026-09-10.

## Arquitetura (KISS)
- 1 função por fonte → devolve vaga no formato comum → merge → dedupe → pontua → Excel.
- Fontes degradam com elegância: sem chave, a fonte é pulada (não quebra).
- Excel com 2 abas: **Vagas** (automáticas, ordenadas por nota) e **Links pra clicar**
  (busca pronta e filtrada nos grandes, pra clique manual — sem robô).

## Camadas
1. **Automático e limpo:** Adzuna (feito) + Jooble (novo, opcional por chave).
2. **Grandes (LinkedIn/Indeed/Catho/Gupy):** links de busca já filtrados (cargo+Brasília)
   numa aba separada. Zero scraping.
3. **Pontuação + Excel** (reusa o que já existe).

## Onda 1 — MVP (agora)
- **E1** Refatorar `buscar_vagas.py` para arquitetura multi-fonte (Adzuna vira 1 módulo
  de fonte; não quebrar o que já funciona). Provar com `--demo`.
- **E2** Adicionar fonte **Jooble** (opcional por chave `JOOBLE_API_KEY`; pula sem chave).
- **E3** Adicionar aba **"Links pra clicar"** (LinkedIn/Indeed/Catho/Gupy, URLs filtradas).
- **E4** Atualizar guia HTML (2 chaves grátis: Adzuna + Jooble; explicar a aba de links).
  Prova final rodando `--demo` ponta a ponta.
- **E5** (com as chaves do Ygor) rodar de verdade e provar com vagas reais.

## Onda 2 — depois (cobertura+)
- Gupy público (portais de empresas) + leitura de JSON-LD `JobPosting` de páginas de
  carreira, guiado por uma lista `empresas.csv` de empresas que atuam em Brasília.
- Delays gentis, headers honestos, tratamento de erro por fonte.

## Riscos (do juiz)
- Páginas/rotas mudam → manutenção pontual (mitigado: onda 2 isolada por fonte).
- Rate-limiting → delays + headers honestos.
- Cobertura local depende de `empresas.csv` bem curada (onda 2).

## Fora de escopo agora
- Scraping de sites que proíbem robô. Banco de dados. Servidor. Painel (Fase 3).
