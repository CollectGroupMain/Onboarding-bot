# Onboarding Bot

Telegram bot that runs a **step-by-step survey** after `/start`. Answers are validated per question type; completed forms are appended to **JSONL** (and can be downloaded as **CSV** from the web admin).

Includes a **lightweight web admin**: edit the survey, browse submissions, and export data.

## Features

- Sequential questions from `data/survey.json` (reloads on each `/start` for new sessions)
- Types: `text`, `number`, `date`, `email`, `phone`, `choice` (inline buttons)
- `/cancel` to abort without saving
- Submissions: `data/submissions.jsonl` (one JSON object per line)
- **FastAPI** admin UI with password login (`ADMIN_WEB_PASSWORD`)
- Optional import of question drafts from Word: `scripts/import_docx.py`

## Requirements

- Python **3.10+**
- A Telegram bot token from [@BotFather](https://t.me/BotFather)

## Quick start

```bash
git clone https://github.com/YOUR_USERNAME/Onboarding-Bot.git
cd Onboarding-Bot
python -m venv .venv

# Windows
.venv\Scripts\activate
# Linux / macOS
# source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
```

Edit **`.env`**:

| Variable | Required | Description |
|----------|----------|-------------|
| `BOT_TOKEN` | Yes | Telegram bot token |
| `ADMIN_WEB_PASSWORD` | For admin UI | Password for the web panel |
| `ADMIN_WEB_HOST` | No | Default `127.0.0.1` |
| `ADMIN_WEB_PORT` | No | Default `8080` |
| `ADMIN_SESSION_SECRET` | No | Random string for session cookies (recommended in production) |
| `SURVEY_PATH` | No | Path to survey JSON (default `data/survey.json`) |
| `SUBMISSIONS_PATH` | No | Path to JSONL file (default `data/submissions.jsonl`) |

Ensure **`data/survey.json`** exists (sample included).

### Run the Telegram bot only

```bash
python -m bot.main
```

### Run the web admin only

```bash
python -m bot.admin_main
```

Open `http://127.0.0.1:8080` (or your `ADMIN_WEB_PORT`). Use **http**, not https, unless you terminate TLS in front (e.g. nginx).

### Run bot + admin in one process

```bash
python -m bot.run_all
```

## Import questions from `.docx`

Each non-empty paragraph becomes a `text` question. Refine types and rules in `survey.json` afterward.

```bash
python scripts/import_docx.py "path/to/file.docx" -o data/survey_imported.json
```

## Optional: PDF instructions (Russian)

```bash
pip install -r requirements-docs.txt
python scripts/make_instructions_pdf.py
```

Output: `docs/` (see filenames in that folder).

## Deployment notes

- **One bot token → one running polling process.** Do not run the same token on two machines.
- For a VPS, use **systemd** (or similar) for `bot.main` and `bot.admin_main` separately, or a single unit for `bot.run_all`.
- Keep **`.env` out of git**; configure secrets on the server.
- Bind the admin to `127.0.0.1` and use SSH tunnel or a reverse proxy with HTTPS for remote access.

## Project layout

```
bot/           Application code (Telegram handlers, admin app, templates, static)
data/          survey.json (and optional imported JSON); submissions.jsonl is gitignored by default
scripts/       import_docx.py, PDF helper
docs/          Optional instruction PDF/Markdown
```

## License

Use and modify as needed for your organization. Add a `LICENSE` file if you want an explicit open-source terms.
