import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "crm.db"
SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def run():
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA_PATH.read_text())

    cur = conn.cursor()

    # --- Reps ---
    cur.execute("INSERT INTO reps (name, title) VALUES ('Maria Chen', 'Sales Rep')")
    maria = cur.lastrowid
    cur.execute("INSERT INTO reps (name, title) VALUES ('Sam Patel', 'Sales Rep')")
    sam = cur.lastrowid

    # --- Accounts ---
    accounts = [
        ("Acme Logistics", "Transportation", maria, 12_000_000),
        ("Brightleaf Co", "Retail", maria, 4_800_000),
        ("Northgate Retail", "Retail", maria, 6_200_000),
        ("Ridgeline Foods", "Food & Beverage", maria, 9_100_000),
        ("Vista Dental Group", "Healthcare", maria, 2_300_000),
        ("Ferro Supply Co", "Wholesale", sam, 5_400_000),
        ("Coastal Freight", "Transportation", sam, 8_700_000),
        ("Meridian Health", "Healthcare", sam, 15_000_000),
        ("Bluepeak Retail", "Retail", maria, 3_100_000),
    ]
    account_id = {}
    for name, industry, owner, revenue in accounts:
        cur.execute(
            "INSERT INTO accounts (name, industry, owner_id, annual_revenue) VALUES (?,?,?,?)",
            (name, industry, owner, revenue),
        )
        account_id[name] = cur.lastrowid

    # --- Leads ---
    leads = [
        ("Dana Whitfield", "Bluepeak Retail", "New", "Web", 12000),
        ("Marcus Yee", "Ferro Supply Co", "New", "Referral", 8400),
        ("Priya Nathan", "Ridgeline Foods", "Working", "Trade Show", 22500),
        ("Owen Castillo", "Vista Dental Group", "Working", "Cold Call", 6750),
        ("Elena Torres", "Northgate Retail", "Qualified", "Web", 38900),
        ("Felix Grant", "Brightleaf Co", "Qualified", "Partner", 41200),
        ("Tara Simmons", "Coastal Freight", "Unqualified", "Web", 4200),
        ("Ibrahim Saad", "Meridian Health", "New", "Referral", 15600),
    ]
    for name, company, status, source, value in leads:
        cur.execute(
            "INSERT INTO leads (name, company, status, source, value) VALUES (?,?,?,?,?)",
            (name, company, status, source, value),
        )

    # --- Contacts ---
    contacts = [
        ("Jordan Reyes", "Ops Director", "Acme Logistics", "jordan@acmelogistics.com", "(415) 555-0132"),
        ("Casey Lin", "Fleet Manager", "Acme Logistics", "casey@acmelogistics.com", "(415) 555-0198"),
        ("Felix Grant", "VP Merchandising", "Brightleaf Co", "felix@brightleafco.com", "(212) 555-0110"),
        ("Nora Diaz", "Store Operations Lead", "Brightleaf Co", "nora@brightleafco.com", "(212) 555-0142"),
        ("Elena Torres", "IT Director", "Northgate Retail", "elena@northgateretail.com", "(206) 555-0177"),
        ("Priya Nathan", "Procurement Manager", "Ridgeline Foods", "priya@ridgelinefoods.com", "(312) 555-0163"),
        ("Owen Castillo", "Practice Manager", "Vista Dental Group", "owen@vistadental.com", "(602) 555-0119"),
    ]
    contact_id = {}
    for name, title, company, email, phone in contacts:
        cur.execute(
            "INSERT INTO contacts (name, title, account_id, email, phone) VALUES (?,?,?,?,?)",
            (name, title, account_id[company], email, phone),
        )
        contact_id[name] = cur.lastrowid

    # --- Activities (Jordan Reyes timeline, matches mockup) ---
    activities = [
        ("Jordan Reyes", "email", "Email sent — Q3 pricing overview", "2026-07-01"),
        ("Jordan Reyes", "call", "Call logged — discovery follow-up", "2026-06-27"),
        ("Jordan Reyes", "meeting", "Meeting scheduled — product walkthrough", "2026-06-19"),
        ("Felix Grant", "email", "Email sent — platform upgrade proposal", "2026-06-30"),
        ("Elena Torres", "call", "Call logged — POS rollout timeline", "2026-06-28"),
    ]
    for contact, kind, desc, when in activities:
        cur.execute(
            "INSERT INTO activities (contact_id, kind, description, occurred_at) VALUES (?,?,?,?)",
            (contact_id[contact], kind, desc, when),
        )

    # --- Open Opportunities (matches mockup kanban) ---
    open_opps = [
        ("Supply contract", "Ridgeline Foods", maria, 22500, "Qualify", "2026-08-20"),
        ("Equipment lease", "Vista Dental Group", maria, 18300, "Qualify", "2026-08-22"),
        ("POS rollout", "Northgate Retail", maria, 38900, "Discovery", "2026-08-05"),
        ("Onboarding suite", "Meridian Health", sam, 33750, "Discovery", "2026-08-10"),
        ("Platform upgrade", "Brightleaf Co", maria, 41200, "Proposal", "2026-07-25"),
        ("Fleet renewal", "Acme Logistics", maria, 64000, "Negotiation", "2026-07-18"),
        ("Fleet expansion", "Coastal Freight", sam, 52000, "Negotiation", "2026-07-22"),
    ]
    for name, company, rep, amount, stage, close_date in open_opps:
        cur.execute(
            "INSERT INTO opportunities (name, account_id, rep_id, amount, stage, close_date, closed_at) VALUES (?,?,?,?,?,?,NULL)",
            (name, account_id[company], rep, amount, stage, close_date),
        )

    # --- Closed Won history (drives Reports / leaderboard, spread over the past year) ---
    closed_won = [
        ("Signage refresh", "Bluepeak Retail", maria, 6200, "2026-07-02"),
        ("Renewal", "Ferro Supply Co", sam, 27000, "2026-07-01"),
        ("Fleet telematics upgrade", "Acme Logistics", maria, 18500, "2026-06-24"),
        ("Seasonal staffing suite", "Northgate Retail", maria, 9800, "2026-06-18"),
        ("Warehouse module", "Ridgeline Foods", maria, 15200, "2026-06-11"),
        ("Patient portal add-on", "Vista Dental Group", sam, 7600, "2026-06-04"),
        ("Loyalty program rollout", "Bluepeak Retail", maria, 12400, "2026-05-27"),
        ("Route optimization", "Coastal Freight", sam, 21300, "2026-05-14"),
        ("Multi-site licensing", "Meridian Health", sam, 48200, "2026-04-30"),
        ("POS hardware refresh", "Brightleaf Co", maria, 16700, "2026-04-09"),
        ("Cold-chain tracking", "Ridgeline Foods", maria, 19900, "2026-03-15"),
        ("Fleet insurance bundle", "Acme Logistics", maria, 24100, "2026-02-20"),
        ("Supplier portal", "Ferro Supply Co", sam, 13800, "2026-01-28"),
        ("Regional expansion", "Northgate Retail", maria, 31500, "2025-12-12"),
        ("Compliance suite", "Meridian Health", sam, 27700, "2025-10-30"),
        ("Initial platform deal", "Vista Dental Group", maria, 14200, "2025-08-22"),
    ]
    for name, company, rep, amount, closed_at in closed_won:
        cur.execute(
            "INSERT INTO opportunities (name, account_id, rep_id, amount, stage, close_date, closed_at) VALUES (?,?,?,?,'Closed Won',?,?)",
            (name, account_id[company], rep, amount, closed_at, closed_at),
        )

    # --- Closed Lost history (so win rate is a genuine ratio, not a placeholder) ---
    closed_lost = [
        ("Trial expansion", "Bluepeak Retail", maria, 9200, "2026-06-15"),
        ("Distribution add-on", "Ferro Supply Co", sam, 14500, "2026-05-20"),
        ("Second warehouse", "Ridgeline Foods", maria, 11800, "2026-04-18"),
        ("Legacy system swap", "Meridian Health", sam, 22000, "2026-02-27"),
        ("Franchise rollout", "Northgate Retail", maria, 17300, "2025-11-05"),
    ]
    for name, company, rep, amount, closed_at in closed_lost:
        cur.execute(
            "INSERT INTO opportunities (name, account_id, rep_id, amount, stage, close_date, closed_at) VALUES (?,?,?,?,'Closed Lost',?,?)",
            (name, account_id[company], rep, amount, closed_at, closed_at),
        )

    # --- Tasks due today ---
    tasks = [
        ("Call Jordan Reyes — renewal", "Acme Logistics · 10:30 AM", "2026-07-03T10:30", 0),
        ("Send proposal follow-up", "Brightleaf Co · 1:00 PM", "2026-07-03T13:00", 1),
        ("Demo prep — Northgate", "Northgate Retail · 3:30 PM", "2026-07-03T15:30", 0),
    ]
    for title, subtitle, due_at, done in tasks:
        cur.execute(
            "INSERT INTO tasks (title, subtitle, due_at, done) VALUES (?,?,?,?)",
            (title, subtitle, due_at, done),
        )

    conn.commit()
    conn.close()
    print(f"Seeded database at {DB_PATH}")


if __name__ == "__main__":
    run()
