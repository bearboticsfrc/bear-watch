CREATE TABLE IF NOT EXISTS users (
    user_id INT PRIMARY KEY,
    username VARCHAR(255) NOT NULL,
    role VARCHAR(100) NOT NULL
);

CREATE TABLE IF NOT EXISTS logins (
    login_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INT,
    login_time REAL NOT NULL,
    logout_time REAL NULL,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);