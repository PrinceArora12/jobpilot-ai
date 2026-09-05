"""
Playwright-driven application-form automation — spec sections 20-24/59.

Compliance rules this module exists to enforce, not just document:
  - Only ever navigates to this backend's own mock form server (the
    caller builds the URL from settings.MOCK_FORM_BASE_URL +
    /api/mock-forms/{job_id}) — never a real job portal.
  - CAPTCHA and MFA are *detected and stopped at*, never solved or
    bypassed. Detection happens before a single field is touched.
  - A required field the semantic field mapper can't confidently map is
    also a stop condition, not a guess — this build never fabricates an
    answer to submit on the user's behalf.
Every stop returns a specific machine-readable reason so the resulting
Application can honestly explain, in its timeline, exactly why it needs a
human (spec section 24's "fallback to manual completion").
"""
from dataclasses import dataclass, field

from playwright.async_api import async_playwright

from app.automation.field_mapper import FormField, map_fields
from app.core.logging import get_logger
from app.models.job import Job
from app.models.profile import Profile
from app.models.resume import Resume
from app.models.user import User

logger = get_logger(__name__)

CAPTCHA_SELECTOR = "[data-testid='captcha']"
MFA_SELECTOR = "[data-testid='mfa-code']"
SUBMIT_CONFIRMATION_TEXT = "Application Received"
NAVIGATION_TIMEOUT_MS = 15_000


@dataclass
class AutomationResult:
    status: str  # "submitted" | "failsafe_stopped" | "error"
    reason: str | None = None
    filled_fields: list[str] = field(default_factory=list)


async def _scan_fields(page) -> list[FormField]:
    locators = await page.locator("#application-form [name]").all()
    fields: list[FormField] = []
    for locator in locators:
        name = await locator.get_attribute("name")
        if not name:
            continue
        tag = await locator.evaluate("el => el.tagName.toLowerCase()")
        input_type = await locator.get_attribute("type") or ("textarea" if tag == "textarea" else "text")
        required = (await locator.get_attribute("required")) is not None
        fields.append(FormField(name=name, field_type=input_type, required=required))
    return fields


async def run_application_automation(
    form_url: str,
    profile: Profile,
    user: User,
    resume: Resume | None,
    job: Job,
    matched_skills: list[str],
) -> AutomationResult:
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch()
        try:
            page = await browser.new_page()
            await page.goto(form_url, timeout=NAVIGATION_TIMEOUT_MS)

            # Failsafe checks run before any field is touched.
            if await page.locator(CAPTCHA_SELECTOR).count() > 0:
                logger.info("automation_failsafe_stop", job_id=str(job.id), reason="captcha_detected")
                return AutomationResult(status="failsafe_stopped", reason="captcha_detected")
            if await page.locator(MFA_SELECTOR).count() > 0:
                logger.info("automation_failsafe_stop", job_id=str(job.id), reason="mfa_required")
                return AutomationResult(status="failsafe_stopped", reason="mfa_required")

            fields = await _scan_fields(page)
            mapping = map_fields(fields, profile, user, resume, job, matched_skills)

            if mapping.unmapped_required:
                unmapped_names = ", ".join(f.name for f in mapping.unmapped_required)
                logger.info(
                    "automation_failsafe_stop",
                    job_id=str(job.id),
                    reason="unmapped_required_field",
                    fields=unmapped_names,
                )
                return AutomationResult(
                    status="failsafe_stopped", reason=f"unmapped_required_field:{unmapped_names}"
                )

            filled: list[str] = []
            for mapped_field in mapping.mapped:
                selector = f"#application-form [name='{mapped_field.field.name}']"
                if mapped_field.field.field_type == "file":
                    await page.set_input_files(selector, mapped_field.value)
                else:
                    await page.fill(selector, mapped_field.value)
                filled.append(mapped_field.field.name)

            await page.click("#application-form button[type='submit']")
            await page.wait_for_selector(f"text={SUBMIT_CONFIRMATION_TEXT}", timeout=NAVIGATION_TIMEOUT_MS)

            logger.info("automation_submitted", job_id=str(job.id), filled_fields=filled)
            return AutomationResult(status="submitted", filled_fields=filled)
        except Exception as exc:
            logger.error("automation_error", job_id=str(job.id), error=str(exc))
            return AutomationResult(status="error", reason=str(exc))
        finally:
            await browser.close()
