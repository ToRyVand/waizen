# Waizen — Setup

> 🚧 Showcase build. These steps describe how the system is assembled.
> The production-tuned agent and managed hosting are part of the commercial service.

## 1. Requirements

- **Python 3.10+** (API + PDF generator orchestration)
- **Node.js 20+** (server-side PDF generator via Playwright)
- **Docker** (Caddy reverse proxy)
- **OpenClaw** (WhatsApp + LLM agent) — https://openclaw.ai
- A **Google Gemini API key** — https://aistudio.google.com/app/apikey
  (enable billing on the project for production-grade quota)

## 2. Personalize

```bash
cp config.example.json config.json     # business name, logo, contact, bank, theme
cp .env.example .env                    # secrets (keys, auth hash) — never commit this
python3 setup.py                        # applies config.json to the templates
```

Generate your panel password hash:

```bash
python3 -c "import bcrypt;print(bcrypt.hashpw(b'YOUR_PASSWORD', bcrypt.gensalt(12)).decode())"
# paste the result into AUTH_HASH in .env
```

## 3. Install dependencies

```bash
# API
pip install -r api/requirements.txt          # bcrypt
# PDF generator
cd pdfgen && npm install && npx playwright install chromium && cd ..
```

## 4. Run the pieces

| Piece | What | How |
|---|---|---|
| **API** | data, auth, PDF endpoints, follow-ups | `python3 api/app.py` (port 18788) |
| **Reverse proxy** | HTTPS + auth gate + serves the panel | `infra/` → `docker compose up -d` |
| **WhatsApp agent** | conversational service | OpenClaw gateway bound to your number |
| **PDF generator** | batch / regeneration | called by the API (`pdfgen/generate_pdfs.js`) |

`systemd` unit examples (24/7) are in `infra/systemd/`.

## 5. Architecture

See the diagram in the main [README](../README.md). In short:

```
WhatsApp ⇄ AI Agent (OpenClaw + Gemini) ⇄ API (Python) ⇄ Web Panel
                                              │
                                     PDF gen (Playwright)
                                     Caddy (proxy + auth)
```

## Project layout

- `dashboard/` — the web panel (one HTML file per tool + shared JS vendor libs)
- `api/` — `app.py`, the backend
- `pdfgen/` — server-side PDF generator
- `agent/` — personality, context and skills the agent loads
- `infra/` — Caddy, docker-compose, systemd
- `data/samples/` — example data (real data lives outside the repo, gitignored)

## Security notes

- **Never commit** `.env`, `config.json`, `.auth_hash`, `.auth_secret` (all gitignored).
- The API key is read from the environment (`GOOGLE_API_KEY`), never hard-coded.
- The panel is gated by token login; the reverse proxy enforces auth before serving files.
