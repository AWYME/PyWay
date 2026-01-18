"""
Модуль для работы с базой данных приложения PyWay.
Объединяет все функции для работы с пользователями, курсами, уроками и прогрессом.
"""

import sqlite3
import os
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

# Путь к файлу базы данных. Он будет создан в корне проекта.
DATABASE_PATH = os.path.join(os.path.dirname(__file__), 'app.db')

def get_db_connection():
    """
    Создает и возвращает соединение с базой данных SQLite.
    Устанавливает row_factory для доступа к столбцам по имени.
    
    Returns:
        sqlite3.Connection: Объект соединения с базой данных.
    """
    # ВАЖНО: `check_same_thread=False` необходим для корректной работы с Flask,
    # так как запросы могут поступать из разных потоков.
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    # Позволяет обращаться к данным в строках как к словарю: row['column_name']
    conn.row_factory = sqlite3.Row
    return conn

# ========== ФУНКЦИИ ДЛЯ РАБОТЫ С ПОЛЬЗОВАТЕЛЯМИ ==========

def create_user(username, email, password):
    """
    Создает нового пользователя в базе данных.
    
    Args:
        username (str): Уникальное имя пользователя.
        email (str): Уникальный email пользователя.
        password (str): Пароль (будет захэширован перед сохранением).
    
    Returns:
        int|None: ID нового пользователя в случае успеха, None если пользователь с таким именем/email уже существует.
    """
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
        # Ошибка уникальности (UNIQUE constraint failed) для username или email
        return None
    finally:
        conn.close()

def get_user_by_username(username):
    """
    Ищет пользователя по имени пользователя (username).
    
    Args:
        username (str): Имя пользователя для поиска.
    
    Returns:
        sqlite3.Row|None: Строка с данными пользователя или None, если пользователь не найден.
    """
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
    conn.close()
    return user

def get_user_by_email(email):
    """
    Ищет пользователя по имени пользователя (email).
    
    Args:
        email (str): Имя пользователя для поиска.
    
    Returns:
        sqlite3.Row|None: Строка с данными пользователя или None, если пользователь не найден.
    """
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
    conn.close()
    return user

def verify_password(user_row, password):
    """
    Проверяет, соответствует ли введенный пароль хэшу в базе данных.
    
    Args:
        user_row (sqlite3.Row): Строка из таблицы users (объект, возвращенный get_user_by_username).
        password (str): Пароль для проверки.
    
    Returns:
        bool: True, если пароль верный, иначе False.
    """
    return check_password_hash(user_row['password_hash'], password)

# ========== ФУНКЦИИ ДЛЯ РАБОТЫ С КУРСАМИ И УРОКАМИ ==========

def get_all_courses():
    """
    Получает список всех активных курсов, отсортированных по order_index.
    
    Returns:
        list: Список объектов sqlite3.Row с данными курсов.
    """
    conn = get_db_connection()
    courses = conn.execute('''
        SELECT * FROM courses 
        WHERE is_active = TRUE 
        ORDER BY order_index
    ''').fetchall()
    conn.close()
    return courses

def get_course_with_content(course_id):
    """
    Получает подробную информацию о курсе, включая все его модули и уроки.
    
    Args:
        course_id (int): ID курса.
    
    Returns:
        dict: Словарь с данными курса, списком модулей и вложенными уроками.
              None, если курс не найден.
    """
    conn = get_db_connection()
    
    # Получаем данные самого курса
    course = conn.execute('SELECT * FROM courses WHERE id = ?', (course_id,)).fetchone()
    if not course:
        conn.close()
        return None
    
    # Получаем модули этого курса
    modules = conn.execute('''
        SELECT * FROM modules 
        WHERE course_id = ? 
        ORDER BY order_index
    ''', (course_id,)).fetchall()
    
    result_course = dict(course)
    result_course['modules'] = []
    
    # Для каждого модуля получаем его уроки
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
    """
    Получает данные конкретного урока.
    
    Args:
        lesson_id (int): ID урока.
    
    Returns:
        sqlite3.Row|None: Строка с данными урока или None.
    """
    conn = get_db_connection()
    lesson = conn.execute('SELECT * FROM lessons WHERE id = ?', (lesson_id,)).fetchone()
    conn.close()
    return lesson

# ========== ФУНКЦИИ ДЛЯ РАБОТЫ С ПРОГРЕССОМ ПОЛЬЗОВАТЕЛЯ ==========

def update_user_progress(user_id, lesson_id, code_submission=None, completed=True):
    """
    Обновляет или создает запись о прогрессе пользователя по уроку.
    
    Args:
        user_id (int): ID пользователя.
        lesson_id (int): ID урока.
        code_submission (str, optional): Код, отправленный пользователем.
        completed (bool, optional): Отметка о завершении урока.
    
    Returns:
        bool: True, если операция прошла успешно.
    """
    conn = get_db_connection()
    
    # Проверяем, есть ли уже запись о прогрессе
    existing = conn.execute('''
        SELECT * FROM user_progress 
        WHERE user_id = ? AND lesson_id = ?
    ''', (user_id, lesson_id)).fetchone()
    
    if existing:
        # Обновляем существующую запись
        conn.execute('''
            UPDATE user_progress 
            SET completed = ?, 
                completed_at = CASE WHEN ? THEN CURRENT_TIMESTAMP ELSE completed_at END,
                code_submission = ?, 
                attempts = attempts + 1
            WHERE user_id = ? AND lesson_id = ?
        ''', (completed, completed, code_submission, user_id, lesson_id))
    else:
        # Создаем новую запись
        conn.execute('''
            INSERT INTO user_progress (user_id, lesson_id, completed, completed_at, code_submission, attempts)
            VALUES (?, ?, ?, ?, ?, 1)
        ''', (user_id, lesson_id, completed, datetime.now() if completed else None, code_submission))
    
    # Если урок завершен, начисляем опыт пользователю
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
    """
    Получает информацию о прогрессе пользователя.
    Если передан course_id — возвращает прогресс по конкретному курсу.
    Если нет — возвращает общую сводку по всем урокам.
    
    Args:
        user_id (int): ID пользователя.
        course_id (int, optional): ID курса для детализации.
    
    Returns:
        list|dict: В зависимости от запроса.
    """
    conn = get_db_connection()
    
    if course_id:
        # Детальный прогресс по курсу: список всех уроков с отметкой о завершении
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
        # Общая сводка: сколько всего уроков и сколько завершено
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
    """
    Получает данные профиля пользователя: основную информацию и статистику.
    
    Args:
        user_id (int): ID пользователя.
    
    Returns:
        dict: Данные профиля пользователя.
    """
    conn = get_db_connection()
    
    # Основные данные пользователя
    user = conn.execute('''
        SELECT id, username, email, created_at, experience, level, streak_days
        FROM users WHERE id = ?
    ''', (user_id,)).fetchone()
    
    if not user:
        conn.close()
        return None
    
    profile_data = dict(user)
    
    # Считаем количество завершенных уроков для отображения в профиле
    progress_stats = get_user_progress(user_id)
    profile_data['progress_stats'] = progress_stats
    
    conn.close()
    return profile_data

# ========== ФУНКЦИИ ДЛЯ УПРАЖНЕНИЙ И ТЕСТОВ ==========

def get_exercise_for_lesson(lesson_id):
    """
    Получает упражнение для урока с тестовыми случаями
    
    Args:
        lesson_id (int): ID урока
    
    Returns:
        dict: Данные упражнения с тестами или None
    """
    conn = get_db_connection()
    
    # Ищем упражнение для этого урока
    exercise = conn.execute('''
        SELECT * FROM exercises 
        WHERE lesson_id = ?
    ''', (lesson_id,)).fetchone()
    
    if not exercise:
        conn.close()
        return None
    
    # Парсим тест-кейсы из JSON
    import json
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
    """
    Создает упражнение для урока
    
    Args:
        lesson_id (int): ID урока
        question (str): Вопрос/описание задачи
        starter_code (str): Начальный код для редактора
        solution_code (str): Правильное решение
        test_cases (list): Список тестовых случаев
    
    Returns:
        int: ID созданного упражнения
    """
    conn = get_db_connection()
    
    # Конвертируем тест-кейсы в JSON
    import json
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
    """Получает сводную информацию о прогрессе пользователя"""
    conn = get_db_connection()
    
    try:
        # Общая статистика
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
        
    except Exception as e:
        print(f"[ERROR] Ошибка при получении статистики: {e}")
        return None
    finally:
        conn.close()