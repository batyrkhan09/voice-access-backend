import sqlite3

def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            passphrase TEXT
        )
    ''')
    # Пример: добавим пользователя
    cursor.execute('INSERT OR IGNORE INTO users (username, passphrase) VALUES (?, ?)', 
               ('test_user', 'мой голос мой пропуск'))

    conn.commit()
    conn.close()
