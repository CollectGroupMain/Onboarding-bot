from __future__ import annotations

import csv
import html
import io
import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware

from bot.config import (
    ADMIN_SESSION_SECRET,
    ADMIN_WEB_PASSWORD,
    SUBMISSIONS_PATH,
    SURVEY_PATH,
)
from bot.submissions import read_submissions
from bot.survey_store import read_survey_dict, validate_survey_dict, write_survey_atomic

PACKAGE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="Pre-boarding bot admin")
app.mount(
    "/static",
    StaticFiles(directory=str(PACKAGE_DIR / "static")),
    name="static",
)


class RequireAdminMiddleware(BaseHTTPMiddleware):
    """Registered before SessionMiddleware in code, but runs after it: the last add_middleware
    wraps the outermost layer, so Session runs first and attaches request.session."""

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path.startswith("/static"):
            return await call_next(request)
        if path in ("/login", "/favicon.ico"):
            return await call_next(request)
        if request.method == "POST" and path == "/login":
            return await call_next(request)
        if request.session.get("admin"):
            return await call_next(request)
        return RedirectResponse(url="/login", status_code=302)


# Order: auth middleware inner, Session outer (added last) so session is available in auth.
app.add_middleware(RequireAdminMiddleware)
app.add_middleware(
    SessionMiddleware,
    secret_key=ADMIN_SESSION_SECRET,
    max_age=60 * 60 * 24 * 7,
    same_site="lax",
)


@app.get("/login", response_class=HTMLResponse)
async def login_get(request: Request) -> HTMLResponse:
    html = (PACKAGE_DIR / "templates" / "login.html").read_text(encoding="utf-8")
    if not ADMIN_WEB_PASSWORD:
        msg = "Set ADMIN_WEB_PASSWORD in your .env file and restart the admin server."
        return HTMLResponse(html.replace("{{ error }}", msg))
    return HTMLResponse(html.replace("{{ error }}", ""))


@app.post("/login", response_class=HTMLResponse)
async def login_post(request: Request) -> Response:
    form = await request.form()
    password = str(form.get("password", ""))
    err_html = (PACKAGE_DIR / "templates" / "login.html").read_text(encoding="utf-8")
    if not ADMIN_WEB_PASSWORD:
        return HTMLResponse(
            err_html.replace(
                "{{ error }}",
                "Password not configured. Set ADMIN_WEB_PASSWORD in .env.",
            ),
            status_code=503,
        )
    if password != ADMIN_WEB_PASSWORD:
        return HTMLResponse(
            err_html.replace("{{ error }}", "Incorrect password."),
            status_code=401,
        )
    request.session["admin"] = True
    return RedirectResponse(url="/", status_code=302)


@app.post("/logout")
async def logout(request: Request) -> RedirectResponse:
    request.session.clear()
    return RedirectResponse(url="/login", status_code=302)


def _render(name: str, **kwargs: Any) -> HTMLResponse:
    tpl_dir = PACKAGE_DIR / "templates"
    base = (tpl_dir / "base.html").read_text(encoding="utf-8")
    body = (tpl_dir / name).read_text(encoding="utf-8")
    content = base.replace("{% block content %}{% endblock %}", body)
    for k, v in kwargs.items():
        content = content.replace("{{ " + k + " }}", str(v))
    return HTMLResponse(content)


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request) -> HTMLResponse:
    subs = read_submissions(SUBMISSIONS_PATH)
    survey = read_survey_dict(SURVEY_PATH)
    nq = len(survey.get("questions") or [])
    return _render(
        "dashboard.html",
        submissions_count=len(subs),
        questions_count=nq,
        survey_path=str(SURVEY_PATH),
        submissions_path=str(SUBMISSIONS_PATH),
    )


@app.get("/submissions", response_class=HTMLResponse)
async def submissions_page(request: Request) -> HTMLResponse:
    subs = read_submissions(SUBMISSIONS_PATH)
    rows = []
    for s in reversed(subs[-200:]):
        sid = (s.get("submission_id", "") or "")[:8]
        ts = str(s.get("completed_at", ""))
        uid = str(s.get("telegram_user_id", ""))
        un = str(s.get("username") or "")
        na = ((s.get("first_name") or "") + " " + (s.get("last_name") or "")).strip()
        n_ans = len(s.get("answers") or [])
        rows.append(
            "<tr><td>"
            + html.escape(sid)
            + "…</td><td>"
            + html.escape(ts)
            + "</td><td>"
            + html.escape(uid)
            + "</td><td>"
            + html.escape(un)
            + "</td><td>"
            + html.escape(na)
            + "</td><td>"
            + html.escape(str(n_ans))
            + "</td></tr>"
        )
    table = "\n".join(rows) if rows else "<tr><td colspan='6'>No records yet</td></tr>"
    return _render("submissions.html", submissions_table=table, total=len(subs))


@app.get("/submissions/download/jsonl")
async def download_jsonl() -> Response:
    if not SUBMISSIONS_PATH.is_file():
        return Response(content="", media_type="application/x-ndjson")
    return Response(
        content=SUBMISSIONS_PATH.read_bytes(),
        media_type="application/x-ndjson",
        headers={
            "Content-Disposition": 'attachment; filename="submissions.jsonl"'
        },
    )


@app.get("/submissions/download/csv")
async def download_csv() -> Response:
    subs = read_submissions(SUBMISSIONS_PATH)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(
        [
            "submission_id",
            "completed_at",
            "telegram_user_id",
            "username",
            "first_name",
            "last_name",
            "question_id",
            "question_text",
            "answer",
        ]
    )
    for s in subs:
        sid = s.get("submission_id", "")
        ts = s.get("completed_at", "")
        uid = s.get("telegram_user_id", "")
        un = s.get("username", "")
        fn = s.get("first_name", "")
        ln = s.get("last_name", "")
        answers = s.get("answers") or []
        if not answers:
            w.writerow([sid, ts, uid, un, fn, ln, "", "", ""])
        else:
            for a in answers:
                w.writerow(
                    [
                        sid,
                        ts,
                        uid,
                        un,
                        fn,
                        ln,
                        a.get("question_id", ""),
                        a.get("question_text", ""),
                        a.get("answer", ""),
                    ]
                )
    data = "\ufeff" + buf.getvalue()
    return Response(
        content=data.encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="submissions.csv"'},
    )


@app.get("/api/survey", response_class=Response)
async def api_survey_get() -> Response:
    data = read_survey_dict(SURVEY_PATH)
    return Response(
        content=json.dumps(data, ensure_ascii=False, indent=2),
        media_type="application/json; charset=utf-8",
    )


@app.put("/api/survey")
async def api_survey_put(request: Request) -> Response:
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")
    ok, msg = validate_survey_dict(body)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    write_survey_atomic(SURVEY_PATH, body)
    return Response(content=json.dumps({"ok": True}), media_type="application/json")


@app.get("/survey", response_class=HTMLResponse)
async def survey_editor(request: Request) -> HTMLResponse:
    return _render("survey_editor.html")
