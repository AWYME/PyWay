from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from db.db import *
import subprocess
import sys
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SECURE'] = False
app.config['PERMANENT_SESSION_LIFETIME'] = 86400
app.config['JSON_AS_ASCII'] = False
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True


# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================

def login_required(f):
    from functools import wraps
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Для доступа к этой странице необходимо войти в систему.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    
    return decorated_function

def execute_python_code(code, user_input=""):
    try:
        process = subprocess.Popen(
            [sys.executable, '-c', code],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            errors='ignore'
        )
        
        try:
            stdout, stderr = process.communicate(input=user_input, timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()
            return "Ошибка: время выполнения кода истекло (максимум 5 секунд)"
        
        if stderr:
            error_lines = []
            for line in stderr.split('\n'):
                if line and not any(x in line.lower() for x in ['warning', 'deprecation']):
                    error_lines.append(line)
            
            if error_lines:
                return f"Ошибка выполнения:\n{''.join(error_lines[:5])}"
        
        return stdout.strip() if stdout else "(нет вывода)"
        
    except Exception as e:
        return f"Системная ошибка: {str(e)}"

def get_user_progress_summary(user_id):
    conn = get_db_connection()
    
    stats = conn.execute('''
        SELECT 
            COUNT(DISTINCT l.id) as total_lessons,
            COUNT(DISTINCT up.lesson_id) as completed_lessons,
            COALESCE(SUM(up.score), 0) as total_score,
            u.experience,
            u.level
        FROM lessons l
        CROSS JOIN users u
        LEFT JOIN user_progress up ON l.id = up.lesson_id AND up.user_id = ?
        WHERE u.id = ?
        GROUP BY u.id
    ''', (user_id, user_id)).fetchone()
    
    conn.close()
    
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

# ==================== МАРШРУТЫ АУТЕНТИФИКАЦИИ ====================

@app.route('/')
def index():
    courses = get_all_courses()
    user_stats = None
    
    if 'user_id' in session:
        user_stats = get_user_progress_summary(session['user_id'])
    
    return render_template('index.html', 
                         courses=courses, 
                         user_stats=user_stats,
                         username=session.get('username'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if 'user_id' in session:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        
        if not username or not email or not password:
            flash('Все поля обязательны для заполнения.', 'error')
            return render_template('auth/signup.html')
        
        if len(password) < 6:
            flash('Пароль должен содержать минимум 6 символов.', 'error')
            return render_template('auth/signup.html')
        
        user = create_user(username, email, password)

        
        if user:
            flash('Регистрация успешна!', 'success')
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['email'] = user['email']
            session.permanent = True
            return redirect(url_for('index'))
        else:
            flash('Пользователь с таким именем или email уже существует.', 'error')
    
    return render_template('auth/signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        
        user = get_user_by_email(email)
        
        if user and verify_password(user, password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['email'] = user['email']
            session.permanent = True
            
            conn = get_db_connection()
            conn.execute("UPDATE users SET last_activity_date = DATE('now') WHERE id = ?", 
                        (user['id'],))
            conn.commit()
            conn.close()
            
            flash(f'Добро пожаловать, {user["username"]}!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Неверное имя пользователя или пароль.', 'error')
    
    return render_template('auth/login.html')

@app.route('/logout')
def logout():
    """Выход из системы"""
    session.clear()
    flash('Вы успешно вышли из системы.', 'success')
    return redirect(url_for('index'))

# ==================== МАРШРУТЫ КУРСОВ И УРОКОВ ====================

@app.route('/courses')
@login_required
def courses():
    """Страница со списком всех курсов"""
    courses_list = get_all_courses()
    user_progress = {}
    
    for course in courses_list:
        progress = get_user_progress(session['user_id'], course['id'])
        user_progress[course['id']] = progress
    
    return render_template('courses.html', 
                         courses=courses_list, 
                         user_progress=user_progress)

@app.route('/course/<int:course_id>')
@login_required
def course_detail(course_id):
    """Детальная информация о курсе"""
    course_data = get_course_with_content(course_id)
    
    if not course_data:
        flash('Курс не найден.', 'error')
        return redirect(url_for('courses'))
    
    progress_data = get_user_progress(session['user_id'], course_id)
    
    return render_template('course_detail.html',
                         course=course_data,
                         progress=progress_data)

@app.route('/lesson/<int:lesson_id>')
@login_required
def lesson(lesson_id):
    """
    Страница урока с редактором кода
    """
    # Получаем данные урока
    lesson_data = get_lesson(lesson_id)
    
    if not lesson_data:
        flash('Урок не найден.', 'error')
        return redirect(url_for('courses'))
    
    # Получаем информацию о модуле и курсе
    conn = get_db_connection()
    module = conn.execute('SELECT * FROM modules WHERE id = ?', 
                         (lesson_data['module_id'],)).fetchone()
    course = conn.execute('SELECT * FROM courses WHERE id = ?', 
                         (module['course_id'],)).fetchone()
    
    # Получаем упражнение для этого урока
    exercise = get_exercise_for_lesson(lesson_id)
    conn.close()
    
    # Проверяем, пройден ли урок
    conn = get_db_connection()
    progress = conn.execute('''
        SELECT completed FROM user_progress 
        WHERE user_id = ? AND lesson_id = ?
    ''', (session['user_id'], lesson_id)).fetchone()
    conn.close()
    
    lesson_completed = bool(progress and progress['completed'])
    
    # Если у урока нет упражнения, используем заглушку
    if not exercise:
        test_cases = [
    {
        "input": "",
        "output": "Hello, World!",
        "description": "Basic output test"
    },
    {
        "input": "",
        "output": "Hello, World!\n",
        "description": "Test with newline"
    }
]
        starter_code = '''# Your first Python program
# Write code that prints "Hello, World!"

# Example solution:
# print("Hello, World!")

# Your code below:'''
        question = "Задание для этого урока находится в разработке"
    else:
        test_cases = exercise.get('test_cases', [])
        starter_code = exercise.get('starter_code', '')
        question = exercise.get('question', '')
    
    # Получаем следующий и предыдущий уроки для навигации
    conn = get_db_connection()
    next_lesson = conn.execute('''
        SELECT id, title FROM lessons 
        WHERE module_id = ? AND order_index > ? 
        ORDER BY order_index LIMIT 1
    ''', (lesson_data['module_id'], lesson_data['order_index'])).fetchone()
    
    prev_lesson = conn.execute('''
        SELECT id, title FROM lessons 
        WHERE module_id = ? AND order_index < ? 
        ORDER BY order_index DESC LIMIT 1
    ''', (lesson_data['module_id'], lesson_data['order_index'])).fetchone()
    conn.close()
    
    return render_template('lesson.html',
                         lesson=lesson_data,
                         module_title=module['title'],
                         course_title=course['title'],
                         lesson_completed=lesson_completed,
                         test_cases=test_cases,
                         starter_code=starter_code,
                         question=question,
                         next_lesson=next_lesson,
                         prev_lesson=prev_lesson)

@app.route('/lesson/<int:lesson_id>/complete', methods=['POST'])
@login_required
def complete_lesson(lesson_id):
    """
    Отметка урока как пройденного
    POST-запрос: сохранение прогресса
    """
    try:
        code_submission = request.form.get('code', '')
        
        update_user_progress(
            session['user_id'], 
            lesson_id, 
            code_submission=code_submission if code_submission else None,
            completed=True
        )
        
        flash('Урок успешно завершен!', 'success')
        
        return redirect(url_for('lesson', lesson_id=lesson_id))
        
    except Exception as e:
        flash(f'Ошибка при сохранении прогресса: {str(e)}', 'error')
        return redirect(url_for('lesson', lesson_id=lesson_id))

# ==================== API ДЛЯ РЕДАКТОРА КОДА ====================

@app.route('/api/execute', methods=['POST'])
@login_required
def execute_code():
    """
    API для выполнения Python кода
    Используется редактором кода на странице урока
    """
    if not request.is_json:
        return jsonify({'error': 'Content-Type должен быть application/json'}), 400
    
    data = request.get_json()
    code = data.get('code', '')
    user_input = data.get('input', '')
    
    if not code:
        return jsonify({'error': 'Код не может быть пустым'}), 400
    
    if len(code) > 10000:
        return jsonify({'error': 'Код слишком длинный (максимум 10000 символов)'}), 400
    
    result = execute_python_code(code, user_input)
    
    return jsonify({
        'success': not result.startswith('Ошибка'),
        'output': result,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/lesson/<int:lesson_id>/tests')
@login_required
def get_lesson_tests(lesson_id):
    """API для получения тестовых данных урока"""
    # В реальном проекте брать из БД
    test_cases = [
        {"input": "5\n3", "output": "8", "description": "Тест 1"},
        {"input": "10\n-2", "output": "8", "description": "Тест 2"},
        {"input": "0\n0", "output": "0", "description": "Тест 3"}
    ]
    
    return jsonify({
        'lesson_id': lesson_id,
        'test_cases': test_cases
    })

# ==================== ПРОФИЛЬ И СТАТИСТИКА ====================

@app.route('/profile')
@login_required
def profile():
    """Страница профиля пользователя"""
    user_data = get_user_profile(session['user_id'])
    
    if not user_data:
        flash('Профиль не найден.', 'error')
        return redirect(url_for('index'))
    progress_stats = get_user_progress_summary(session['user_id'])
    conn = get_db_connection()
    recent_lessons = conn.execute('''
        SELECT l.title, up.completed_at, m.title as module_title
        FROM user_progress up
        JOIN lessons l ON up.lesson_id = l.id
        JOIN modules m ON l.module_id = m.id
        WHERE up.user_id = ? AND up.completed = TRUE
        ORDER BY up.completed_at DESC
        LIMIT 5
    ''', (session['user_id'],)).fetchall()
    conn.close()
    
    return render_template('profile.html',
                         user=user_data,
                         progress_stats=progress_stats,
                         recent_lessons=recent_lessons)

# ==================== ОБРАБОТЧИКИ ОШИБОК ====================

@app.errorhandler(404)
def page_not_found(error):
    """Обработка ошибки 404"""
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    """Обработка ошибки 500"""
    return render_template('errors/500.html'), 500

# ==================== ЗАПУСК ПРИЛОЖЕНИЯ ====================

if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True,
        threaded=True
    )

@app.route('/api/lesson/<int:lesson_id>/save-code', methods=['POST'])
@login_required
def save_lesson_code(lesson_id):
    """Сохранение кода пользователя для урока"""
    if not request.is_json:
        return jsonify({'error': 'Invalid content type'}), 400
    
    data = request.get_json()
    code = data.get('code', '')
    
    if not code:
        return jsonify({'error': 'Code is empty'}), 400
    
    # Сохраняем код в прогресс пользователя
    conn = get_db_connection()
    conn.execute('''
        INSERT OR REPLACE INTO user_progress 
        (user_id, lesson_id, code_submission, completed)
        VALUES (?, ?, ?, ?)
    ''', (session['user_id'], lesson_id, code, False))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': 'Код сохранён'})

@app.route('/api/lesson/<int:lesson_id>/get-code', methods=['GET'])
@login_required
def get_saved_code(lesson_id):
    """Получение сохранённого кода пользователя"""
    conn = get_db_connection()
    progress = conn.execute('''
        SELECT code_submission FROM user_progress 
        WHERE user_id = ? AND lesson_id = ?
    ''', (session['user_id'], lesson_id)).fetchone()
    conn.close()
    
    if progress and progress['code_submission']:
        return jsonify({
            'success': True,
            'code': progress['code_submission']
        })
    
    return jsonify({'success': False, 'code': ''})