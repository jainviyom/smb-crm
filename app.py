import csv
import io
import os
import secrets
from datetime import date, timedelta

from flask import Flask, render_template, request, redirect, url_for, jsonify, abort, session, Response
from werkzeug.security import check_password_hash

import db
import seed

if not db.DB_PATH.exists():
    seed.run()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
db.init_app(app)

STAGES = ["Qualify", "Discovery", "Proposal", "Negotiation", "Closed Won"]
STAGE_PROBABILITY = {
    "Qualify": 20,
    "Discovery": 40,
    "Proposal": 60,
    "Negotiation": 80,
    "Closed Won": 100,
}
LEAD_STATUSES = ["New", "Working", "Qualified", "Unqualified"]

# Fixed reference "today" so date-range stats stay meaningful regardless of
# when this demo is actually run (the seed data is written relative to it).
ANCHOR_DATE = date(2026, 7, 3)

PUBLIC_ENDPOINTS = {"login", "static"}


def current_rep(conn):
    rep_id = session.get("rep_id")
    if rep_id is None:
        return None
    return conn.execute("SELECT * FROM reps WHERE id = ?", (rep_id,)).fetchone()


def log_activity(conn, contact_id, kind, description):
    conn.execute(
        "INSERT INTO activities (contact_id, kind, description, occurred_at) VALUES (?, ?, ?, ?)",
        (contact_id, kind, description, ANCHOR_DATE.isoformat()),
    )


@app.before_request
def require_login():
    if request.endpoint in PUBLIC_ENDPOINTS or request.endpoint is None:
        return None
    if "rep_id" not in session:
        return redirect(url_for("login", next=request.path))


@app.context_processor
def inject_globals():
    conn = db.get_db()
    all_accounts = conn.execute("SELECT id, name FROM accounts ORDER BY name").fetchall()
    rep = current_rep(conn) if "rep_id" in session else None
    overdue_tasks = conn.execute(
        "SELECT * FROM tasks WHERE done = 0 ORDER BY due_at"
    ).fetchall() if rep else []
    recent_wins = conn.execute(
        """SELECT o.*, a.name AS account_name FROM opportunities o
           JOIN accounts a ON a.id = o.account_id
           WHERE o.stage = 'Closed Won' AND o.closed_at IS NOT NULL
           ORDER BY o.closed_at DESC LIMIT 3"""
    ).fetchall() if rep else []
    return {
        "all_accounts": all_accounts,
        "lead_statuses": LEAD_STATUSES,
        "stages": STAGES,
        "current_rep_ctx": rep,
        "overdue_tasks": overdue_tasks,
        "recent_wins": recent_wins,
        "notification_count": len(overdue_tasks),
    }


@app.route("/login", methods=["GET", "POST"])
def login():
    conn = db.get_db()
    error = None
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        rep = conn.execute("SELECT * FROM reps WHERE lower(email) = ?", (email,)).fetchone()
        if rep and rep["password_hash"] and check_password_hash(rep["password_hash"], password):
            session["rep_id"] = rep["id"]
            next_path = request.form.get("next") or url_for("dashboard")
            return redirect(next_path)
        error = "Invalid email or password."
    return render_template("login.html", error=error, next=request.args.get("next", ""))


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
def index():
    return redirect(url_for("dashboard"))


@app.route("/search")
def search():
    conn = db.get_db()
    rep = current_rep(conn)
    q = request.args.get("q", "").strip()
    results = {"leads": [], "contacts": [], "accounts": [], "opportunities": []}
    if q:
        like = f"%{q}%"
        results["leads"] = conn.execute(
            "SELECT * FROM leads WHERE name LIKE ? OR company LIKE ? ORDER BY name", (like, like)
        ).fetchall()
        results["contacts"] = conn.execute(
            """SELECT c.*, a.name AS account_name FROM contacts c JOIN accounts a ON a.id = c.account_id
               WHERE c.name LIKE ? OR c.email LIKE ? ORDER BY c.name""",
            (like, like),
        ).fetchall()
        results["accounts"] = conn.execute(
            "SELECT * FROM accounts WHERE name LIKE ? OR industry LIKE ? ORDER BY name", (like, like)
        ).fetchall()
        results["opportunities"] = conn.execute(
            """SELECT o.*, a.name AS account_name FROM opportunities o JOIN accounts a ON a.id = o.account_id
               WHERE o.name LIKE ? OR a.name LIKE ? ORDER BY o.name""",
            (like, like),
        ).fetchall()
    total = sum(len(v) for v in results.values())
    return render_template("search.html", rep=rep, q=q, results=results, total=total)


@app.route("/dashboard")
def dashboard():
    conn = db.get_db()
    rep = current_rep(conn)

    open_rows = conn.execute(
        "SELECT amount, stage FROM opportunities WHERE closed_at IS NULL"
    ).fetchall()
    open_pipeline = sum(r["amount"] for r in open_rows)
    open_deal_count = len(open_rows)

    month_start = ANCHOR_DATE.replace(day=1).isoformat()
    won_month_rows = conn.execute(
        "SELECT amount FROM opportunities WHERE stage = 'Closed Won' AND closed_at >= ?",
        (month_start,),
    ).fetchall()
    won_this_month = sum(r["amount"] for r in won_month_rows)

    week_ago = (ANCHOR_DATE - timedelta(days=7)).isoformat()
    new_leads = conn.execute("SELECT COUNT(*) c FROM leads WHERE status = 'New'").fetchone()["c"]
    new_leads_prev_week = conn.execute(
        "SELECT COUNT(*) c FROM leads WHERE status = 'New' AND created_at < ?", (week_ago,)
    ).fetchone()["c"]

    won_count = conn.execute("SELECT COUNT(*) c FROM opportunities WHERE stage = 'Closed Won'").fetchone()["c"]
    lost_count = conn.execute("SELECT COUNT(*) c FROM opportunities WHERE stage = 'Closed Lost'").fetchone()["c"]
    win_rate = round(100 * won_count / (won_count + lost_count)) if (won_count + lost_count) else 0

    pipeline_by_stage = []
    max_amount = 1
    for stage in STAGES[:-1] + ["Closed Won"]:
        rows = conn.execute(
            "SELECT amount FROM opportunities WHERE stage = ? AND (closed_at IS NULL OR stage='Closed Won')",
            (stage,),
        ).fetchall()
        total = sum(r["amount"] for r in rows)
        pipeline_by_stage.append({"stage": stage, "total": total})
        max_amount = max(max_amount, total)
    for row in pipeline_by_stage:
        row["pct"] = max(6, round(100 * row["total"] / max_amount))

    tasks = conn.execute("SELECT * FROM tasks ORDER BY due_at").fetchall()

    top_opps = conn.execute(
        """SELECT o.*, a.name AS account_name FROM opportunities o
           JOIN accounts a ON a.id = o.account_id
           WHERE o.closed_at IS NULL
           ORDER BY o.amount DESC LIMIT 3"""
    ).fetchall()

    return render_template(
        "dashboard.html",
        rep=rep,
        open_pipeline=open_pipeline,
        open_deal_count=open_deal_count,
        won_this_month=won_this_month,
        won_month_count=len(won_month_rows),
        new_leads=new_leads,
        new_leads_delta=new_leads - new_leads_prev_week,
        win_rate=win_rate,
        pipeline_by_stage=pipeline_by_stage,
        tasks=tasks,
        top_opps=top_opps,
    )


@app.route("/leads")
def leads():
    conn = db.get_db()
    rep = current_rep(conn)
    status_filter = request.args.get("status", "All")

    counts = {"All": conn.execute("SELECT COUNT(*) c FROM leads").fetchone()["c"]}
    for s in LEAD_STATUSES:
        counts[s] = conn.execute("SELECT COUNT(*) c FROM leads WHERE status = ?", (s,)).fetchone()["c"]

    if status_filter == "All":
        rows = conn.execute("SELECT * FROM leads ORDER BY id").fetchall()
    else:
        rows = conn.execute("SELECT * FROM leads WHERE status = ? ORDER BY id", (status_filter,)).fetchall()

    return render_template(
        "leads.html", rep=rep, leads=rows, counts=counts, status_filter=status_filter, statuses=LEAD_STATUSES
    )


@app.route("/leads/<int:lead_id>/convert", methods=["POST"])
def convert_lead(lead_id):
    conn = db.get_db()
    lead = conn.execute("SELECT * FROM leads WHERE id = ?", (lead_id,)).fetchone()
    if lead is None:
        abort(404)
    rep = current_rep(conn)

    account = conn.execute("SELECT * FROM accounts WHERE name = ?", (lead["company"],)).fetchone()
    if account is None:
        cur = conn.execute(
            "INSERT INTO accounts (name, industry, owner_id, annual_revenue) VALUES (?, 'Unknown', ?, 0)",
            (lead["company"], rep["id"]),
        )
        account_id = cur.lastrowid
    else:
        account_id = account["id"]

    existing_contact = conn.execute(
        "SELECT * FROM contacts WHERE name = ? AND account_id = ?", (lead["name"], account_id)
    ).fetchone()
    if existing_contact is None:
        cur = conn.execute(
            "INSERT INTO contacts (name, title, account_id, email, phone) VALUES (?, 'Contact', ?, ?, '')",
            (lead["name"], account_id, f"{lead['name'].split()[0].lower()}@{lead['company'].lower().replace(' ', '')}.com"),
        )
        contact_id = cur.lastrowid
    else:
        contact_id = existing_contact["id"]

    close_date = (ANCHOR_DATE + timedelta(days=45)).isoformat()
    conn.execute(
        "INSERT INTO opportunities (name, account_id, rep_id, amount, stage, close_date, closed_at) "
        "VALUES (?, ?, ?, ?, 'Qualify', ?, NULL)",
        (f"{lead['company']} — new opportunity", account_id, rep["id"], lead["value"], close_date),
    )

    conn.execute("UPDATE leads SET status = 'Qualified', converted = 1 WHERE id = ?", (lead_id,))
    log_activity(conn, contact_id, "note", f"Converted from lead by {rep['name']}")
    conn.commit()
    return redirect(url_for("leads"))


@app.route("/leads/<int:lead_id>/edit", methods=["POST"])
def edit_lead(lead_id):
    conn = db.get_db()
    conn.execute(
        "UPDATE leads SET name=?, company=?, status=?, source=?, value=? WHERE id=?",
        (
            request.form["name"].strip(),
            request.form["company"].strip(),
            request.form.get("status", "New"),
            request.form.get("source", "Web"),
            int(request.form.get("value") or 0),
            lead_id,
        ),
    )
    conn.commit()
    return redirect(url_for("leads"))


@app.route("/leads/<int:lead_id>/delete", methods=["POST"])
def delete_lead(lead_id):
    conn = db.get_db()
    conn.execute("DELETE FROM leads WHERE id = ?", (lead_id,))
    conn.commit()
    return redirect(url_for("leads"))


@app.route("/leads/new", methods=["POST"])
def new_lead():
    conn = db.get_db()
    conn.execute(
        "INSERT INTO leads (name, company, status, source, value) VALUES (?, ?, ?, ?, ?)",
        (
            request.form["name"].strip(),
            request.form["company"].strip(),
            request.form.get("status", "New"),
            request.form.get("source", "Web"),
            int(request.form.get("value") or 0),
        ),
    )
    conn.commit()
    return redirect(url_for("leads"))


@app.route("/contacts")
def contacts():
    conn = db.get_db()
    rep = current_rep(conn)
    rows = conn.execute(
        """SELECT c.*, a.name AS account_name FROM contacts c
           JOIN accounts a ON a.id = c.account_id ORDER BY c.name"""
    ).fetchall()

    selected_id = request.args.get("id", type=int) or (rows[0]["id"] if rows else None)
    selected = next((r for r in rows if r["id"] == selected_id), None)
    activities = []
    if selected:
        activities = conn.execute(
            "SELECT * FROM activities WHERE contact_id = ? ORDER BY occurred_at DESC", (selected_id,)
        ).fetchall()

    return render_template("contacts.html", rep=rep, contacts=rows, selected=selected, activities=activities)


@app.route("/contacts/new", methods=["POST"])
def new_contact():
    conn = db.get_db()
    cur = conn.execute(
        "INSERT INTO contacts (name, title, account_id, email, phone) VALUES (?, ?, ?, ?, ?)",
        (
            request.form["name"].strip(),
            request.form.get("title", "").strip() or "Contact",
            request.form["account_id"],
            request.form.get("email", "").strip(),
            request.form.get("phone", "").strip(),
        ),
    )
    conn.commit()
    return redirect(url_for("contacts", id=cur.lastrowid))


@app.route("/contacts/<int:contact_id>/edit", methods=["POST"])
def edit_contact(contact_id):
    conn = db.get_db()
    conn.execute(
        "UPDATE contacts SET name=?, title=?, account_id=?, email=?, phone=? WHERE id=?",
        (
            request.form["name"].strip(),
            request.form.get("title", "").strip() or "Contact",
            request.form["account_id"],
            request.form.get("email", "").strip(),
            request.form.get("phone", "").strip(),
            contact_id,
        ),
    )
    conn.commit()
    return redirect(url_for("contacts", id=contact_id))


@app.route("/contacts/<int:contact_id>/delete", methods=["POST"])
def delete_contact(contact_id):
    conn = db.get_db()
    conn.execute("DELETE FROM activities WHERE contact_id = ?", (contact_id,))
    conn.execute("DELETE FROM contacts WHERE id = ?", (contact_id,))
    conn.commit()
    return redirect(url_for("contacts"))


@app.route("/accounts")
def accounts():
    conn = db.get_db()
    rep = current_rep(conn)
    rows = conn.execute("SELECT * FROM accounts ORDER BY name").fetchall()

    selected_id = request.args.get("id", type=int) or (rows[0]["id"] if rows else None)
    selected = next((r for r in rows if r["id"] == selected_id), None)
    tab = request.args.get("tab", "overview")

    account_contacts = []
    account_opps = []
    open_opp_count = 0
    if selected:
        account_contacts = conn.execute(
            "SELECT * FROM contacts WHERE account_id = ? ORDER BY name", (selected_id,)
        ).fetchall()
        account_opps = conn.execute(
            "SELECT * FROM opportunities WHERE account_id = ? ORDER BY closed_at IS NULL DESC, close_date",
            (selected_id,),
        ).fetchall()
        open_opp_count = sum(1 for o in account_opps if o["closed_at"] is None)

    return render_template(
        "accounts.html",
        rep=rep,
        accounts=rows,
        selected=selected,
        tab=tab,
        account_contacts=account_contacts,
        account_opps=account_opps,
        open_opp_count=open_opp_count,
    )


@app.route("/accounts/new", methods=["POST"])
def new_account():
    conn = db.get_db()
    rep = current_rep(conn)
    cur = conn.execute(
        "INSERT INTO accounts (name, industry, owner_id, annual_revenue) VALUES (?, ?, ?, ?)",
        (
            request.form["name"].strip(),
            request.form.get("industry", "").strip() or "Unknown",
            rep["id"],
            int(request.form.get("annual_revenue") or 0),
        ),
    )
    conn.commit()
    return redirect(url_for("accounts", id=cur.lastrowid))


@app.route("/accounts/<int:account_id>/edit", methods=["POST"])
def edit_account(account_id):
    conn = db.get_db()
    conn.execute(
        "UPDATE accounts SET name=?, industry=?, annual_revenue=? WHERE id=?",
        (
            request.form["name"].strip(),
            request.form.get("industry", "").strip() or "Unknown",
            int(request.form.get("annual_revenue") or 0),
            account_id,
        ),
    )
    conn.commit()
    return redirect(url_for("accounts", id=account_id))


@app.route("/accounts/<int:account_id>/delete", methods=["POST"])
def delete_account(account_id):
    conn = db.get_db()
    contact_ids = [r["id"] for r in conn.execute("SELECT id FROM contacts WHERE account_id = ?", (account_id,)).fetchall()]
    for cid in contact_ids:
        conn.execute("DELETE FROM activities WHERE contact_id = ?", (cid,))
    conn.execute("DELETE FROM contacts WHERE account_id = ?", (account_id,))
    conn.execute("DELETE FROM opportunities WHERE account_id = ?", (account_id,))
    conn.execute("DELETE FROM accounts WHERE id = ?", (account_id,))
    conn.commit()
    return redirect(url_for("accounts"))


@app.route("/opportunities")
def opportunities():
    conn = db.get_db()
    rep = current_rep(conn)
    columns = {}
    for stage in STAGES:
        rows = conn.execute(
            """SELECT o.*, a.name AS account_name FROM opportunities o
               JOIN accounts a ON a.id = o.account_id
               WHERE o.stage = ? AND (o.closed_at IS NULL OR o.stage = 'Closed Won')
               ORDER BY o.close_date""",
            (stage,),
        ).fetchall()
        if stage == "Closed Won":
            rows = [r for r in rows if r["closed_at"] and r["closed_at"] >= ANCHOR_DATE.replace(day=1).isoformat()]
        total = sum(r["amount"] for r in rows)
        columns[stage] = {"deals": rows, "count": len(rows), "total": total}

    return render_template(
        "opportunities.html", rep=rep, columns=columns, stages=STAGES, stage_probability=STAGE_PROBABILITY
    )


@app.route("/opportunities/new", methods=["POST"])
def new_opportunity():
    conn = db.get_db()
    rep = current_rep(conn)
    stage = request.form.get("stage", "Qualify")
    if stage not in STAGES:
        stage = "Qualify"
    close_date = request.form.get("close_date") or (ANCHOR_DATE + timedelta(days=30)).isoformat()
    closed_at = ANCHOR_DATE.isoformat() if stage == "Closed Won" else None
    conn.execute(
        "INSERT INTO opportunities (name, account_id, rep_id, amount, stage, close_date, closed_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            request.form["name"].strip(),
            request.form["account_id"],
            rep["id"],
            int(request.form.get("amount") or 0),
            stage,
            close_date,
            closed_at,
        ),
    )
    conn.commit()
    return redirect(url_for("opportunities"))


@app.route("/opportunities/<int:opp_id>/edit", methods=["POST"])
def edit_opportunity(opp_id):
    conn = db.get_db()
    stage = request.form.get("stage", "Qualify")
    if stage not in STAGES:
        stage = "Qualify"
    existing = conn.execute("SELECT closed_at FROM opportunities WHERE id = ?", (opp_id,)).fetchone()
    closed_at = existing["closed_at"] if existing else None
    if stage == "Closed Won" and not closed_at:
        closed_at = ANCHOR_DATE.isoformat()
    elif stage != "Closed Won":
        closed_at = None
    conn.execute(
        "UPDATE opportunities SET name=?, account_id=?, amount=?, stage=?, close_date=?, closed_at=? WHERE id=?",
        (
            request.form["name"].strip(),
            request.form["account_id"],
            int(request.form.get("amount") or 0),
            stage,
            request.form.get("close_date") or (ANCHOR_DATE + timedelta(days=30)).isoformat(),
            closed_at,
            opp_id,
        ),
    )
    conn.commit()
    return redirect(url_for("opportunities"))


@app.route("/opportunities/<int:opp_id>/delete", methods=["POST"])
def delete_opportunity(opp_id):
    conn = db.get_db()
    conn.execute("DELETE FROM opportunities WHERE id = ?", (opp_id,))
    conn.commit()
    return redirect(url_for("opportunities"))


@app.route("/opportunities/<int:opp_id>/stage", methods=["POST"])
def update_stage(opp_id):
    conn = db.get_db()
    stage = request.json.get("stage")
    if stage not in STAGES:
        return jsonify({"error": "invalid stage"}), 400
    opp = conn.execute("SELECT * FROM opportunities WHERE id = ?", (opp_id,)).fetchone()
    closed_at = ANCHOR_DATE.isoformat() if stage == "Closed Won" else None
    conn.execute("UPDATE opportunities SET stage = ?, closed_at = ? WHERE id = ?", (stage, closed_at, opp_id))
    if opp and opp["stage"] != stage:
        first_contact = conn.execute(
            "SELECT id FROM contacts WHERE account_id = ? ORDER BY id LIMIT 1", (opp["account_id"],)
        ).fetchone()
        if first_contact:
            log_activity(conn, first_contact["id"], "stage", f"Opportunity “{opp['name']}” moved to {stage}")
    conn.commit()
    return jsonify({"ok": True})


@app.route("/tasks/<int:task_id>/toggle", methods=["POST"])
def toggle_task(task_id):
    conn = db.get_db()
    task = conn.execute("SELECT done FROM tasks WHERE id = ?", (task_id,)).fetchone()
    if task is None:
        abort(404)
    conn.execute("UPDATE tasks SET done = ? WHERE id = ?", (0 if task["done"] else 1, task_id))
    conn.commit()
    return jsonify({"ok": True})


@app.route("/reports")
def reports():
    conn = db.get_db()
    rep = current_rep(conn)
    range_ = request.args.get("range", "month")

    if range_ == "month":
        start = ANCHOR_DATE.replace(day=1)
    elif range_ == "quarter":
        q_start_month = ((ANCHOR_DATE.month - 1) // 3) * 3 + 1
        start = ANCHOR_DATE.replace(month=q_start_month, day=1)
    else:
        start = ANCHOR_DATE.replace(month=1, day=1)
    start_iso = start.isoformat()

    won_rows = conn.execute(
        "SELECT amount FROM opportunities WHERE stage = 'Closed Won' AND closed_at >= ?", (start_iso,)
    ).fetchall()
    revenue_won = sum(r["amount"] for r in won_rows)
    deals_closed = len(won_rows)
    avg_deal_size = round(revenue_won / deals_closed) if deals_closed else 0

    lead_source_rows = conn.execute(
        "SELECT source, COUNT(*) c FROM leads GROUP BY source ORDER BY c DESC"
    ).fetchall()
    total_leads = sum(r["c"] for r in lead_source_rows) or 1
    lead_sources = [{"source": r["source"], "pct": round(100 * r["c"] / total_leads)} for r in lead_source_rows]

    leaderboard = conn.execute(
        """SELECT reps.name, COUNT(*) deals_won, SUM(opportunities.amount) revenue
           FROM opportunities JOIN reps ON reps.id = opportunities.rep_id
           WHERE opportunities.stage = 'Closed Won' AND opportunities.closed_at >= ?
           GROUP BY reps.id ORDER BY revenue DESC""",
        (start_iso,),
    ).fetchall()

    trend = []
    max_trend = 1
    for i in range(5, -1, -1):
        month_index = ANCHOR_DATE.month - 1 - i
        year = ANCHOR_DATE.year + month_index // 12
        month = month_index % 12 + 1
        bucket_start = date(year, month, 1)
        if month == 12:
            bucket_end = date(year + 1, 1, 1)
        else:
            bucket_end = date(year, month + 1, 1)
        rows = conn.execute(
            "SELECT amount FROM opportunities WHERE stage = 'Closed Won' AND closed_at >= ? AND closed_at < ?",
            (bucket_start.isoformat(), bucket_end.isoformat()),
        ).fetchall()
        total = sum(r["amount"] for r in rows)
        trend.append({"label": bucket_start.strftime("%b"), "total": total})
        max_trend = max(max_trend, total)
    for row in trend:
        row["pct"] = max(4, round(100 * row["total"] / max_trend))

    return render_template(
        "reports.html",
        rep=rep,
        range_=range_,
        revenue_won=revenue_won,
        deals_closed=deals_closed,
        avg_deal_size=avg_deal_size,
        lead_sources=lead_sources,
        leaderboard=leaderboard,
        trend=trend,
    )


def _csv_response(filename, header, rows):
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(header)
    writer.writerows(rows)
    return Response(
        buf.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@app.route("/leads/export.csv")
def export_leads():
    conn = db.get_db()
    rows = conn.execute("SELECT name, company, status, source, value FROM leads ORDER BY id").fetchall()
    return _csv_response(
        "leads.csv",
        ["Name", "Company", "Status", "Source", "Value"],
        [[r["name"], r["company"], r["status"], r["source"], r["value"]] for r in rows],
    )


@app.route("/leads/import", methods=["POST"])
def import_leads():
    conn = db.get_db()
    file = request.files.get("file")
    if file and file.filename:
        stream = io.StringIO(file.stream.read().decode("utf-8-sig"))
        reader = csv.DictReader(stream)
        for row in reader:
            name = (row.get("Name") or "").strip()
            company = (row.get("Company") or "").strip()
            if not name or not company:
                continue
            status = (row.get("Status") or "New").strip()
            if status not in LEAD_STATUSES:
                status = "New"
            source = (row.get("Source") or "Web").strip() or "Web"
            try:
                value = int(row.get("Value") or 0)
            except ValueError:
                value = 0
            conn.execute(
                "INSERT INTO leads (name, company, status, source, value) VALUES (?, ?, ?, ?, ?)",
                (name, company, status, source, value),
            )
        conn.commit()
    return redirect(url_for("leads"))


@app.route("/accounts/export.csv")
def export_accounts():
    conn = db.get_db()
    rows = conn.execute("SELECT name, industry, annual_revenue FROM accounts ORDER BY name").fetchall()
    return _csv_response(
        "accounts.csv",
        ["Name", "Industry", "Annual Revenue"],
        [[r["name"], r["industry"], r["annual_revenue"]] for r in rows],
    )


@app.route("/contacts/export.csv")
def export_contacts():
    conn = db.get_db()
    rows = conn.execute(
        """SELECT c.name, c.title, a.name AS account_name, c.email, c.phone
           FROM contacts c JOIN accounts a ON a.id = c.account_id ORDER BY c.name"""
    ).fetchall()
    return _csv_response(
        "contacts.csv",
        ["Name", "Title", "Account", "Email", "Phone"],
        [[r["name"], r["title"], r["account_name"], r["email"], r["phone"]] for r in rows],
    )


@app.route("/opportunities/export.csv")
def export_opportunities():
    conn = db.get_db()
    rows = conn.execute(
        """SELECT o.name, a.name AS account_name, o.amount, o.stage, o.close_date, o.closed_at
           FROM opportunities o JOIN accounts a ON a.id = o.account_id ORDER BY o.name"""
    ).fetchall()
    return _csv_response(
        "opportunities.csv",
        ["Name", "Account", "Amount", "Stage", "Close Date", "Closed At"],
        [[r["name"], r["account_name"], r["amount"], r["stage"], r["close_date"], r["closed_at"] or ""] for r in rows],
    )


if __name__ == "__main__":
    app.run(debug=True, port=5050)
