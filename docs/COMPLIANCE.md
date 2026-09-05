# Compliance requirements

These constraints apply to every phase of JobPilot AI, without exception.
They are enforced in code review at each phase, not just documented here.

## The system must NOT

- Bypass CAPTCHA, MFA, or login security
- Circumvent anti-bot systems, rate limits, or application restrictions
- Create fake identities or submit fabricated information
- Invent qualifications, work experience, education, or certifications
- Spam applications
- Use stolen credentials
- Automate a portal whose terms prohibit automation

## The system MUST

- Use official APIs, feeds, public career pages, or permitted integrations
  wherever possible
- Fall back to human-assisted application whenever a step can't be
  automated compliantly:

  ```
  Job detected → Job matched → Application prepared → Browser opened →
  Fields prepared/autofilled where permitted → User completes the
  restricted step manually
  ```

- Stop immediately — never attempt to work around — when automation hits a
  CAPTCHA, MFA, an unexpected form, an unknown question, a portal
  restriction, an application limit, or any other automation block. The
  user sees "⚠ Manual Action Required" with their application already
  prepared, plus a way to continue manually.
- Never fabricate an AI-generated answer to an application question. If the
  profile/resume doesn't support an answer, the system returns
  `NEEDS_USER_INPUT` rather than guessing.
- Never store a user's password for any external job portal. JobPilot AI's
  own authentication (this repo's `users` table) is unrelated to and never
  reused for portal credentials.
- Respect source-specific rate limits and polling intervals; never
  aggressively poll a source that prohibits it.
- Provide a global "Stop All Automation" control, plus pause/resume,
  skip-job, blacklist-company, and require-manual-approval controls (Phase
  10).
- Enforce configurable application limits (per hour/day/source/company)
  regardless of any other setting (Phase 10).
- Prevent duplicate applications to the same opportunity via distributed
  locks across workers (Phase 7+).

## Product priority

Optimize for **speed + relevance + accuracy + reliability + compliance** —
never for raw application volume.
