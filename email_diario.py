"""Email diário: versão leve do relatório (Gmail não mostra gráficos SVG) + link para a página."""
from __future__ import annotations

import os
import smtplib
import ssl
from email.message import EmailMessage

from analise import brl

COR = {"alerta": "#16a34a", "bom": "#0e9aa7", "ok": "#d97706", "caro": "#dc2626"}


def corpo(cfg: dict, r: dict) -> str:
    v = cfg["viagem"]
    url = os.environ.get("PAGINA_URL", "")
    linhas = ""
    for a in r["periodos"]:
        d = "primeiro dia" if a["delta"] is None else (
            f'{"▼" if a["delta"] < 0 else "▲"} {brl(abs(a["delta"]))} vs. ontem' if a["delta"] else "igual a ontem")
        cor_d = "#16a34a" if (a["delta"] or 0) < 0 else "#dc2626" if (a["delta"] or 0) > 0 else "#64748b"
        linhas += f'''<tr><td style="padding:16px;border-top:1px solid #e3eae9">
  <div style="font:600 15px Arial;color:#13283a">{a["nome"]}{" ⭐" if a is r["melhor"] else ""}</div>
  <div style="font:12px Arial;color:#64748b">menor já visto: {brl(a["min"][1])} · {a["tendencia"][1]}</div></td>
  <td style="padding:16px;border-top:1px solid #e3eae9;text-align:right">
  <div style="font:bold 22px Georgia;color:#13283a">{brl(a["hoje"])}<span style="font:12px Arial;color:#64748b">/pessoa</span></div>
  <div style="font:12px Arial;color:{cor_d}">{d}</div>
  <div style="display:inline-block;margin-top:4px;padding:2px 8px;border-radius:8px;background:{COR[a["status"]]};color:#fff;font:bold 11px Arial">{a["titulo"]}</div></td></tr>'''
    alerta = (f'<tr><td colspan="2" style="background:#16a34a;color:#fff;padding:14px 16px;font:bold 15px Arial">'
              f'🎉 ALERTA: {r["alerta"]}</td></tr>') if r["alerta"] else ""
    botao = (f'<tr><td colspan="2" style="padding:18px 16px"><a href="{url}" style="display:block;text-align:center;'
             f'background:#0e9aa7;color:#fff;text-decoration:none;padding:12px;border-radius:10px;font:bold 15px Arial">'
             f'Ver gráfico, previsão e todos os voos</a></td></tr>') if url else ""
    return f'''<div style="background:#f4f8f7;padding:20px 8px"><table role="presentation" width="100%" style="max-width:560px;margin:0 auto;background:#fff;border-radius:16px;overflow:hidden;border-collapse:collapse">
<tr><td colspan="2" style="background:#0e9aa7;background:linear-gradient(160deg,#0e9aa7,#ffb26b);color:#fff;padding:26px 16px;text-align:center">
  <div style="font:12px Arial;letter-spacing:2px;text-transform:uppercase">Radar de passagens</div>
  <div style="font:bold 30px Georgia;margin:6px 0">{v["nome"]} 🌴</div>
  <div style="font:14px Arial">Faltam {r["dias"]} dias · {v["origem"]} ✈ {v["destino"]}</div></td></tr>
{alerta}{linhas}
<tr><td colspan="2" style="padding:14px 16px;font:13px Arial;color:#475569;background:#fffbea">🗓️ {r["janela"]}</td></tr>
{botao}</table></div>'''


def enviar(cfg: dict, r: dict) -> None:
    usuario, senha, destino = ((os.environ.get(k) or "").strip() for k in ("EMAIL_USUARIO", "EMAIL_SENHA_APP", "EMAIL_DESTINO"))
    senha = senha.replace(" ", "")  # a senha de app do Google vem com espaços
    if not (usuario and senha and destino):
        print("Email não configurado; pulando envio.")
        return
    m = r["melhor"]
    assunto = (f"🎉 ALERTA {cfg['viagem']['nome']}: {brl(m['hoje'])}/pessoa!" if r["alerta"]
               else f"✈️ {cfg['viagem']['nome']} hoje: {brl(m['hoje'])}/pessoa ({m['nome']})")
    msg = EmailMessage()
    msg["Subject"], msg["From"], msg["To"] = assunto, f"Radar de Passagens <{usuario}>", destino
    msg.set_content("Seu leitor de email não mostra HTML. Veja a página do radar: " + os.environ.get("PAGINA_URL", ""))
    msg.add_alternative(corpo(cfg, r), subtype="html")
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ssl.create_default_context()) as s:
            s.login(usuario, senha)
            s.send_message(msg)
        print("Email enviado para", destino)
    except Exception as e:  # o email falhar não pode impedir a página de ser atualizada
        print(f"::warning::Falha ao enviar o email ({type(e).__name__}: {e}). Confira EMAIL_USUARIO e EMAIL_SENHA_APP.")
