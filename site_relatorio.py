"""Página web completa do radar (um arquivo HTML, funciona no celular)."""
from __future__ import annotations

import datetime as dt
import html

from analise import brl

MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
DIAS = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]
CORES = ["var(--c1)", "var(--c2)"]


def dc(iso: str) -> str:
    d = dt.date.fromisoformat(iso[:10])
    return f"{d.day} {MESES[d.month - 1]}"


def dl(d: dt.date) -> str:
    return f"{DIAS[d.weekday()]}, {d.day} de {MESES[d.month - 1]} de {d.year}"


def hhmm(s: str | None) -> str:
    return s[-5:] if s else "—"


def dur(m: int | None) -> str:
    return f"{m // 60}h{m % 60:02d}" if m else "—"


def pct(v: float | None, sinal: bool = True) -> str:
    if v is None:
        return "—"
    return (f"{v:+.1f}%" if sinal else f"{v:.1f}%").replace(".", ",")


def delta_html(a: dict) -> str:
    if a["delta"] is None:
        return '<span class="delta">primeiro dia</span>'
    d = a["delta"]
    c = "desce" if d < 0 else "sobe" if d > 0 else ""
    s = "▼" if d < 0 else "▲" if d > 0 else "＝"
    return f'<span class="delta {c}">{s} {brl(abs(d))} ({pct(abs(a["delta_pct"]), False)}) vs. ontem</span>'


def grafico(pers: list, metas: dict) -> str:
    W, H, PX, PY = 760, 300, 70, 28
    todas = [v for a in pers for _, v in a["serie"]] + [metas["alerta"], metas["ok"]]
    lo, hi = min(todas) * 0.95, max(todas) * 1.03
    datas = sorted({d for a in pers for d, _ in a["serie"]})
    idx = {d: i for i, d in enumerate(datas)}
    n = max(len(datas) - 1, 1)
    x = lambda i: PX + i * (W - PX - 14) / n
    y = lambda v: PY + (hi - v) * (H - 2 * PY) / (hi - lo)
    s = ""
    for k in range(5):
        v = lo + (hi - lo) * k / 4
        rot = f"{v / 1000:.1f}k".replace(".", ",")
        s += (f'<line x1="{PX}" x2="{W - 14}" y1="{y(v):.1f}" y2="{y(v):.1f}" class="g"/>'
              f'<text x="{PX - 10}" y="{y(v) + 4:.1f}" class="eixo" text-anchor="end">{rot}</text>')
    ya = y(metas["alerta"] * (1 + metas.get("margem_alerta_pct", 5) / 100))
    s += f'<rect x="{PX}" y="{ya:.1f}" width="{W - PX - 14}" height="{H - PY - ya:.1f}" class="zona"/>'
    s += f'<text x="{PX + 8}" y="{H - PY - 8}" class="zona-t">zona de alerta</text>'
    for nome, cls in (("bom", "m-bom"), ("ok", "m-ok")):
        s += (f'<line x1="{PX}" x2="{W - 14}" y1="{y(metas[nome]):.1f}" y2="{y(metas[nome]):.1f}" class="{cls}"/>'
              f'<text x="{W - 16}" y="{y(metas[nome]) - 6:.1f}" class="{cls}-t" text-anchor="end">{brl(metas[nome])}</text>')
    passo = max(len(datas) // 6, 1)
    for i in range(0, len(datas), passo):
        s += f'<text x="{x(i):.1f}" y="{H - 6}" class="eixo" text-anchor="middle">{dc(datas[i])}</text>'
    for a, cor in zip(pers, CORES):
        pts = [(x(idx[d]), y(v)) for d, v in a["serie"]]
        s += f'<polyline points="{" ".join(f"{px:.1f},{py:.1f}" for px, py in pts)}" fill="none" stroke="{cor}" class="linha"/>'
        s += f'<circle cx="{pts[-1][0]:.1f}" cy="{pts[-1][1]:.1f}" r="6" fill="{cor}" class="ponto"/>'
    legenda = "".join(f'<span><i style="background:{c}"></i>{html.escape(a["nome"])}</span>' for a, c in zip(pers, CORES))
    return (f'<div class="legenda">{legenda}<span><i class="li-zona"></i>perto de {brl(metas["alerta"])}</span></div>'
            f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Preço por pessoa ao longo do tempo">{s}</svg>')


def card_periodo(a: dict, cor: str, melhor: bool) -> str:
    aviso = "" if a["encaixa"] else '<p class="nota">⚠️ Hoje nenhum voo chega cedinho; mostrando o mais barato.</p>'
    return f'''<article class="card per" style="--cor:{cor}">
  <header><span class="bolinha"></span><h3>{html.escape(a["nome"])}</h3>{'<span class="selo">mais barato hoje</span>' if melhor else ''}</header>
  <div class="pp">{brl(a["hoje"])}<small>/pessoa</small></div>
  <div class="tot">{brl(a["total"])} no total · {delta_html(a)}</div>
  <div class="badge {a["status"]}">{a["titulo"]}</div>
  <dl>
    <div><dt>Menor já visto</dt><dd>{brl(a["min"][1])} <small>{dc(a["min"][0])}</small></dd></div>
    <div><dt>Tendência</dt><dd>{a["tendencia"][1]}</dd></div>
  </dl>{aviso}
</article>'''


def tabela_oscilacoes(pers: list) -> str:
    linhas = [
        ("Menor preço já visto", lambda a: f'{brl(a["min"][1])} <small>({dc(a["min"][0])})</small>'),
        ("Maior preço já visto", lambda a: f'{brl(a["max"][1])} <small>({dc(a["max"][0])})</small>'),
        ("Média dos últimos 7 dias", lambda a: brl(a["media7"])),
        ("Variação em 7 dias", lambda a: pct(a["var7_pct"])),
        ("Maior queda em um dia", lambda a: f'{pct(a["maior_queda"][1])} <small>({dc(a["maior_queda"][0])})</small>' if a["maior_queda"] else "—"),
        ("Sobe e desce diário (média)", lambda a: "±" + pct(a["volatilidade"], False) if a["volatilidade"] else "—"),
        ("Dias na zona de alerta", lambda a: str(a["dias_alerta"])),
    ]
    cab = "".join(f'<th style="color:{c}">{html.escape(a["nome"])}</th>' for a, c in zip(pers, CORES))
    corpo = "".join(f"<tr><td>{r}</td>" + "".join(f"<td>{f(a)}</td>" for a in pers) + "</tr>" for r, f in linhas)
    return f'<div class="tab"><table><thead><tr><th></th>{cab}</tr></thead><tbody>{corpo}</tbody></table></div>'


def previsoes(pers: list, r: dict) -> str:
    cards = ""
    for a, c in zip(pers, CORES):
        lo, hi = a["prev7_faixa"]
        cards += f'''<div class="prev" style="--cor:{c}"><div class="rot">{html.escape(a["nome"])} · daqui a 7 dias</div>
  <div class="prev-v">≈ {brl(a["prev7"])}</div><div class="nota" style="margin:0">provável entre {brl(lo)} e {brl(hi)} · {a["tendencia"][1]}</div></div>'''
    return f'''<div class="prevs">{cards}</div>
<p class="janela">🗓️ {html.escape(r["janela"])}</p>
<p class="nota">Previsão estatística simples, feita com a tendência das últimas 2 semanas. Companhias aéreas mudam preços sem aviso, então use como termômetro, não como garantia.</p>'''


def lista_voos(a: dict, pax: int) -> str:
    itens = ""
    for o in a["opcoes"]:
        esc = "direto" if o["escalas"] == 0 else f'{o["escalas"]} escala' + ("s" if o["escalas"] > 1 else "")
        tag = '<span class="ok-h">✓ chega cedo</span>' if o["encaixa"] else '<span class="no-h">chega tarde</span>'
        itens += f'''<li><div class="v-cia">{html.escape(" + ".join(o["cias"]))} {tag}</div>
  <div class="v-inf">sai {dc(o["saida"])} {hhmm(o["saida"])} → chega {dc(o["chegada"]) if o["chegada"] else ""} {hhmm(o["chegada"])} · {esc} · {dur(o.get("duracao_min"))}</div>
  <div class="v-p">{brl(o["pp"])}<small>{brl(o["total"])} p/ {pax}</small></div></li>'''
    link = f'<a class="btn" href="{html.escape(a["link"])}">Abrir no Google Flights</a>' if a.get("link") else ""
    return f'<div class="voos"><h4>{html.escape(a["nome"])}</h4><ul>{itens}</ul>{link}</div>'


def resumo_geral(cfg: dict, r: dict) -> str:
    pers, m = r["periodos"], r["melhor"]
    frases = []
    if r["alerta"]:
        frases.append(f"<b>Temos alerta!</b> {html.escape(r['alerta'])}. Esse é o tipo de preço que estávamos esperando.")
    if len(pers) == 2:
        outro = [a for a in pers if a is not m][0]
        dif = outro["hoje"] - m["hoje"]
        frases.append(f"Hoje a opção <b>{html.escape(m['nome'])}</b> está {brl(dif)} mais barata por pessoa "
                      f"({brl(dif * cfg['viagem'].get('adultos', 1))} no total) que {html.escape(outro['nome'])}.")
    for a in pers:
        frases.append(f"{html.escape(a['nome'])}: {a['tendencia'][1].lower()}, menor valor visto foi {brl(a['min'][1])} em {dc(a['min'][0])}.")
    frases.append(f"Estamos acompanhando há {r['n_dias']} dia{'s' if r['n_dias'] != 1 else ''}.")
    return "<p>" + "</p><p>".join(frases) + "</p>"


CSS = """
:root{--fundo:#f4f8f7;--papel:#fff;--tinta:#13283a;--suave:#64748b;--linha:#e3eae9;
  --c1:#ff7a45;--c2:#0e9aa7;--verde:#16a34a;--verm:#dc2626;--amar:#d97706;--sol:#ffd166;
  --sombra:0 1px 2px rgba(19,40,58,.05),0 10px 30px rgba(19,40,58,.08)}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--fundo:#0d1820;--papel:#14232d;--tinta:#eef4f6;
  --suave:#94a3b8;--linha:#24343f;--c1:#ff9466;--c2:#3cc6cf;--verde:#4ade80;--verm:#f87171;--amar:#fbbf24;--sombra:none}}
*{box-sizing:border-box}body{margin:0;background:var(--fundo);color:var(--tinta);font:15px/1.55 Inter,system-ui,sans-serif}
.wrap{max-width:860px;margin:0 auto;padding:0 16px 48px}
.topo{background:linear-gradient(160deg,#0e9aa7 0%,#11b5b0 45%,#ffb26b 100%);color:#fff;text-align:center;padding:40px 16px 70px;
  border-radius:0 0 32px 32px;position:relative;overflow:hidden}
.topo:after{content:"🌴";position:absolute;font-size:150px;right:-20px;bottom:-30px;opacity:.18}
.kicker{text-transform:uppercase;letter-spacing:.16em;font-size:12px;opacity:.9}
h1{font:800 clamp(34px,8vw,56px)/1.05 Fraunces,Georgia,serif;margin:8px 0 2px}
.sub{font:italic 600 18px Fraunces,serif;opacity:.95}
.rota{margin:14px 0 4px;font-weight:600;font-size:15px}
.contagem{display:inline-block;margin-top:14px;padding:7px 16px;border-radius:999px;background:rgba(255,255,255,.22);backdrop-filter:blur(4px);font-weight:600}
.alerta{background:var(--verde);color:#fff;border-radius:16px;padding:16px 18px;font-weight:600;margin:-40px 0 16px;position:relative;box-shadow:var(--sombra)}
.card{background:var(--papel);border:1px solid var(--linha);border-radius:20px;padding:22px;box-shadow:var(--sombra);margin-bottom:16px}
.sobe-topo{margin-top:-40px;position:relative}
.alerta+.sobe-topo{margin-top:0}
.hero{display:grid;grid-template-columns:1.4fr 1fr;gap:18px;align-items:center}
.rot{font-size:12px;text-transform:uppercase;letter-spacing:.1em;color:var(--suave)}
.preco{font:800 clamp(40px,9vw,60px)/1 Fraunces,serif;margin:8px 0 4px}.preco small{font:500 16px Inter;color:var(--suave);margin-left:4px}
.delta{font-weight:600;color:var(--suave)}.delta.desce{color:var(--verde)}.delta.sobe{color:var(--verm)}
.veredito{border-radius:16px;padding:18px}.veredito h2{font:700 22px/1.2 Fraunces,serif;margin:0 0 6px}.veredito p{margin:0;font-size:14px}
.alerta-bg{background:color-mix(in srgb,var(--verde) 16%,transparent)}.bom-bg{background:color-mix(in srgb,var(--c2) 15%,transparent)}
.ok-bg{background:color-mix(in srgb,var(--amar) 15%,transparent)}.caro-bg{background:color-mix(in srgb,var(--verm) 12%,transparent)}
h2.sec{font:700 24px Fraunces,serif;margin:30px 0 12px}
.duas{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.per{border-top:5px solid var(--cor);margin:0}.per header{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.per h3{font:700 18px Fraunces,serif;margin:0}.bolinha{width:10px;height:10px;border-radius:50%;background:var(--cor)}
.selo{font-size:11px;font-weight:700;padding:2px 9px;border-radius:999px;background:var(--cor);color:#fff;white-space:nowrap}
.pp{font:800 36px Fraunces,serif;margin:10px 0 0}.pp small{font:500 14px Inter;color:var(--suave);margin-left:3px}
.tot{font-size:13px;color:var(--suave)}
.badge{display:inline-block;margin:12px 0 4px;padding:5px 12px;border-radius:10px;font-weight:600;font-size:14px}
.badge.alerta{background:color-mix(in srgb,var(--verde) 18%,transparent);color:var(--verde)}
.badge.bom{background:color-mix(in srgb,var(--c2) 16%,transparent);color:var(--c2)}
.badge.ok{background:color-mix(in srgb,var(--amar) 16%,transparent);color:var(--amar)}
.badge.caro{background:color-mix(in srgb,var(--verm) 13%,transparent);color:var(--verm)}
dl{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin:12px 0 0}dt{font-size:12px;color:var(--suave)}dd{margin:0;font-weight:600}
dd small,td small{color:var(--suave);font-weight:400}
.nota{font-size:12.5px;color:var(--suave);margin:10px 0 0}
.legenda{display:flex;flex-wrap:wrap;gap:14px;font-size:13px;margin-bottom:8px}.legenda i{display:inline-block;width:14px;height:4px;border-radius:2px;margin-right:6px;vertical-align:middle}
.li-zona{background:color-mix(in srgb,var(--verde) 35%,transparent)!important;height:10px!important}
svg{width:100%;height:auto;display:block}.g{stroke:var(--linha)}.eixo{fill:var(--suave);font-size:11px}
.linha{stroke-width:3;stroke-linejoin:round;stroke-linecap:round}.ponto{stroke:var(--papel);stroke-width:3}
.zona{fill:var(--verde);opacity:.1}.zona-t{fill:var(--verde);font-size:11px;font-weight:600}
.m-bom,.m-ok{stroke:var(--suave);stroke-dasharray:5 5;stroke-width:1}.m-bom-t,.m-ok-t{fill:var(--suave);font-size:11px}
.tab{overflow-x:auto}table{width:100%;border-collapse:collapse;font-size:14px}th{text-align:right;font-size:13px;padding:8px}
td{padding:10px 8px;border-top:1px solid var(--linha);text-align:right}td:first-child,th:first-child{text-align:left;color:var(--suave)}
.prevs{display:grid;grid-template-columns:1fr 1fr;gap:14px}.prev{border-left:4px solid var(--cor);padding:4px 0 4px 14px}
.prev-v{font:800 30px Fraunces,serif;margin:4px 0}
.janela{background:color-mix(in srgb,var(--sol) 25%,transparent);border-radius:12px;padding:12px 14px;margin:16px 0 0}
.voos h4{font:700 17px Fraunces,serif;margin:6px 0 4px}.voos+.voos{margin-top:22px}
.voos ul{list-style:none;margin:0;padding:0}.voos li{display:grid;grid-template-columns:1fr auto;gap:2px 12px;padding:12px 0;border-top:1px solid var(--linha)}
.v-cia{font-weight:600}.v-inf{grid-row:2;font-size:13px;color:var(--suave)}.v-p{grid-row:1/3;grid-column:2;text-align:right;font:700 18px Fraunces,serif;align-self:center}
.v-p small{display:block;font:400 12px Inter;color:var(--suave)}
.ok-h,.no-h{font-size:11px;font-weight:600;padding:1px 7px;border-radius:999px;margin-left:6px;white-space:nowrap}
.ok-h{background:color-mix(in srgb,var(--verde) 16%,transparent);color:var(--verde)}.no-h{background:var(--linha);color:var(--suave)}
.btn{display:block;text-align:center;margin-top:12px;padding:11px;border-radius:12px;background:var(--c2);color:#fff;text-decoration:none;font-weight:600}
.geral p{margin:0 0 10px}
footer{text-align:center;color:var(--suave);font-size:12px;margin-top:28px}footer a{color:inherit}
@media (max-width:620px){.hero,.duas,.prevs{grid-template-columns:1fr}
  .eixo,.zona-t,.m-bom-t,.m-ok-t{font-size:20px}.linha{stroke-width:5}}
"""


def pagina(cfg: dict, hist: list, r: dict) -> str:
    v, pers, m = cfg["viagem"], r["periodos"], r["melhor"]
    pax = v.get("adultos", 1) + v.get("criancas", 0)
    cor_m = CORES[pers.index(m)]
    explic = {
        "alerta": f"Está perto ou abaixo de {brl(cfg['metas']['alerta'])} por pessoa, a meta de alerta.",
        "bom": f"Abaixo de {brl(cfg['metas']['bom'])} por pessoa. Bom preço para julho no Caribe.",
        "ok": f"Entre {brl(cfg['metas']['bom'])} e {brl(cfg['metas']['ok'])} por pessoa. Dá, mas dá pra esperar melhor.",
        "caro": f"Acima de {brl(cfg['metas']['ok'])} por pessoa. Vamos esperar baixar.",
    }[m["status"]]
    banner = f'<div class="alerta">🎉 ALERTA DE PREÇO: {html.escape(r["alerta"])}</div>' if r["alerta"] else ""
    return f'''<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(v["nome"])} · Radar de passagens</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,600;0,9..144,800;1,9..144,600&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>{CSS}</style></head><body>
<div class="topo">
  <div class="kicker">Radar de passagens · atualizado {dl(r["data"])}</div>
  <h1>{html.escape(v["nome"])}</h1>
  <div class="sub">{html.escape(v.get("subtitulo", ""))}</div>
  <div class="rota">{v["origem"]} ✈ {v["destino"]} · ida e volta · {pax} viajantes · econômica</div>
  <div class="contagem">{"Faltam " + str(r["dias"]) + " dias 🌊" if r["dias"] > 0 else "É agora! 🧳"}</div>
</div>
<div class="wrap">
{banner}
<section class="card hero sobe-topo">
  <div><div class="rot">Melhor preço hoje · {html.escape(m["nome"])}</div>
    <div class="preco" style="color:{cor_m}">{brl(m["hoje"])}<small>por pessoa</small></div>
    <div class="tot">{brl(m["total"])} para os {pax} · {delta_html(m)}</div></div>
  <div class="veredito {m["status"]}-bg"><h2>{m["titulo"]}</h2><p>{explic}</p></div>
</section>

<h2 class="sec">As duas datas, lado a lado</h2>
<div class="duas">{"".join(card_periodo(a, c, a is m) for a, c in zip(pers, CORES))}</div>

<h2 class="sec">Como o preço andou</h2>
<section class="card">{grafico(pers, cfg["metas"])}
<p class="nota">Preço por pessoa, ida e volta, do voo mais barato que chega cedinho e volta à noite.</p></section>

<h2 class="sec">Oscilações</h2>
<section class="card">{tabela_oscilacoes(pers)}</section>

<h2 class="sec">Previsão</h2>
<section class="card">{previsoes(pers, r)}</section>

<h2 class="sec">Melhores voos de hoje</h2>
<section class="card">{"".join(lista_voos(a, pax) for a in pers)}</section>

<h2 class="sec">Resumo geral</h2>
<section class="card geral">{resumo_geral(cfg, r)}</section>

<footer>Atualizado automaticamente todo dia às 8h · preços do Google Flights, podem mudar na hora da compra ·
<a href="historico.json">baixar histórico</a></footer>
</div></body></html>'''
