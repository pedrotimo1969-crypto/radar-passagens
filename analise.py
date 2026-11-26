"""Números do relatório: oscilações, tendência, previsão simples e veredito."""
from __future__ import annotations

import datetime as dt
import statistics as st


def brl(v: float | None) -> str:
    return "—" if v is None else "R$ " + f"{v:,.0f}".replace(",", ".")


def _regressao(ys: list[float]) -> tuple[float, float]:
    """Retorna (inclinação por dia, valor ajustado no último ponto)."""
    n = len(ys)
    if n < 2:
        return 0.0, ys[-1]
    xs = range(n)
    mx, my = (n - 1) / 2, sum(ys) / n
    den = sum((x - mx) ** 2 for x in xs)
    a = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / den
    return a, my + a * (n - 1 - mx)


def status(valor: float, metas: dict) -> tuple[str, str]:
    lim_alerta = metas["alerta"] * (1 + metas.get("margem_alerta_pct", 5) / 100)
    if valor <= lim_alerta:
        return "alerta", "Hora de comprar! 🎉"
    if valor <= metas["bom"]:
        return "bom", "Preço bom 👍"
    if valor <= metas["ok"]:
        return "ok", "Dentro do orçamento 🙂"
    return "caro", "Ainda caro 😬"


def janela_compra(dias: int) -> str:
    if dias > 180:
        return ("Ainda é cedo. Para o Caribe em julho (férias escolares), os preços costumam ficar "
                "estáveis até uns 4 a 5 meses antes. Dá para esperar uma boa queda com calma.")
    if dias > 75:
        return ("Estamos na janela que costuma ter os melhores preços para julho. "
                "Se aparecer um valor perto da meta, vale fechar.")
    return "Faltam menos de ~2 meses e alta temporada: os preços tendem a subir daqui pra frente. Melhor não esperar muito."


def analisar_periodo(cfg: dict, hist: list, nome: str) -> dict | None:
    pts = []
    for h in hist:
        p = h["periodos"].get(nome)
        if p:
            pts.append((h["data"], p["menor_encaixa_pp"] or p["menor_pp"], p))
    if not pts:
        return None
    vals = [v for _, v, _ in pts]
    hoje_d, hoje_v, reg = pts[-1]
    ontem = vals[-2] if len(vals) > 1 else None
    i_min = min(range(len(vals)), key=vals.__getitem__)
    i_max = max(range(len(vals)), key=vals.__getitem__)
    variacoes = [(vals[i] - vals[i - 1]) / vals[i - 1] * 100 for i in range(1, len(vals))]
    queda_i = min(range(len(variacoes)), key=variacoes.__getitem__) if variacoes else None
    ult = vals[-14:]
    incl, ajuste = _regressao(ult)
    prev7 = max(ajuste + incl * 7, 0)
    margem = (st.pstdev(ult) if len(ult) > 2 else 0) * 1.2
    if incl < -8:
        tendencia = ("desce", "Tendência de queda 📉")
    elif incl > 8:
        tendencia = ("sobe", "Tendência de alta 📈")
    else:
        tendencia = ("estavel", "Preço andando de lado ➡️")
    cls, titulo = status(hoje_v, cfg["metas"])
    pax = cfg["viagem"].get("adultos", 1) + cfg["viagem"].get("criancas", 0)
    return {
        "nome": nome, "serie": [(d, v) for d, v, _ in pts], "hoje": hoje_v, "total": hoje_v * pax,
        "ontem": ontem, "delta": None if ontem is None else hoje_v - ontem,
        "delta_pct": None if ontem is None else (hoje_v - ontem) / ontem * 100,
        "min": (pts[i_min][0], vals[i_min]), "max": (pts[i_max][0], vals[i_max]),
        "media7": sum(vals[-7:]) / len(vals[-7:]),
        "var7_pct": (hoje_v - vals[-8]) / vals[-8] * 100 if len(vals) > 7 else None,
        "maior_queda": None if queda_i is None or variacoes[queda_i] >= 0 else (pts[queda_i + 1][0], variacoes[queda_i]),
        "volatilidade": st.pstdev(variacoes) if len(variacoes) > 2 else None,
        "prev7": prev7, "prev7_faixa": (prev7 - margem, prev7 + margem), "tendencia": tendencia,
        "status": cls, "titulo": titulo, "opcoes": reg["opcoes"], "faixa_pp": reg.get("faixa_pp"),
        "nivel": reg.get("nivel"), "link": reg.get("link"), "encaixa": reg["menor_encaixa_pp"] is not None,
        "menor_qualquer": reg["menor_pp"],
        "dias_alerta": sum(1 for v in vals if status(v, cfg["metas"])[0] == "alerta"),
    }


def analisar(cfg: dict, hist: list) -> dict:
    hoje = dt.date.fromisoformat(hist[-1]["data"])
    pers = [a for p in cfg["periodos"] if (a := analisar_periodo(cfg, hist, p["nome"]))]
    melhor = min(pers, key=lambda a: a["hoje"]) if pers else None
    primeira = min(dt.date.fromisoformat(p["chegada"]) for p in cfg["periodos"])
    dias = (primeira - hoje).days
    alerta = None
    alertas = [a for a in pers if a["status"] == "alerta"]
    if alertas:
        a = min(alertas, key=lambda a: a["hoje"])
        alerta = f"{a['nome']}: {brl(a['hoje'])} por pessoa ({brl(a['total'])} no total)"
    return {"data": hoje, "dias": dias, "periodos": pers, "melhor": melhor,
            "alerta": alerta, "janela": janela_compra(dias), "n_dias": len(hist)}
