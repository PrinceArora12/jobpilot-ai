"""
Resume text extraction + deterministic structured parsing (spec section 10).

CRITICAL rule this module exists to enforce: it never invents information.
Every field returned is either found verbatim in the resume text (email,
phone, links, skills matched against a known vocabulary) or a raw excerpt
of a section the resume itself labeled (education/experience/projects/
certifications). If something isn't in the text, it's simply absent from
the output — never guessed. The spec's own example output leaves
education/experience/projects/certifications as empty arrays and only
populates skills reliably; this parser matches that bar and adds
best-effort raw section text on top, without fabricating structure the
source document doesn't provide.
"""
import re
from pathlib import Path

from docx import Document
from pypdf import PdfReader

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
# Matches a phone-shaped run of digits/spaces/dashes/dots/parens on a single
# line (line-scoped in _find_phone below, so it can't span across a line
# break into unrelated numbers), then validated by digit count.
PHONE_CANDIDATE_RE = re.compile(r"\+?\(?\d[\d\-\s.()]{5,}\d")
LINKEDIN_RE = re.compile(r"(https?://)?(www\.)?linkedin\.com/\S+", re.IGNORECASE)
GITHUB_RE = re.compile(r"(https?://)?(www\.)?github\.com/\S+", re.IGNORECASE)
PORTFOLIO_URL_RE = re.compile(r"https?://\S+")

SECTION_HEADERS = {
    "education": ["education", "academic background"],
    "experience": ["experience", "work experience", "employment history", "professional experience"],
    "projects": ["projects", "personal projects", "academic projects"],
    "certifications": ["certifications", "certificates", "licenses"],
    "achievements": ["achievements", "awards", "honors"],
    "skills": ["skills", "technical skills", "skills & tools", "core competencies"],
}

# Known vocabulary for deterministic skill matching — extendable, never inferred.
SKILL_VOCABULARY = [
    "Python", "Java", "C++", "C#", "JavaScript", "TypeScript", "Go", "Rust", "Kotlin", "Swift", "Ruby", "PHP", "Scala",
    "React", "Angular", "Vue", "Next.js", "Node.js", "Express", "FastAPI", "Django", "Flask", "Spring", "Spring Boot",
    ".NET", "GraphQL", "REST", "gRPC",
    "PostgreSQL", "MySQL", "MongoDB", "Redis", "SQLite", "Oracle", "DynamoDB", "Cassandra", "Elasticsearch", "SQL",
    "AWS", "Azure", "GCP", "Google Cloud", "Docker", "Kubernetes", "Terraform", "Jenkins", "CI/CD", "Ansible",
    "Kafka", "RabbitMQ", "Spark", "Hadoop", "Airflow", "Celery",
    "TensorFlow", "PyTorch", "scikit-learn", "Keras", "Pandas", "NumPy", "OpenCV", "NLP", "LLM", "Machine Learning",
    "Deep Learning",
    "Power BI", "Tableau", "Excel", "Looker",
    "Git", "Linux", "Bash", "Jira", "Figma",
    "HTML", "CSS", "Tailwind CSS", "Bootstrap",
]


def extract_text_from_pdf(path: str | Path) -> str:
    reader = PdfReader(str(path))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def extract_text_from_docx(path: str | Path) -> str:
    document = Document(str(path))
    return "\n".join(paragraph.text for paragraph in document.paragraphs)


def extract_text(path: str | Path, content_type: str) -> str:
    if content_type == "pdf":
        return extract_text_from_pdf(path)
    if content_type == "docx":
        return extract_text_from_docx(path)
    raise ValueError(f"Unsupported resume file type: {content_type}")


def _find_phone(text: str) -> str | None:
    """Scans line-by-line so a phone number is never assembled from digits
    that happen to land on different lines, then validates by digit count
    (7-15 digits, the ITU-T E.164 range) rather than a rigid chunk shape —
    real resumes format numbers many different ways."""
    for line in text.splitlines():
        for match in PHONE_CANDIDATE_RE.finditer(line):
            candidate = match.group(0)
            digits = re.sub(r"\D", "", candidate)
            if 7 <= len(digits) <= 15:
                return candidate.strip()
    return None


def _extract_contact_info(text: str) -> dict:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    email_match = EMAIL_RE.search(text)
    phone = _find_phone(text)
    linkedin_match = LINKEDIN_RE.search(text)
    github_match = GITHUB_RE.search(text)

    # Heuristic: the resume's own first non-empty line is conventionally the
    # candidate's name. This is a textual observation, not an invention.
    name = lines[0] if lines else None
    if name and (EMAIL_RE.search(name) or len(name) > 60):
        name = None

    return {
        "name": name,
        "email": email_match.group(0) if email_match else None,
        "phone": phone,
        "linkedin": linkedin_match.group(0) if linkedin_match else None,
        "github": github_match.group(0) if github_match else None,
    }


def _extract_skills(text: str) -> list[str]:
    found = []
    lowered = text.lower()
    for skill in SKILL_VOCABULARY:
        pattern = r"(?<![a-zA-Z0-9+#.])" + re.escape(skill.lower()) + r"(?![a-zA-Z0-9+#])"
        if re.search(pattern, lowered):
            found.append(skill)
    return found


def _split_into_sections(text: str) -> dict[str, str]:
    lines = text.splitlines()
    header_positions: list[tuple[int, str]] = []

    for idx, line in enumerate(lines):
        cleaned = line.strip().strip(":").lower()
        for section, aliases in SECTION_HEADERS.items():
            if cleaned in aliases:
                header_positions.append((idx, section))
                break

    sections: dict[str, str] = {}
    for i, (line_idx, section) in enumerate(header_positions):
        end = header_positions[i + 1][0] if i + 1 < len(header_positions) else len(lines)
        body = "\n".join(lines[line_idx + 1 : end]).strip()
        if body:
            sections[section] = body
    return sections


def parse_resume(text: str) -> dict:
    """
    Returns structured data shaped like the spec's example output:
    { name, email, phone, links, skills, education, experience, projects,
      certifications, achievements }.
    Anything not found in the source text is left empty/null — never guessed.
    """
    contact = _extract_contact_info(text)
    sections = _split_into_sections(text)
    skills = _extract_skills(text)

    return {
        "name": contact["name"],
        "email": contact["email"],
        "phone": contact["phone"],
        "links": {
            "linkedin": contact["linkedin"],
            "github": contact["github"],
        },
        "skills": skills,
        "education": [sections["education"]] if "education" in sections else [],
        "experience": [sections["experience"]] if "experience" in sections else [],
        "projects": [sections["projects"]] if "projects" in sections else [],
        "certifications": [sections["certifications"]] if "certifications" in sections else [],
        "achievements": [sections["achievements"]] if "achievements" in sections else [],
    }
