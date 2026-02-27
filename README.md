# study-analyzer


# Study Tracker

A full-stack web application for tracking study sessions, managing exams, and analyzing study patterns with intelligent insights.

## Features

### Core Functionality
- Track study sessions with duration, type, and effectiveness ratings (1-5 stars)
- Manage courses with custom icons
- Log exams/quizzes with grades and weighted percentages
- Filter and sort sessions by date, type, rating, and duration
- Timezone-aware session tracking

### Analytics & Insights
- Interactive charts showing study patterns (Chart.js)
- 7 intelligent analysis algorithms:
  - Spacing effect detection (distributed vs cramming)
  - Diminishing returns analysis (optimal session length)
  - Cramming penalty calculation
  - Study type mix optimization
  - Time decay modeling (study recency effects)
  - Multi-factor optimization (best time/duration/type combos)
  - Optimal session length finder

### Reports
- Generate Word (.docx) or PDF reports
- Weekly, monthly, and yearly summaries
- Study time breakdown by course and type
- Automatic weighted grade calculations

### Intelligent Recommendations
- Evidence-based insights with confidence levels
- Sample size and statistical backing shown for each recommendation
- Personalized study strategies based on your patterns

## Tech Stack

**Backend:**
- Python 3.x
- Flask (web framework)
- SQLite (database)
- python-docx (Word document generation)
- ReportLab (PDF generation)

**Frontend:**
- HTML/CSS/JavaScript (vanilla)
- Chart.js 4.4.0 (data visualization)
- Responsive design

## Installation

1. Clone the repository
2. Install dependencies
3. Run the application
4. Open browser to `http://127.0.0.1:5000`

## Usage

### Adding a Course
1. Click "Add Course" on homepage
2. Enter course name
3. Optionally upload custom icon
4. Click "Add Course"

### Logging Study Sessions
1. Click on a course
2. Select study type (or add custom type)
3. Enter duration in minutes
4. Rate session effectiveness (1-5 stars)
5. Click "Add Session"

### Recording Exams
1. Navigate to course page
2. Scroll to "Exams & Grades" section
3. Select exam type (Quiz/Test/Midterm/Final/Project/Assignment)
4. Enter exam name, grade received, max grade, and weight percentage
5. Select exam date
6. Click "Add Exam"

### Viewing Insights
1. Click "View Insights" button on course page
2. See performance metrics, study patterns, and recommendations
3. Charts show exam timeline, day-of-week breakdown, study type effectiveness
4. Recommendations include evidence and confidence levels

### Generating Reports
1. Navigate to Analytics page (from homepage)
2. Choose report type (Weekly/Monthly/Yearly)
3. Choose format (Word or PDF)
4. Report downloads automatically

## Database Schema

**courses**
- id (PRIMARY KEY)
- name (TEXT)
- icon (TEXT, default: 'default-icon.jpg')

**sessions**
- id (PRIMARY KEY)
- course_id (FOREIGN KEY)
- type (TEXT)
- duration (INTEGER, minutes)
- created_at (TIMESTAMP)
- rating (INTEGER, 1-5)
- timezone_offset (TEXT)

**exams**
- id (PRIMARY KEY)
- course_id (FOREIGN KEY)
- exam_type (TEXT)
- exam_name (TEXT)
- grade (REAL)
- max_grade (REAL)
- exam_date (DATE)
- weight (REAL, percentage)
- created_at (TIMESTAMP)
- timezone_offset (TEXT)

**study_types**
- id (PRIMARY KEY)
- name (TEXT UNIQUE)

## Analysis Algorithms

### Spacing Effect Analysis
Detects if spacing sessions 2-3 days apart improves exam performance by comparing well-spaced vs daily cramming patterns.

### Diminishing Returns Detection
Identifies if longer sessions (120+ min) are less effective than medium-length sessions (60-120 min).

### Cramming Penalty
Analyzes if last-minute studying (last 3 days) hurts exam scores compared to distributed preparation.

### Study Type Mix Optimization
Determines if mixing different study types improves performance or if focusing on one type works better.

### Time Decay Modeling
Finds optimal timing for study sessions before exams (0-3 days, 4-7 days, 8-14 days windows).

### Multi-Factor Optimization
Identifies best combination of time of day, session duration, and study type based on 5-star sessions.

### Optimal Session Length
Finds your personal sweet spot for session duration by analyzing ratings across 15-minute buckets.

## Confidence Levels

All recommendations include confidence scoring:
- **High**: 5+ data points, strong pattern detected
- **Medium**: 3-4 data points, likely pattern
- **Low**: 2-3 data points, possible pattern but needs more data

## File Structure
