# Migration 004 — Add Threads and Substack tables
UP = [
    # threads_posts table (publisher)
    '''CREATE TABLE IF NOT EXISTS threads_posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        threads_post_id TEXT UNIQUE,
        media_type TEXT,
        text_content TEXT,
        media_url TEXT,
        status TEXT DEFAULT 'draft',
        created_at TEXT,
        published_at TEXT,
        views INTEGER DEFAULT 0,
        likes INTEGER DEFAULT 0,
        replies_count INTEGER DEFAULT 0,
        reposts INTEGER DEFAULT 0,
        quotes INTEGER DEFAULT 0
    )''',
    # substack_posts table (publisher)
    '''CREATE TABLE IF NOT EXISTS substack_posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        substack_post_id TEXT UNIQUE,
        title TEXT,
        subtitle TEXT,
        body_preview TEXT,
        post_url TEXT,
        status TEXT DEFAULT 'draft',
        audience TEXT DEFAULT 'everyone',
        send_email INTEGER DEFAULT 1,
        created_at TEXT,
        published_at TEXT,
        views INTEGER DEFAULT 0,
        likes INTEGER DEFAULT 0,
        comments_count INTEGER DEFAULT 0,
        email_opens INTEGER DEFAULT 0
    )''',
    # threads_interactions table (connector)
    '''CREATE TABLE IF NOT EXISTS threads_interactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        external_id TEXT UNIQUE,
        author_id TEXT,
        author_name TEXT,
        content TEXT,
        parent_id TEXT,
        url TEXT,
        reply_sent TEXT,
        escalated_to_slack INTEGER DEFAULT 0,
        created_at TEXT,
        processed_at TEXT
    )''',
    # substack_interactions table (connector)
    '''CREATE TABLE IF NOT EXISTS substack_interactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        external_id TEXT UNIQUE,
        author_id TEXT,
        author_name TEXT,
        content TEXT,
        parent_id TEXT,
        url TEXT,
        reply_sent TEXT,
        escalated_to_slack INTEGER DEFAULT 0,
        created_at TEXT,
        processed_at TEXT
    )'''
]

DOWN = [
    'DROP TABLE IF EXISTS threads_posts',
    'DROP TABLE IF EXISTS substack_posts',
    'DROP TABLE IF EXISTS threads_interactions',
    'DROP TABLE IF EXISTS substack_interactions',
]


def up(conn):
    for sql in UP:
        conn.execute(sql)
    conn.commit()
    print('Migration 004 applied: threads + substack tables created')


def down(conn):
    for sql in DOWN:
        conn.execute(sql)
    conn.commit()
    print('Migration 004 rolled back')


if __name__ == '__main__':
    import sqlite3
    import os
    db_path = os.environ.get('DB_PATH', 'data/eworks.db')
    conn = sqlite3.connect(db_path)
    up(conn)
    conn.close()
