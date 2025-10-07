import os, html, sys, traceback
from fastapi import FastAPI, Request, Response
import httpx

app = FastAPI(title="HGA Bot")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

@app.get("/")
def index():
    return {"ok": True, "message": "HGA Bot online", "routes": ["/health", "/diag/openai", "/whatsapp", "/status"]}

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/diag/openai")
async def diag_openai():
    if not OPENAI_API_KEY:
        return {"ok": False, "error": "OPENAI_API_KEY ausente no ambiente da Vercel"}
    try:
        url = "https://api.openai.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
        payload = {"model": "gpt-4o-mini","messages":[{"role":"user","content":"Responda apenas: ok"}],"temperature":0.1,"max_tokens":10}
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.post(url, headers=headers, json=payload)
            if r.status_code >= 400:
                try: return {"ok": False, "status": r.status_code, "error": r.json()}
                except: return {"ok": False, "status": r.status_code, "error_text": r.text}
            return {"ok": True, "text": r.json()["choices"][0]["message"]["content"].strip()}
    except Exception as e:
        return {"ok": False, "error": repr(e)}

async def call_openai_brief(prompt: str) -> str:
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY ausente")
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
    payload = {"model":"gpt-4o-mini","messages":[
        {"role":"system","content":"Você é um assistente informativo do Hosken & Geraldino. Responda de forma breve e clara, sem aconselhamento jurídico individual."},
        {"role":"user","content": prompt}
    ],"temperature":0.3,"max_tokens":180}
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.post(url, headers=headers, json=payload)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()

@app.post("/whatsapp")
async def whatsapp(request: Request):
    try:
        form = dict((await request.form()).items())  # Twilio envia form-urlencoded
    except Exception:
        return Response(status_code=415, content="Unsupported Media Type (esperado form-urlencoded)")
    user_text = (form.get("Body") or "").strip() or "Olá! Faça uma pergunta objetiva."
    try:
        ai = await call_openai_brief(user_text)
    except Exception as e:
        print("OPENAI_ERROR:", repr(e), file=sys.stderr); traceback.print_exc()
        ai = "Estou com instabilidade de IA no momento; nossa equipe retornará em breve."
    disclaimer = "[Aviso] Resposta informativa. Não substitui consulta com advogado(a). Contato: (21) 2018-4200 • WhatsApp: +1 415 523 8886"
    final_xml = html.escape(f"{ai}\n\n{disclaimer}")
    twiml = f'<?xml version="1.0" encoding="UTF-8"?><Response><Message>{final_xml}</Message></Response>'
    return Response(content=twiml, media_type="application/xml")

@app.post("/status")
async def status_callback(request: Request):
    try:
        data = dict((await request.form()).items())
    except Exception:
        data = {"error": "esperado form-urlencoded"}
    return {"ok": True, "received": data.get("MessageStatus", "unknown")}

