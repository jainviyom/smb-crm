DROP TABLE IF EXISTS activities;
DROP TABLE IF EXISTS tasks;
DROP TABLE IF EXISTS opportunities;
DROP TABLE IF EXISTS contacts;
DROP TABLE IF EXISTS accounts;
DROP TABLE IF EXISTS leads;
DROP TABLE IF EXISTS reps;

CREATE TABLE reps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    title TEXT NOT NULL
);

CREATE TABLE leads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    company TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('New','Working','Qualified','Unqualified')),
    source TEXT NOT NULL,
    value INTEGER NOT NULL,
    converted INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    industry TEXT NOT NULL,
    owner_id INTEGER REFERENCES reps(id),
    annual_revenue INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE contacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    title TEXT NOT NULL,
    account_id INTEGER NOT NULL REFERENCES accounts(id),
    email TEXT NOT NULL,
    phone TEXT NOT NULL
);

CREATE TABLE opportunities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    account_id INTEGER NOT NULL REFERENCES accounts(id),
    rep_id INTEGER NOT NULL REFERENCES reps(id),
    amount INTEGER NOT NULL,
    stage TEXT NOT NULL CHECK (stage IN ('Qualify','Discovery','Proposal','Negotiation','Closed Won','Closed Lost')),
    close_date TEXT NOT NULL,
    closed_at TEXT
);

CREATE TABLE activities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contact_id INTEGER NOT NULL REFERENCES contacts(id),
    kind TEXT NOT NULL,
    description TEXT NOT NULL,
    occurred_at TEXT NOT NULL
);

CREATE TABLE tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    subtitle TEXT NOT NULL,
    due_at TEXT NOT NULL,
    done INTEGER NOT NULL DEFAULT 0
);
