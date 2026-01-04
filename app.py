from flask import Flask, render_template, request, redirect, jsonify
import sqlite3
import time
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)

UPLOAD_FOLDER = 'static'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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

    c.execute('''CREATE TABLE IF NOT EXISTS study_types
                 (id INTEGER PRIMARY KEY,
                  name TEXT UNIQUE)''')

    conn.commit()
    conn.close()

init_db()

#home page
@app.route('/')
def index():
    conn = sqlite3.connect('study.db')
    c = conn.cursor()
    c.execute("SELECT * FROM courses ORDER BY id DESC")
    courses = c.fetchall()
    conn.close()
    return render_template('index.html', courses=courses)

#add course
@app.route('/add_course', methods=['POST'])
def add_course():
    name = request.form['name']
    default_icon = 'default-icon.jpg'

    conn = sqlite3.connect('study.db')
    c = conn.cursor()
    c.execute("INSERT INTO courses (name, icon) VALUES (?, ?)", (name, default_icon))
    course_id = c.lastrowid
    conn.commit()
    conn.close()

    return jsonify({'id': course_id, 'name': name, 'icon': default_icon})

#course opened
@app.route('/course/<int:course_id>')
def course_page(course_id):
    conn = sqlite3.connect('study.db')
    c = conn.cursor()

    c.execute("SELECT * FROM courses WHERE id = ?", (course_id,))
    course = c.fetchone()

    c.execute("SELECT * FROM sessions WHERE course_id = ?", (course_id,))
    sessions = c.fetchall()

    c.execute("""
        SELECT 
            COUNT(*), 
            COALESCE(SUM(duration), 0)
        FROM sessions
        WHERE course_id = ?
    """, (course_id,))
    session_count, total_minutes = c.fetchone()

    # Get all study types
    c.execute("SELECT name FROM study_types ORDER BY name")
    study_types = [row[0] for row in c.fetchall()]

    conn.close()

    return render_template(
        'course.html',
        course=course,
        sessions=sessions,
        session_count=session_count,
        total_minutes=total_minutes,
        study_types=study_types
    )

#add session
@app.route('/add_session/<int:course_id>', methods=['POST'])
def add_session_for_course(course_id):
    study_type = request.form['type']
    duration = int(request.form['duration'])

    conn = sqlite3.connect('study.db')
    c = conn.cursor()
    
    # Add study type if it doesn't exist
    c.execute("INSERT OR IGNORE INTO study_types (name) VALUES (?)", (study_type,))
    
    c.execute("INSERT INTO sessions (course_id, type, duration) VALUES (?, ?, ?)",
              (course_id, study_type, duration))
    conn.commit()
    
    session_id = c.lastrowid
    conn.close()

    return jsonify({
        "id": session_id,
        "type": study_type,
        "duration": duration
    })

#edit course
@app.route('/edit_course/<int:course_id>', methods=['POST'])
def edit_course(course_id):
    new_name = request.form['name']

    conn = sqlite3.connect('study.db')
    c = conn.cursor()
    c.execute("UPDATE courses SET name = ? WHERE id = ?", (new_name, course_id))
    conn.commit()
    conn.close()

    return {"success": True}

#delete course
@app.route('/delete_course/<int:course_id>', methods=['POST'])
def delete_course(course_id):
    conn = sqlite3.connect('study.db')
    c = conn.cursor()

    c.execute("DELETE FROM sessions WHERE course_id = ?", (course_id,))
    c.execute("DELETE FROM courses WHERE id = ?", (course_id,))

    conn.commit()
    conn.close()

    return {"success": True}

# Edit session
@app.route('/edit_session/<int:session_id>', methods=['POST'])
def edit_session(session_id):
    new_type = request.form['type']
    new_duration = int(request.form['duration'])

    conn = sqlite3.connect('study.db')
    c = conn.cursor()
    
    # Add study type if it doesn't exist
    c.execute("INSERT OR IGNORE INTO study_types (name) VALUES (?)", (new_type,))
    
    c.execute("UPDATE sessions SET type = ?, duration = ? WHERE id = ?", 
              (new_type, new_duration, session_id))
    conn.commit()
    conn.close()

    return jsonify({"success": True})

# Delete session
@app.route('/delete_session/<int:session_id>', methods=['POST'])
def delete_session(session_id):
    conn = sqlite3.connect('study.db')
    c = conn.cursor()
    c.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
    conn.commit()
    conn.close()

    return jsonify({"success": True})

# Upload image for course
@app.route('/upload_image/<int:course_id>', methods=['POST'])
def upload_image(course_id):
    if 'image' not in request.files:
        return {"error": "No image file"}, 400
    
    file = request.files['image']
    
    if file.filename == '':
        return {"error": "No selected file"}, 400
    
    if file:
        # Generate unique filename
        filename = f"course-{course_id}-{int(time.time())}.jpg"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        
        file.save(filepath)
        
        # Update database
        conn = sqlite3.connect('study.db')
        c = conn.cursor()
        c.execute("UPDATE courses SET icon = ? WHERE id = ?", (filename, course_id))
        conn.commit()
        conn.close()
        
        return {"success": True, "icon": filename}

# Get all study types
@app.route('/get_study_types', methods=['GET'])
def get_study_types():
    conn = sqlite3.connect('study.db')
    c = conn.cursor()
    c.execute("SELECT name FROM study_types ORDER BY name")
    study_types = [row[0] for row in c.fetchall()]
    conn.close()
    
    return jsonify({"study_types": study_types})

if __name__ == "__main__":
    app.run(debug=True)