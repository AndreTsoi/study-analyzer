from flask import Flask, render_template, request, redirect, jsonify
import sqlite3
import time
import os
import sys
import statistics
from datetime import datetime
from collections import defaultdict
from werkzeug.utils import secure_filename

app = Flask(__name__)

UPLOAD_FOLDER = 'static'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


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
                  duration INTEGER,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  rating INTEGER,
                  timezone_offset TEXT DEFAULT '+0:00')''')

    c.execute('''CREATE TABLE IF NOT EXISTS study_types
                 (id INTEGER PRIMARY KEY,
                  name TEXT UNIQUE)''')

    c.execute('''CREATE TABLE IF NOT EXISTS exams
                 (id INTEGER PRIMARY KEY,
                  course_id INTEGER,
                  exam_type TEXT,
                  exam_name TEXT,
                  grade REAL,
                  max_grade REAL,
                  exam_date DATE,
                  weight REAL DEFAULT 0,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  timezone_offset TEXT DEFAULT '+0:00',
                  FOREIGN KEY (course_id) REFERENCES courses (id))''')

    try:
        c.execute("ALTER TABLE sessions ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
        conn.commit()
    except:
        pass

    try:
        c.execute("ALTER TABLE sessions ADD COLUMN rating INTEGER")
        conn.commit()
    except:
        pass

    try:
        c.execute("ALTER TABLE sessions ADD COLUMN timezone_offset TEXT DEFAULT '+0:00'")
        conn.commit()
    except:
        pass

    try:
        c.execute("ALTER TABLE exams ADD COLUMN weight REAL DEFAULT 0")
        conn.commit()
    except:
        pass

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

    c.execute("SELECT * FROM sessions WHERE course_id = ? ORDER BY created_at DESC", (course_id,))
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

    # Get exams for this course
    c.execute("SELECT * FROM exams WHERE course_id = ? ORDER BY exam_date DESC", (course_id,))
    exams = c.fetchall()

    conn.close()

    return render_template(
        'course.html',
        course=course,
        sessions=sessions,
        session_count=session_count,
        total_minutes=total_minutes,
        study_types=study_types,
        exams=exams
    )

#add session
@app.route('/add_session/<int:course_id>', methods=['POST'])
def add_session_for_course(course_id):
    study_type = request.form['type']
    duration = int(request.form['duration'])
    rating = int(request.form.get('rating', 0))
    timezone_offset = request.form.get('timezone_offset', '+0:00')  # Format: "+8:00" or "-5:00"

    if duration < 0:
        return jsonify({"error": "Duration cannot be negative"}), 400

    conn = sqlite3.connect('study.db')
    c = conn.cursor()
    
    c.execute("INSERT OR IGNORE INTO study_types (name) VALUES (?)", (study_type,))
    
    c.execute("INSERT INTO sessions (course_id, type, duration, created_at, rating, timezone_offset) VALUES (?, ?, ?, CURRENT_TIMESTAMP, ?, ?)",
              (course_id, study_type, duration, rating, timezone_offset))
    conn.commit()
    
    session_id = c.lastrowid
    
    #get the created_at timestamp and timezone_offset
    c.execute("SELECT created_at, timezone_offset FROM sessions WHERE id = ?", (session_id,))
    result = c.fetchone()
    created_at = result[0]
    stored_offset = result[1]
    
    conn.close()

    return jsonify({
        "id": session_id,
        "type": study_type,
        "duration": duration,
        "created_at": created_at,
        "rating": rating,
        "timezone_offset": stored_offset
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

#edit session
@app.route('/edit_session/<int:session_id>', methods=['POST'])
def edit_session(session_id):
    new_type = request.form['type']
    new_duration = int(request.form['duration'])
    new_rating = int(request.form.get('rating', 0))

    conn = sqlite3.connect('study.db')
    c = conn.cursor()
    
    # Add study type if it doesn't exist
    c.execute("INSERT OR IGNORE INTO study_types (name) VALUES (?)", (new_type,))
    
    c.execute("UPDATE sessions SET type = ?, duration = ?, rating = ? WHERE id = ?", 
              (new_type, new_duration, new_rating, session_id))
    conn.commit()
    conn.close()

    return jsonify({"success": True})

#delete session
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
        
        #update database
        conn = sqlite3.connect('study.db')
        c = conn.cursor()
        c.execute("UPDATE courses SET icon = ? WHERE id = ?", (filename, course_id))
        conn.commit()
        conn.close()
        
        return {"success": True, "icon": filename}

#get all study types
@app.route('/get_study_types', methods=['GET'])
def get_study_types():
    conn = sqlite3.connect('study.db')
    c = conn.cursor()
    c.execute("SELECT name FROM study_types ORDER BY name")
    study_types = [row[0] for row in c.fetchall()]
    conn.close()
    
    return jsonify({"study_types": study_types})

#add exam
@app.route('/add_exam/<int:course_id>', methods=['POST'])
def add_exam(course_id):
    exam_type = request.form['exam_type']  # 'Midterm', 'Final', 'Quiz', 'Test'
    exam_name = request.form['exam_name']
    grade = float(request.form['grade'])
    max_grade = float(request.form['max_grade'])
    exam_date = request.form['exam_date']
    weight = float(request.form.get('weight', 0))
    timezone_offset = request.form.get('timezone_offset', '+0:00')

    conn = sqlite3.connect('study.db')
    c = conn.cursor()
    
    c.execute("""INSERT INTO exams (course_id, exam_type, exam_name, grade, max_grade, exam_date, weight, timezone_offset) 
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
              (course_id, exam_type, exam_name, grade, max_grade, exam_date, weight, timezone_offset))
    conn.commit()
    
    exam_id = c.lastrowid
    conn.close()

    return jsonify({
        "id": exam_id,
        "exam_type": exam_type,
        "exam_name": exam_name,
        "grade": grade,
        "max_grade": max_grade,
        "percentage": round((grade / max_grade) * 100, 1) if max_grade > 0 else 0,
        "exam_date": exam_date,
        "weight": weight
    })

#edit exam
@app.route('/edit_exam/<int:exam_id>', methods=['POST'])
def edit_exam(exam_id):
    exam_type = request.form['exam_type']
    exam_name = request.form['exam_name']
    grade = float(request.form['grade'])
    max_grade = float(request.form['max_grade'])
    exam_date = request.form['exam_date']
    weight = float(request.form.get('weight', 0))

    conn = sqlite3.connect('study.db')
    c = conn.cursor()
    c.execute("""UPDATE exams SET exam_type = ?, exam_name = ?, grade = ?, max_grade = ?, exam_date = ?, weight = ? 
                 WHERE id = ?""", 
              (exam_type, exam_name, grade, max_grade, exam_date, weight, exam_id))
    conn.commit()
    conn.close()

    return jsonify({"success": True})

#delete exam
@app.route('/delete_exam/<int:exam_id>', methods=['POST'])
def delete_exam(exam_id):
    conn = sqlite3.connect('study.db')
    c = conn.cursor()
    c.execute("DELETE FROM exams WHERE id = ?", (exam_id,))
    conn.commit()
    conn.close()

    return jsonify({"success": True})

#get course insights
@app.route('/get_insights/<int:course_id>', methods=['GET'])
def get_insights(course_id):
    from datetime import datetime, timedelta
    import json
    
    try:
        conn = sqlite3.connect('study.db')
        c = conn.cursor()
        
        #get all sessions for this course
        c.execute("""
            SELECT * FROM sessions 
            WHERE course_id = ? 
            ORDER BY created_at ASC
        """, (course_id,))
        sessions = c.fetchall()
        
        print(f"Found {len(sessions)} sessions for course {course_id}")
        
        #get all exams for this course
        c.execute("""
            SELECT * FROM exams 
            WHERE course_id = ? 
            ORDER BY exam_date ASC
        """, (course_id,))
        exams = c.fetchall()
        
        print(f"Found {len(exams)} exams for course {course_id}")
        
        conn.close()
        
        #calculate insights
        insights = calculate_insights(sessions, exams)
        
        print("Insights calculated successfully")
        
        return jsonify(insights)
    
    except Exception as e:
        print(f"ERROR in get_insights: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

def analyze_session_spacing(sessions, exams):
    """Analyze if spacing between sessions affects performance"""
    from datetime import datetime, timedelta
    
    if len(sessions) < 5 or len(exams) < 2:
        return None
    
    # Group sessions by gaps between them
    sorted_sessions = sorted([s for s in sessions if s[4]], key=lambda x: x[4])
    
    gaps = []
    for i in range(1, len(sorted_sessions)):
        prev_date = datetime.fromisoformat(sorted_sessions[i-1][4].replace('Z', '+00:00'))
        curr_date = datetime.fromisoformat(sorted_sessions[i][4].replace('Z', '+00:00'))
        gap_days = (curr_date - prev_date).days
        
        if gap_days <= 7:  #only count gaps up to 1 week
            gaps.append(gap_days)
    
    if not gaps:
        return None
    
    avg_gap = statistics.mean(gaps)
    
    #analyze exam performance by session spacing
    exam_spacing_scores = []
    for exam in exams:
        exam_date = datetime.strptime(exam[6], '%Y-%m-%d')
        
        #get sessions in 14 days before exam
        exam_sessions = []
        for s in sessions:
            if s[4]:
                session_date = datetime.fromisoformat(s[4].replace('Z', '+00:00'))
                days_before = (exam_date - session_date.replace(tzinfo=None)).days
                if 0 <= days_before <= 14:
                    exam_sessions.append(s)
        
        if len(exam_sessions) >= 2:
            # Calculate spacing for this exam's prep
            exam_sessions_sorted = sorted(exam_sessions, key=lambda x: x[4])
            exam_gaps = []
            for i in range(1, len(exam_sessions_sorted)):
                prev = datetime.fromisoformat(exam_sessions_sorted[i-1][4].replace('Z', '+00:00'))
                curr = datetime.fromisoformat(exam_sessions_sorted[i][4].replace('Z', '+00:00'))
                exam_gaps.append((curr - prev).days)
            
            if exam_gaps:
                avg_exam_gap = statistics.mean(exam_gaps)
                exam_score = (exam[4] / exam[5] * 100) if exam[5] > 0 else 0
                exam_spacing_scores.append({
                    'avg_gap': avg_exam_gap,
                    'score': exam_score,
                    'sessions': len(exam_sessions)
                })
    
    if len(exam_spacing_scores) < 2:
        return {
            'avg_gap': round(avg_gap, 1),
            'total_sessions': len(sessions),
            'confidence': 'low',
            'recommendation': None
        }
    
    #find correlation between spacing and scores
    well_spaced = [e for e in exam_spacing_scores if e['avg_gap'] >= 2]
    cramped = [e for e in exam_spacing_scores if e['avg_gap'] < 2]
    
    if well_spaced and cramped:
        well_spaced_avg = statistics.mean([e['score'] for e in well_spaced])
        cramped_avg = statistics.mean([e['score'] for e in cramped])
        difference = well_spaced_avg - cramped_avg
        
        if abs(difference) >= 5:  #at least 5% difference
            recommendation = None
            if difference > 0:
                recommendation = {
                    'type': 'info',
                    'icon': '📊',
                    'text': f"Spacing sessions 2-3 days apart correlates with {abs(difference):.0f}% higher exam scores",
                    'evidence': f"Well-spaced prep: {well_spaced_avg:.0f}% avg ({len(well_spaced)} exams) vs Daily cramming: {cramped_avg:.0f}% avg ({len(cramped)} exams)",
                    'confidence': 'medium' if len(exam_spacing_scores) >= 3 else 'low'
                }
            
            return {
                'avg_gap': round(avg_gap, 1),
                'well_spaced_avg': round(well_spaced_avg, 1),
                'cramped_avg': round(cramped_avg, 1),
                'difference': round(difference, 1),
                'confidence': 'medium' if len(exam_spacing_scores) >= 3 else 'low',
                'sample_size': len(exam_spacing_scores),
                'recommendation': recommendation
            }
    
    return None

def analyze_diminishing_returns(sessions):
    """Detect if longer sessions have diminishing effectiveness"""
    if len(sessions) < 10:
        return None
    
    rated_sessions = [s for s in sessions if s[5] and s[5] > 0]
    if len(rated_sessions) < 10:
        return None
    
    #group by duration buckets
    short = [s for s in rated_sessions if s[3] < 60]  # <60 min
    medium = [s for s in rated_sessions if 60 <= s[3] < 120]  # 60-120 min
    long = [s for s in rated_sessions if s[3] >= 120]  # 120+ min
    
    if not (short and medium) and not (medium and long):
        return None
    
    results = {}
    
    if short:
        results['short'] = {
            'avg_rating': round(statistics.mean([s[5] for s in short]), 1),
            'count': len(short),
            'duration': '<60 min'
        }
    
    if medium:
        results['medium'] = {
            'avg_rating': round(statistics.mean([s[5] for s in medium]), 1),
            'count': len(medium),
            'duration': '60-120 min'
        }
    
    if long:
        results['long'] = {
            'avg_rating': round(statistics.mean([s[5] for s in long]), 1),
            'count': len(long),
            'duration': '120+ min'
        }
    
    # Detect diminishing returns
    recommendation = None
    if medium and long and len(long) >= 3:
        if results['medium']['avg_rating'] > results['long']['avg_rating'] + 0.3:
            drop = results['medium']['avg_rating'] - results['long']['avg_rating']
            recommendation = {
                'type': 'warning',
                'icon': '⚠️',
                'text': f"Sessions over 120min show diminishing returns (avg {results['long']['avg_rating']}★ vs {results['medium']['avg_rating']}★ for 60-120min)",
                'evidence': f"Based on {results['long']['count']} long sessions vs {results['medium']['count']} medium sessions",
                'confidence': 'medium' if len(long) >= 5 else 'low'
            }
    
    results['recommendation'] = recommendation
    return results

def analyze_cramming_effect(sessions, exams):
    """Analyze if cramming (last-minute studying) affects exam scores"""
    if len(exams) < 3:
        return None
    
    cramming_data = []
    
    for exam in exams:
        exam_date = datetime.strptime(exam[6], '%Y-%m-%d')
        
        #sessions in last 3 days before exam
        last_minute = []
        #sessions 4-14 days before exam
        distributed = []
        
        total_hours = 0
        
        for s in sessions:
            if s[4]:
                session_date = datetime.fromisoformat(s[4].replace('Z', '+00:00'))
                days_before = (exam_date - session_date.replace(tzinfo=None)).days
                
                if 0 <= days_before <= 14:
                    total_hours += s[3] / 60
                    
                    if days_before <= 3:
                        last_minute.append(s)
                    elif days_before <= 14:
                        distributed.append(s)
        
        if total_hours > 0:
            last_minute_pct = (sum(s[3] for s in last_minute) / 60) / total_hours * 100 if total_hours > 0 else 0
            exam_score = (exam[4] / exam[5] * 100) if exam[5] > 0 else 0
            
            cramming_data.append({
                'last_minute_pct': last_minute_pct,
                'score': exam_score,
                'total_hours': total_hours,
                'exam_name': exam[3]
            })
    
    if len(cramming_data) < 3:
        return None
    
    #classify as cramming vs distributed
    crammed_exams = [e for e in cramming_data if e['last_minute_pct'] > 50]
    distributed_exams = [e for e in cramming_data if e['last_minute_pct'] <= 50]
    
    if crammed_exams and distributed_exams and len(crammed_exams) >= 2 and len(distributed_exams) >= 2:
        crammed_avg = statistics.mean([e['score'] for e in crammed_exams])
        distributed_avg = statistics.mean([e['score'] for e in distributed_exams])
        difference = distributed_avg - crammed_avg
        
        recommendation = None
        if difference >= 5:
            recommendation = {
                'type': 'warning',
                'icon': '🚨',
                'text': f"Cramming penalty detected: Distributed study over 2 weeks = {difference:.0f}% higher scores vs last-minute cramming",
                'evidence': f"Distributed prep: {distributed_avg:.0f}% avg ({len(distributed_exams)} exams) vs Crammed prep: {crammed_avg:.0f}% avg ({len(crammed_exams)} exams)",
                'confidence': 'high' if len(cramming_data) >= 5 else 'medium'
            }
        
        return {
            'crammed_avg': round(crammed_avg, 1),
            'distributed_avg': round(distributed_avg, 1),
            'difference': round(difference, 1),
            'sample_size': len(cramming_data),
            'recommendation': recommendation
        }
    
    return None

def analyze_multi_factor_optimization(sessions):
    """Find the optimal combination of factors"""
    if len(sessions) < 15:
        return None
    
    rated_sessions = [s for s in sessions if s[5] and s[5] > 0 and s[4]]
    if len(rated_sessions) < 15:
        return None
    
    #find sessions rated 5 stars
    perfect_sessions = [s for s in rated_sessions if s[5] == 5]
    
    if len(perfect_sessions) < 3:
        return None
    
    #analyze common factors in perfect sessions
    factors = {
        'times_of_day': defaultdict(int),
        'durations': [],
        'types': defaultdict(int)
    }
    
    for s in perfect_sessions:
        #time of day
        date = datetime.fromisoformat(s[4].replace('Z', '+00:00'))
        hour = date.hour
        if 6 <= hour < 12:
            factors['times_of_day']['Morning'] += 1
        elif 12 <= hour < 17:
            factors['times_of_day']['Afternoon'] += 1
        elif 17 <= hour < 21:
            factors['times_of_day']['Evening'] += 1
        else:
            factors['times_of_day']['Night'] += 1
        
        #duration
        factors['durations'].append(s[3])
        
        #type
        factors['types'][s[2]] += 1
    
    # Find most common factors
    best_time = max(factors['times_of_day'].items(), key=lambda x: x[1])[0] if factors['times_of_day'] else None
    avg_duration = round(statistics.mean(factors['durations']))
    best_type = max(factors['types'].items(), key=lambda x: x[1])[0] if factors['types'] else None
    
    recommendation = {
        'type': 'success',
        'icon': '🎯',
        'text': f"Your perfect study combo: {best_time} sessions, ~{avg_duration}min duration, {best_type}",
        'evidence': f"Based on {len(perfect_sessions)} of your 5-star sessions",
        'confidence': 'high' if len(perfect_sessions) >= 5 else 'medium'
    }
    
    return {
        'best_time': best_time,
        'avg_duration': avg_duration,
        'best_type': best_type,
        'sample_size': len(perfect_sessions),
        'recommendation': recommendation
    }

def analyze_study_type_mix(sessions, exams):
    """Analyze if mixing different study types improves performance"""
    if not exams:
        return None
    
    exam_mix_data = []
    
    for exam in exams:
        exam_date = datetime.strptime(exam[6], '%Y-%m-%d')
        
        # Get sessions in 14 days before exam
        exam_sessions = []
        for s in sessions:
            if s[4]:
                session_date = datetime.fromisoformat(s[4].replace('Z', '+00:00'))
                days_before = (exam_date - session_date.replace(tzinfo=None)).days
                if 0 <= days_before <= 14:
                    exam_sessions.append(s)
        
        if len(exam_sessions) >= 2:
            # Count unique study types
            unique_types = len(set(s[2] for s in exam_sessions))
            total_sessions = len(exam_sessions)
            variety_score = unique_types / total_sessions  # 0 to 1
            
            # Calculate type distribution
            type_counts = defaultdict(int)
            for s in exam_sessions:
                type_counts[s[2]] += 1
            
            exam_score = (exam[4] / exam[5] * 100) if exam[5] > 0 else 0
            
            exam_mix_data.append({
                'unique_types': unique_types,
                'total_sessions': total_sessions,
                'variety_score': variety_score,
                'score': exam_score,
                'exam_name': exam[3],
                'type_distribution': dict(type_counts)
            })
    
    if not exam_mix_data:
        return None
    
    # Analyze correlation between variety and performance
    avg_variety = statistics.mean([e['variety_score'] for e in exam_mix_data])
    
    # Find best performing exams
    if len(exam_mix_data) >= 2:
        sorted_by_score = sorted(exam_mix_data, key=lambda x: x['score'], reverse=True)
        top_half = sorted_by_score[:len(sorted_by_score)//2] if len(sorted_by_score) >= 4 else sorted_by_score[:1]
        bottom_half = sorted_by_score[len(sorted_by_score)//2:] if len(sorted_by_score) >= 4 else sorted_by_score[1:]
        
        if top_half and bottom_half:
            top_variety = statistics.mean([e['variety_score'] for e in top_half])
            bottom_variety = statistics.mean([e['variety_score'] for e in bottom_half])
            
            # Find most common mix in top performers
            top_types = defaultdict(int)
            for exam in top_half:
                for study_type in exam['type_distribution'].keys():
                    top_types[study_type] += 1
            
            common_types = [t for t, count in sorted(top_types.items(), key=lambda x: x[1], reverse=True)[:3]]
            
            recommendation = None
            if top_variety > bottom_variety + 0.1:
                recommendation = {
                    'type': 'info',
                    'icon': '🔄',
                    'text': f"Mixing study types improves performance. Your best exams used {len(common_types)} types: {', '.join(common_types)}",
                    'evidence': f"Top {len(top_half)} exams averaged {len(set().union(*[set(e['type_distribution'].keys()) for e in top_half]))} different study types",
                    'confidence': 'medium' if len(exam_mix_data) >= 3 else 'low'
                }
            elif bottom_variety > top_variety + 0.1:
                # Find dominant type in top performers
                dominant_type = max(
                    [(t, sum(e['type_distribution'].get(t, 0) for e in top_half)) for t in top_types.keys()],
                    key=lambda x: x[1]
                )[0] if top_types else None
                
                if dominant_type:
                    recommendation = {
                        'type': 'info',
                        'icon': '🎯',
                        'text': f"Focusing on {dominant_type} works better than mixing types for this course",
                        'evidence': f"Your best exams had {dominant_type} as the primary study type",
                        'confidence': 'medium' if len(exam_mix_data) >= 3 else 'low'
                    }
            
            return {
                'avg_variety': round(avg_variety, 2),
                'sample_size': len(exam_mix_data),
                'top_types': common_types,
                'recommendation': recommendation
            }
    
    return {
        'avg_variety': round(avg_variety, 2),
        'sample_size': len(exam_mix_data),
        'recommendation': None
    }

def analyze_time_decay(sessions, exams):
    """Analyze how study recency affects exam performance"""
    if not exams:
        return None
    
    decay_data = []
    
    for exam in exams:
        exam_date = datetime.strptime(exam[6], '%Y-%m-%d')
        
        # Categorize sessions by recency
        very_recent = 0  # 0-3 days before
        recent = 0       # 4-7 days before
        older = 0        # 8-14 days before
        
        for s in sessions:
            if s[4]:
                session_date = datetime.fromisoformat(s[4].replace('Z', '+00:00'))
                days_before = (exam_date - session_date.replace(tzinfo=None)).days
                
                session_hours = s[3] / 60
                
                if 0 <= days_before <= 3:
                    very_recent += session_hours
                elif 4 <= days_before <= 7:
                    recent += session_hours
                elif 8 <= days_before <= 14:
                    older += session_hours
        
        total_hours = very_recent + recent + older
        
        if total_hours > 0:
            exam_score = (exam[4] / exam[5] * 100) if exam[5] > 0 else 0
            
            decay_data.append({
                'very_recent_pct': (very_recent / total_hours * 100),
                'recent_pct': (recent / total_hours * 100),
                'older_pct': (older / total_hours * 100),
                'score': exam_score,
                'total_hours': total_hours,
                'exam_name': exam[3]
            })
    
    if not decay_data:
        return None
    
    # Find optimal recency distribution
    if len(decay_data) >= 2:
        sorted_by_score = sorted(decay_data, key=lambda x: x['score'], reverse=True)
        top_half = sorted_by_score[:max(1, len(sorted_by_score)//2)]
        
        avg_very_recent = statistics.mean([e['very_recent_pct'] for e in top_half])
        avg_recent = statistics.mean([e['recent_pct'] for e in top_half])
        avg_older = statistics.mean([e['older_pct'] for e in top_half])
        
        # Determine recommendation based on distribution
        recommendation = None
        
        if avg_very_recent > 60:
            recommendation = {
                'type': 'warning',
                'icon': '⏰',
                'text': f"Your best exams had {avg_very_recent:.0f}% of study in the last 3 days - but consider starting earlier",
                'evidence': f"Analysis of your top {len(top_half)} exam{'s' if len(top_half) > 1 else ''}",
                'confidence': 'medium' if len(decay_data) >= 3 else 'low'
            }
        elif avg_recent > avg_very_recent and avg_recent > avg_older:
            recommendation = {
                'type': 'success',
                'icon': '📅',
                'text': f"Sweet spot: {avg_recent:.0f}% of study 4-7 days before exams works best for you",
                'evidence': f"Based on your top {len(top_half)} exam{'s' if len(top_half) > 1 else ''}",
                'confidence': 'medium' if len(decay_data) >= 3 else 'low'
            }
        elif avg_older > 40:
            recommendation = {
                'type': 'info',
                'icon': '🔄',
                'text': f"Early preparation helps: {avg_older:.0f}% of your best exam prep started 8+ days early",
                'evidence': f"Pattern from your top {len(top_half)} exam{'s' if len(top_half) > 1 else ''}",
                'confidence': 'medium' if len(decay_data) >= 3 else 'low'
            }
        
        return {
            'optimal_very_recent': round(avg_very_recent, 1),
            'optimal_recent': round(avg_recent, 1),
            'optimal_older': round(avg_older, 1),
            'sample_size': len(decay_data),
            'recommendation': recommendation
        }
    
    return {
        'sample_size': len(decay_data),
        'recommendation': None
    }

def analyze_optimal_session_length(sessions):
    """Find the optimal session length based on ratings"""
    rated_sessions = [s for s in sessions if s[5] and s[5] > 0]
    
    if not rated_sessions:
        return None
    
    # Group by 15-minute increments
    length_ratings = defaultdict(list)
    
    for s in rated_sessions:
        duration = s[3]
        # Round to nearest 15 min bucket
        bucket = (duration // 15) * 15
        length_ratings[bucket].append(s[5])
    
    # Find sweet spot
    avg_by_length = {
        length: statistics.mean(ratings) 
        for length, ratings in length_ratings.items() 
        if len(ratings) >= 2  # At least 2 sessions
    }
    
    if not avg_by_length:
        return None
    
    optimal_length = max(avg_by_length.items(), key=lambda x: x[1])
    
    recommendation = {
        'type': 'success',
        'icon': '⏱️',
        'text': f"Your optimal session length: {optimal_length[0]}-{optimal_length[0]+15} minutes (avg {optimal_length[1]:.1f}★)",
        'evidence': f"Based on {len(length_ratings[optimal_length[0]])} sessions at this duration",
        'confidence': 'medium' if len(length_ratings[optimal_length[0]]) >= 5 else 'low'
    }
    
    return {
        'optimal_length': optimal_length[0],
        'optimal_rating': round(optimal_length[1], 1),
        'sample_size': len(length_ratings[optimal_length[0]]),
        'recommendation': recommendation
    }

def calculate_insights(sessions, exams):
    """Calculate all insights for a course"""
    from datetime import datetime, timedelta
    from collections import defaultdict
    
    insights = {
        'performance': {},
        'study_patterns': {},
        'effectiveness': {},
        'recommendations': [],
        'predictions': {}
    }
    
    if not sessions:
        insights['recommendations'].append({
            'type': 'warning',
            'text': 'No study sessions recorded yet. Start logging your study time!'
        })
        return insights
    
    # === PERFORMANCE ANALYSIS ===
    if exams:
        exam_scores = [(e[4]/e[5]*100 if e[5] > 0 else 0) for e in exams]
        
        # Get weights and convert to float, handling None and empty strings
        exam_weights = []
        for e in exams:
            if len(e) > 7 and e[7]:
                try:
                    exam_weights.append(float(e[7]))
                except (ValueError, TypeError):
                    exam_weights.append(0)
            else:
                exam_weights.append(0)
        
        # Calculate weighted average
        total_weight = sum(exam_weights)
        if total_weight > 0:
            weighted_avg = sum(score * weight for score, weight in zip(exam_scores, exam_weights)) / total_weight
            insights['performance']['avg_score'] = round(weighted_avg, 1)
            insights['performance']['is_weighted'] = True
            insights['performance']['total_weight'] = total_weight
        else:
            # Fallback to simple average if no weights
            insights['performance']['avg_score'] = round(statistics.mean(exam_scores), 1)
            insights['performance']['is_weighted'] = False
        
        insights['performance']['best_score'] = round(max(exam_scores), 1)
        insights['performance']['worst_score'] = round(min(exam_scores), 1)
        insights['performance']['total_exams'] = len(exams)
        
        # Trend calculation
        if len(exam_scores) >= 2:
            recent_avg = statistics.mean(exam_scores[-2:]) if len(exam_scores) >= 2 else exam_scores[-1]
            older_avg = statistics.mean(exam_scores[:-2]) if len(exam_scores) > 2 else exam_scores[0]
            
            if recent_avg > older_avg + 5:
                insights['performance']['trend'] = 'improving'
                insights['performance']['trend_text'] = '📈 Improving'
            elif recent_avg < older_avg - 5:
                insights['performance']['trend'] = 'declining'
                insights['performance']['trend_text'] = '📉 Declining'
            else:
                insights['performance']['trend'] = 'stable'
                insights['performance']['trend_text'] = '➡️ Stable'
        
        # Exam timeline data for chart
        insights['performance']['exam_timeline'] = [
            {
                'date': e[6],
                'score': round(e[4]/e[5]*100 if e[5] > 0 else 0, 1),
                'name': e[3]
            }
            for e in exams
        ]
    else:
        insights['performance']['no_exams'] = True
    
    # === STUDY PATTERNS ===
    
    # Best day of week
    day_stats = defaultdict(lambda: {'count': 0, 'total_rating': 0, 'total_minutes': 0})
    for s in sessions:
        if s[4]:  # has created_at
            date = datetime.fromisoformat(s[4].replace('Z', '+00:00'))
            day_name = date.strftime('%A')
            day_stats[day_name]['count'] += 1
            day_stats[day_name]['total_minutes'] += s[3]
            if s[5]:  # has rating
                day_stats[day_name]['total_rating'] += s[5]
    
    if day_stats:
        best_day = max(day_stats.items(), 
                      key=lambda x: (x[1]['total_rating'] / x[1]['count'] if x[1]['count'] > 0 else 0))
        insights['study_patterns']['best_day'] = best_day[0]
        insights['study_patterns']['best_day_avg_rating'] = round(
            best_day[1]['total_rating'] / best_day[1]['count'], 1
        ) if best_day[1]['count'] > 0 else 0
        
        # Day breakdown for heatmap
        insights['study_patterns']['day_breakdown'] = {
            day: {
                'sessions': stats['count'],
                'minutes': stats['total_minutes'],
                'avg_rating': round(stats['total_rating'] / stats['count'], 1) if stats['count'] > 0 else 0
            }
            for day, stats in day_stats.items()
        }
    
    # Best time of day
    time_stats = defaultdict(lambda: {'count': 0, 'total_rating': 0})
    for s in sessions:
        if s[4] and s[5]:
            date = datetime.fromisoformat(s[4].replace('Z', '+00:00'))
            hour = date.hour
            if 6 <= hour < 12:
                period = 'Morning'
            elif 12 <= hour < 17:
                period = 'Afternoon'
            elif 17 <= hour < 21:
                period = 'Evening'
            else:
                period = 'Night'
            
            time_stats[period]['count'] += 1
            time_stats[period]['total_rating'] += s[5]
    
    if time_stats:
        best_time = max(time_stats.items(), 
                       key=lambda x: (x[1]['total_rating'] / x[1]['count'] if x[1]['count'] > 0 else 0))
        insights['study_patterns']['best_time'] = best_time[0]
        insights['study_patterns']['best_time_avg_rating'] = round(
            best_time[1]['total_rating'] / best_time[1]['count'], 1
        ) if best_time[1]['count'] > 0 else 0
    
    # Current streak
    sorted_sessions = sorted(sessions, key=lambda x: x[4] if x[4] else '', reverse=True)
    streak = 0
    last_date = None
    
    for s in sorted_sessions:
        if s[4]:
            session_date = datetime.fromisoformat(s[4].replace('Z', '+00:00')).date()
            if last_date is None:
                streak = 1
                last_date = session_date
            elif (last_date - session_date).days == 1:
                streak += 1
                last_date = session_date
            elif (last_date - session_date).days == 0:
                continue  # Same day
            else:
                break
    
    insights['study_patterns']['current_streak'] = streak
    
    # === EFFECTIVENESS ===
    
    # Best study type
    type_stats = defaultdict(lambda: {'count': 0, 'total_rating': 0, 'total_minutes': 0})
    for s in sessions:
        type_stats[s[2]]['count'] += 1
        type_stats[s[2]]['total_minutes'] += s[3]
        if s[5]:
            type_stats[s[2]]['total_rating'] += s[5]
    
    type_effectiveness = []
    for study_type, stats in type_stats.items():
        avg_rating = stats['total_rating'] / stats['count'] if stats['count'] > 0 else 0
        type_effectiveness.append({
            'type': study_type,
            'avg_rating': round(avg_rating, 1),
            'sessions': stats['count'],
            'total_minutes': stats['total_minutes']
        })
    
    type_effectiveness.sort(key=lambda x: x['avg_rating'], reverse=True)
    insights['effectiveness']['study_types'] = type_effectiveness
    
    if type_effectiveness:
        insights['effectiveness']['best_type'] = type_effectiveness[0]['type']
        insights['effectiveness']['best_type_rating'] = type_effectiveness[0]['avg_rating']
    
    # Optimal session length
    rated_sessions = [s for s in sessions if s[5]]
    if rated_sessions:
        duration_ratings = defaultdict(list)
        for s in rated_sessions:
            duration = s[3]
            if duration < 30:
                bucket = '<30 min'
            elif duration < 60:
                bucket = '30-60 min'
            elif duration < 90:
                bucket = '60-90 min'
            elif duration < 120:
                bucket = '90-120 min'
            else:
                bucket = '120+ min'
            
            duration_ratings[bucket].append(s[5])
        
        best_duration = max(duration_ratings.items(), 
                           key=lambda x: statistics.mean(x[1]))
        insights['effectiveness']['optimal_duration'] = best_duration[0]
        insights['effectiveness']['optimal_duration_rating'] = round(statistics.mean(best_duration[1]), 1)
    
    # === STUDY HOURS vs EXAM PERFORMANCE ===
    if exams:
        exam_correlations = []
        for exam in exams:
            exam_date = datetime.strptime(exam[6], '%Y-%m-%d').date()
            # Get sessions in the 14 days before exam
            study_hours = 0
            for s in sessions:
                if s[4]:
                    session_date = datetime.fromisoformat(s[4].replace('Z', '+00:00')).date()
                    days_before = (exam_date - session_date).days
                    if 0 <= days_before <= 14:
                        study_hours += s[3] / 60
            
            exam_score = (exam[4] / exam[5] * 100) if exam[5] > 0 else 0
            exam_correlations.append({
                'exam_name': exam[3],
                'study_hours': round(study_hours, 1),
                'score': round(exam_score, 1)
            })
        
        insights['effectiveness']['exam_correlations'] = exam_correlations
    
    # === RECOMMENDATIONS ===
    
    # Good habits
    if type_effectiveness and type_effectiveness[0]['avg_rating'] >= 4:
        insights['recommendations'].append({
            'type': 'success',
            'icon': '✅',
            'text': f"Keep doing {type_effectiveness[0]['type']} sessions - they work best! (avg {type_effectiveness[0]['avg_rating']}★)",
            'evidence': f"Based on {type_effectiveness[0]['sessions']} sessions"
        })
    
    # Streak
    if streak >= 3:
        insights['recommendations'].append({
            'type': 'success',
            'icon': '🔥',
            'text': f"{streak}-day streak! Keep it going!",
            'evidence': f"You've studied {streak} consecutive days"
        })
    
    # Days since last study
    if sessions:
        last_session = max(sessions, key=lambda x: x[4] if x[4] else '')
        if last_session[4]:
            last_date = datetime.fromisoformat(last_session[4].replace('Z', '+00:00'))
            days_since = (datetime.now() - last_date).days
            
            if days_since >= 7:
                insights['recommendations'].append({
                    'type': 'warning',
                    'icon': '⚠️',
                    'text': f"{days_since} days since last study session - time to review!",
                    'evidence': f"Last session: {last_date.strftime('%b %d')}"
                })
            elif days_since >= 3:
                insights['recommendations'].append({
                    'type': 'info',
                    'icon': '💡',
                    'text': f"{days_since} days since last session - consider a quick review",
                    'evidence': f"Last session: {last_date.strftime('%b %d')}"
                })
    
    # Study pattern recommendation
    if 'best_day' in insights['study_patterns'] and 'best_time' in insights['study_patterns']:
        insights['recommendations'].append({
            'type': 'info',
            'icon': '📅',
            'text': f"You study best on {insights['study_patterns']['best_day']} {insights['study_patterns']['best_time'].lower()}s",
            'evidence': f"{insights['study_patterns']['best_day_avg_rating']}★ avg on {insights['study_patterns']['best_day']}"
        })
    
    # === PHASE 2: ADVANCED ANALYSIS ===
    
    # Spacing Effect Analysis
    spacing_analysis = analyze_session_spacing(sessions, exams)
    if spacing_analysis:
        insights['advanced'] = insights.get('advanced', {})
        insights['advanced']['spacing'] = spacing_analysis
        
        if spacing_analysis['recommendation']:
            insights['recommendations'].append(spacing_analysis['recommendation'])
    
    # Diminishing Returns Detection
    diminishing_returns = analyze_diminishing_returns(sessions)
    if diminishing_returns:
        insights['advanced']['diminishing_returns'] = diminishing_returns
        
        if diminishing_returns['recommendation']:
            insights['recommendations'].append(diminishing_returns['recommendation'])
    
    # Cramming vs Distributed Study
    if exams:
        cramming_analysis = analyze_cramming_effect(sessions, exams)
        if cramming_analysis:
            insights['advanced']['cramming'] = cramming_analysis
            
            if cramming_analysis['recommendation']:
                insights['recommendations'].append(cramming_analysis['recommendation'])
    
    # Multi-factor Optimization
    multi_factor = analyze_multi_factor_optimization(sessions)
    if multi_factor:
        insights['advanced']['optimal_combo'] = multi_factor
        
        if multi_factor['recommendation']:
            insights['recommendations'].append(multi_factor['recommendation'])
    
    # Study Type Mix Analysis (#2)
    if exams:
        type_mix = analyze_study_type_mix(sessions, exams)
        if type_mix:
            insights['advanced'] = insights.get('advanced', {})
            insights['advanced']['type_mix'] = type_mix
            
            if type_mix['recommendation']:
                insights['recommendations'].append(type_mix['recommendation'])
    
    if exams:
        time_decay = analyze_time_decay(sessions, exams)
        if time_decay:
            insights['advanced'] = insights.get('advanced', {})
            insights['advanced']['time_decay'] = time_decay
            
            if time_decay['recommendation']:
                insights['recommendations'].append(time_decay['recommendation'])
    
    session_length = analyze_optimal_session_length(sessions)
    if session_length:
        insights['advanced'] = insights.get('advanced', {})
        insights['advanced']['session_length'] = session_length
        
        if session_length['recommendation']:
            insights['recommendations'].append(session_length['recommendation'])
    
    if exams and 'exam_correlations' in insights['effectiveness']:
        correlations = insights['effectiveness']['exam_correlations']
        if len(correlations) >= 2:
            # Find pattern
            high_scorers = [c for c in correlations if c['score'] >= 85]
            if high_scorers:
                avg_hours = statistics.mean([c['study_hours'] for c in high_scorers])
                insights['recommendations'].append({
                    'type': 'info',
                    'icon': '🎯',
                    'text': f"Your best exams (85%+) came after ~{round(avg_hours)} hours of study"
                })
    
    # === PREDICTIONS ===
    if exams and sessions:
        # Simple prediction based on recent study hours
        now = datetime.now()
        recent_hours = sum(s[3] for s in sessions 
                          if s[4] and (now - datetime.fromisoformat(s[4].replace('Z', '+00:00'))).days <= 14) / 60
        
        if 'exam_correlations' in insights['effectiveness'] and len(insights['effectiveness']['exam_correlations']) >= 2:
            # Simple linear relationship
            correlations = insights['effectiveness']['exam_correlations']
            avg_score = statistics.mean([c['score'] for c in correlations])
            avg_hours = statistics.mean([c['study_hours'] for c in correlations])
            
            if avg_hours > 0:
                score_per_hour = avg_score / avg_hours
                predicted_score = min(100, max(0, recent_hours * score_per_hour))
                
                insights['predictions']['next_exam_score'] = round(predicted_score, 1)
                insights['predictions']['based_on_hours'] = round(recent_hours, 1)
    
    return insights

# Analytics page
@app.route('/analytics')
def analytics():
    conn = sqlite3.connect('study.db')
    c = conn.cursor()
    
    # Get all sessions with course names
    c.execute("""
        SELECT s.*, c.name as course_name
        FROM sessions s
        JOIN courses c ON s.course_id = c.id
        ORDER BY s.created_at DESC
    """)
    sessions = c.fetchall()
    
    # Get total stats
    c.execute("SELECT COUNT(*), COALESCE(SUM(duration), 0) FROM sessions")
    total_sessions, total_minutes = c.fetchone()
    
    # Get average rating
    c.execute("SELECT AVG(rating) FROM sessions WHERE rating > 0")
    avg_rating = c.fetchone()[0] or 0
    
    conn.close()
    
    return render_template(
        'analytics.html',
        sessions=sessions,
        total_sessions=total_sessions,
        total_minutes=total_minutes,
        avg_rating=round(avg_rating, 1)
    )

# Generate report
@app.route('/generate_report', methods=['POST'])
def generate_report():
    import subprocess
    import os
    from datetime import datetime
    
    report_type = request.form.get('type', 'weekly')
    report_format = request.form.get('format', 'docx')  # 'docx' or 'pdf'
    
    # Get absolute paths
    current_dir = os.path.dirname(os.path.abspath(__file__))
    script_path = os.path.join(current_dir, 'generate_report.py')
    
    # Generate filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    extension = 'pdf' if report_format == 'pdf' else 'docx'
    filename = f"{report_type}_report_{timestamp}.{extension}"
    
    # Use absolute path for output
    static_dir = os.path.join(current_dir, 'static')
    if not os.path.exists(static_dir):
        os.makedirs(static_dir)
    
    output_path = os.path.join(static_dir, filename)
    
    try:
        # Run Python script to generate report with absolute paths
        result = subprocess.run(
            [sys.executable, script_path, report_type, output_path],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=current_dir  # Set working directory explicitly
        )
        
        print(f"Report generation stdout: {result.stdout}")
        print(f"Report generation stderr: {result.stderr}")
        print(f"Return code: {result.returncode}")
        
        if result.returncode == 0 and os.path.exists(output_path):
            # Return the file path for download
            return jsonify({
                "success": True,
                "filename": filename,
                "download_url": f"/static/{filename}"
            })
        else:
            error_msg = result.stderr or result.stdout or "Unknown error - check Flask console"
            print(f"ERROR: {error_msg}")
            return jsonify({
                "success": False,
                "error": error_msg
            }), 500
            
    except subprocess.TimeoutExpired:
        return jsonify({
            "success": False,
            "error": "Report generation timed out (took longer than 30 seconds)"
        }), 500
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": f"Server error: {str(e)}"
        }), 500

if __name__ == "__main__":
    app.run(debug=True)