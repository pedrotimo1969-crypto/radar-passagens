#!/usr/bin/env python3
"""Radar de passagens: busca os preços do dia, guarda o histórico, gera a página e manda o email.

Uso:
    python buscar.py              # busca real de hoje (precisa de SERPAPI_KEY)
    python buscar.py --demo 40    # 40 dias de dados fictícios para ver o visual
    python buscar.py --sem-email  # não envia email
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import os
import random
import sys
import tomllib
import urllib.parse
import urllib.request
from pathlib import Path

import analise
import email_diario
import site_relatorio

RAIZ = Path(__file__).parent
HISTORICO = RAIZ / "dados" / "historico.json"
SAIDA = RAIZ / "site"
CLASSES = {"economica": 1, "premium": 2, "executiva": 3, "primeira": 4}


def carregar_config() -> dict:
    with open(RAIZ / "config.toml", "rb") as f:
        return tomllib.load(f)


def passageiros(cfg: dict) -> int:
    v = cfg["viagem"]
    return v.get("adultos", 1) + v.get("criancas", 0)


# ------------------------------------------------------------------ fontes

def _serpapi(params: dict) -> dict:
    url = "https://serpapi.com/search.json?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=90) as r:
        return json.load(r)


def _hora(s: str | None) -> tuple[str | None, int | None]:
    """'2027-07-19 06:35' -> ('2027-07-19', 6)"""
    if not s:
        return None, None
    data, _, hora = s.partition(" ")
    return data, int(hora.split(":")[0]) if hora else None


def buscar_periodo_serpapi(cfg: dict, per: dict) -> dict:
    chave = os.environ.get("SERPAPI_KEY")
    if not chave:
        sys.exit("Faltou a variável SERPAPI_KEY (crie grátis em serpapi.com).")
    v, pref = cfg["viagem"], cfg["preferencias"]
    chegada = dt.date.fromisoformat(per["chegada"])
    pax = passageiros(cfg)
    divisor = pax if cfg["busca"].get("preco_api_e_total", True) else 1
    opcoes, nivel, faixa, link = [], None, None, None
    # Para chegar cedinho no dia X, vale sair na véspera (voo noturno) ou de madrugada no dia X.
    for saida in (chegada - dt.timedelta(days=1), chegada):
        bruto = _serpapi({
            "engine": "google_flights", "departure_id": v["origem"], "arrival_id": v["destino"],
            "outbound_date": saida.isoformat(), "return_date": per["volta"], "type": 1,
            "adults": v.get("adultos", 1), "children": v.get("criancas", 0),
            "travel_class": CLASSES.get(v.get("classe", "economica"), 1),
            "return_times": f"{pref['voltar_a_partir']},23",
            "currency": cfg["busca"].get("moeda", "BRL"), "hl": "pt-BR", "gl": "br", "api_key": chave,
        })
        if "error" in bruto:
            print(f"[{per['nome']} / saída {saida}] SerpAPI: {bruto['error']}")
            continue
        ins = bruto.get("price_insights", {})
        nivel = nivel or ins.get("price_level")
        faixa = faixa or ins.get("typical_price_range")
        link = link or bruto.get("search_metadata", {}).get("google_flights_url")
        for o in bruto.get("best_flights", []) + bruto.get("other_flights", []):
            trechos = o.get("flights") or []
            if "price" not in o or not trechos:
                continue
            chega = trechos[-1]["arrival_airport"].get("time")
            d_cheg, h_cheg = _hora(chega)
            opcoes.append({
                "pp": round(o["price"] / divisor),
                "total": round(o["price"] / divisor * pax),
                "cias": sorted({t.get("airline", "?") for t in trechos}),
                "escalas": len(trechos) - 1,
                "duracao_min": o.get("total_duration"),
                "saida": trechos[0]["departure_airport"].get("time"),
                "chegada": chega,
                "encaixa": d_cheg == per["chegada"] and h_cheg is not None and h_cheg < pref["chegar_ate"],
            })
    if faixa:
        faixa = [round(x / divisor) for x in faixa]
    return {"opcoes": opcoes, "nivel": nivel, "faixa_pp": faixa, "link": link}


def buscar_periodo_demo(cfg: dict, per: dict, dia: dt.date) -> dict:
    rnd = random.Random(dia.toordinal() * 7 + len(per["nome"]) + int(per["chegada"][-2:]))
    k = dia.toordinal()
    base = 5150 if per["chegada"].endswith("19") else 4850
    tend = base + 380 * math.sin(k / 5.5 + base) - (k % 45) * 14
    chegada = dt.date.fromisoformat(per["chegada"])
    cias = [["Copa Airlines"], ["Copa Airlines"], ["LATAM", "Arajet"], ["Avianca"], ["American"], ["GOL", "Copa Airlines"]]
    opcoes = []
    for i, c in enumerate(cias):
        pp = round(tend * (1 + i * 0.045) + rnd.uniform(-160, 160))
        cedo = rnd.random() > 0.35
        d = chegada if cedo else chegada + dt.timedelta(days=0)
        h = rnd.choice([5, 6, 7, 9, 10]) if cedo else rnd.choice([14, 16, 19])
        opcoes.append({
            "pp": pp, "total": pp * passageiros(cfg), "cias": c, "escalas": 1,
            "duracao_min": 9 * 60 + rnd.randint(0, 300),
            "saida": f"{chegada - dt.timedelta(days=1)} {rnd.choice([18, 20, 22, 23])}:{rnd.choice(['05', '30', '50'])}",
            "chegada": f"{d} {h:02d}:{rnd.choice(['10', '25', '40'])}", "encaixa": cedo,
        })
    return {"opcoes": opcoes, "nivel": None, "faixa_pp": [4600, 5900], "link": None}


# ------------------------------------------------------------------ histórico

def carregar_historico() -> list:
    return json.loads(HISTORICO.read_text(encoding="utf-8")) if HISTORICO.exists() else []


def salvar_historico(hist: list) -> None:
    HISTORICO.parent.mkdir(parents=True, exist_ok=True)
    HISTORICO.write_text(json.dumps(hist, ensure_ascii=False, indent=1), encoding="utf-8")


def montar_registro(dia: dt.date, cfg: dict, resultados: dict) -> dict:
    periodos = {}
    for nome, res in resultados.items():
        ops = sorted(res["opcoes"], key=lambda o: o["pp"])
        if not ops:
            continue
        boas = [o for o in ops if o["encaixa"]]
        periodos[nome] = {
            "menor_pp": ops[0]["pp"],
            "menor_encaixa_pp": boas[0]["pp"] if boas else None,
            "opcoes": (boas[:4] + [o for o in ops if not o["encaixa"]][:2]),
            "nivel": res.get("nivel"), "faixa_pp": res.get("faixa_pp"), "link": res.get("link"),
        }
    return {"data": dia.isoformat(), "periodos": periodos}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", type=int, metavar="DIAS")
    ap.add_argument("--sem-email", action="store_true")
    args = ap.parse_args()
    cfg = carregar_config()
    hoje = dt.date.today()
    if all(dt.date.fromisoformat(p["chegada"]) < hoje for p in cfg["periodos"]):
        print("A viagem já passou. Boa viagem! 🌴 Nada a fazer.")
        return

    if args.demo:
        hist = []
        for n in range(args.demo - 1, -1, -1):
            d = hoje - dt.timedelta(days=n)
            hist.append(montar_registro(d, cfg, {p["nome"]: buscar_periodo_demo(cfg, p, d) for p in cfg["periodos"]}))
    else:
        demo = cfg["busca"]["fonte"] == "demo"
        res = {p["nome"]: (buscar_periodo_demo(cfg, p, hoje) if demo else buscar_periodo_serpapi(cfg, p))
               for p in cfg["periodos"] if dt.date.fromisoformat(p["chegada"]) >= hoje}
        hist = [h for h in carregar_historico() if h["data"] != hoje.isoformat()]
        hist.append(montar_registro(hoje, cfg, res))
    salvar_historico(hist)

    resumo = analise.analisar(cfg, hist)
    SAIDA.mkdir(exist_ok=True)
    (SAIDA / "index.html").write_text(site_relatorio.pagina(cfg, hist, resumo), encoding="utf-8")
    (SAIDA / "historico.json").write_text(json.dumps(hist, ensure_ascii=False), encoding="utf-8")
    (SAIDA / "email.html").write_text(email_diario.corpo(cfg, resumo), encoding="utf-8")
    print("Página gerada em", SAIDA / "index.html")
    if resumo["alerta"]:
        print("ALERTA:", resumo["alerta"])
    if not args.sem_email and not args.demo:
        email_diario.enviar(cfg, resumo)


if __name__ == "__main__":
    main()
