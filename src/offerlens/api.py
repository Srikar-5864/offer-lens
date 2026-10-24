"""Demo API (SPEC §3) with SECURITY.md §3 hardening. The only public surface; SGLang stays on 127.0.0.1."""

from __future__ import annotations

import asyncio
import hmac
import json
import logging
import os
import re
import unicodedata
from collections.abc import Awaitable, Callable
from datetime import date
from typing import Annotated, Any, Literal

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, field_validator
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from offerlens import prompt, sglang_client
from offerlens.settings import ROOT, Role, get_settings

logging.basicConfig(level=logging.INFO, format="%(message)s")
settings = get_settings()
MAX_BODY = 8 * 1024
MAX_TEXT = 2000
_CONTROL = re.compile(r"[\x00-\x09\x0b-\x1f\x7f-\x9f]")
SECURITY_HEADERS = {
    "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self'; font-src 'self'; "
    "img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
}

dev = settings.env == "dev"
app = FastAPI(
    title="OfferLens", debug=False, docs_url="/docs" if dev else None, redoc_url=None,
    openapi_url="/openapi.json" if dev else None,
)  # fmt: skip
def client_ip(request: Request) -> str:
    # Behind Vercel's proxy request.client is the proxy; Vercel sets x-real-ip to the caller and
    # overwrites any client-supplied value, so it is only trusted when running there.
    if os.environ.get("VERCEL") and (ip := request.headers.get("x-real-ip")):
        return ip
    return get_remote_address(request)


limiter = Limiter(key_func=client_ip)
app.state.limiter = limiter
gpu = asyncio.Semaphore(settings.max_concurrency)
http = httpx.AsyncClient()


def problem(status: int, title: str, detail: str) -> JSONResponse:
    return JSONResponse(
        {"type": "about:blank", "title": title, "status": status, "detail": detail},
        status_code=status,
        media_type="application/problem+json",
    )


@app.middleware("http")
async def harden(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
    if request.method not in ("GET", "POST", "HEAD"):
        resp: Response = problem(405, "Method not allowed", "Only GET and POST are supported.")
    elif int(request.headers.get("content-length") or 0) > MAX_BODY:
        resp = problem(413, "Request too large", "Bodies are capped at 8 KB.")
    else:
        resp = await call_next(request)
    resp.headers.update(SECURITY_HEADERS)
    return resp


@app.exception_handler(RequestValidationError)
async def _invalid(_: Request, exc: RequestValidationError) -> JSONResponse:
    first = exc.errors()[0] if exc.errors() else {}
    msg = str(first.get("msg", "Invalid request.")).removeprefix("Value error, ")
    return problem(422, "Invalid request", msg)


@app.exception_handler(RateLimitExceeded)
async def _limited(_: Request, __: RateLimitExceeded) -> JSONResponse:
    return problem(429, "Too many requests", "Slow down — 30 requests per minute.")


@app.exception_handler(HTTPException)
async def _http(_: Request, exc: HTTPException) -> JSONResponse:
    return problem(exc.status_code, "Error", str(exc.detail))


@app.exception_handler(Exception)
async def _crash(_: Request, __: Exception) -> JSONResponse:
    return problem(500, "Internal error", "Something went wrong. Try again.")


def require_key(x_api_key: Annotated[str | None, Header()] = None) -> None:
    expected = settings.offerlens_api_key
    if expected and not hmac.compare_digest((x_api_key or "").encode(), expected.get_secret_value().encode()):
        raise HTTPException(401, "Missing or wrong X-API-Key.")


class CompareIn(BaseModel):
    text: str
    reference_date: date | None = None

    @field_validator("text")
    @classmethod
    def _clean(cls, v: str) -> str:
        v = _CONTROL.sub("", unicodedata.normalize("NFKC", v)).strip()
        if not v:
            raise ValueError("Paste some offer text first.")
        if len(v) > MAX_TEXT:
            raise ValueError(f"That's longer than {MAX_TEXT:,} characters — trim it.")
        return v


class ExtractIn(CompareIn):
    model: Literal["student", "base"] = "student"


async def _extract(text: str, ref: date, role: Role) -> dict[str, Any]:
    async with gpu:
        try:
            res = await sglang_client.aextract(http, role, text, ref, constrained=True)
        except httpx.HTTPError as exc:
            raise HTTPException(503, f"The {role} model server is not reachable.") from exc
    return {
        # Re-validated with Pydantic; invalid output is never passed through.
        "extraction": res.extraction.model_dump(mode="json") if res.extraction else None,
        "latency_ms": round(res.latency_ms),
        "model": role,
        "valid": res.valid,
        "prompt_version": prompt.PROMPT_VERSION,
    }


@app.post("/api/extract", dependencies=[Depends(require_key)])
@limiter.limit("30/minute")
async def extract(request: Request, body: ExtractIn) -> dict[str, Any]:
    return await _extract(body.text, body.reference_date or date.today(), body.model)


@app.post("/api/compare", dependencies=[Depends(require_key)])
@limiter.limit("30/minute")
async def compare(request: Request, body: CompareIn) -> dict[str, Any]:
    ref = body.reference_date or date.today()
    base, student = await asyncio.gather(
        _extract(body.text, ref, "base"), _extract(body.text, ref, "student")
    )
    return {"base": base, "student": student}


@app.get("/api/results")
@limiter.limit("30/minute")
async def results(request: Request) -> Any:
    path = ROOT / "reports" / "results.json"
    if not path.exists():
        raise HTTPException(404, "No results yet — run make eval.")
    return json.loads(path.read_text())


@app.get("/api/examples")
@limiter.limit("30/minute")
async def examples(request: Request) -> Any:
    return json.loads((ROOT / "data" / "demo_examples.json").read_text())


@app.get("/healthz")
async def healthz() -> dict[str, bool]:
    student, base = await asyncio.gather(
        sglang_client.healthy(http, "student"), sglang_client.healthy(http, "base")
    )
    return {"ok": True, "sglang_student": student, "sglang_base": base}


app.mount("/", StaticFiles(directory=ROOT / "web", html=True), name="web")
