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

def init_db():
    """
    Инициализирует базу данных: создает все необходимые таблицы
    """
    conn = get_db_connection()
    
    # Включаем поддержку внешних ключей
    conn.execute("PRAGMA foreign_keys = ON")
    
    # СОЗДАЕМ ТАБЛИЦЫ по порядку:
    
    # 1. Таблица пользователей
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username VARCHAR(50) UNIQUE NOT NULL,
            email VARCHAR(100) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            experience INTEGER DEFAULT 0,
            level INTEGER DEFAULT 1,
            streak_days INTEGER DEFAULT 0,
            last_activity_date DATE
        )
    ''')
    
    # 2. Таблица курсов (ДОЛЖНА БЫТЬ ПЕРВОЙ из зависимых)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title VARCHAR(100) NOT NULL,
            description TEXT,
            difficulty_level VARCHAR(20) DEFAULT 'beginner',
            order_index INTEGER DEFAULT 0,
            is_active BOOLEAN DEFAULT TRUE,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 3. Таблица модулей (зависит от courses)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS modules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_id INTEGER NOT NULL,
            title VARCHAR(100) NOT NULL,
            description TEXT,
            order_index INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (course_id) REFERENCES courses (id) ON DELETE CASCADE
        )
    ''')
    
    # 4. Таблица уроков (зависит от modules)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS lessons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            module_id INTEGER NOT NULL,
            title VARCHAR(100) NOT NULL,
            content TEXT NOT NULL,
            order_index INTEGER DEFAULT 0,
            lesson_type VARCHAR(20) DEFAULT 'theory',
            expected_output TEXT,
            hints TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (module_id) REFERENCES modules (id) ON DELETE CASCADE
        )
    ''')
    
    # 5. Таблица упражнений (зависит от lessons)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS exercises (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lesson_id INTEGER NOT NULL,
            question TEXT NOT NULL,
            starter_code TEXT,
            solution_code TEXT NOT NULL,
            test_cases TEXT,
            difficulty VARCHAR(20) DEFAULT 'easy',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (lesson_id) REFERENCES lessons (id) ON DELETE CASCADE
        )
    ''')
    
    # 6. Таблица прогресса пользователя (зависит от users и lessons)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS user_progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            lesson_id INTEGER NOT NULL,
            completed BOOLEAN DEFAULT FALSE,
            completed_at DATETIME,
            code_submission TEXT,
            attempts INTEGER DEFAULT 0,
            score INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
            FOREIGN KEY (lesson_id) REFERENCES lessons (id) ON DELETE CASCADE,
            UNIQUE(user_id, lesson_id)
        )
    ''')
    
    conn.commit()
    conn.close()
    
    print("[INFO] Таблицы БД созданы успешно")
    
    # ТОЛЬКО ПОСЛЕ СОЗДАНИЯ ТАБЛИЦ добавляем тестовые данные
    add_sample_course_with_exercises()

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

def add_sample_course_with_exercises():
    """
    Добавляет тестовый курс с уроками (вызывается ПОСЛЕ создания таблиц)
    """
    conn = get_db_connection()
    
    try:
        # Проверяем, есть ли уже курсы
        existing = conn.execute('SELECT COUNT(*) as count FROM courses').fetchone()
        
        if existing and existing['count'] > 0:
            print("[INFO] Курсы уже существуют, пропускаем создание")
            return
        
        print("[INFO] Создаём тестовый курс...")
        
        # 1. Создаем курс
        conn.execute('''
            INSERT INTO courses (id, title, description, difficulty_level, order_index)
            VALUES (?, ?, ?, ?, ?)
        ''', (1, 'Python Basics', 'Practical course for beginners: from variables to functions', 'beginner', 1))
        
        # 2. Создаем модули
        modules = [
            (1, 1, 'Getting Started', 'Basic Python concepts', 1),
            (2, 1, 'Variables and Data Types', 'Working with data in Python', 2),
            (3, 1, 'Control Flow', 'Decision making in programs', 3),
        ]
        
        for module_id, course_id, title, description, order in modules:
            conn.execute('''
                INSERT INTO modules (id, course_id, title, description, order_index)
                VALUES (?, ?, ?, ?, ?)
            ''', (module_id, course_id, title, description, order))
        
        # 3. Создаем уроки
        lessons = [
            # Модуль 1
            (1, 1, 'First Program', 'Learn how to write and run your first Python program', 1, 'practice'),
            (2, 1, 'Reading Input', 'Learn to read user input in Python', 2, 'practice'),
            # Модуль 2
            (3, 2, 'Variables and Assignment', 'Working with variables and basic operations', 1, 'practice'),
            (4, 2, 'Arithmetic Operations', 'Performing mathematical calculations', 2, 'practice'),
            # Модуль 3
            (5, 3, 'If Statement', 'Simple conditional statements', 1, 'practice'),
            (6, 3, 'If-Else Statement', 'Making decisions in code', 2, 'practice'),
        ]
        
        for lesson_id, module_id, title, content, order_index, lesson_type in lessons:
            conn.execute('''
                INSERT INTO lessons (id, module_id, title, content, order_index, lesson_type)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (lesson_id, module_id, title, content, order_index, lesson_type))
        
        conn.commit()
        print("[INFO] Курс и уроки созданы")
        
    except sqlite3.Error as e:
        print(f"[ERROR] Ошибка при создании курса: {e}")
        conn.rollback()
    finally:
        conn.close()
    
    # 4. Создаем упражнения (отдельно, т.к. есть JSON)
    create_sample_exercises()

def create_sample_exercises():
    """Создает упражнения для тестового курса (БЕЗ кириллицы в коде)"""
    import json
    
    # === УРОК 1: Первая программа ===
    test_cases_1 = [
        {
            "input": "",
            "output": "Hello, World!",
            "description": "Базовая проверка вывода"
        },
        {
            "input": "",
            "output": "Hello, World!\n",
            "description": "Проверка с переводом строки"
        }
    ]
    
    create_exercise(
        lesson_id=1,
        question="Напишите программу, которая выводит текст 'Hello, World!'",
        starter_code='''# Your first Python program
# Write code that prints "Hello, World!"

# Example:
# print("Hello, World!")

# Your code below:''',
        solution_code='print("Hello, World!")',
        test_cases=test_cases_1
    )
    
    # === УРОК 2: Чтение ввода ===
    test_cases_2 = [
        {
            "input": "Alice",
            "output": "Hello, Alice!",
            "description": "Одно слово"
        },
        {
            "input": "John Doe",
            "output": "Hello, John Doe!",
            "description": "Два слова"
        },
        {
            "input": "Python",
            "output": "Hello, Python!",
            "description": "Слово Python"
        }
    ]
    
    create_exercise(
        lesson_id=2,
        question="Напишите программу, которая читает имя и выводит приветствие",
        starter_code='''# Program to greet a user
# Read a name from input and print "Hello, [name]!"

# Hint: use input() to read and print() to output

# Example solution:
# name = input()
# print(f"Hello, {name}!")

# Your code:''',
        solution_code='''name = input()
print(f"Hello, {name}!")''',
        test_cases=test_cases_2
    )
    
    # === УРОК 3: Сложение чисел ===
    test_cases_3 = [
        {
            "input": "5\n3",
            "output": "8",
            "description": "Сложение положительных чисел"
        },
        {
            "input": "-5\n10",
            "output": "5",
            "description": "Сложение отрицательного и положительного"
        },
        {
            "input": "0\n0",
            "output": "0",
            "description": "Сложение нулей"
        }
    ]
    
    create_exercise(
        lesson_id=3,
        question="Напишите программу, которая складывает два числа",
        starter_code='''# Program to add two numbers
# Read two numbers from input and print their sum

# Hint: use int() to convert strings to numbers

# Example:
# a = int(input())
# b = int(input())
# print(a + b)

# Your code:''',
        solution_code='''a = int(input())
b = int(input())
print(a + b)''',
        test_cases=test_cases_3
    )
    
    # === УРОК 4: Умножение чисел ===
    test_cases_4 = [
        {
            "input": "5\n3",
            "output": "15",
            "description": "Умножение положительных"
        },
        {
            "input": "-5\n10",
            "output": "-50",
            "description": "Умножение отрицательного и положительного"
        },
        {
            "input": "7\n0",
            "output": "0",
            "description": "Умножение на ноль"
        }
    ]
    
    create_exercise(
        lesson_id=4,
        question="Напишите программу, которая умножает два числа",
        starter_code='''# Program to multiply two numbers
# Read two numbers and print their product

# Your code here:''',
        solution_code='''a = int(input())
b = int(input())
print(a * b)''',
        test_cases=test_cases_4
    )
    
    # === УРОК 5: Проверка чётности ===
    test_cases_5 = [
        {
            "input": "4",
            "output": "even",
            "description": "Чётное число"
        },
        {
            "input": "7",
            "output": "odd",
            "description": "Нечётное число"
        },
        {
            "input": "0",
            "output": "even",
            "description": "Ноль - чётное"
        }
    ]
    
    create_exercise(
        lesson_id=5,
        question="Напишите программу, которая определяет чётность числа",
        starter_code='''# Check if a number is even or odd
# Read a number, print "even" if even, "odd" if odd

# Hint: use % operator (remainder)
# Example: 5 % 2 == 1 (odd), 4 % 2 == 0 (even)

# Your code:''',
        solution_code='''num = int(input())
if num % 2 == 0:
    print("even")
else:
    print("odd")''',
        test_cases=test_cases_5
    )
    
    # === УРОК 6: Максимум из двух чисел ===
    test_cases_6 = [
        {
            "input": "5\n3",
            "output": "5",
            "description": "Первое число больше"
        },
        {
            "input": "3\n10",
            "output": "10",
            "description": "Второе число больше"
        },
        {
            "input": "7\n7",
            "output": "7",
            "description": "Числа равны"
        }
    ]
    
    create_exercise(
        lesson_id=6,
        question="Напишите программу, которая находит максимальное из двух чисел",
        starter_code='''# Find maximum of two numbers
# Read two numbers, print the larger one
# If equal, print either one

# Your code:''',
        solution_code='''a = int(input())
b = int(input())
if a >= b:
    print(a)
else:
    print(b)''',
        test_cases=test_cases_6
    )
    
    print("[INFO] Тестовые упражнения созданы (без кириллицы в коде)")

# Обновим функцию init_db() для создания таблицы упражнений
def init_db():
    """
    Инициализирует базу данных: создает все необходимые таблицы
    """
    conn = get_db_connection()
    
    # Включаем поддержку внешних ключей
    conn.execute("PRAGMA foreign_keys = ON")
    
    # СОЗДАЕМ ТАБЛИЦУ УПРАЖНЕНИЙ (добавляем к существующим)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS exercises (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lesson_id INTEGER NOT NULL,
            question TEXT NOT NULL,
            starter_code TEXT,
            solution_code TEXT NOT NULL,
            test_cases TEXT,
            difficulty VARCHAR(20) DEFAULT 'easy',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (lesson_id) REFERENCES lessons (id) ON DELETE CASCADE
        )
    ''')
    
    conn.commit()
    conn.close()
    
    # Добавляем тестовый курс
    add_sample_course_with_exercises()