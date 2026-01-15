from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory
app = Flask(  
	__name__,
	template_folder='templates',  
	static_folder='static',
)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login')
def login():
    return render_template('auth/login.html')

@app.route('/signup')
def signup():
    return render_template('auth/signup.html')

@app.route('/courses')
def courses():
    return render_template('courses.html')

@app.route('/profile')
def profile():
    return render_template('profile.html')

@app.route('/lesson/<int:lesson_id>')
def lesson(lesson_id):
    return render_template('lesson.html', lesson_id=lesson_id)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)

app.run(host='0.0.0.0', port=81)