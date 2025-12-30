from flask import Flask, render_template, request, redirect
import sqlite3

app = Flask(__name__)

#initialize the database
def init_db():
    conn = sqlite3.connect('study.db')
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS courses
             (id INTEGER PRIMARY KEY,
              name TEXT,
              icon TEXT DEFAULT 'default-icon.jpg')''')


    c.execute('''CREATE TABLE IF NOT EXISTS sessions
                 (id INTEGER PRIMARY KEY,
                  course_id INTEGER,
                  type TEXT,
                  duration INTEGER)''')

    conn.commit()
    conn.close()


init_db()

#home page
@app.route('/')
@app.route('/')
def index():
    conn = sqlite3.connect('study.db')
    c = conn.cursor()
    # order by id descending
    c.execute("SELECT * FROM courses ORDER BY id DESC")
    courses = c.fetchall()
    conn.close()
    return render_template('index.html', courses=courses)


#add session
@app.route('/add_session', methods=['POST'])
def add_session():
    course = request.form['course']
    study_type = request.form['type']
    duration = int(request.form['duration'])
    conn = sqlite3.connect('study.db')
    c = conn.cursor()
    c.execute("INSERT INTO sessions (course, type, duration) VALUES (?, ?, ?)",
              (course, study_type, duration))
    conn.commit()
    conn.close()
    return redirect('/')


#add course
@app.route('/add_course', methods=['POST'])
def add_course():
    name = request.form['name']
    default_icon = 'default-icon.jpg'

    conn = sqlite3.connect('study.db')
    c = conn.cursor()
    c.execute("INSERT INTO courses (name, icon) VALUES (?, ?)", (name, default_icon))
    conn.commit()
    conn.close()

    return redirect('/')



if __name__ == "__main__":
    app.run(debug=True)