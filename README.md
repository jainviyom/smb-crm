# SMB CRM

A Salesforce-style CRM: leads, contacts, accounts, opportunities (kanban), dashboard, and reports.

## Stack

Flask + SQLite + Tailwind (CDN) + vanilla JS. No Node/build step required — the environment this was
built in has no Node.js installed, so this intentionally avoids a JS framework/build pipeline.

## Setup

```bash
pip3 install -r requirements.txt
python3 seed.py      # (re)creates crm.db with demo data — wipes existing data
python3 app.py        # http://127.0.0.1:5050
```

## Structure

- `app.py` — routes / business logic
- `db.py` — SQLite connection helper
- `schema.sql` / `seed.py` — schema + demo data
- `templates/` — Jinja pages (one per screen: dashboard, leads, contacts, accounts, opportunities, reports)
- `static/js/app.js` — task checkbox toggle + kanban drag-drop

## Notes

- Dashboard/Reports numbers are computed live from `crm.db`, not hardcoded — they won't match the
  original mockup's placeholder figures exactly (those weren't internally consistent across slides),
  but every screen reflects the same real dataset.
- "Convert" on a lead creates/reuses an Account + Contact and opens a new Opportunity in the Qualify stage.
- Dragging a card in Opportunities updates its stage (and closes it, if dropped in Closed Won) via `POST /opportunities/<id>/stage`.
