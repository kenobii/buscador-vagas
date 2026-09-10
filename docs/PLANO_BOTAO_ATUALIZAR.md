# Plano — Botão "Atualizar agora" (roda na hora)

Escolha do Ygor (2026-09-10): botão que atualiza sem sair da página, com senha (link é público).

## Arquitetura (recomendada — reusa o que ele já tem)
- **Ajudante na nuvem = função serverless na Vercel** (conta kenobii, grátis). Rota `/api/atualizar`.
  - Recebe a senha do botão → confere contra `SENHA` (env var na Vercel).
  - Se OK, chama a API do GitHub (`workflow_dispatch`) usando um **token fino** guardado em `GH_TOKEN` (env var na Vercel) → dispara o workflow `atualiza-vagas.yml`.
  - Retorna CORS liberado só para `https://kenobii.github.io`.
- **Segurança:** nem o token nem a senha ficam na página pública. A página só manda a senha que o Ygor digita; a conferência é no servidor. Token é fino (só Actions:write no repo `buscador-vagas`).
- **Botão:** editar o gerador `buscar_vagas.py` (HTML do `site/index.html`) para incluir
  "🔄 Atualizar agora" → pede a senha → chama `/api/atualizar` → mostra "atualizando… volte em ~1 min".

## Por que Vercel (e não Cloudflare/Railway)
- Ygor já tem conta Vercel; grátis; 1 função só; zero servidor rodando o tempo todo. Menos peças novas.

## Etapas
1. **B1** — Criar o projeto Vercel com a função `/api/atualizar` (Node) + CORS + checagem de senha + dispatch.
2. **B2** — Ygor cria um token fino do GitHub (guio no clique exato); guardo em `GH_TOKEN` na Vercel (via coletor, não passa pelo chat).
3. **B3** — Ygor escolhe uma senha; guardo em `SENHA` na Vercel.
4. **B4** — Deploy da função; anoto a URL.
5. **B5** — Adicionar o botão na página (editar `buscar_vagas.py`), commit/push, rodar o workflow p/ publicar a página com o botão.
6. **B6 (prova)** — Clicar no botão com a senha certa → workflow dispara e página atualiza. Sem senha → recusa.

## O que é do Ygor (2 coisas)
- Criar o token fino do GitHub (passo guiado).
- Escolher a senha.
