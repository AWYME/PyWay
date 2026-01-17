from flask import Flask, render_template, request, redirect, url_for, session, flash
from db.db import *

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'

@app.route('/')
def index():
    courses = get_courses()
    user_progress = None
    if 'user_id' in session:
        user_progress = get_user_progress(session['user_id'])
    return render_template('index.html', courses=courses, user_progress=user_progress)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        user_id = create_user(username, email, password)
        if user_id:
            flash('Регистрация успешна! Теперь войдите в систему.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Пользователь с таким именем или email уже существует.', 'error')
    
    return render_template('auth/register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = get_user_by_username(username)
        if user and verify_password(user, password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            flash('Вход выполнен успешно!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Неверное имя пользователя или пароль.', 'error')    
    return render_template('auth/login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/courses')
def courses():
    courses_list = get_courses()
    user_progress = {}
    if 'user_id' in session:
        for course in courses_list:
            user_progress[course['id']] = get_user_progress(session['user_id'], course['id'])
    
    return render_template('courses.html', courses=courses_list, user_progress=user_progress)

@app.route('/lesson/<int:lesson_id>', methods=['GET', 'POST'])
def lesson(lesson_id):
    if 'user_id' not in session:
        flash('Пожалуйста, войдите для доступа к урокам.', 'error')
        return redirect(url_for('login'))
    
    lesson_data = get_lesson(lesson_id)
    if not lesson_data:
        flash('Урок не найден.', 'error')
        return redirect(url_for('courses'))
#TODO: вставить нужный код  
    if request.method == 'POST':
        code_submission = request.form.get('code_submission', '')
        # Здесь можно добавить проверку кода
        completed = True
        
        update_user_progress(session['user_id'], lesson_id, code_submission, completed)
        flash('Прогресс сохранен!', 'success')
        return redirect(url_for('lesson', lesson_id=lesson_id))
    return render_template('lesson.html', lesson=lesson_data)

@app.route('/profile')
def profile():
    if 'user_id' not in session:
        flash('Пожалуйста, войдите для просмотра профиля.', 'error')
        return redirect(url_for('login'))
    
    user_progress = get_user_progress(session['user_id'])
    return render_template('profile.html', user_progress=user_progress)

if __name__ == '__main__':
    app.run(debug=True)