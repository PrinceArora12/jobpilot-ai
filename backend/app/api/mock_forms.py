"""
Mock external application-form server — spec section 56/59. Models "the
company's own application page" that a real Rapid Apply system would have
to fill out, entirely inside infrastructure this build controls. Browser
automation (app/automation/) only ever targets these pages: this project
never automates, and never attempts to bypass anti-bot/CAPTCHA/MFA on, an
actual third-party job portal (spec section 6/51).

Four variants (Job.automation_variant, set at mock-job publish time via
`form_variant`) exist specifically to exercise every failsafe path:
  - standard: a form automation can complete end-to-end.
  - captcha: a CAPTCHA widget the automator must detect and stop at.
  - mfa: a one-time-code field the automator must detect and stop at.
  - unknown_field: a required field with no recognizable name/label, so
    the semantic field mapper's confidence never clears the bar to fill it.

This is not a template-engine app (no Jinja anywhere else in the
codebase), so the HTML is built with plain f-strings — small and easy to
audit for exactly which `name` attributes the automator has to map.
"""
import uuid

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from sqlalchemy import select

from app.database.session import AsyncSessionLocal
from app.models.job import Job

router = APIRouter(prefix="/mock-forms", tags=["mock-forms"])


def _page(body: str) -> str:
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>Mock Application Form</title></head>
<body>{body}</body></html>"""


@router.get("/{job_id}", response_class=HTMLResponse)
async def render_application_form(job_id: uuid.UUID):
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Job).where(Job.id == job_id))
        job = result.scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    variant = job.automation_variant

    extra_fields = ""
    if variant == "captcha":
        extra_fields += (
            '<div data-testid="captcha" id="captcha-widget">'
            "Please verify you're not a robot before continuing.</div>"
        )
    if variant == "mfa":
        extra_fields += (
            '<label>Verification code sent to your phone '
            '<input type="text" name="otp_code" data-testid="mfa-code" required></label>'
        )
    if variant == "unknown_field":
        # A deliberately unrecognizable required field: no "name"/"label"
        # text a semantic mapper could ever confidently match against a
        # profile field, which is exactly the point of this variant.
        extra_fields += (
            '<label>Screening question Q-7f3ac1 '
            '<input type="text" name="q_7f3ac1" required></label>'
        )

    body = f"""
    <h1>Apply to {job.title}</h1>
    <form id="application-form" method="post" action="/api/mock-forms/{job.id}/submit" enctype="multipart/form-data">
        <label>Full name <input type="text" name="full_name" required></label>
        <label>Email <input type="email" name="email" required></label>
        <label>Phone <input type="text" name="phone"></label>
        <label>LinkedIn URL <input type="text" name="linkedin_url"></label>
        <label>Resume <input type="file" name="resume" required></label>
        <label>Cover letter <textarea name="cover_letter"></textarea></label>
        {extra_fields}
        <button type="submit">Submit application</button>
    </form>
    """
    return HTMLResponse(_page(body))


@router.post("/{job_id}/submit", response_class=HTMLResponse)
async def submit_application_form(job_id: uuid.UUID, request: Request):
    """Accepts whatever the automator (or a human, in a browser) posted
    and returns a confirmation page. This mock ATS doesn't need to persist
    the submission anywhere — JobPilot AI's own Application/ApplicationEvent
    records (written by app/services/automation_service.py) are the
    system of record for "did we actually submit this"."""
    form = await request.form()
    if not form.get("full_name") or not form.get("email"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing required fields")
    return HTMLResponse(_page("<h1>Application Received</h1><p>Thanks for applying!</p>"))
