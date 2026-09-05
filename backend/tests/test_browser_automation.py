"""
Exercises the real Playwright automation (app/automation/browser_automation.py)
against a small, self-contained HTTP server serving the same field markup
as app/api/mock_forms.py — deliberately NOT going through the FastAPI test
client (which uses an in-process ASGI transport with no real socket) or a
real Postgres-backed Job/Profile, since all this module needs is genuine
HTTP + a genuine headless browser. This is what actually proves the
mapper, the CAPTCHA/MFA failsafes, and the fill-and-submit path all work,
independent of the rest of the stack (covered separately by
test_rapid_apply_api.py and the live end-to-end Playwright script).
"""
import http.server
import tempfile
import threading
from types import SimpleNamespace

import pytest

from app.automation.browser_automation import run_application_automation


def _form_body(variant: str) -> str:
    extra = ""
    if variant == "captcha":
        extra = '<div data-testid="captcha" id="captcha-widget">Verify you are not a robot.</div>'
    elif variant == "mfa":
        extra = '<label>Code <input type="text" name="otp_code" data-testid="mfa-code" required></label>'
    elif variant == "unknown_field":
        extra = '<label>Screening question <input type="text" name="q_7f3ac1" required></label>'

    return f"""<!doctype html><html><body>
    <h1>Apply</h1>
    <form id="application-form" method="post" action="/submit" enctype="multipart/form-data">
        <label>Full name <input type="text" name="full_name" required></label>
        <label>Email <input type="email" name="email" required></label>
        <label>Phone <input type="text" name="phone"></label>
        <label>LinkedIn <input type="text" name="linkedin_url"></label>
        <label>Resume <input type="file" name="resume" required></label>
        <label>Cover letter <textarea name="cover_letter"></textarea></label>
        {extra}
        <button type="submit">Submit application</button>
    </form>
    </body></html>"""


class _Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args):  # silence test output
        pass

    def do_GET(self):
        variant = self.path.strip("/").split("/")[-1] or "standard"
        body = _form_body(variant).encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        body = b"<html><body><h1>Application Received</h1></body></html>"
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


@pytest.fixture(scope="module")
def form_server():
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{port}"
    server.shutdown()
    thread.join(timeout=5)


@pytest.fixture
def fake_resume_file():
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(b"%PDF-1.4 fake resume content for automation tests")
        path = f.name
    yield path


def _fake_actors(fake_resume_file):
    profile = SimpleNamespace(first_name="Ada", last_name="Lovelace", phone="555-0100", linkedin_url="https://linkedin.com/in/ada")
    user = SimpleNamespace(email="ada@example.com")
    resume = SimpleNamespace(file_path=fake_resume_file)
    job = SimpleNamespace(id="job-1", title="Analytical Engine Engineer", company=SimpleNamespace(name="Babbage Co"))
    return profile, user, resume, job


async def test_standard_form_fills_and_submits(form_server, fake_resume_file):
    profile, user, resume, job = _fake_actors(fake_resume_file)
    result = await run_application_automation(f"{form_server}/form/standard", profile, user, resume, job, ["Python"])

    assert result.status == "submitted"
    assert "full_name" in result.filled_fields
    assert "email" in result.filled_fields
    assert "resume" in result.filled_fields


async def test_captcha_stops_before_filling_anything(form_server, fake_resume_file):
    profile, user, resume, job = _fake_actors(fake_resume_file)
    result = await run_application_automation(f"{form_server}/form/captcha", profile, user, resume, job, [])

    assert result.status == "failsafe_stopped"
    assert result.reason == "captcha_detected"
    assert result.filled_fields == []


async def test_mfa_stops_before_filling_anything(form_server, fake_resume_file):
    profile, user, resume, job = _fake_actors(fake_resume_file)
    result = await run_application_automation(f"{form_server}/form/mfa", profile, user, resume, job, [])

    assert result.status == "failsafe_stopped"
    assert result.reason == "mfa_required"
    assert result.filled_fields == []


async def test_unknown_required_field_stops_rather_than_guessing(form_server, fake_resume_file):
    profile, user, resume, job = _fake_actors(fake_resume_file)
    result = await run_application_automation(
        f"{form_server}/form/unknown_field", profile, user, resume, job, []
    )

    assert result.status == "failsafe_stopped"
    assert result.reason is not None and result.reason.startswith("unmapped_required_field")
    assert "q_7f3ac1" in result.reason
    assert result.filled_fields == []


async def test_missing_profile_data_for_required_field_also_fails_safe(form_server):
    """No resume on file (file_path is None) means the resume field, even
    though it's *recognized*, has nothing real to fill it with — this must
    never be treated as "skip it", since resume is required."""
    profile = SimpleNamespace(first_name="Ada", last_name=None, phone=None, linkedin_url=None)
    user = SimpleNamespace(email="ada@example.com")
    resume = None
    job = SimpleNamespace(id="job-2", title="Engineer", company=SimpleNamespace(name="Babbage Co"))

    result = await run_application_automation(f"{form_server}/form/standard", profile, user, resume, job, [])

    assert result.status == "failsafe_stopped"
    assert "resume" in result.reason
