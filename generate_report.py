#!/usr/bin/env python3
import sys
import os
import sqlite3
from datetime import datetime, timedelta

try:
    from docx import Document
    from docx.shared import Inches, Pt, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx2pdf import convert
    HAS_DOCX = True
except ImportError as e:
    print(f"ERROR: python-docx not installed. Run: pip install python-docx --break-system-packages", file=sys.stderr)
    HAS_DOCX = False
    sys.exit(1)

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.enums import TA_CENTER
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False

def format_time(minutes):
    """Format minutes into readable time string"""
    if minutes < 60:
        return f"{minutes} min"
    hrs = minutes // 60
    mins = minutes % 60
    return f"{hrs} hr {mins} min" if mins > 0 else f"{hrs} hr"

def generate_pdf_report(report_type, output_path, sessions):
    """Generate PDF report using reportlab"""
    if not HAS_REPORTLAB:
        raise ImportError("reportlab not installed. Install with: pip install reportlab --break-system-packages")
    
    # Determine title
    if report_type == 'weekly':
        title = 'Weekly Study Report'
    elif report_type == 'monthly':
        title = 'Monthly Study Report'
    else:
        title = 'Yearly Study Report'
    
    # Calculate statistics
    total_sessions = len(sessions)
    total_minutes = sum(s[3] for s in sessions)
    rated_sessions = [s for s in sessions if s[5] and s[5] > 0]
    avg_rating = sum(s[5] for s in rated_sessions) / len(rated_sessions) if rated_sessions else 0
    
    # Group by course
    by_course = {}
    for s in sessions:
        course = s[7]
        if course not in by_course:
            by_course[course] = {'sessions': 0, 'minutes': 0}
        by_course[course]['sessions'] += 1
        by_course[course]['minutes'] += s[3]
    
    # Group by type
    by_type = {}
    for s in sessions:
        study_type = s[2]
        if study_type not in by_type:
            by_type[study_type] = {'sessions': 0, 'minutes': 0}
        by_type[study_type]['sessions'] += 1
        by_type[study_type]['minutes'] += s[3]
    
    # Create PDF
    doc = SimpleDocTemplate(output_path, pagesize=letter)
    story = []
    styles = getSampleStyleSheet()
    
    # Title style
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.black,
        alignment=TA_CENTER,
        spaceAfter=12
    )
    
    # Heading style
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.black,
        spaceAfter=12
    )
    
    # Add title
    story.append(Paragraph(title, title_style))
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%B %d, %Y')}", styles['Normal']))
    story.append(Spacer(1, 0.3*inch))
    
    # Summary section
    story.append(Paragraph("Summary", heading_style))
    story.append(Paragraph(f"Total Sessions: {total_sessions}", styles['Normal']))
    story.append(Paragraph(f"Total Study Time: {format_time(total_minutes)}", styles['Normal']))
    story.append(Paragraph(f"Average Rating: {avg_rating:.1f} ★", styles['Normal']))
    story.append(Spacer(1, 0.3*inch))
    
    # By Course table
    story.append(Paragraph("Study Time by Course", heading_style))
    course_data = [['Course', 'Sessions', 'Time']]
    for course, data in sorted(by_course.items(), key=lambda x: x[1]['minutes'], reverse=True):
        course_data.append([course, str(data['sessions']), format_time(data['minutes'])])
    
    course_table = Table(course_data, colWidths=[3*inch, 1.5*inch, 1.5*inch])
    course_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('TOPPADDING', (0, 1), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
    ]))
    story.append(course_table)
    story.append(Spacer(1, 0.3*inch))
    
    # By Type table
    story.append(Paragraph("Study Time by Type", heading_style))
    type_data = [['Type', 'Sessions', 'Time']]
    for study_type, data in sorted(by_type.items(), key=lambda x: x[1]['minutes'], reverse=True):
        type_data.append([study_type, str(data['sessions']), format_time(data['minutes'])])
    
    type_table = Table(type_data, colWidths=[3*inch, 1.5*inch, 1.5*inch])
    type_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('TOPPADDING', (0, 1), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
    ]))
    story.append(type_table)
    
    # Build PDF
    doc.build(story)
    print(f"PDF report generated: {output_path}")

def generate_docx_report(report_type, output_path, sessions):
    """Generate DOCX report using python-docx"""
def generate_docx_report(report_type, output_path, sessions):
    """Generate DOCX report using python-docx"""
    # Determine title
    if report_type == 'weekly':
        title = 'Weekly Study Report'
    elif report_type == 'monthly':
        title = 'Monthly Study Report'
    else:
        title = 'Yearly Study Report'
    
    # Calculate statistics
    total_sessions = len(sessions)
    total_minutes = sum(s[3] for s in sessions)
    rated_sessions = [s for s in sessions if s[5] and s[5] > 0]
    avg_rating = sum(s[5] for s in rated_sessions) / len(rated_sessions) if rated_sessions else 0
    
    # Group by course
    by_course = {}
    for s in sessions:
        course = s[7]  # course_name
        if course not in by_course:
            by_course[course] = {'sessions': 0, 'minutes': 0}
        by_course[course]['sessions'] += 1
        by_course[course]['minutes'] += s[3]
    
    # Group by type
    by_type = {}
    for s in sessions:
        study_type = s[2]
        if study_type not in by_type:
            by_type[study_type] = {'sessions': 0, 'minutes': 0}
        by_type[study_type]['sessions'] += 1
        by_type[study_type]['minutes'] += s[3]
    
    # Create document
    doc = Document()
    
    # Title
    heading = doc.add_heading(title, 0)
    heading.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    # Date
    date_para = doc.add_paragraph(f"Generated: {datetime.now().strftime('%B %d, %Y')}")
    date_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_paragraph()  # Blank line
    
    # Summary section
    doc.add_heading('Summary', 1)
    doc.add_paragraph(f"Total Sessions: {total_sessions}")
    doc.add_paragraph(f"Total Study Time: {format_time(total_minutes)}")
    doc.add_paragraph(f"Average Rating: {avg_rating:.1f} ★")
    doc.add_paragraph()  # Blank line
    
    # By Course section
    doc.add_heading('Study Time by Course', 1)
    table = doc.add_table(rows=1, cols=3)
    table.style = 'Light Grid Accent 1'
    
    # Header row
    hdr_cells = table.rows[0].cells
    hdr_cells[0].text = 'Course'
    hdr_cells[1].text = 'Sessions'
    hdr_cells[2].text = 'Time'
    
    # Data rows
    for course, data in sorted(by_course.items(), key=lambda x: x[1]['minutes'], reverse=True):
        row_cells = table.add_row().cells
        row_cells[0].text = course
        row_cells[1].text = str(data['sessions'])
        row_cells[2].text = format_time(data['minutes'])
    
    doc.add_paragraph()  # Blank line
    
    # By Type section
    doc.add_heading('Study Time by Type', 1)
    table = doc.add_table(rows=1, cols=3)
    table.style = 'Light Grid Accent 1'
    
    # Header row
    hdr_cells = table.rows[0].cells
    hdr_cells[0].text = 'Type'
    hdr_cells[1].text = 'Sessions'
    hdr_cells[2].text = 'Time'
    
    # Data rows
    for study_type, data in sorted(by_type.items(), key=lambda x: x[1]['minutes'], reverse=True):
        row_cells = table.add_row().cells
        row_cells[0].text = study_type
        row_cells[1].text = str(data['sessions'])
        row_cells[2].text = format_time(data['minutes'])
    
    # Save document
    doc.save(output_path)
    print(f"DOCX report generated: {output_path}")

def generate_report(report_type='weekly', output_path='study_report.docx'):
    try:
        # Calculate date range
        if report_type == 'weekly':
            days = 7
        elif report_type == 'monthly':
            days = 30
        else:
            days = 365
        
        # Check if database exists
        if not os.path.exists('study.db'):
            print("ERROR: study.db not found. Make sure you're running from the correct directory.", file=sys.stderr)
            sys.exit(1)
        
        # Connect to database
        conn = sqlite3.connect('study.db')
        c = conn.cursor()
        
        # Get sessions
        c.execute(f"""
            SELECT s.*, c.name as course_name
            FROM sessions s
            JOIN courses c ON s.course_id = c.id
            WHERE datetime(s.created_at) >= datetime('now', '-{days} days')
            ORDER BY s.created_at DESC
        """)
        sessions = c.fetchall()
        conn.close()
        
        # Ensure output directory exists
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # Determine format from file extension
        if output_path.lower().endswith('.pdf'):
            generate_pdf_report(report_type, output_path, sessions)
        else:
            generate_docx_report(report_type, output_path, sessions)
        
    except Exception as e:
        print(f"ERROR generating report: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    report_type = sys.argv[1] if len(sys.argv) > 1 else 'weekly'
    output_path = sys.argv[2] if len(sys.argv) > 2 else 'study_report.docx'
    generate_report(report_type, output_path)