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
