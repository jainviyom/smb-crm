# SMB CRM — Project Documentation

Version 2.0 · Prepared for internal use · Repository: github.com/jainviyom/smb-crm · Live: smb-crm.onrender.com

---

## 1. Executive Summary

SMB CRM is a lightweight, Salesforce-style customer relationship management application built for small sales teams. It tracks leads through conversion into accounts, contacts, and opportunities, visualizes pipeline health on a dashboard, and reports on team performance. It was built as a working prototype from a set of Claude-generated UI mockups, then extended into a fully functional, database-backed application with login, full CRUD (create/edit/delete), search, notifications, CSV import/export, and reporting.

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
| 6 | Give each rep their own login so pipeline and performance data can eventually be scoped per-user. |

### 2.3 Target Users / Personas

| Persona | Description | Primary needs |
|---|---|---|
| Sales Rep (e.g. "Maria Chen") | Individual contributor managing their own leads and deals | Daily dashboard, fast lead conversion, drag-drop pipeline updates, edit/delete their own records |
| Sales Manager | Oversees team performance | Reports: leaderboard, win rate, revenue trends |
| Prospective user / evaluator | Someone trying the app via a shared link | Demo login credentials, realistic seeded data, obvious navigation |

### 2.4 Scope — In Scope (delivered)

- **Session-based login** for named reps (demo accounts for Maria Chen and Sam Patel); every page requires sign-in
- Lead capture, filtering by status, and one-click conversion to Account + Contact + Opportunity
- **Full edit and delete** for Leads, Contacts, Accounts, and Opportunities (not just create)
- **Global search** across leads, contacts, accounts, and opportunities from the header search bar
- Account records with tabbed detail view (Overview, Contacts, Opportunities)
- Contact records with an activity timeline, **now auto-populated** on lead conversion and opportunity stage changes
- Opportunity pipeline as a 5-stage kanban board (Qualify → Discovery → Proposal → Negotiation → Closed Won) with drag-and-drop stage updates
- Dashboard with live pipeline totals, task list, and top-deals summary
- **Notifications dropdown** surfacing open tasks and recently won deals
- Reports with This Month / This Quarter / This Year filtering: revenue won, deals closed, average deal size, lead source breakdown, rep leaderboard, and a **6-month revenue trend chart**
- **CSV export** for Leads, Contacts, Accounts, and Opportunities; **CSV import** for Leads
- Global "+ New" creation flow for Leads, Contacts, Accounts, and Opportunities via modal forms
- Public deployment with automatic redeploy on every `git push`

### 2.5 Scope — Out of Scope (current version) / Roadmap

| Item | Status |
|---|---|
| Persistent data storage across redeploys | Not guaranteed — free hosting tier has an ephemeral disk; app auto-reseeds on boot |
| Stable session secret on the hosted deployment | Recommended but not yet configured — see §8.3 |
| Email/calendar integration | Not started |
| AI assistant / natural-language actions over the CRM | **In progress** — a chat-based assistant using Claude's tool-calling to query and act on CRM data is being designed (see §9 Roadmap Notes) |
| Role-based permissions | Not started — any logged-in rep can see and edit every record, not just their own |
| Password reset / self-service account creation | Not started — demo accounts are seeded, not self-registered |

### 2.6 Functional Requirements

| Module | Requirement |
|---|---|
| Authentication | Require a valid rep login (email + password) before any page loads; provide logout |
| Dashboard | Show open pipeline value and deal count, computed live from non-closed opportunities |
| Dashboard | Show revenue won this month, new-lead count and week-over-week delta, and win rate |
| Dashboard | Render a bar chart of pipeline value by stage |
| Dashboard | List today's tasks with a persistent toggle-complete checkbox |
| Dashboard | List the 3 largest open opportunities |
| Leads | List all leads with filter tabs for All / New / Working / Qualified / Unqualified, each showing a live count |
| Leads | "Convert" action must create (or reuse) an Account matching the lead's company, create a Contact, open a new Opportunity in the Qualify stage, mark the lead Qualified, and log a conversion activity on the contact |
| Leads | Support editing a lead's fields and deleting a lead |
| Leads | Support CSV export of all leads and CSV import of new leads |
| Contacts | List all contacts; selecting one shows its details and a reverse-chronological activity timeline |
| Contacts | Support editing a contact's fields and deleting a contact (cascades to its activities) |
| Accounts | List all accounts; selecting one shows Overview / Contacts / Opportunities tabs scoped to that account |
| Accounts | Support editing an account's fields and deleting an account (cascades to its contacts and opportunities) |
| Opportunities | Render all open + this-period Closed Won deals as cards grouped into 5 stage columns with running deal count and total value per column |
| Opportunities | Dragging a card to another column must persist the new stage, log an activity on the account's primary contact, and mark it closed if dropped into Closed Won |
| Opportunities | Support editing an opportunity's fields (including stage) and deleting an opportunity |
| Search | The header search bar must query leads, contacts, accounts, and opportunities and group results by type |
| Notifications | The bell icon must show a count badge and a dropdown of open tasks and recently won deals |
| Reports | Recompute Revenue Won, Deals Closed, and Avg Deal Size for the selected period (Month/Quarter/Year) |
| Reports | Show lead source distribution as percentages, a rep leaderboard ranked by revenue won in the period, and a 6-month revenue trend chart |
| Record creation | A single "+ New" control must offer New Lead, New Contact, New Account, and New Opportunity, each via a modal form that persists directly to the database |

### 2.7 Non-Functional Requirements

| Category | Requirement |
|---|---|
| Cost | Must run on a free-tier hosting plan with no recurring cost for demo/evaluation use |
| Portability | Must not require a Node.js/npm toolchain to build or run |
| Performance | Page loads should complete in under 1 second once the hosting instance is warm |
| Availability | Acceptable to sleep after 15 minutes of inactivity on the free tier (cold start ≈ 30–60s) |
| Data integrity | All computed figures (dashboard, reports) must be derived live from the database, not hardcoded |
| Security | Passwords must be hashed at rest (never stored in plaintext); every page except the login screen must require an active session |
| Usability | Demo credentials must be visible on the login screen so evaluators aren't blocked; navigation limited to a single left sidebar |

### 2.8 Assumptions & Constraints

- Multi-user via session login, but **not** multi-tenant — every logged-in rep can see and edit every other rep's records; there is no per-rep data scoping yet.
- SQLite is acceptable as the system of record for a small team's data volume; it is not designed for concurrent-write-heavy, multi-tenant use.
- The reference "today" used for all date-relative logic (task due dates, "this month," win-rate windows) is pinned to a fixed anchor date in application code rather than the system clock, so that seeded demo data remains meaningful regardless of when the app is actually run.
- The original visual reference (a set of AI-generated mockup slides) contained plausible but mutually inconsistent placeholder numbers across screens; this build intentionally replaced them with one internally consistent seeded dataset rather than reproducing the mismatched figures.
- Session cookies are signed with a Flask `SECRET_KEY` that falls back to a randomly generated value at process start if the environment variable isn't set — meaning, on the hosted deployment, everyone is logged out whenever the instance restarts unless `SECRET_KEY` is fixed via an environment variable (see §8.3).

### 2.9 Success Criteria

- A new visitor can sign in with the published demo credentials, find and convert a lead, drag a deal across the pipeline, edit or delete a record, search for something by name, and read the reports page — all without instruction.
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
│   - native <form> POSTs for: login, convert, +New/edit/delete       │
└───────────────────────────────┬──────────────────────────────────--┘
                                 │ HTTP (session cookie)
┌────────────────────────────────▼───────────────────────────────────┐
│                         Flask application (app.py)                 │
│  ┌───────────────┐  ┌────────────────┐  ┌─────────────────────┐    │
│  │ before_request │→ │  Route layer   │→ │ Jinja2 templates    │    │
│  │ (login guard)  │  │ (GET/POST,     │  │ (base + 8 pages +    │    │
│  │                │  │  business      │  │  4 new + 4 edit      │    │
│  │                │  │  logic)        │  │  modal forms)        │    │
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
| Auth guard | `app.py` (`before_request`) | Redirects any request without a session `rep_id` to `/login`, except the login page and static assets |
| Route layer | `app.py` | Maps URLs to handlers; parses form/query input; returns rendered templates or redirects |
| Business logic | `app.py` (inline in handlers) | Lead-conversion logic, activity auto-logging, pipeline/stage aggregation, date-window filtering, search queries, CSV read/write |
| Data access | `db.py` | Opens one SQLite connection per request via Flask's `g` object; closes it on teardown |
| Schema & seed data | `schema.sql`, `seed.py` | Defines all 7 tables (reps now carry `email`/`password_hash`); populates a realistic, internally consistent demo dataset with two login-ready reps |
| Presentation | `templates/*.html` | Server-rendered Jinja2 pages sharing a common `base.html` (sidebar, topbar, search form, notifications, "+ New" and edit modals); standalone `login.html` outside the shared layout |
| Client interactivity | `static/js/app.js` | "+ New"/edit dropdown and modal open-close (including populating edit forms from `data-*` attributes), notifications dropdown toggle, task-checkbox AJAX toggle, kanban drag-and-drop AJAX |
| Styling | `static/css/app.css` + Tailwind (CDN) | Small set of custom rules (drag-over states, tabular numerals); all layout/utility styling via Tailwind |

### 3.3 Request Lifecycle Examples

**A. Standard page view (e.g. `GET /opportunities`)**
1. `before_request` checks the session for `rep_id`; if absent, redirects to `/login?next=/opportunities`.
2. The route queries SQLite for each pipeline stage's open (and this-period closed-won) deals.
3. Data is passed into `opportunities.html`, which extends `base.html`.
4. Server returns fully-rendered HTML; no client-side data fetching is needed for the initial view.

**B. Login**
1. User submits email + password on `/login`.
2. The handler looks up the rep by email and verifies the password with `werkzeug.security.check_password_hash` against the stored hash.
3. On success, `session["rep_id"]` is set and the user is redirected to the originally requested page (or the dashboard).

**C. Drag-and-drop stage change**
1. User drags a kanban card to a new column in the browser.
2. `app.js` intercepts the HTML5 drag events and issues `POST /opportunities/<id>/stage` with `{ "stage": "<new stage>" }` as JSON.
3. The Flask handler updates the `opportunities` row (setting `closed_at` if the new stage is Closed Won), logs an activity on the account's first contact if the stage actually changed, and returns `{ "ok": true }`.
4. The client reloads the page to reflect the new column totals.

**D. Lead conversion**
1. User clicks **Convert** on a lead row → browser submits a plain HTML form (`POST /leads/<id>/convert`).
2. The handler: finds or creates an `accounts` row matching the lead's company → creates (or reuses) a `contacts` row for the lead's name → creates an `opportunities` row in the Qualify stage using the lead's estimated value → marks the lead `Qualified` and `converted = 1` → logs a "Converted from lead" activity on the contact.
3. Handler redirects back to `/leads`; the row now shows "Converted" instead of the Convert button.

**E. Edit an existing record**
1. User clicks **Edit** on a row/card. A JS handler reads that element's `data-*` attributes (id, and every editable field), fills the shared edit-modal's form fields, points the form's `action` at `/<entity>/<id>/edit`, and opens the modal.
2. On submit, the Flask handler updates the row directly by ID and redirects back to the list/detail page.

**F. Delete an existing record**
1. User clicks **Delete**; a `confirm()` dialog gates the submit.
2. The form POSTs to `/<entity>/<id>/delete`. For Contacts, related activities are deleted first; for Accounts, related contacts (and their activities) and opportunities are cascade-deleted before the account row itself.

**G. Search**
1. The header search form GETs `/search?q=<term>`.
2. The handler runs a `LIKE`-based query against leads, contacts, accounts, and opportunities and renders `search.html` with results grouped by type.

**H. CSV export / import**
1. Export: `GET /<entity>/export.csv` streams a `text/csv` response built with Python's stdlib `csv` module — no new dependency.
2. Import (Leads only): `POST /leads/import` reads an uploaded file via `csv.DictReader`, validates/defaults each row (invalid status falls back to `New`, non-numeric value falls back to `0`), and inserts one row per valid CSV line.

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
 leads row                 accounts row               contacts row              opportunities row        activities row
┌────────────┐   lookup    ┌─────────────┐             ┌────────────┐            ┌─────────────┐        ┌───────────────┐
│ name        │──by company─▶│ name       │  create    │ name        │  create   │ name          │       │ contact_id     │
│ company     │  (create if │ industry    │──────────▶│ title       │──────────▶│ account_id     │       │ kind: note      │
│ status: New │   missing)  │ owner_id    │            │ account_id  │            │ rep_id         │       │ description:    │
│ value       │             │ annual_rev. │            │ email/phone │            │ amount         │       │  "Converted..." │
└─────┬──────┘             └─────────────┘             └─────┬──────┘            │ stage: Qualify │       └───────▲───────┘
      │ update status → Qualified, converted → 1              │                   │ close_date     │               │
      └────────────────────────────────────────────────────────────────────────▶ └─────────────┘               │
                                                                └──────────────────────────────────────────────────┘
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
| Templating | Jinja2 (bundled with Flask) | Server-side rendering, one shared `base.html` layout + standalone `login.html` |
| Auth | Flask `session` + Werkzeug `security` (`generate_password_hash`/`check_password_hash`, `pbkdf2:sha256`) | Bundled with Flask — no new dependency |
| CSS | Tailwind CSS via CDN `<script>` | No build step; utility classes only, plus a handful of custom rules |
| Client JS | Vanilla JS (`static/js/app.js`) | Dropdown/modal control (new + edit), notifications toggle, `fetch()` for two AJAX actions, native HTML5 drag-and-drop |
| CSV | Python stdlib `csv` module | Used for both export (`csv.writer`) and import (`csv.DictReader`) — no new dependency |
| Hosting | Render.com (free web service) | Auto-deploy from GitHub via `render.yaml` blueprint |
| Source control | GitHub — `jainviyom/smb-crm` | Public repository |

### 4.2 Why This Stack

The development environment this app was built in has **no Node.js, npm, or Homebrew installed**, which ruled out a conventional React/Next.js + Prisma stack despite that being a common default for this kind of app. Flask + SQLite + server-rendered templates was chosen because it:

- Installs entirely via `pip` (no compiler toolchain, no JS package manager)
- Runs the exact same way locally and in production (`gunicorn app:app`)
- Needs no separate frontend build/bundle step — Tailwind is loaded from a CDN at runtime
- Keeps the whole app auditable in a small number of plain-text files
- Lets features like auth and CSV import/export ride on libraries already bundled with Flask/Python (Werkzeug's password hashing, the `csv` stdlib module) rather than pulling in new dependencies

### 4.3 Dependencies (`requirements.txt`)

```
Flask>=3.1
gunicorn>=23.0
```

No other third-party Python packages are required. Password hashing (Werkzeug) ships with Flask; CSV handling uses the Python standard library. The frontend has zero installed dependencies (Tailwind and fonts load from CDN URLs at request time).

---

## 5. Data Model

### 5.1 Entity Overview

```
 reps  ──1───┬── owns ──*  accounts ──1───*  contacts
   │         │                  │
   │         └── owns ──*  opportunities ──*───1 accounts
   │
   └── owns ──* opportunities

 contacts ──1───*  activities   (now written by app logic, not just seed data)

 tasks   (standalone — not foreign-keyed to any other table)
 leads    (standalone until Convert — then produces accounts/contacts/opportunities rows)
```

### 5.2 Table Reference

**reps** — sales users, now with login credentials
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| name | TEXT | |
| title | TEXT | e.g. "Sales Rep" |
| email | TEXT UNIQUE | Login identifier, e.g. `maria@smbcrm.demo` |
| password_hash | TEXT | Werkzeug `pbkdf2:sha256` hash; demo password for both seeded reps is `demo1234` |

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

**activities** — timeline entries on a contact (seeded, plus auto-written by lead conversion and stage-change events)
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| contact_id | INTEGER FK → contacts.id | |
| kind | TEXT | email / call / meeting / note / stage |
| description | TEXT | |
| occurred_at | TEXT | |

**tasks** — the dashboard's "due today" list, also surfaced in the notifications dropdown
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
| GET, POST | `/login` | Login form / authenticates and starts a session |
| POST | `/logout` | Clears the session |
| GET | `/dashboard` | Pipeline totals, tasks, top opportunities |
| GET | `/search` | Cross-entity search results, `?q=` |
| GET | `/leads` | Lead list, optional `?status=` filter |
| POST | `/leads/<id>/convert` | Converts a lead into Account + Contact + Opportunity, logs an activity |
| POST | `/leads/new` | Creates a lead from the modal form |
| POST | `/leads/<id>/edit` | Updates a lead's fields |
| POST | `/leads/<id>/delete` | Deletes a lead |
| GET | `/leads/export.csv` | Downloads all leads as CSV |
| POST | `/leads/import` | Bulk-creates leads from an uploaded CSV |
| GET | `/contacts` | Contact list + detail (`?id=`) with activity timeline |
| POST | `/contacts/new` | Creates a contact from the modal form |
| POST | `/contacts/<id>/edit` | Updates a contact's fields |
| POST | `/contacts/<id>/delete` | Deletes a contact and its activities |
| GET | `/contacts/export.csv` | Downloads all contacts as CSV |
| GET | `/accounts` | Account list + detail (`?id=`, `?tab=overview|contacts|opportunities`) |
| POST | `/accounts/new` | Creates an account from the modal form |
| POST | `/accounts/<id>/edit` | Updates an account's fields |
| POST | `/accounts/<id>/delete` | Deletes an account, cascading to its contacts/activities/opportunities |
| GET | `/accounts/export.csv` | Downloads all accounts as CSV |
| GET | `/opportunities` | 5-column kanban board |
| POST | `/opportunities/new` | Creates an opportunity from the modal form |
| POST | `/opportunities/<id>/edit` | Updates an opportunity's fields (including stage) |
| POST | `/opportunities/<id>/delete` | Deletes an opportunity |
| POST | `/opportunities/<id>/stage` | AJAX: updates an opportunity's stage (kanban drag-drop), logs an activity |
| GET | `/opportunities/export.csv` | Downloads all opportunities as CSV |
| POST | `/tasks/<id>/toggle` | AJAX: toggles a task's done state |
| GET | `/reports` | Revenue/lead-source/leaderboard/trend stats, `?range=month|quarter|year` |

All state-changing routes are `POST`; all `GET` routes are safe/idempotent. Every route except `/login` and static assets requires an active session (enforced by a `before_request` guard).

---

## 7. Feature Documentation

**Login** — A standalone sign-in screen (outside the app's shared sidebar layout) with email + password fields; demo credentials for both seeded reps are printed on the screen itself so evaluators aren't blocked. Successful login redirects back to whatever page was originally requested.

**Dashboard** — Greets the signed-in rep by name; shows Open Pipeline (sum of all non-closed opportunity amounts), Won This Month, New Leads (with week-over-week delta), and Win Rate (Closed Won ÷ (Closed Won + Closed Lost)), a bar chart of pipeline value per stage, a task checklist, and the 3 largest open deals.

**Search** — The header search bar submits to a dedicated results page that groups matches by Leads, Contacts, Accounts, and Opportunities, each linking straight to that record.

**Notifications** — The bell icon shows a red count badge (open task count) and, on click, a dropdown listing open tasks and the most recent Closed Won deals.

**Leads** — A filterable table (All / New / Working / Qualified / Unqualified) with a status badge, an Edit and Delete action on every row, and a **Convert** button on every unconverted row (converted rows show "Converted" instead). Export/Import CSV controls sit above the table.

**Contacts** — A left-hand contact list; selecting a contact shows their email/phone, an Edit/Delete action, and a reverse-chronological activity timeline that now includes automatically logged conversion and stage-change events.

**Accounts** — A left-hand account list; selecting an account shows Annual Revenue, an Edit/Delete action (delete cascades to that account's contacts and opportunities), and three tabs — Overview (open-opportunity and contact counts), Contacts, and Opportunities — all scoped to that account.

**Opportunities** — A 5-column kanban (Qualify, Discovery, Proposal, Negotiation, Closed Won). Cards show amount, close date, a stage-based progress bar, and Edit/Delete actions. Dragging a card to another column persists the change immediately and logs an activity.

**Reports** — A period switcher (This Month / This Quarter / This Year) recomputes Revenue Won, Deals Closed, and Avg Deal Size; a 6-month revenue trend bar chart; a lead-source percentage breakdown; and a rep leaderboard by revenue won in the period.

**Record creation** — A single "+ New" control in the top bar opens a dropdown with New Lead / New Contact / New Account / New Opportunity; each opens a modal form that submits directly to its `/*/new` route.

**Record editing** — Every list/detail page has Edit actions that open the same style of modal, pre-filled from the clicked row's data, and pointed at that record's `/*/<id>/edit` route.

---

## 8. Setup & Deployment Guide

### 8.1 Local development

```bash
git clone https://github.com/jainviyom/smb-crm.git
cd smb-crm
pip3 install -r requirements.txt
python3 seed.py        # creates crm.db with demo data (overwrites existing data)
python3 app.py          # http://127.0.0.1:5050 — sign in with maria@smbcrm.demo / demo1234
```

### 8.2 Production (Render)

1. Push to `main` on GitHub.
2. In Render: **New +** → **Blueprint** → connect the repo. Render reads `render.yaml` and pre-fills the service.
3. **Apply** — Render builds with `pip install -r requirements.txt` and starts with `gunicorn app:app --bind 0.0.0.0:$PORT`.
4. Every subsequent push to `main` auto-deploys (`autoDeploy: yes`, `autoDeployTrigger: commit`) with no manual step.

### 8.3 Operational caveats

- **Ephemeral disk**: Render's free tier does not persist the filesystem across restarts/redeploys. `app.py` calls `seed.run()` automatically at import time if `crm.db` is missing, so the app always boots cleanly — but any data entered by visitors is lost on the next restart.
- **Session secret not fixed (action recommended)**: `app.py` falls back to a freshly generated `SECRET_KEY` on every process start if the `SECRET_KEY` environment variable isn't set. On Render's free tier this means every restart/redeploy invalidates all logged-in sessions. Set a fixed `SECRET_KEY` environment variable in the Render dashboard to keep sessions stable across restarts.
- **Cold start**: the free web service spins down after ~15 minutes idle; the first request afterward takes roughly 30–60 seconds to respond.
- **Single shared dataset, no per-rep scoping**: all logged-in reps read and write the same database and can see/edit each other's records — one person's "+ New" lead or edit is visible to everyone else immediately.

---

## 9. Known Limitations, Risks & Roadmap Notes

| Area | Note |
|---|---|
| Authorization scope | Login is required, but there's no per-rep data isolation or role-based permissions — any signed-in rep can edit or delete any other rep's records. |
| Session stability (hosted) | Without a fixed `SECRET_KEY` env var on Render, all sessions are invalidated on every restart (see §8.3). |
| Data persistence | Not durable on the current free hosting tier (see §8.3). |
| Concurrency | SQLite handles the expected demo load fine but is not intended for high-concurrency multi-tenant use. |
| Account creation / password reset | Demo accounts are seeded directly in the database; there's no sign-up flow or forgot-password flow. |
| AI Assistant (in progress) | A conversational assistant is being designed to let a rep ask natural-language questions ("which deals are at risk?") and take actions (convert a lead, log a task) via Claude's tool-calling API against this same SQLite schema. This requires an Anthropic API key and a model-cost decision (Opus vs. Sonnet vs. Haiku) that had not been finalized as of this document's writing. |

---

## 10. Appendix

### 10.1 File Structure

```
custom-app/
├── app.py                  # Flask routes, auth guard, business logic
├── db.py                   # SQLite connection helper (Flask `g`-scoped)
├── schema.sql               # Table definitions (reps now include email/password_hash)
├── seed.py                  # Demo data population, incl. hashed demo passwords
├── requirements.txt
├── render.yaml               # Render Blueprint (build/start commands)
├── .gitignore                # excludes crm.db, __pycache__, .venv
├── README.md
├── docs/
│   └── PROJECT_DOCUMENTATION.md   # this file
├── static/
│   ├── css/app.css
│   └── js/app.js            # modal (new + edit), notifications, drag-drop, task toggle
└── templates/
    ├── base.html            # sidebar, topbar, search form, notifications, "+ New"/edit modals
    ├── login.html            # standalone sign-in page
    ├── search.html           # cross-entity search results
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
| Rep | A logged-in sales user; currently Maria Chen and Sam Patel, both with the same demo password |

### 10.3 Version History (from commit log)

| Commit | Summary |
|---|---|
| Initial commit | Flask + SQLite + Tailwind SMB CRM: Dashboard, Leads, Contacts, Accounts, Opportunities kanban, Reports |
| Add production deploy config for Render | Auto-seed on boot, gunicorn, `render.yaml` blueprint |
| Add create flows for leads, contacts, accounts, and opportunities | Global "+ New" dropdown + modal forms backed by new POST routes |
| Add project documentation | Initial BRD, architecture, tech stack, and full reference (this document, v1.0) |
| Add auth, edit/delete, search, notifications, CSV, and reports trend | Session-based login, full edit/delete for all 4 entities, working header search, auto-logged activities, notifications dropdown, CSV import/export, 6-month revenue trend chart |
