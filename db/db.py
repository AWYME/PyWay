import sqlite3
import os
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import json

DATABASE_PATH = os.path.join(os.path.dirname(__file__), 'app.db')

def get_db_connection():
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def create_user(username, email, password):
    conn = get_db_connection()
    password_hash = generate_password_hash(password)
    
    try:
        cursor = conn.execute('''
            INSERT INTO users (username, email, password_hash)
            VALUES (?, ?, ?)
        ''', (username, email, password_hash))
        user_id = cursor.lastrowid
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

def get_user_by_email(email):
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
    conn.close()
    return user

def verify_password(user_row, password):
    return check_password_hash(user_row['password_hash'], password)

def get_all_courses():
    conn = get_db_connection()
    
    try:
        courses = conn.execute('''
            SELECT * FROM courses 
            WHERE is_active = TRUE 
            ORDER BY order_index
        ''').fetchall()
        
        print(f"[DB] get_all_courses() вернула {len(courses)} курсов")
        return courses
        
    except Exception as e:
        print(f"[DB ERROR] Ошибка в get_all_courses(): {e}")
        return []
    finally:
        conn.close()

def get_course_with_content(course_id):
    conn = get_db_connection()
    course = conn.execute('SELECT * FROM courses WHERE id = ?', (course_id,)).fetchone()
    if not course:
        conn.close()
        return None
    modules = conn.execute('''
        SELECT * FROM modules 
        WHERE course_id = ? 
        ORDER BY order_index
    ''', (course_id,)).fetchall()
    result_course = dict(course)
    result_course['modules'] = []
    for module in modules:
        module_dict = dict(module)
        lessons = conn.execute('''
            SELECT * FROM lessons 
            WHERE module_id = ? 
            ORDER BY order_index
        ''', (module['id'],)).fetchall()
        module_dict['lessons'] = [dict(lesson) for lesson in lessons]
        result_course['modules'].append(module_dict)
    conn.close()
    return result_course

def get_lesson(lesson_id):
    conn = get_db_connection()
    lesson = conn.execute('SELECT * FROM lessons WHERE id = ?', (lesson_id,)).fetchone()
    conn.close()
    return lesson

def update_user_progress(user_id, lesson_id, code_submission=None, completed=True):
    conn = get_db_connection()
    existing = conn.execute('''
        SELECT * FROM user_progress 
        WHERE user_id = ? AND lesson_id = ?
    ''', (user_id, lesson_id)).fetchone()   
    if existing:
        conn.execute('''
            UPDATE user_progress 
            SET completed = ?, 
                completed_at = CASE WHEN ? THEN CURRENT_TIMESTAMP ELSE completed_at END,
                code_submission = ?, 
                attempts = attempts + 1
            WHERE user_id = ? AND lesson_id = ?
        ''', (completed, completed, code_submission, user_id, lesson_id))
    else:
        conn.execute('''
            INSERT INTO user_progress (user_id, lesson_id, completed, completed_at, code_submission, attempts)
            VALUES (?, ?, ?, ?, ?, 1)
        ''', (user_id, lesson_id, completed, datetime.now() if completed else None, code_submission))
    if completed:
        conn.execute('''
            UPDATE users 
            SET experience = experience + 10, 
                last_activity_date = DATE('now')
            WHERE id = ?
        ''', (user_id,))
    
    conn.commit()
    conn.close()
    return True

def get_user_progress(user_id, course_id=None):
    conn = get_db_connection()
    if course_id:
        progress = conn.execute('''
            SELECT l.id, l.title, l.module_id, l.order_index,
                   COALESCE(up.completed, 0) as completed,
                   up.completed_at, up.attempts
            FROM lessons l
            JOIN modules m ON l.module_id = m.id
            LEFT JOIN user_progress up ON l.id = up.lesson_id AND up.user_id = ?
            WHERE m.course_id = ?
            ORDER BY m.order_index, l.order_index
        ''', (user_id, course_id)).fetchall()
        result = [dict(row) for row in progress]
    else:
        stats = conn.execute('''
            SELECT 
                COUNT(l.id) as total_lessons,
                COUNT(up.lesson_id) as completed_lessons
            FROM lessons l
            LEFT JOIN user_progress up ON l.id = up.lesson_id AND up.user_id = ?
        ''', (user_id,)).fetchone()
        result = dict(stats)
    conn.close()
    return result

def get_user_profile(user_id):
    conn = get_db_connection()
    user = conn.execute('''
        SELECT id, username, email, created_at, experience, level, streak_days
        FROM users WHERE id = ?
    ''', (user_id,)).fetchone()   
    if not user:
        conn.close()
        return None
    profile_data = dict(user)
    progress_stats = get_user_progress(user_id)
    profile_data['progress_stats'] = progress_stats
    conn.close()
    return profile_data

def get_exercise_for_lesson(lesson_id):
    conn = get_db_connection()
    exercise = conn.execute('''
        SELECT * FROM exercises 
        WHERE lesson_id = ?
    ''', (lesson_id,)).fetchone()
    if not exercise:
        conn.close()
        return None
    test_cases = []
    if exercise['test_cases']:
        try:
            test_cases = json.loads(exercise['test_cases'])
        except:
            test_cases = []
    result = dict(exercise)
    result['test_cases'] = test_cases
    result['parsed_test_cases'] = test_cases
    conn.close()
    return result

def create_exercise(lesson_id, question, starter_code, solution_code, test_cases):
    conn = get_db_connection()
    test_cases_json = json.dumps(test_cases, ensure_ascii=False)
    cursor = conn.execute('''
        INSERT INTO exercises (lesson_id, question, starter_code, solution_code, test_cases)
        VALUES (?, ?, ?, ?, ?)
    ''', (lesson_id, question, starter_code, solution_code, test_cases_json))
    exercise_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return exercise_id

def get_user_progress_summary(user_id):
    conn = get_db_connection()
    try:
        stats = conn.execute('''
            SELECT 
                COUNT(DISTINCT l.id) as total_lessons,
                COUNT(DISTINCT up.lesson_id) as completed_lessons,
                COALESCE(SUM(up.score), 0) as total_score,
                u.experience,
                u.level
            FROM lessons l
            CROSS JOIN users u
            LEFT JOIN user_progress up ON l.id = up.lesson_id AND up.user_id = u.id AND up.completed = TRUE
            WHERE u.id = ?
            GROUP BY u.id
        ''', (user_id,)).fetchone()
        
        if stats:
            progress_percent = (stats['completed_lessons'] / stats['total_lessons'] * 100) if stats['total_lessons'] > 0 else 0
            return {
                'total_lessons': stats['total_lessons'],
                'completed_lessons': stats['completed_lessons'],
                'progress_percent': round(progress_percent, 1),
                'total_score': stats['total_score'],
                'experience': stats['experience'],
                'level': stats['level']
            }
        
        return None
        
    except Exception:
        print(f"[ERROR] Ошибка при получении статистики: {Exception}")
        return None
    finally:
        conn.close()