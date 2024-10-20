CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    role TEXT NOT NULL,
    mac TEXT NULL
);

CREATE TABLE IF NOT EXISTS logins (
    login_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT,
    login_time REAL NOT NULL,
    logout_time REAL NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
