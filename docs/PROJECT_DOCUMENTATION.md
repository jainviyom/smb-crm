# SMB CRM — Project Documentation

Version 1.0 · Prepared for internal use · Repository: github.com/jainviyom/smb-crm · Live: smb-crm.onrender.com

---

## 1. Executive Summary

SMB CRM is a lightweight, Salesforce-style customer relationship management application built for small sales teams. It tracks leads through conversion into accounts, contacts, and opportunities, visualizes pipeline health on a dashboard, and reports on team performance. It was built as a working prototype from a set of Claude-generated UI mockups, then extended into a fully functional, database-backed application with live create/update flows.

The application intentionally uses a minimal, dependency-light stack (Python/Flask, SQLite, server-rendered HTML, vanilla JS) so it can run and deploy without a Node.js toolchain — a deliberate constraint of the environment it was built in, detailed in §4.

---

## 2. Business Requirements Document (BRD)

### 2.1 Purpose & Background

Small sales teams need a central system of record for leads, customers, and deals, but full-scale CRM platforms (Salesforce, HubSpot) are often more than a small team needs operationally or wants to pay for. SMB CRM provides the core CRM workflow — capture a lead, qualify it, convert it into a customer record, track the resulting deal through a pipeline, and report on outcomes — in a simple, self-hostable application.

### 2.2 Business Objectives

| # | Objective |
|---|---|
| 1 | Give a sales rep a single place to see today's pipeline, tasks, and top deals at a glance. |
| 2 | Make lead qualification and conversion a one-click action instead of manual record creation. |
| 3 | Visualize the deal pipeline as a stage-based board that reflects reality via drag-and-drop. |
| 4 | Report on team and individual performance (revenue won, win rate, lead source mix) over selectable time windows. |
| 5 | Keep the system cheap to run and easy to share (no license cost, deployable on a free hosting tier). |

### 2.3 Target Users / Personas

| Persona | Description | Primary needs |
|---|---|---|
| Sales Rep (e.g. "Maria Chen") | Individual contributor managing their own leads and deals | Daily dashboard, fast lead conversion, drag-drop pipeline updates |
| Sales Manager | Oversees team performance | Reports: leaderboard, win rate, revenue trends |
| Prospective user / evaluator | Someone trying the app via a shared link | Realistic seeded data, obvious navigation, no login friction |

### 2.4 Scope — In Scope (delivered)

- Lead capture, filtering by status, and one-click conversion to Account + Contact + Opportunity
- Account records with tabbed detail view (Overview, Contacts, Opportunities)
- Contact records with an activity timeline
- Opportunity pipeline as a 5-stage kanban board (Qualify → Discovery → Proposal → Negotiation → Closed Won) with drag-and-drop stage updates
- Dashboard with live pipeline totals, task list, and top-deals summary
- Reports with This Month / This Quarter / This Year filtering: revenue won, deals closed, average deal size, lead source breakdown, rep leaderboard
- Global "+ New" creation flow for Leads, Contacts, Accounts, and Opportunities via modal forms
- Public deployment with automatic redeploy on every `git push`

### 2.5 Scope — Out of Scope (current version) / Roadmap

| Item | Status |
|---|---|
| User authentication / multi-user login | Not implemented — single hardcoded "current rep" (Maria Chen) |
| Persistent data storage across redeploys | Not guaranteed — free hosting tier has an ephemeral disk; app auto-reseeds on boot |
| Editing or deleting existing records | Not implemented — only create and, for opportunities, stage-change are supported |
| Email/calendar integration | Not implemented |
| AI assistant / natural-language actions over the CRM | **In progress** — a chat-based assistant using Claude's tool-calling to query and act on CRM data is being designed (see §9 Roadmap Notes) |
| Role-based permissions | Not implemented |

### 2.6 Functional Requirements

| Module | Requirement |
|---|---|
| Dashboard | Show open pipeline value and deal count, computed live from non-closed opportunities |
| Dashboard | Show revenue won this month, new-lead count and week-over-week delta, and win rate |
| Dashboard | Render a bar chart of pipeline value by stage |
| Dashboard | List today's tasks with a persistent toggle-complete checkbox |
| Dashboard | List the 3 largest open opportunities |
| Leads | List all leads with filter tabs for All / New / Working / Qualified / Unqualified, each showing a live count |
| Leads | "Convert" action must create (or reuse) an Account matching the lead's company, create a Contact, open a new Opportunity in the Qualify stage, and mark the lead Qualified |
| Contacts | List all contacts; selecting one shows its details and a reverse-chronological activity timeline |
| Accounts | List all accounts; selecting one shows Overview / Contacts / Opportunities tabs scoped to that account |
| Opportunities | Render all open + this-period Closed Won deals as cards grouped into 5 stage columns with running deal count and total value per column |
| Opportunities | Dragging a card to another column must persist the new stage; dropping into Closed Won marks it closed as of the current date |
| Reports | Recompute Revenue Won, Deals Closed, and Avg Deal Size for the selected period (Month/Quarter/Year) |
| Reports | Show lead source distribution as percentages and a rep leaderboard ranked by revenue won in the period |
| Record creation | A single "+ New" control must offer New Lead, New Contact, New Account, and New Opportunity, each via a modal form that persists directly to the database |

### 2.7 Non-Functional Requirements

| Category | Requirement |
|---|---|
| Cost | Must run on a free-tier hosting plan with no recurring cost for demo/evaluation use |
| Portability | Must not require a Node.js/npm toolchain to build or run |
| Performance | Page loads should complete in under 1 second once the hosting instance is warm |
| Availability | Acceptable to sleep after 15 minutes of inactivity on the free tier (cold start ≈ 30–60s) |
| Data integrity | All computed figures (dashboard, reports) must be derived live from the database, not hardcoded |
| Usability | No login required to explore the demo; navigation limited to a single left sidebar |

### 2.8 Assumptions & Constraints

- Single-tenant, single "current rep" model — there is no session-based user identity.
- SQLite is acceptable as the system of record for a small team's data volume; it is not designed for concurrent-write-heavy, multi-tenant use.
- The reference "today" used for all date-relative logic (task due dates, "this month," win-rate windows) is pinned to a fixed anchor date in application code rather than the system clock, so that seeded demo data remains meaningful regardless of when the app is actually run.
- The original visual reference (a set of AI-generated mockup slides) contained plausible but mutually inconsistent placeholder numbers across screens; this build intentionally replaced them with one internally consistent seeded dataset rather than reproducing the mismatched figures.

### 2.9 Success Criteria

- A new visitor can, without instruction, find and convert a lead, drag a deal across the pipeline, and read the reports page.
- All dashboard and report figures reconcile with the underlying opportunity/lead records at any time.
- The app is reachable at a public URL and recovers automatically after every code change is pushed to `main`.

---

## 3. System Architecture

### 3.1 High-Level Architecture

```
┌────────────────────────────────────────────────────────────────────┐
│                              Browser                               │
│   Jinja-rendered HTML  +  Tailwind (CDN)  +  vanilla JS (app.js)    │
│   - page navigation (full reload)                                  │
│   - fetch() calls for: task toggle, kanban stage drag/drop          │
│   - native <form> POSTs for: lead convert, all "+ New" creates      │
└───────────────────────────────┬──────────────────────────────────--┘
                                 │ HTTP
┌────────────────────────────────▼───────────────────────────────────┐
│                         Flask application (app.py)                 │
│  ┌───────────────┐  ┌────────────────┐  ┌─────────────────────┐    │
│  │  Route layer  │→ │ Business logic │→ │  Jinja2 templates   │    │
│  │ (GET/POST)    │  │ (aggregation,  │  │ (base + 6 pages +    │    │
│  │               │  │  conversion)   │  │  4 modal forms)      │    │
│  └───────┬───────┘  └────────┬───────┘  └─────────────────────┘    │
│          │                   │                                     │
│          └─────────┬─────────┘                                     │
│                     ▼                                              │
│           db.py — sqlite3 connection per request (Flask `g`)        │
└─────────────────────┬────────────────────────────────────────────--┘
                       │
              ┌────────▼─────────┐
              │   crm.db (SQLite) │   auto-seeded on first boot if missing
              │  7 tables, no ORM │   (schema.sql + seed.py)
              └───────────────────┘
```

### 3.2 Component Responsibilities

| Component | File(s) | Responsibility |
|---|---|---|
| Route layer | `app.py` | Maps URLs to handlers; parses form/query input; returns rendered templates or redirects |
| Business logic | `app.py` (inline in handlers) | Lead-conversion logic, pipeline/stage aggregation, date-window filtering for reports |
| Data access | `db.py` | Opens one SQLite connection per request via Flask's `g` object; closes it on teardown |
| Schema & seed data | `schema.sql`, `seed.py` | Defines all 7 tables; populates a realistic, internally consistent demo dataset |
| Presentation | `templates/*.html` | Server-rendered Jinja2 pages sharing a common `base.html` (sidebar, topbar, modals) |
| Client interactivity | `static/js/app.js` | "+ New" dropdown/modal open-close, task-checkbox AJAX toggle, kanban drag-and-drop AJAX |
| Styling | `static/css/app.css` + Tailwind (CDN) | Small set of custom rules (drag-over states, tabular numerals); all layout/utility styling via Tailwind |

### 3.3 Request Lifecycle Examples

**A. Standard page view (e.g. `GET /opportunities`)**
1. Browser requests the page → Flask route queries SQLite for each pipeline stage's open (and this-period closed-won) deals.
2. Data is passed into `opportunities.html`, which extends `base.html`.
3. Server returns fully-rendered HTML; no client-side data fetching is needed for the initial view.

**B. Drag-and-drop stage change**
1. User drags a kanban card to a new column in the browser.
2. `app.js` intercepts the HTML5 drag events and issues `POST /opportunities/<id>/stage` with `{ "stage": "<new stage>" }` as JSON.
3. The Flask handler updates the `opportunities` row (and sets `closed_at` if the new stage is Closed Won) and returns `{ "ok": true }`.
4. The client reloads the page to reflect the new column totals.

**C. Lead conversion**
1. User clicks **Convert** on a lead row → browser submits a plain HTML form (`POST /leads/<id>/convert`).
2. The handler: finds or creates an `accounts` row matching the lead's company → creates a `contacts` row for the lead's name → creates an `opportunities` row in the Qualify stage using the lead's estimated value → marks the lead `Qualified` and `converted = 1`.
3. Handler redirects back to `/leads`; the row now shows "Converted" instead of the Convert button.

**D. Record creation (any of the 4 "+ New" modals)**
1. User opens the global "+ New" menu (rendered once in `base.html`, available on every page) and picks a record type.
2. A modal form (also in `base.html`) is shown client-side; on submit, a plain HTML form POSTs to the matching `/*/new` route.
3. The handler inserts the row and redirects to that record's list/detail page.

### 3.4 Deployment Architecture

```
 Local machine                 GitHub                         Render.com
┌──────────────┐   git push   ┌───────────────────┐  webhook  ┌───────────────────────┐
│  custom-app/  │ ───────────▶│ jainviyom/smb-crm │──────────▶│  Web Service (free)    │
│  (source)     │              │   branch: main     │           │  build: pip install -r │
└──────────────┘              └───────────────────┘           │  requirements.txt      │
                                                                │  start: gunicorn        │
                                                                │  app:app --bind 0.0.0.0│
                                                                │  :$PORT               │
                                                                └───────────┬───────────┘
                                                                            │
                                                              ephemeral disk│ (resets on
                                                                            ▼  redeploy/restart)
                                                                  crm.db auto-seeded
                                                                  on boot if absent
```

`render.yaml` in the repo root lets Render auto-detect the build/start commands as a Blueprint, so connecting the GitHub repo is a one-click setup with no manual dashboard configuration. Auto-deploy is on by default: every push to `main` triggers a new build and rollout.

### 3.5 Data Flow — Lead Conversion (detailed)

```
 leads row                 accounts row               contacts row              opportunities row
┌────────────┐   lookup    ┌─────────────┐             ┌────────────┐            ┌─────────────┐
│ name        │──by company─▶│ name        │  create   │ name        │  create    │ name         │
│ company     │  (create if │ industry    │──────────▶│ title       │──────────▶│ account_id   │
│ status: New │   missing)  │ owner_id    │            │ account_id  │            │ rep_id       │
│ value       │             │ annual_rev. │            │ email/phone │            │ amount       │
└─────┬──────┘             └─────────────┘             └────────────┘            │ stage: Qualify│
      │ update status → Qualified, converted → 1                                 │ close_date    │
      └───────────────────────────────────────────────────────────────────────▶ └─────────────┘
```

---

## 4. Tech Stack

### 4.1 Summary

| Layer | Choice | Notes |
|---|---|---|
| Language / runtime | Python 3.9 | Pre-installed on the build machine |
| Web framework | Flask 3.1 | Minimal, no ORM — direct SQL via `sqlite3` |
| Production server | Gunicorn 23 | WSGI server used on Render; Flask's dev server is used only for local runs |
| Database | SQLite (stdlib `sqlite3`) | File-based (`crm.db`); zero external dependency |
| Templating | Jinja2 (bundled with Flask) | Server-side rendering, one shared `base.html` layout |
| CSS | Tailwind CSS via CDN `<script>` | No build step; utility classes only, plus a handful of custom rules |
| Client JS | Vanilla JS (`static/js/app.js`) | Dropdown/modal control, `fetch()` for two AJAX actions, native HTML5 drag-and-drop |
| Hosting | Render.com (free web service) | Auto-deploy from GitHub via `render.yaml` blueprint |
| Source control | GitHub — `jainviyom/smb-crm` | Public repository |

### 4.2 Why This Stack

The development environment this app was built in has **no Node.js, npm, or Homebrew installed**, which ruled out a conventional React/Next.js + Prisma stack despite that being a common default for this kind of app. Flask + SQLite + server-rendered templates was chosen because it:

- Installs entirely via `pip` (no compiler toolchain, no JS package manager)
- Runs the exact same way locally and in production (`gunicorn app:app`)
- Needs no separate frontend build/bundle step — Tailwind is loaded from a CDN at runtime
- Keeps the whole app auditable in a small number of plain-text files

### 4.3 Dependencies (`requirements.txt`)

```
Flask>=3.1
gunicorn>=23.0
```

No other third-party Python packages are required. The frontend has zero installed dependencies (Tailwind and fonts load from CDN URLs at request time).

---

## 5. Data Model

### 5.1 Entity Overview

```
 reps  ──1───┬── owns ──*  accounts ──1───*  contacts
   │         │                  │
   │         └── owns ──*  opportunities ──*───1 accounts
   │
   └── owns ──* opportunities

 contacts ──1───*  activities

 tasks   (standalone — not foreign-keyed to any other table)
 leads    (standalone until Convert — then produces accounts/contacts/opportunities rows)
```

### 5.2 Table Reference

**reps** — sales users (currently one active "current rep": Maria Chen)
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| name | TEXT | |
| title | TEXT | e.g. "Sales Rep" |

**leads** — inbound prospects prior to qualification
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| name | TEXT | |
| company | TEXT | |
| status | TEXT | `New` / `Working` / `Qualified` / `Unqualified` |
| source | TEXT | Web / Referral / Trade Show / Cold Call / Partner |
| value | INTEGER | Estimated deal value |
| converted | INTEGER | 0/1 flag set by the Convert action |
| created_at | TEXT | Defaults to `datetime('now')` |

**accounts** — customer companies
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| name | TEXT | |
| industry | TEXT | |
| owner_id | INTEGER FK → reps.id | |
| annual_revenue | INTEGER | |

**contacts** — people at an account
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| name | TEXT | |
| title | TEXT | |
| account_id | INTEGER FK → accounts.id | |
| email | TEXT | |
| phone | TEXT | |

**opportunities** — deals in the pipeline
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| name | TEXT | |
| account_id | INTEGER FK → accounts.id | |
| rep_id | INTEGER FK → reps.id | |
| amount | INTEGER | |
| stage | TEXT | Qualify / Discovery / Proposal / Negotiation / Closed Won / Closed Lost |
| close_date | TEXT | Expected close date |
| closed_at | TEXT (nullable) | Set when stage becomes Closed Won (or Closed Lost in seed data) |

**activities** — timeline entries on a contact
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| contact_id | INTEGER FK → contacts.id | |
| kind | TEXT | email / call / meeting |
| description | TEXT | |
| occurred_at | TEXT | |

**tasks** — the dashboard's "due today" list
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| title | TEXT | |
| subtitle | TEXT | e.g. "Acme Logistics · 10:30 AM" |
| due_at | TEXT | |
| done | INTEGER | 0/1, toggled from the dashboard |

---

## 6. Application Reference (Routes)

| Method | Path | Purpose |
|---|---|---|
| GET | `/` | Redirects to `/dashboard` |
| GET | `/dashboard` | Pipeline totals, tasks, top opportunities |
| GET | `/leads` | Lead list, optional `?status=` filter |
| POST | `/leads/<id>/convert` | Converts a lead into Account + Contact + Opportunity |
| POST | `/leads/new` | Creates a lead from the modal form |
| GET | `/contacts` | Contact list + detail (`?id=`) with activity timeline |
| POST | `/contacts/new` | Creates a contact from the modal form |
| GET | `/accounts` | Account list + detail (`?id=`, `?tab=overview|contacts|opportunities`) |
| POST | `/accounts/new` | Creates an account from the modal form |
| GET | `/opportunities` | 5-column kanban board |
| POST | `/opportunities/new` | Creates an opportunity from the modal form |
| POST | `/opportunities/<id>/stage` | AJAX: updates an opportunity's stage (kanban drag-drop) |
| POST | `/tasks/<id>/toggle` | AJAX: toggles a task's done state |
| GET | `/reports` | Revenue/lead-source/leaderboard stats, `?range=month|quarter|year` |

All state-changing routes are `POST`; all `GET` routes are safe/idempotent.

---

## 7. Feature Documentation

**Dashboard** — Greets the current rep by name; shows Open Pipeline (sum of all non-closed opportunity amounts), Won This Month, New Leads (with week-over-week delta), and Win Rate (Closed Won ÷ (Closed Won + Closed Lost)), a bar chart of pipeline value per stage, a task checklist, and the 3 largest open deals.

**Leads** — A filterable table (All / New / Working / Qualified / Unqualified) with a status badge and a **Convert** button on every unconverted row; converted rows show "Converted" in place of the button.

**Contacts** — A left-hand contact list; selecting a contact shows their email/phone and a reverse-chronological activity timeline.

**Accounts** — A left-hand account list; selecting an account shows Annual Revenue and three tabs — Overview (open-opportunity and contact counts), Contacts, and Opportunities — all scoped to that account.

**Opportunities** — A 5-column kanban (Qualify, Discovery, Proposal, Negotiation, Closed Won). Cards show amount, close date, and a stage-based progress bar. Dragging a card to another column persists the change immediately.

**Reports** — A period switcher (This Month / This Quarter / This Year) recomputes Revenue Won, Deals Closed, and Avg Deal Size; also shows a lead-source percentage breakdown and a rep leaderboard by revenue won in the period.

**Record creation** — A single "+ New" control in the top bar opens a dropdown with New Lead / New Contact / New Account / New Opportunity; each opens a modal form that submits directly to its `/*/new` route.

---

## 8. Setup & Deployment Guide

### 8.1 Local development

```bash
git clone https://github.com/jainviyom/smb-crm.git
cd smb-crm
pip3 install -r requirements.txt
python3 seed.py        # creates crm.db with demo data (overwrites existing data)
python3 app.py          # http://127.0.0.1:5050
```

### 8.2 Production (Render)

1. Push to `main` on GitHub.
2. In Render: **New +** → **Blueprint** → connect the repo. Render reads `render.yaml` and pre-fills the service.
3. **Apply** — Render builds with `pip install -r requirements.txt` and starts with `gunicorn app:app --bind 0.0.0.0:$PORT`.
4. Every subsequent push to `main` auto-deploys (`autoDeploy: yes`, `autoDeployTrigger: commit`) with no manual step.

### 8.3 Operational caveats

- **Ephemeral disk**: Render's free tier does not persist the filesystem across restarts/redeploys. `app.py` calls `seed.run()` automatically at import time if `crm.db` is missing, so the app always boots cleanly — but any data entered by visitors is lost on the next restart.
- **Cold start**: the free web service spins down after ~15 minutes idle; the first request afterward takes roughly 30–60 seconds to respond.
- **Single shared dataset**: because there is no per-visitor login, all visitors read and write the same database — one person's "+ New" lead is visible to everyone else using the live link at the same time.

---

## 9. Known Limitations, Risks & Roadmap Notes

| Area | Note |
|---|---|
| Authentication | None. Anyone with the link has full read/write access. Acceptable for an internal demo; not acceptable for real customer data. |
| Editing/deleting records | Not implemented for any entity — only creation and (for opportunities) stage changes are supported. |
| Data persistence | Not durable on the current free hosting tier (see §8.3). |
| Concurrency | SQLite handles the expected demo load fine but is not intended for high-concurrency multi-tenant use. |
| AI Assistant (in progress) | A conversational assistant is being designed to let a rep ask natural-language questions ("which deals are at risk?") and take actions (convert a lead, log a task) via Claude's tool-calling API against this same SQLite schema. This requires an Anthropic API key and a model-cost decision (Opus vs. Sonnet vs. Haiku) that had not been finalized as of this document's writing. |

---

## 10. Appendix

### 10.1 File Structure

```
custom-app/
├── app.py                  # Flask routes + business logic
├── db.py                   # SQLite connection helper (Flask `g`-scoped)
├── schema.sql               # Table definitions
├── seed.py                  # Demo data population
├── requirements.txt
├── render.yaml               # Render Blueprint (build/start commands)
├── .gitignore                # excludes crm.db, __pycache__, .venv
├── README.md
├── docs/
│   └── PROJECT_DOCUMENTATION.md   # this file
├── static/
│   ├── css/app.css
│   └── js/app.js
└── templates/
    ├── base.html            # sidebar, topbar, "+ New" modals (shared by all pages)
    ├── dashboard.html
    ├── leads.html
    ├── contacts.html
    ├── accounts.html
    ├── opportunities.html
    └── reports.html
```

### 10.2 Glossary

| Term | Meaning |
|---|---|
| Lead | An unqualified prospect not yet linked to an Account/Contact/Opportunity |
| Convert | The action that turns a Lead into an Account + Contact + Opportunity |
| Opportunity / Deal | A trackable sales pipeline item with a stage and dollar amount |
| Stage | One of Qualify, Discovery, Proposal, Negotiation, Closed Won, Closed Lost |
| Anchor date | The fixed "today" (2026-07-03) used for all relative-date logic, independent of the server's real clock |

### 10.3 Version History (from commit log)

| Commit | Summary |
|---|---|
| Initial commit | Flask + SQLite + Tailwind SMB CRM: Dashboard, Leads, Contacts, Accounts, Opportunities kanban, Reports |
| Add production deploy config for Render | Auto-seed on boot, gunicorn, `render.yaml` blueprint |
| Add create flows for leads, contacts, accounts, and opportunities | Global "+ New" dropdown + modal forms backed by new POST routes |
