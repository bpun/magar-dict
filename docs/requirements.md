# Magar Dictionary: Requirements Specification

**Version:** 1.0 (Day 1 baseline)
**Status:** Draft for stakeholder sign-off
**Owners:** Product lead, language lead, engineering lead

---

## 1. Purpose and Scope

The Magar Dictionary is a web and mobile learning dictionary for the Magar language, covering three dialects: **Dhut**, **Kham**, and **Kaike**. It lets guests browse and search published content without an account, and lets learners study with flashcards and AI-assisted explanations. Admins maintain the content, dialect forms, and users.

### 1.1 In scope for v1.0
- Public browsing and search (keyword, fuzzy, and semantic) with no login
- Dialect tagging, per-dialect word forms, and per-dialect audio
- Learner accounts, spaced repetition review, favorites, and progress
- AI-generated explanations and examples, gated by review and quotas
- Admin word, tag, user, review, and import management
- Installable Progressive Web App (PWA) for Android and iOS

### 1.2 Out of scope for v1.0
- Native Android or iOS apps (planned for v2)
- Learner offline sync of progress data
- Community editing by untrusted users (learners can only propose changes)
- Voice input or speech recognition
- Monetization, advertising, or in-app purchases
- Dialects beyond Dhut, Kham, and Kaike

---

## 2. Personas

| ID | Persona | Description | Goals | Key constraints |
|---|---|---|---|---|
| P1 | **Guest (Visitor)** | Someone who finds the site through search, a link, or a classroom | Look up a word quickly, hear how it's said, understand which dialect it belongs to | Will leave if they must sign up first; may use an older phone on mobile data |
| P2 | **Learner** | A diaspora child, student, or adult learning Magar | Study regularly, track progress, practice with flashcards, get explanations | Needs clear progress feedback; often studies on a phone |
| P3 | **Admin (Content Manager)** | A staff member who maintains the dictionary | Add and correct words, publish approved content, manage users | Needs an audit trail; must not be able to delete learner data by accident |
| P4 | **Dialect Verifier** | A native speaker from one dialect community who approves that dialect's forms | Confirm that forms are correct for their dialect | Works part-time; may be less comfortable with software |

**Implementation note for P4:** In v1.0, verifiers are a permission on an admin account, limited to the dialects they are assigned to (`verifier_dialects`). Verifiers are not a separate login role. This decision is recorded as OD-1 in Section 12.

---

## 3. User Stories and Acceptance Criteria

### 3.1 Guest (P1)

| ID | User story | Acceptance criteria |
|---|---|---|
| US-01 | As a guest, I want to search for a word without logging in, so I can get an answer immediately. | Search works with no account; results show only published words. |
| US-02 | As a guest, I want to filter results by dialect, so I see the form that matches my community. | Dialect filter (Dhut, Kham, Kaike, All) changes results; each result shows its dialect labels. |
| US-03 | As a guest, I want to see a word's form in each dialect, so I can compare them. | Word page shows all published dialect forms as tabs or side by side, with "shared" or "dialect-specific" badges. |
| US-04 | As a guest, I want to hear a word pronounced, so I can learn the sound. | Each dialect form with audio has a play button; audio is labeled "approximate pronunciation" until native recordings exist. |
| US-05 | As a guest, I want to be told when a dialect form is missing, so I'm not misled. | When no form exists for the chosen dialect, the page shows the shared form labeled "general Magar." Another dialect's form is never substituted silently. |
| US-06 | As a guest, I want to find a word by typing an English or Nepali meaning, so I don't need to know the Magar spelling. | Search matches English and Nepali glosses; semantic mode returns related meanings. |
| US-07 | As a guest, I want typos to still return results, so I don't have to spell perfectly. | Fuzzy matching returns the intended word for common one- and two-character typos. |
| US-08 | As a guest, I want to create an account when I'm ready, so I can start learning. | Registration is reachable from every page; the guest keeps their current search context. |

### 3.2 Learner (P2)

| ID | User story | Acceptance criteria |
|---|---|---|
| US-09 | As a learner, I want to register and verify my email, so my account is secure. | Verification link expires after 24 hours; unverified accounts cannot save progress. |
| US-10 | As a learner, I want to set my preferred dialect, so my searches default to it. | Setting persists across sessions; search and browse use it as the default filter. |
| US-11 | As a learner, I want a daily review of due words, so I remember them over time. | Review shows words due today using SM-2 scheduling; ratings Again, Hard, Good, Easy update the schedule. |
| US-12 | As a learner, I want to see my progress by dialect, so I know where to focus. | Dashboard shows streak, words learned, words due, and progress per dialect. |
| US-13 | As a learner, I want to save words and add private notes, so I can revisit them. | Favorites and notes are visible only to me; deleting a word removes it from favorites without error. |
| US-14 | As a learner, I want AI explanations and examples, so I understand grammar and usage. | Each AI output is labeled as AI-generated and held for review; it is visible to others only after approval. |
| US-15 | As a learner, I want a daily limit on AI requests, so the service stays affordable. | 20 AI generations per day; the remaining count is shown; the limit resets at 00:00 UTC. |
| US-16 | As a learner, I want to suggest a correction, so I can help improve the dictionary. | Correction is submitted as a revision; the live entry does not change until an admin approves it. |
| US-17 | As a learner, I want to delete my account and export my data, so I control my personal information. | Account deletion removes personal data within 30 days; data export returns a JSON file of my profile, progress, favorites, and notes. |

### 3.3 Admin (P3) and Verifier (P4)

| ID | User story | Acceptance criteria |
|---|---|---|
| US-18 | As an admin, I want to create and edit words, so the dictionary grows. | Create and edit work; every change is written to the audit log with before and after values. |
| US-19 | As an admin, I want to tag a word with one, two, or three dialects, so it appears in the right places. | Tag set is validated against the dialect rules; invalid combinations are rejected with a clear message. |
| US-20 | As an admin, I want to add a form for each dialect, so every dialect is represented. | Each dialect tag requires a form before publication; the form records its verifier. |
| US-21 | As a verifier, I want to approve only forms for my own dialect, so my approvals are meaningful. | A verifier can approve only forms for dialects in their `verifier_dialects` list. |
| US-22 | As an admin, I want to review AI output beside the original entry, so I can approve or fix it. | Review queue shows AI output and source entry side by side; actions are approve, edit-and-approve, and reject. |
| US-23 | As an admin, I want to publish a word only when its rules are met, so guests never see incomplete content. | Publish fails with a list of missing forms, missing verifiers, or missing sources. |
| US-24 | As an admin, I want to import word lists from CSV, so I can add many entries at once. | Import runs validation, shows errors and warnings before saving, and imports everything in one transaction or nothing. |
| US-25 | As an admin, I want to manage user accounts, so I can handle roles and misuse. | Admins can change roles, disable and enable accounts; the last active admin cannot be demoted or disabled. |
| US-26 | As an admin, I want to see how complete each dialect is, so I can prioritize work. | Coverage report shows word count and missing-form count per dialect. |
| US-27 | As an admin, I want to keep edits from overwriting each other, so no one loses work silently. | Stale saves return a conflict; the admin is shown the current version. |

### 3.4 Mobile user

| ID | User story | Acceptance criteria |
|---|---|---|
| US-28 | As a mobile user, I want to add the app to my home screen, so I can open it like an app. | Installable on Android (Chrome) and iOS (Safari, Add to Home Screen); manifest and icons present. |
| US-29 | As a mobile user, I want recently viewed public words to open offline, so I can study without signal. | Last 200 public words viewed are available offline; authenticated pages are never cached. |

---

## 4. Permission Matrix

Legend: ✅ allowed, ❌ not allowed, 🔶 allowed only within assigned scope.

| Capability | Guest | Learner | Admin | Verifier (admin scope) |
|---|:-:|:-:|:-:|:-:|
| Browse and search published words | ✅ | ✅ | ✅ | ✅ |
| Filter by dialect | ✅ | ✅ | ✅ | ✅ |
| View all published dialect forms | ✅ | ✅ | ✅ | ✅ |
| Play public audio | ✅ | ✅ | ✅ | ✅ |
| See approved AI content | ✅ | ✅ | ✅ | ✅ |
| Save preferred dialect | ❌ | ✅ | ✅ | ✅ |
| Generate AI content (quota) | ❌ | ✅ (20/day) | ✅ (unlimited) | ✅ (unlimited) |
| Flashcards and progress | ❌ | ✅ | ✅ | ✅ |
| Favorites and private notes | ❌ | ✅ | ✅ | ✅ |
| Submit correction or topic suggestion | ❌ | ✅ | ✅ | ✅ |
| Create or edit words | ❌ | ❌ | ✅ | ❌ |
| Add or change dialect tags | ❌ | ❌ | ✅ | ❌ |
| Create or edit a dialect form | ❌ | ❌ | ✅ | 🔶 (own dialects) |
| Approve a dialect form | ❌ | ❌ | ✅ | 🔶 (own dialects) |
| Approve AI or learner submissions | ❌ | ❌ | ✅ | 🔶 (own dialects) |
| Publish or archive a word | ❌ | ❌ | ✅ | ❌ |
| Create topic, level, or source tags | ❌ | ❌ | ✅ | ❌ |
| Manage users and roles | ❌ | ❌ | ✅ | ❌ |
| CSV import | ❌ | ❌ | ✅ | ❌ |
| View audit log | ❌ | ❌ | ✅ | ❌ |
| View dialect coverage report | ❌ | ❌ | ✅ | ✅ (own dialects) |
| Delete own account and export data | ❌ | ✅ | ✅ | ✅ |

**Rules that apply to every row:**
1. Guests and learners only ever receive words and forms with status `PUBLISHED`.
2. Every admin route passes through one role-check dependency and is covered by a permission test.
3. The last active admin cannot be demoted or disabled.
4. Admin actions that change content or access are written to the audit log, which is append-only.

---

## 5. Functional Requirements

### 5.1 Content and tags
- **FR-01** Each word has a unique slug, an English gloss, a Nepali gloss, and a part of speech from a controlled list.
- **FR-02** Each word has one or more dialect tags (`dhut`, `kham`, `kaike`). A word tagged with all three is marked "shared."
- **FR-03** Each dialect tag on a word has a matching form record with script, romanization, and optional IPA and audio.
- **FR-04** A word cannot be published unless every dialect tag has a published form, and each form has a named verifier.
- **FR-05** Dialect tags are managed only by admins. AI generation cannot add or change them.
- **FR-06** Topic, level, and source tags are optional and may be added by admins. Learners may suggest topic tags for review.
- **FR-07** Every word records its source and license. Records without a permitted source fail validation.

### 5.2 Status workflow
- **FR-08** Words move through `DRAFT → NEEDS_REVIEW → PUBLISHED → ARCHIVED`, with `REJECTED` as a branch. Invalid transitions are refused.
- **FR-09** Each dialect form has its own status, so one dialect can be published while another is in review.
- **FR-10** Every status change records the actor, timestamp, and reason in the audit log.

### 5.3 Search and browse
- **FR-11** Search matches Magar script, romanization, English gloss, and Nepali gloss.
- **FR-12** Search modes: keyword (prefix and full-text), fuzzy (typo tolerance), semantic (meaning-based), and hybrid (combined ranking).
- **FR-13** Dialect filter applies to browse, search, and detail views. Results from different dialects are never mixed in one cache entry.
- **FR-14** Browse is paginated by starting letter and returns 20 results per page by default, with a maximum of 100.

### 5.4 Learning
- **FR-15** SM-2 scheduling updates ease, interval, and due date from a 0–5 quality rating.
- **FR-16** A learner's daily review queue contains words due on or before today, ordered by due date.
- **FR-17** Progress summary includes words learned, words due, current streak, and counts by dialect.

### 5.5 AI features
- **FR-18** AI generates explanations and examples only for published words, using verified glosses and approved examples as context.
- **FR-19** Every AI output is saved with status `NEEDS_REVIEW`, the prompt version, the model name, and the dialect it targets.
- **FR-20** AI output is visible to the public only after a verifier for that dialect approves it.
- **FR-21** Learners are limited to 20 AI generations per day. Admins are not limited.
- **FR-22** Identical requests (same word, dialect, kind, prompt version, and model) are served from cache.
- **FR-23** AI responses are validated against a schema. Invalid output is rejected and logged.
- **FR-24** Prompts must not contain personal data about learners.

### 5.6 Accounts and administration
- **FR-25** Registration requires email verification before the account can save progress.
- **FR-26** Login locks an email for 15 minutes after 5 failed attempts within 15 minutes.
- **FR-27** Access tokens last 15 minutes. Refresh tokens rotate on each use; reuse of an old token revokes the token family.
- **FR-28** Password reset returns the same response whether or not the email is registered.
- **FR-29** Admin edits use optimistic locking. A stale save returns HTTP 409.
- **FR-30** CSV import validates every row, reports errors and warnings, and commits all rows or none.
- **FR-31** Account deletion removes personal data within 30 days and keeps anonymized audit records.
- **FR-32** Data export returns the user's profile, progress, favorites, and notes as JSON.

### 5.7 Audio
- **FR-33** Audio is stored per dialect form, not per word.
- **FR-34** Audio files are served through short-lived signed URLs from a private bucket.
- **FR-35** Each audio record stores its dialect, source (synthetic or native), and speaker attribution if native.

---

## 6. Non-Functional Requirements

### 6.1 Performance
| ID | Requirement | Measurement |
|---|---|---|
| NFR-01 | Search API responds in under **150 ms at p95** (server-side) | Measured on staging with a dataset of up to 20,000 entries, at 50 concurrent requests |
| NFR-02 | Word detail and browse pages respond in under **300 ms at p95** under 100 requests per second | Locust load test, run before each release |
| NFR-03 | Time to interactive on a mid-range Android phone over 4G is under **3 seconds** | Lighthouse mobile profile |
| NFR-04 | Public pages are cacheable at the CDN, with dialect in the cache key | Response header check in CI |

### 6.2 Availability and reliability
| ID | Requirement | Notes |
|---|---|---|
| NFR-05 | **99.5% monthly uptime** for public pages and API | 99.5% of a 30-day month (43,200 minutes) allows about **216 minutes (3 hours 36 minutes)** of downtime. Planned maintenance counts toward this budget unless announced in advance. |
| NFR-06 | Recovery point objective (RPO): **24 hours** | Daily automated database backups |
| NFR-07 | Recovery time objective (RTO): **4 hours** | Restore procedure tested before launch (Day 29) |
| NFR-08 | Database migrations are reversible | Every migration has a tested downgrade |
| NFR-09 | `/health` reports database and Redis status | Used by the uptime monitor |

### 6.3 Accessibility (WCAG 2.1 AA)
| ID | Requirement |
|---|---|
| NFR-10 | Text contrast is at least **4.5:1** (3:1 for large text and UI components) |
| NFR-11 | All functions work with keyboard alone, with a visible focus indicator |
| NFR-12 | Every form field has a label; errors are announced to screen readers |
| NFR-13 | Content reflows at 320 px width and remains usable at 200% text zoom |
| NFR-14 | Audio controls have accessible names and do not autoplay |
| NFR-15 | Devanagari text uses a self-hosted font with a readable fallback stack |
| NFR-16 | Page language is set (`lang="en"` or `lang="ne"`), and dialect forms are marked with the correct `lang` attribute where applicable |

### 6.4 Security and privacy
| ID | Requirement |
|---|---|
| NFR-17 | Passwords hashed with Argon2; minimum 10 characters; checked against breached-password lists |
| NFR-18 | Session cookies are HttpOnly, Secure, and SameSite=Strict |
| NFR-19 | Content Security Policy blocks inline scripts |
| NFR-20 | All state-changing web forms are protected by CSRF tokens |
| NFR-21 | Rate limits on login, registration, password reset, search, and AI endpoints |
| NFR-22 | No known high-severity findings from bandit, pip-audit, or OWASP ZAP at release |
| NFR-23 | Secrets are stored only in the hosting platform's secret store |
| NFR-24 | Learner data is encrypted at rest and in transit |
| NFR-25 | Privacy policy and terms are published before public launch |

### 6.5 Compatibility
| ID | Requirement |
|---|---|
| NFR-26 | Supported browsers: latest two versions of Chrome, Edge, Firefox, Safari; Samsung Internet |
| NFR-27 | Supported mobile OS: Android 10 and later; iOS 16 and later |
| NFR-28 | Layout tested at 360 px width (common Android size) and 1280 px width |

### 6.6 Maintainability and quality
| ID | Requirement |
|---|---|
| NFR-29 | Code passes ruff, black, and mypy (strict) through pre-commit and CI |
| NFR-30 | Unit and API test coverage of at least 80% on `core/`, `services/`, and `api/` |
| NFR-31 | Every merge to `main` runs CI; deployments run from CI only |
| NFR-32 | Architecture decisions are recorded in `docs/adr/` |

---

## 7. Data Requirements

- **Sources:** Every entry records its source and license in the `sources` table. Unlicensed data cannot be imported.
- **Retention:** Learner progress is kept while the account is active. After deletion, personal data is removed within 30 days. Audit records are kept with the actor anonymized.
- **Language data:** Each dialect form is verified by a named native speaker. Verifier names are displayed with the form, subject to each verifier's consent.
- **Backups:** Daily encrypted backups, retained for 30 days.

---

## 8. Constraints and Assumptions

- **C-1** The team has one language lead with access to native speakers for at least two of the three dialects. Kaike and Dhut verifiers are required before publication of their forms.
- **C-2** Monthly AI costs must stay within the budget approved by the product lead. An alert fires at 80% of budget.
- **C-3** A solo developer can build v1.0 in 30 days with the MVP cut line from the plan. The scope beyond the cut line moves to v1.1.
- **C-4** Initial dictionary data is small (a few hundred to a few thousand entries). Performance targets are set for up to 20,000 entries.
- **A-1** Learners and guests have reliable access to the internet at least once a day.
- **A-2** Community organizations grant permission to use the source data for public display.

---

## 9. Glossary

| Term | Meaning |
|---|---|
| Dialect | A regional variety of Magar: Dhut, Kham, or Kaike |
| Form | The spelling, romanization, pronunciation, and audio of one word in one dialect |
| Shared word | A word tagged with all three dialects, shown as "shared across Dhut, Kham, Kaike" |
| General Magar | The shared form shown when no dialect-specific form exists |
| Verifier | A native speaker authorized to approve forms for their dialect |
| SM-2 | A spaced repetition algorithm that schedules reviews based on recall quality |
| PUBLISHED | The only status visible to guests and learners |

---

## 10. Out-of-Scope Decisions Deferred to v1.1

- Community editing rights beyond suggestions
- Native recorded audio pipeline
- Learner offline progress sync
- Flutter or native mobile apps

---

## 11. Acceptance Criteria for This Document

This document is accepted when:
1. The product lead, language lead, and engineering lead have each signed off.
2. Each dialect has a named verifier (or an open decision is recorded for that dialect).
3. Open decisions in Section 12 are resolved or have an owner and due date.

---

## 12. Open Decisions

| ID | Decision | Options | Owner | Due |
|---|---|---|---|---|
| OD-1 | How are dialect verifiers modeled? | (a) Admin account with `verifier_dialects` list (recommended for v1); (b) separate `verifier` role | Engineering lead | Day 2 |
| OD-2 | Which LLM provider? | OpenAI or Anthropic, behind the same adapter | Engineering lead | Day 19 |
| OD-3 | Which hosting platform? | Render or Fly.io | Engineering lead | Day 29 |
| OD-4 | Which TTS for interim audio? | gTTS (dev) or Coqui TTS (prod) | Language lead | Day 21 |
| OD-5 | Are community forum comments in v1? | Yes (moderation needed) or no (defer to v1.1) | Product lead | Day 2 |
