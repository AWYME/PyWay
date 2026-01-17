import sqlite3
import os
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

DATABASE_PATH = 'ProjectDb.db'

def get_db_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def create_user(username, email, password):
    conn = get_db_connection()
    password_hash = generate_password_hash(password)
    
    try:
        conn.execute('''
            INSERT INTO users (username, email, password_hash)
            VALUES (?, ?, ?)
        ''', (username, email, password_hash))
        user_id = conn.lastrowid
        conn.commit()
        return user_id
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()

def get_user_by_username(username):
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
    conn.close()
    return user

def verify_password(user, password):
    return check_password_hash(user['password_hash'], password)

def update_user_progress(user_id, lesson_id, code_submission=None, completed=True):
    conn = get_db_connection()
    existing = conn.execute(
        'SELECT * FROM user_progress WHERE user_id = ? AND lesson_id = ?',
        (user_id, lesson_id)
    ).fetchone()
    
    if existing:
        conn.execute('''
            UPDATE user_progress 
            SET completed = ?, completed_at = ?, code_submission = ?, attempts = attempts + 1
            WHERE user_id = ? AND lesson_id = ?
        ''', (completed, datetime.now() if completed else None, code_submission, user_id, lesson_id))
    else:
        conn.execute('''
            INSERT INTO user_progress (user_id, lesson_id, completed, completed_at, code_submission, attempts)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, lesson_id, completed, datetime.now() if completed else None, code_submission, 1))
    
    if completed:
        conn.execute('''
            UPDATE users 
            SET experience = experience + 10, last_activity_date = DATE('now')
            WHERE id = ?
        ''', (user_id,))
    
    conn.commit()
    conn.close()

def get_user_progress(user_id, course_id=None):
    conn = get_db_connection()
    
    if course_id:
        progress = conn.execute('''
            SELECT l.*, up.completed, up.completed_at, up.attempts, up.score
            FROM lessons l
            JOIN modules m ON l.module_id = m.id
            LEFT JOIN user_progress up ON l.id = up.lesson_id AND up.user_id = ?
            WHERE m.course_id = ?
            ORDER BY m.order_index, l.order_index
        ''', (user_id, course_id)).fetchall()
    else:
        progress = conn.execute('''
            SELECT COUNT(*) as total_lessons,
                   SUM(CASE WHEN up.completed THEN 1 ELSE 0 END) as completed_lessons
            FROM lessons l
            LEFT JOIN user_progress up ON l.id = up.lesson_id AND up.user_id = ?
        ''', (user_id,)).fetchone()
    
    conn.close()
    return progress

def get_courses():
    conn = get_db_connection()
    courses = conn.execute('SELECT * FROM courses WHERE is_active = TRUE ORDER BY order_index').fetchall()
    conn.close()
    return courses

def get_lesson(lesson_id):
    conn = get_db_connection()
    lesson = conn.execute('''
        SELECT l.*, m.title as module_title, c.title as course_title
        FROM lessons l
        JOIN modules m ON l.module_id = m.id
        JOIN courses c ON m.course_id = c.id
        WHERE l.id = ?
    ''', (lesson_id,)).fetchone()
    conn.close()
    return lesson