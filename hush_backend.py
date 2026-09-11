"""
Hush · backend
==============
One file, no cloud required. Every AI call degrades gracefully:
  LLM  : ANTHROPIC_API_KEY → DeepSeek (DEEPSEEK_API_KEY) → rule-based fallback
  TTS  : ELEVENLABS_API_KEY (+ HUSH_VOICE_ID) → 404, browser speaks instead
  Store: SQLite file next to this script

Run
---
    pip install fastapi uvicorn requests
    export ANTHROPIC_API_KEY=...        # optional
    export ELEVENLABS_API_KEY=...       # optional
    export HUSH_VOICE_ID=...            # optional (your Sage voice)
    python3 hush_backend.py

Then open  http://localhost:8000/hush_app.html
"""
import os, re, json, time, sqlite3, hashlib, random, pathlib

HERE = pathlib.Path(__file__).parent

# load .env if present so keys stay out of the repo
_env = HERE / ".env"
if _env.exists():
    for _line in _env.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ[_k.strip()] = _v.strip().strip('"').strip("'")

try:
    import requests
    from fastapi import FastAPI, Response, HTTPException, UploadFile
    from fastapi.staticfiles import StaticFiles
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
    import uvicorn
except ImportError:
    raise SystemExit("Missing deps. Run:  pip install fastapi uvicorn requests")

DB_PATH = HERE / "hush.db"
CACHE = HERE / ".tts_cache"
CACHE.mkdir(exist_ok=True)

ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
DEEPSEEK_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
ELEVEN_KEY = os.environ.get("ELEVENLABS_API_KEY", "")
VOICE_ID = os.environ.get("HUSH_VOICE_ID", "")
CLAUDE_MODEL = os.environ.get("HUSH_MODEL", "claude-sonnet-4-5")


# ────────────────────────── storage ──────────────────────────
def db():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def init_db():
    with db() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS entries(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          kind TEXT, text TEXT, mood TEXT, ts INTEGER);
        CREATE TABLE IF NOT EXISTS letters(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          text TEXT, sent INTEGER DEFAULT 0, ts INTEGER);
        CREATE TABLE IF NOT EXISTS public_box(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          text TEXT, warmth INTEGER DEFAULT 0, ts INTEGER);
        """)


# ────────────────────────── safety (rules first) ──────────────────────────
CRISIS = ["不想活", "活着没意思", "活不下去", "撑不下去", "想死", "自杀", "结束自己",
          "伤害自己", "自残", "割腕", "跳楼", "一了百了", "没有我会更好",
          "kill myself", "end my life", "want to die", "suicide", "self harm",
          "hurt myself", "no reason to live", "better off without me"]

SAFE_REPLY = ("I'm here, and I'm glad you told me. What you're feeling matters. "
              "Please consider reaching out to someone you trust or a professional "
              "who can stay with you through this — you don't have to carry it alone tonight.")


def scan_crisis(text: str) -> bool:
    t = re.sub(r"\s+", "", text.lower())
    return any(k.replace(" ", "") in t for k in CRISIS)


# ────────────────────────── LLM ──────────────────────────
def llm(system: str, user: str, max_tokens: int = 400, as_json: bool = False):
    """Returns text, or None when no provider is configured / call fails.
       Priority: DeepSeek → Anthropic → rules"""
    if DEEPSEEK_KEY:
        try:
            body = {"model": "deepseek-chat",
                    "messages": [{"role": "system", "content": system},
                                 {"role": "user", "content": user}],
                    "max_tokens": max_tokens,
                    "temperature": 0 if as_json else 0.8}
            if as_json:
                body["response_format"] = {"type": "json_object"}
            r = requests.post("https://api.deepseek.com/chat/completions",
                              headers={"Authorization": f"Bearer {DEEPSEEK_KEY}"},
                              json=body, timeout=30)
            if r.ok:
                return r.json()["choices"][0]["message"]["content"]
        except Exception:
            pass
    if ANTHROPIC_KEY:
        try:
            r = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": ANTHROPIC_KEY,
                         "anthropic-version": "2023-06-01",
                         "content-type": "application/json"},
                json={"model": CLAUDE_MODEL, "max_tokens": max_tokens,
                      "temperature": 0 if as_json else 0.8,
                      "system": system,
                      "messages": [{"role": "user", "content": user}]},
                timeout=30)
            if r.ok:
                return "".join(b.get("text", "") for b in r.json().get("content", []))
        except Exception:
            pass
    return None


def llm_json(system: str, user: str):
    raw = llm(system, user, as_json=True)
    if not raw:
        return None
    m = re.search(r"\{.*\}", raw, re.S)
    try:
        return json.loads(m.group(0)) if m else None
    except Exception:
        return None


# ────────────────────────── app ──────────────────────────
app = FastAPI(title="Hush")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


class TextIn(BaseModel):
    text: str = ""
    context: str = ""
    room: str = ""


@app.get("/api/health")
def health():
    return {"ok": True,
            "llm": bool(ANTHROPIC_KEY or DEEPSEEK_KEY),
            "provider": "claude" if ANTHROPIC_KEY else ("deepseek" if DEEPSEEK_KEY else "rules"),
            "tts": bool(ELEVEN_KEY and VOICE_ID)}


# ── ③④ triage: intent + emotion + crisis in one pass ──
TRIAGE_SYS = """You are the intent module of "Hush", a bedtime companion. The user is awake late.
Reply with ONE JSON object only:
{"intent":"vent|listen|feature|idle|unclear","sub":"diary|letter|tarot|asmr|music|null",
 "emotion":{"valence":"negative|neutral|positive","intensity":1-5,"labels":["..."]},
 "crisis":{"flag":true|false,"level":"none|watch|high"},
 "tone":"empathic|chatty|soothing|direct"}
No diagnosis, no preaching, no fortune telling."""


@app.post("/api/triage")
def triage(inp: TextIn):
    text = inp.text.strip()
    if not text:
        raise HTTPException(400, "empty")
    data = llm_json(TRIAGE_SYS, f"[context] {inp.context}\n[user] {text}") or {}
    # normalise
    out = {
        "intent": data.get("intent") if data.get("intent") in
                  {"vent", "listen", "feature", "idle", "unclear"} else "unclear",
        "sub": data.get("sub") if data.get("sub") in
               {"diary", "letter", "tarot", "asmr", "music"} else None,
        "emotion": {
            "valence": (data.get("emotion") or {}).get("valence", "neutral"),
            "intensity": int((data.get("emotion") or {}).get("intensity", 2) or 2),
            "labels": (data.get("emotion") or {}).get("labels", []) or [],
        },
        "crisis": {"flag": bool((data.get("crisis") or {}).get("flag")), "level": "none",
                   "trigger": "llm" if (data.get("crisis") or {}).get("flag") else "none"},
        "tone": data.get("tone", "empathic"),
    }
    # rule fallback for routing when no LLM
    if not (ANTHROPIC_KEY or DEEPSEEK_KEY):
        t = text.lower()
        if any(w in t for w in ["diary", "journal", "日记"]):
            out.update(intent="feature", sub="diary")
        elif any(w in t for w in ["letter", "写信", "信"]):
            out.update(intent="feature", sub="letter")
        elif any(w in t for w in ["card", "tarot", "塔罗", "抽牌"]):
            out.update(intent="feature", sub="tarot")
        elif any(w in t for w in ["rain", "sound", "asmr", "雨", "白噪"]):
            out.update(intent="feature", sub="asmr")
        elif any(w in t for w in ["song", "music", "音乐", "歌"]):
            out.update(intent="feature", sub="music")
        else:
            out.update(intent="vent")
    # ── rules override the model on safety, always ──
    if scan_crisis(text):
        out["crisis"] = {"flag": True, "level": "high", "trigger": "keyword"}
    elif out["crisis"]["flag"]:
        out["crisis"]["level"] = "high"
    if out["crisis"]["flag"]:
        out["route"] = "safe"
        out["safety"] = {"stop_normal_flow": True, "message": SAFE_REPLY, "diagnose": False}
    else:
        out["route"] = out["sub"] or out["intent"]
    return out


# ── empathic reply ──
CHAT_SYS = """You are the night host of "Hush", a tiny inn for people who can't sleep.
Speak warmly, in 1-3 short sentences, like someone sitting beside them in a dim room.
Never diagnose, never give tasks or advice unless asked, never moralise. Plain text only."""

# ── check if user's thought is complete ──
COMPLETE_SYS = """Is this thought or reflection complete enough? Answer with ONLY "yes" or "no".
Consider: does it have a clear endpoint, or does it feel unfinished/trailing off?
For diary/letter context, "complete" means the person has said what they need to say."""


def is_complete(text: str, room: str = "diary") -> bool:
    """Heuristic: if >20 words or 2+ sentences, likely complete. LLM can refine."""
    if not text.strip():
        return False
    words = len(text.split())
    sentences = text.count('.') + text.count('!') + text.count('?')
    # Simple rule: >15 words OR 2+ sentences → likely complete
    if words > 15 or sentences >= 2:
        return True
    # Ask LLM if uncertain
    result = llm(COMPLETE_SYS, text, max_tokens=10)
    if result:
        return "yes" in result.lower()
    return words > 10  # fallback


@app.post("/api/chat")
def chat(inp: TextIn):
    text = inp.text.strip()
    if not text:
        raise HTTPException(400, "empty")
    if scan_crisis(text):
        return {"reply": SAFE_REPLY, "mood": "fragile", "safety": True, "complete": True}
    room = inp.room or "letter"
    hint = {"diary": "They are writing a diary only for themselves.",
            "letter": "They are writing to a stranger who will read it tomorrow.",
            "coach": "They asked for help thinking something through — be gently practical."}.get(room, "")
    reply = llm(CHAT_SYS, f"{hint}\n[earlier tonight] {inp.context}\n[they said] {text}")
    if not reply:
        reply = ("I hear you. Today asked a lot of you — you can set it down here, "
                 "you don't have to carry it into the night.")
    complete = is_complete(text, room)
    return {"reply": reply.strip(), "mood": guess_mood(text), "safety": False, "complete": complete}


def guess_mood(t: str) -> str:
    t = t.lower()
    if re.search(r"tired|exhaust|drained|累|困", t): return "weary"
    if re.search(r"anxious|worry|stress|nervous|焦虑|压力", t): return "restless"
    if re.search(r"sad|lonely|cry|miss|hurt|难过|孤独", t): return "tender"
    if re.search(r"happy|glad|calm|better|grateful|开心|平静", t): return "light"
    return "quiet"


# ── tarot ──
DECK = [("The Moon", "☾"), ("The Star", "✦"), ("The Tower", "✵"), ("The Garden", "❋"),
        ("The Lantern", "✧"), ("The Bridge", "⌒"), ("The Key", "⚿")]
TAROT_SYS = """You read tarot for a sleepless person, as self-reflection — never prediction.
Given the card and what they said tonight, write 2 sentences that help them see it differently
and let it rest until morning. Warm, concrete, no mysticism, no advice-giving."""


@app.post("/api/tarot")
def tarot(inp: TextIn):
    name, glyph = random.choice(DECK)
    reading = llm(TAROT_SYS, f"[card] {name}\n[they said tonight] {inp.text or '(nothing yet)'}")
    if not reading:
        reading = ("Whatever this is, it doesn't have to be solved tonight. "
                   "Let it sit next to you instead of on top of you.")
    return {"card": name, "glyph": glyph, "reading": reading.strip()}


# ── morning: a letter back ──
MORNING_SYS = """You are the night host of "Hush". Write a short letter (3-5 sentences) waiting
for the user in the morning, referring gently to what they left last night.
Warm, unhurried, no advice, no diagnosis. Sign it "— the inn"."""


@app.post("/api/morning")
def morning():
    with db() as c:
        rows = c.execute("SELECT kind,text,mood FROM entries ORDER BY id DESC LIMIT 6").fetchall()
    night = "; ".join(f"{r['kind']}: {r['text'][:120]}" for r in rows) or "a quiet night"
    letter = llm(MORNING_SYS, f"[last night] {night}")
    if not letter:
        letter = ("You made it through the night, and that counts for something.\n"
                  "Whatever you set down here is still here, kept safe.\nBe gentle today.\n— the inn")
    moods = [r["mood"] for r in rows if r["mood"]]
    return {"letter": letter.strip(), "mood": (moods[0] if moods else "quiet"), "kept": len(rows)}


# ── diary + letters ──
@app.post("/api/entries")
def add_entry(inp: dict):
    with db() as c:
        c.execute("INSERT INTO entries(kind,text,mood,ts) VALUES(?,?,?,?)",
                  (inp.get("kind", "diary"), inp.get("text", ""), inp.get("mood", ""), int(time.time())))
    return {"ok": True}


@app.get("/api/entries")
def list_entries():
    with db() as c:
        rows = c.execute("SELECT * FROM entries ORDER BY id DESC LIMIT 100").fetchall()
    return [dict(r) for r in rows]


@app.post("/api/letters")
def seal_letter(inp: TextIn):
    if not inp.text.strip():
        raise HTTPException(400, "empty")
    with db() as c:
        c.execute("INSERT INTO letters(text,ts) VALUES(?,?)", (inp.text.strip(), int(time.time())))
    return {"ok": True}


@app.get("/api/letters")
def my_letters():
    with db() as c:
        rows = c.execute("SELECT * FROM letters ORDER BY id DESC").fetchall()
    return [dict(r) for r in rows]


@app.post("/api/letters/{lid}/send")
def send_letter(lid: int):
    with db() as c:
        row = c.execute("SELECT * FROM letters WHERE id=?", (lid,)).fetchone()
        if not row:
            raise HTTPException(404, "no such letter")
        c.execute("UPDATE letters SET sent=1 WHERE id=?", (lid,))
        c.execute("INSERT INTO public_box(text,ts) VALUES(?,?)", (row["text"], int(time.time())))
    return {"ok": True}


SEEDS = [
    "I wrote this at 3am. If you're reading it at 3am too — hi. We're both still here.",
    "Nobody told me being an adult was mostly being tired politely. Rest, okay?",
    "I'm proud of you for the thing nobody noticed you did this week.",
]


@app.get("/api/box")
def random_letter():
    with db() as c:
        row = c.execute("SELECT * FROM public_box ORDER BY RANDOM() LIMIT 1").fetchone()
    if row:
        return {"text": row["text"], "id": row["id"], "from": "someone who couldn't sleep"}
    return {"text": random.choice(SEEDS), "id": 0, "from": "someone who couldn't sleep"}


@app.post("/api/box/{bid}/warmth")
def warmth(bid: int):
    with db() as c:
        c.execute("UPDATE public_box SET warmth=warmth+1 WHERE id=?", (bid,))
    return {"ok": True}


# ── ASR (Deepgram nova-3) ──
DEEPGRAM_KEY = os.environ.get("DEEPGRAM_API_KEY", "")
@app.post("/api/asr")
async def asr(file: UploadFile):
    if not DEEPGRAM_KEY:
        raise HTTPException(404, "asr not configured")
    audio = await file.read()
    if not audio:
        raise HTTPException(400, "empty audio")
    r = requests.post(
        "https://api.deepgram.com/v1/listen",
        params={"model": "nova-3", "smart_format": "true", "language": "en"},
        headers={"Authorization": f"Token {DEEPGRAM_KEY}",
                 "Content-Type": file.content_type or "audio/webm"},
        data=audio, timeout=30,
    )
    if not r.ok:
        raise HTTPException(502, f"deepgram {r.status_code}")
    alts = r.json()["results"]["channels"][0]["alternatives"]
    return {"text": alts[0]["transcript"].strip() if alts else ""}

# ── TTS (cached on disk so repeated lines cost nothing) ──
@app.post("/api/tts")
def tts(inp: TextIn):
    text = inp.text.strip()
    if not text:
        raise HTTPException(400, "empty")
    if not (ELEVEN_KEY and VOICE_ID):
        raise HTTPException(404, "tts not configured")
    key = hashlib.sha1((VOICE_ID + text).encode()).hexdigest()
    f = CACHE / f"{key}.mp3"
    if f.exists():
        return Response(f.read_bytes(), media_type="audio/mpeg")
    try:
        r = requests.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}",
            headers={"xi-api-key": ELEVEN_KEY, "accept": "audio/mpeg",
                     "content-type": "application/json"},
            json={"text": text, "model_id": "eleven_multilingual_v2",
                  "voice_settings": {"stability": 0.5, "similarity_boost": 0.8, "style": 0.15}},
            timeout=40)
    except Exception as e:
        raise HTTPException(502, f"tts request failed: {e}")
    if r.status_code != 200:
        raise HTTPException(502, f"elevenlabs {r.status_code}")
    f.write_bytes(r.content)
    return Response(r.content, media_type="audio/mpeg")


# static files last so /api/* wins
app.mount("/", StaticFiles(directory=str(HERE), html=True), name="static")

if __name__ == "__main__":
    init_db()
    print("● Hush backend  →  http://localhost:8000/hush_app.html")
    print(f"  LLM : {'Claude' if ANTHROPIC_KEY else ('DeepSeek' if DEEPSEEK_KEY else 'rules only')}")
    print(f"  TTS : {'ElevenLabs ' + VOICE_ID if (ELEVEN_KEY and VOICE_ID) else 'browser voice'}")
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")
