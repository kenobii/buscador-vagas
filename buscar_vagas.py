# -*- coding: utf-8 -*-
"""
BUSCADOR CENTRAL DE VAGAS - Fase 2 (Onda 1)
===========================================
O que ele faz, em portugues simples:
  1. Le o seu curriculo mestre (curriculo_mestre.json) pra saber o seu perfil.
  2. Junta vagas de Analista/Coordenador Administrativo em Brasilia-DF de
     fontes LEGAIS (APIs oficiais Adzuna e Jooble).
  3. Da uma NOTA de 0 a 100 pra cada vaga e ordena da melhor pra pior.
  4. Gera uma PAGINA (site/index.html) com:
       - as vagas em cartoes, cada uma com botao "Candidatar-se";
       - uma secao "Buscar nos grandes" com buscas prontas e filtradas
         (LinkedIn, Indeed, Catho, Gupy, Google) pra clique manual.
  Essa pagina e publicada no Vercel -> vira um link que voce abre de qualquer lugar.

Como rodar:
    python buscar_vagas.py            (busca de verdade; precisa de chave Adzuna)
    python buscar_vagas.py --demo     (teste com vagas de exemplo, sem chave)
"""

import sys
import os
import json
import time
import html
import argparse
import datetime
import unicodedata
import re
import urllib.parse
from pathlib import Path

try:
    import requests
except ImportError:
    print("Falta a biblioteca 'requests'. No terminal rode:  pip install requests")
    sys.exit(1)


# =============================================================================
# CONFIGURACAO
# =============================================================================
PAIS = "br"
LOCAL = "Brasilia"
CIDADE_LINK = "Brasília"
DIAS_MAX = 45
POR_PAGINA = 50

TERMOS_BUSCA = [
    "analista administrativo", "coordenador administrativo",
    "assistente administrativo", "auxiliar administrativo",
    "gerente administrativo", "administrativo",
]

PALAVRAS_CURADAS = [
    "estoque", "compras", "nota fiscal", "notas fiscais", "fluxograma",
    "coordenacao", "coordenar", "equipe", "excel", "inventario", "crm",
    "cliente", "clientes", "vendas", "sdr", "processos", "financeiro",
    "folha de ponto", "logistica", "pedidos", "fornecedor", "fornecedores",
    "planilha", "planilhas", "relatorio", "relatorios", "gestao",
    "almoxarifado", "faturamento", "contas a pagar", "contas a receber",
    "rotinas administrativas", "erp", "controle", "organizacao",
    "atendimento", "suprimentos", "recebimento", "administracao",
]

CIDADE_TERMOS = ["brasilia", "df", "distrito federal", "sobradinho", "gama",
                 "taguatinga", "ceilandia", "aguas claras", "guara", "entorno"]

PASTA_SITE = "site"           # o que o Vercel publica
ARQ_SITE = "index.html"
ARQ_DEMO = "preview_demo.html"


# =============================================================================
# TEXTO
# =============================================================================
def normalizar(txt):
    if not txt:
        return ""
    txt = unicodedata.normalize("NFKD", str(txt))
    txt = "".join(c for c in txt if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", txt.lower()).strip()


def limpar_html(txt):
    if not txt:
        return ""
    txt = re.sub(r"<[^>]+>", "", str(txt))
    txt = (txt.replace("&amp;", "&").replace("&lt;", "<")
              .replace("&gt;", ">").replace("&nbsp;", " ").replace("&quot;", '"'))
    return re.sub(r"\s+", " ", txt).strip()


# =============================================================================
# PERFIL / .env
# =============================================================================
def carregar_perfil(caminho):
    with open(caminho, encoding="utf-8") as f:
        cv = json.load(f)
    objetivo = cv.get("objetivo", "")
    cargos_alvo = [normalizar(p) for p in re.split(r"[/,;]", objetivo) if p.strip()]
    palavras = set(normalizar(p) for p in PALAVRAS_CURADAS)
    for hab in cv.get("habilidades", []):
        palavras.add(normalizar(hab))
    return {
        "cargos_alvo": cargos_alvo or ["analista administrativo"],
        "palavras_chave": {p for p in palavras if p},
        "cidade_termos": CIDADE_TERMOS,
    }


def ler_env(caminho):
    dados = {}
    if caminho.exists():
        for linha in caminho.read_text(encoding="utf-8").splitlines():
            linha = linha.strip()
            if linha and not linha.startswith("#") and "=" in linha:
                chave, _, valor = linha.partition("=")
                dados[chave.strip()] = valor.strip()
    return dados


# =============================================================================
# FORMATO COMUM DE VAGA
# =============================================================================
def vaga_vazia():
    return {"titulo": "", "empresa": "Não informado", "local": "", "link": "",
            "descricao": "", "data_fmt": "-", "dias": None, "salary_min": None,
            "salary_max": None, "estimado": False, "salario_txt": "", "fonte": ""}


def _data_e_dias(iso):
    if not iso:
        return "-", None
    try:
        dt = datetime.datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
        return dt.strftime("%d/%m/%Y"), (datetime.datetime.now(datetime.timezone.utc) - dt).days
    except ValueError:
        return "-", None


# =============================================================================
# FONTE 1: ADZUNA
# =============================================================================
def _busca_adzuna(app_id, app_key, termo):
    url = "https://api.adzuna.com/v1/api/jobs/%s/search/1" % PAIS
    params = {"app_id": app_id, "app_key": app_key, "results_per_page": POR_PAGINA,
              "what": termo, "where": LOCAL, "max_days_old": DIAS_MAX, "sort_by": "date"}
    r = requests.get(url, params=params, timeout=25)
    if r.status_code == 401:
        raise RuntimeError("chave Adzuna inválida (401) - confira o .env")
    if r.status_code == 429:
        raise RuntimeError("limite de uso Adzuna (429) - tente mais tarde")
    r.raise_for_status()
    return r.json().get("results", [])


def _normaliza_adzuna(j):
    v = vaga_vazia()
    v["titulo"] = limpar_html(j.get("title", ""))
    v["empresa"] = limpar_html((j.get("company") or {}).get("display_name", "")) or "Não informado"
    v["local"] = limpar_html((j.get("location") or {}).get("display_name", ""))
    v["link"] = j.get("redirect_url", "")
    v["descricao"] = limpar_html(j.get("description", ""))
    v["data_fmt"], v["dias"] = _data_e_dias(j.get("created"))
    v["salary_min"] = j.get("salary_min")
    v["salary_max"] = j.get("salary_max")
    v["estimado"] = j.get("salary_is_predicted") in (1, "1", True)
    v["fonte"] = "Adzuna"
    return v


def fonte_adzuna(perfil, env):
    app_id, app_key = env.get("ADZUNA_APP_ID"), env.get("ADZUNA_APP_KEY")
    if not app_id or not app_key:
        print("  - Adzuna: sem chave, pulando")
        return []
    vagas = []
    for termo in TERMOS_BUSCA:
        try:
            achou = _busca_adzuna(app_id, app_key, termo)
            vagas += [_normaliza_adzuna(j) for j in achou]
            print("    Adzuna '%s': %d" % (termo, len(achou)))
            time.sleep(1)
        except Exception as e:
            print("    ! Adzuna '%s': %s" % (termo, e))
    return vagas


# =============================================================================
# FONTE 2: JOOBLE (opcional)
# =============================================================================
def _normaliza_jooble(j):
    v = vaga_vazia()
    v["titulo"] = limpar_html(j.get("title", ""))
    v["empresa"] = limpar_html(j.get("company", "")) or "Não informado"
    v["local"] = limpar_html(j.get("location", ""))
    v["link"] = j.get("link", "")
    v["descricao"] = limpar_html(j.get("snippet", ""))
    v["data_fmt"], v["dias"] = _data_e_dias(j.get("updated"))
    v["salario_txt"] = limpar_html(j.get("salary", "")) or ""
    v["fonte"] = "Jooble"
    return v


def fonte_jooble(perfil, env):
    key = env.get("JOOBLE_API_KEY")
    if not key:
        print("  - Jooble: sem chave, pulando (opcional)")
        return []
    url = "https://br.jooble.org/api/" + key
    vagas = []
    for termo in TERMOS_BUSCA[:4]:
        try:
            r = requests.post(url, json={"keywords": termo, "location": LOCAL}, timeout=25)
            r.raise_for_status()
            achou = r.json().get("jobs", [])
            vagas += [_normaliza_jooble(j) for j in achou]
            print("    Jooble '%s': %d" % (termo, len(achou)))
            time.sleep(1)
        except Exception as e:
            print("    ! Jooble '%s': %s" % (termo, e))
    return vagas


FONTES = [("Adzuna", fonte_adzuna), ("Jooble", fonte_jooble)]


# =============================================================================
# LINKS DOS GRANDES
# =============================================================================
def montar_links(perfil):
    enc = urllib.parse.quote_plus
    linhas = []
    for cargo in perfil["cargos_alvo"]:
        slug = cargo.replace(" ", "-")
        sites = [
            ("Google Empregos", "https://www.google.com/search?ibp=htl;jobs&q=" + enc(cargo + " " + CIDADE_LINK)),
            ("LinkedIn", "https://www.linkedin.com/jobs/search/?keywords=" + enc(cargo) + "&location=" + enc(CIDADE_LINK + ", Brasil")),
            ("Indeed", "https://br.indeed.com/jobs?q=" + enc(cargo) + "&l=" + enc(CIDADE_LINK)),
            ("Catho", "https://www.catho.com.br/vagas/" + slug + "/brasilia-df/"),
            ("Gupy", "https://portal.gupy.io/job-search/term=" + enc(cargo)),
        ]
        for site, url in sites:
            linhas.append({"cargo": cargo.title(), "site": site, "url": url})
    return linhas


# =============================================================================
# SALARIO / NOTA
# =============================================================================
def formatar_salario(v):
    if v.get("salario_txt"):
        return v["salario_txt"]
    lo, hi = v.get("salary_min"), v.get("salary_max")
    if not lo and not hi:
        return "não informado"

    def real(x):
        return "R$ " + format(int(x), ",d").replace(",", ".")

    if lo and hi and int(lo) != int(hi):
        s = "%s a %s" % (real(lo), real(hi))
    elif lo:
        s = "a partir de %s" % real(lo)
    else:
        s = "até %s" % real(hi)
    if v.get("estimado"):
        s += " (estimado)"
    return s


def pontuar(vaga, perfil):
    titulo = normalizar(vaga["titulo"])
    local = normalizar(vaga["local"])
    texto = titulo + " " + normalizar(vaga["descricao"])
    nota, motivos = 0, []
    ganho = 0
    for cargo in perfil["cargos_alvo"]:
        if cargo and cargo in titulo:
            ganho = 40
            motivos.append("cargo-alvo no título")
            break
    if ganho == 0:
        for termo in ["assistente administrativo", "auxiliar administrativo",
                      "administrativo", "administracao"]:
            if termo in titulo:
                ganho = 22
                motivos.append("área administrativa no título")
                break
    nota += ganho
    if any(c in local for c in perfil["cidade_termos"]):
        nota += 25
        motivos.append("em Brasília/DF")
    achadas = sorted({kw for kw in perfil["palavras_chave"] if kw and kw in texto})
    nota += min(len(achadas) * 4, 25)
    if achadas:
        motivos.append("combina em: " + ", ".join(achadas[:6]))
    dias = vaga.get("dias")
    if dias is not None:
        if dias <= 7:
            nota += 10
            motivos.append("publicada essa semana")
        elif dias <= 21:
            nota += 5
    return min(nota, 100), " · ".join(motivos)


# =============================================================================
# GERAR A PAGINA HTML
# =============================================================================
def _cor_nota(n):
    if n >= 70:
        return "#37c07a"
    if n >= 40:
        return "#e7b84b"
    return "#e88"


def _card_vaga(v):
    e = html.escape
    cor = _cor_nota(v["nota"])
    link = v.get("link") or ""
    if link:
        botao = ('<a class="apply" href="%s" target="_blank" rel="noopener">Candidatar-se &rarr;</a>'
                 % e(link))
    else:
        botao = '<span class="apply off">link indisponível</span>'
    return """
    <article class="card">
      <div class="top">
        <span class="nota" style="background:%s">%d</span>
        <span class="fonte">%s</span>
      </div>
      <h3>%s</h3>
      <p class="meta">%s &middot; %s</p>
      <p class="meta"><b>Salário:</b> %s &nbsp;|&nbsp; <b>Publicada:</b> %s</p>
      <p class="why">%s</p>
      %s
    </article>""" % (
        cor, v["nota"], e(v["fonte"]), e(v["titulo"]),
        e(v["empresa"]), e(v["local"]) or "local não informado",
        e(v["salario"]), e(v["data_fmt"]),
        e(v["motivos"]) or "-", botao)


def salvar_html(vagas, links, caminho, demo=False):
    e = html.escape
    agora = datetime.datetime.now().strftime("%d/%m/%Y às %H:%M")

    if vagas:
        cards = "\n".join(_card_vaga(v) for v in vagas)
        corpo_vagas = '<div class="grid">%s</div>' % cards
    else:
        corpo_vagas = (
            '<div class="empty">Ainda não há vagas automáticas aqui. '
            'Assim que as chaves da Adzuna forem cadastradas e o buscador rodar, '
            'as vagas aparecem neste espaço. Por enquanto, use os atalhos abaixo. 👇</div>')

    # links agrupados por cargo
    por_cargo = {}
    for l in links:
        por_cargo.setdefault(l["cargo"], []).append(l)
    blocos = []
    for cargo, itens in por_cargo.items():
        botoes = "".join(
            '<a class="big" href="%s" target="_blank" rel="noopener">%s</a>'
            % (e(i["url"]), e(i["site"])) for i in itens)
        blocos.append('<div class="grupo"><h4>%s</h4><div class="bigs">%s</div></div>'
                      % (e(cargo), botoes))
    corpo_links = "\n".join(blocos)

    aviso_demo = ('<div class="demo">MODO DEMONSTRAÇÃO — vagas de exemplo</div>'
                  if demo else "")

    pagina = """<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Minhas Vagas — Administrativo · Brasília-DF</title>
<style>
  :root{--bg:#0f1512;--card:#161d19;--bd:#26302a;--fg:#e8efe9;--mut:#9fb0a7;--grn:#37c07a;--blue:#5aa2e6}
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.55 system-ui,"Segoe UI",Arial,sans-serif}
  .wrap{max-width:900px;margin:0 auto;padding:28px 16px 60px}
  h1{font-size:26px;margin:0 0 2px}
  .sub{color:var(--mut);margin:0 0 6px}
  .demo{display:inline-block;background:rgba(231,184,75,.18);color:#e7b84b;font-weight:600;
    font-size:13px;padding:4px 12px;border-radius:999px;margin:8px 0}
  h2{font-size:19px;margin:28px 0 12px;border-bottom:1px solid var(--bd);padding-bottom:8px}
  .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(270px,1fr));gap:14px}
  .card{background:var(--card);border:1px solid var(--bd);border-radius:14px;padding:16px;
    display:flex;flex-direction:column}
  .top{display:flex;align-items:center;gap:8px;margin-bottom:6px}
  .nota{color:#08120b;font-weight:800;min-width:34px;height:28px;border-radius:8px;
    display:inline-grid;place-items:center;font-size:14px}
  .fonte{color:var(--mut);font-size:12px;border:1px solid var(--bd);border-radius:999px;padding:1px 8px}
  .card h3{font-size:16px;margin:2px 0 6px;line-height:1.3}
  .meta{color:var(--mut);font-size:13px;margin:2px 0}
  .why{color:#cfe9db;font-size:13px;margin:8px 0 12px;flex:1}
  .apply{margin-top:auto;text-align:center;background:var(--grn);color:#08120b;font-weight:700;
    text-decoration:none;padding:10px;border-radius:10px}
  .apply.off{background:#333;color:#999;font-weight:500}
  .empty{background:var(--card);border:1px dashed var(--bd);border-radius:14px;padding:22px;color:var(--mut)}
  .grupo{margin:0 0 16px}
  .grupo h4{margin:0 0 8px;font-size:15px;color:var(--fg)}
  .bigs{display:flex;flex-wrap:wrap;gap:8px}
  .big{background:#0c110e;border:1px solid var(--bd);color:var(--blue);text-decoration:none;
    padding:8px 14px;border-radius:10px;font-size:14px}
  .big:hover{border-color:var(--grn)}
  .foot{color:var(--mut);font-size:12px;margin-top:34px;text-align:center}
  .note{color:var(--mut);font-size:13px;margin:0 0 4px}
  .atualizar{margin:12px 0 4px;display:flex;align-items:center;gap:10px;flex-wrap:wrap}
  #btnAtualizar{background:var(--grn);color:#08120b;font-weight:700;border:0;border-radius:10px;
    padding:10px 16px;font-size:14px;cursor:pointer}
  #btnAtualizar:disabled{opacity:.6;cursor:default}
  .stAt{color:var(--mut);font-size:13px}
</style>
</head>
<body>
<div class="wrap">
  <h1>Minhas Vagas</h1>
  <p class="sub">Analista / Coordenador Administrativo &middot; Brasília-DF</p>
  <div class="atualizar">
    <button id="btnAtualizar" onclick="atualizarAgora()">🔄 Atualizar agora</button>
    <span id="statusAtualizar" class="stAt"></span>
  </div>
  %s
  <p class="note">Atualizado em %s &middot; %d vaga(s) encontrada(s)</p>

  <h2>Vagas pra você</h2>
  %s

  <h2>Buscar direto nos grandes</h2>
  <p class="note">Nesses sites robô é proibido, então aqui vão buscas já filtradas — é só clicar.</p>
  %s

  <p class="foot">Gerado automaticamente pelo seu buscador de vagas. Cada vez que rodar, esta página é atualizada.</p>
</div>
<script>
async function atualizarAgora(){
  var s=document.getElementById('statusAtualizar');
  var b=document.getElementById('btnAtualizar');
  var senha=prompt('Digite a senha para atualizar as vagas:');
  if(!senha){return;}
  b.disabled=true; s.textContent='Atualizando… leva cerca de 1 minuto.';
  try{
    var r=await fetch('https://buscador-vagas-botao.vercel.app/api/atualizar',{
      method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({senha:senha})});
    if(r.ok){
      s.textContent='Pedido enviado! Recarregue esta página em ~1 minuto para ver as vagas novas.';
    }else if(r.status===401){
      s.textContent='Senha incorreta. Tente de novo.'; b.disabled=false;
    }else{
      s.textContent='Não consegui atualizar agora. Tente mais tarde.'; b.disabled=false;
    }
  }catch(e){
    s.textContent='Sem conexão com o atualizador. Tente mais tarde.'; b.disabled=false;
  }
}
</script>
</body>
</html>""" % (aviso_demo, e(agora), len(vagas), corpo_vagas, corpo_links)

    os.makedirs(os.path.dirname(caminho) or ".", exist_ok=True)
    with open(caminho, "w", encoding="utf-8") as f:
        f.write(pagina)


# =============================================================================
# DEMO
# =============================================================================
def vagas_demo():
    hoje = datetime.datetime.now(datetime.timezone.utc)

    def mk(titulo, empresa, local, desc, dias, smin, smax, est):
        v = vaga_vazia()
        v["titulo"], v["empresa"], v["local"], v["descricao"] = titulo, empresa, local, desc
        v["data_fmt"], v["dias"] = (hoje - datetime.timedelta(days=dias)).strftime("%d/%m/%Y"), dias
        v["salary_min"], v["salary_max"], v["estimado"], v["fonte"] = smin, smax, est, "DEMO"
        v["link"] = "https://exemplo.com/vaga/" + normalizar(titulo).replace(" ", "-")
        return v

    return [
        mk("Analista Administrativo", "Empresa Exemplo Ltda", "Brasília, Distrito Federal",
           "Rotinas administrativas, controle de estoque, compras, notas fiscais e Excel. Coordenação de equipe.",
           1, 3500, 4500, False),
        mk("Assistente Administrativo Financeiro", "Contábil DF", "Taguatinga, Distrito Federal",
           "Contas a pagar, relatórios, atendimento ao cliente e planilhas.",
           12, 2200, None, True),
        mk("Vendedor de Loja", "Loja Qualquer", "Goiânia, Goiás",
           "Vendas no balcão e atendimento.",
           30, None, None, False),
    ]


# =============================================================================
# MAIN
# =============================================================================
def main():
    ap = argparse.ArgumentParser(description="Buscador de vagas administrativas em Brasília-DF")
    ap.add_argument("--demo", action="store_true", help="testa com vagas de exemplo, sem chave")
    args = ap.parse_args()

    pasta = Path(__file__).resolve().parent
    # Perfil: usa o curriculo mestre localmente; na nuvem (repo publico) usa
    # perfil_busca.json (so objetivo + habilidades, sem dados pessoais).
    arq_perfil = pasta / "curriculo_mestre.json"
    if not arq_perfil.exists():
        arq_perfil = pasta / "perfil_busca.json"
    perfil = carregar_perfil(arq_perfil)

    if args.demo:
        print(">> MODO DEMONSTRACAO (vagas de exemplo)\n")
        brutas = vagas_demo()
        saida = pasta / ARQ_DEMO
    else:
        env = ler_env(pasta / ".env")
        print("Buscando vagas nas fontes oficiais...")
        brutas = []
        for nome, fn in FONTES:
            try:
                brutas += fn(perfil, env)
            except Exception as e:
                print("  ! %s falhou: %s" % (nome, e))
        saida = pasta / PASTA_SITE / ARQ_SITE

    vistas, unicas = set(), []
    for v in brutas:
        chave = v["link"] or (normalizar(v["titulo"]) + "|" + normalizar(v["empresa"]))
        if chave not in vistas:
            vistas.add(chave)
            unicas.append(v)

    for v in unicas:
        v["nota"], v["motivos"] = pontuar(v, perfil)
        v["salario"] = formatar_salario(v)
    unicas.sort(key=lambda x: x["nota"], reverse=True)

    links = montar_links(perfil)
    salvar_html(unicas, links, str(saida), demo=args.demo)

    if unicas:
        print("\n%d vaga(s). Top 5:" % len(unicas))
        for v in unicas[:5]:
            print("  [%3d] %s - %s (%s) [%s]"
                  % (v["nota"], v["titulo"], v["empresa"], v["local"], v["fonte"]))
    else:
        print("\nNenhuma vaga automática ainda (falta cadastrar as chaves).")
        print("A página já traz os atalhos dos grandes.")
    print("\nPágina gerada em:\n  %s" % saida)


if __name__ == "__main__":
    main()
