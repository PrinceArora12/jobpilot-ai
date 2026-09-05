import io

import pytest
from docx import Document
from reportlab.pdfgen import canvas

RESUME_TEXT_LINES = [
    "Ankita Makkar",
    "ankita@example.com",
    "9876543210",
    "linkedin.com/in/ankita-makkar",
    "",
    "EDUCATION",
    "B.Tech Computer Science, IIT Guwahati, 2027",
    "",
    "SKILLS",
    "Python, Kafka, Kubernetes, AWS",
]


def make_docx_bytes() -> bytes:
    doc = Document()
    for line in RESUME_TEXT_LINES:
        doc.add_paragraph(line)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def make_pdf_bytes() -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    y = 800
    for line in RESUME_TEXT_LINES:
        c.drawString(50, y, line)
        y -= 20
    c.save()
    return buf.getvalue()


@pytest.mark.asyncio
async def test_upload_docx_resume_parses_and_becomes_primary(auth_client):
    files = {
        "file": (
            "resume.docx",
            make_docx_bytes(),
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
    }
    response = await auth_client.post("/api/resumes?label=Software%20Engineer%20Resume", files=files)
    assert response.status_code == 201
    body = response.json()
    assert body["is_primary"] is True
    assert body["parsed_data"]["email"] == "ankita@example.com"
    assert "Python" in body["parsed_data"]["skills"]


@pytest.mark.asyncio
async def test_upload_pdf_resume_parses(auth_client):
    files = {"file": ("resume.pdf", make_pdf_bytes(), "application/pdf")}
    response = await auth_client.post("/api/resumes?label=General%20Resume", files=files)
    assert response.status_code == 201
    body = response.json()
    assert body["file_type"] == "pdf"
    assert "Kafka" in body["parsed_data"]["skills"]


@pytest.mark.asyncio
async def test_rejects_unsupported_file_type(auth_client):
    files = {"file": ("resume.txt", b"hello", "text/plain")}
    response = await auth_client.post("/api/resumes", files=files)
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_multiple_resumes_and_set_primary(auth_client):
    files1 = {
        "file": (
            "a.docx",
            make_docx_bytes(),
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
    }
    files2 = {
        "file": (
            "b.docx",
            make_docx_bytes(),
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
    }
    r1 = await auth_client.post("/api/resumes?label=Resume%20A", files=files1)
    r2 = await auth_client.post("/api/resumes?label=Resume%20B", files=files2)
    assert r1.json()["is_primary"] is True  # first upload
    assert r2.json()["is_primary"] is False

    listing = await auth_client.get("/api/resumes")
    assert len(listing.json()) == 2

    set_primary = await auth_client.put(f"/api/resumes/{r2.json()['id']}", json={"is_primary": True})
    assert set_primary.json()["is_primary"] is True

    listing2 = await auth_client.get("/api/resumes")
    primaries = [r["is_primary"] for r in listing2.json()]
    assert primaries.count(True) == 1


@pytest.mark.asyncio
async def test_delete_resume(auth_client):
    files = {
        "file": (
            "c.docx",
            make_docx_bytes(),
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
    }
    created = await auth_client.post("/api/resumes", files=files)
    resume_id = created.json()["id"]

    deleted = await auth_client.delete(f"/api/resumes/{resume_id}")
    assert deleted.status_code == 204

    fetch = await auth_client.get(f"/api/resumes/{resume_id}")
    assert fetch.status_code == 404


@pytest.mark.asyncio
async def test_resume_scoped_to_owner(client):
    reg_a = await client.post("/api/auth/register", json={"email": "ra@example.com", "password": "supersecret1"})
    token_a = reg_a.json()["access_token"]
    files = {
        "file": (
            "a.docx",
            make_docx_bytes(),
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
    }
    created = await client.post(
        "/api/resumes", files=files, headers={"Authorization": f"Bearer {token_a}"}
    )
    resume_id = created.json()["id"]

    reg_b = await client.post("/api/auth/register", json={"email": "rb@example.com", "password": "supersecret1"})
    token_b = reg_b.json()["access_token"]
    fetch_b = await client.get(
        f"/api/resumes/{resume_id}", headers={"Authorization": f"Bearer {token_b}"}
    )
    assert fetch_b.status_code == 404
