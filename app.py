from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_mysqldb import MySQL  # Add this import
from db_connection import (
    check_user_login,
    get_total_students,
    get_total_units,
    get_total_lecturers,
    get_lecturers,
    get_students,
    get_lecture_rooms,
    get_courses,
    get_units,
    get_total_faculties,
    get_faculties,
    get_db_connection,
    add_faculty_to_db,
    add_course_to_db,
    add_unit_to_db,
    get_lecturer_by_email,
    get_lecturer_courses,
    get_units_by_course,
    get_students_by_course,
    add_venue,
    add_lecturer_to_db,
    get_courses_by_faculty,
    add_student_to_db
)
from functools import wraps
import MySQLdb

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Add this if not already present

# MySQL Configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'new11'

mysql = MySQL(app)  # Initialize MySQL

# Add this decorator definition before your routes
def role_required(required_role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'role' not in session:
                flash('Please log in first', 'error')
                return redirect(url_for('login'))
            if session['role'] != required_role:
                flash('Unauthorized access', 'error')
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        role = request.form.get('role')      
        email = request.form.get('email')    
        password = request.form.get('password')  

        print(f"\nLogin attempt - Role: {role}, Email: {email}")

        user = check_user_login(email, password, role)

        if user:
            session['email'] = user['emailAddress']
            session['role'] = role
            session['user_id'] = user['id']
            print(f"Session created: {session}")
            
            if role == 'Admin':
                return redirect(url_for('dashboard'))
            elif role == 'Lecturer':
                return redirect(url_for('lec_dashboard'))
        else:
            flash('Invalid Email, Password, or Role', 'error')

    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'email' not in session:
        return redirect(url_for('login'))  # Prevent access if not logged in

    # Fetch data from the database
    total_students = get_total_students()
    total_units = get_total_units()
    total_lecturers = get_total_lecturers()
    lecturers = get_lecturers()
    students = get_students()
    lecture_rooms = get_lecture_rooms()
    courses = get_courses()

    return render_template('admin_dashboard.html', 
                           total_students=total_students, 
                           total_units=total_units, 
                           total_lecturers=total_lecturers, 
                           lecturers=lecturers, 
                           students=students, 
                           lecture_rooms=lecture_rooms, 
                           courses=courses)

@app.route('/logout')
def logout():
    session.clear()  # Clear all session data
    return redirect(url_for('login'))  # Redirect to login page

@app.route('/manage_courses')
def manage_courses():
    try:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        
        # Updated query with proper date formatting
        cursor.execute("""
            SELECT 
                c.id,
                c.name, 
                c.courseCode,
                c.facultyID,
                (SELECT COUNT(*) FROM tblunit WHERE courseID = c.courseCode) as total_units,
                (SELECT COUNT(*) FROM tblstudent WHERE courseCode = c.courseCode) as total_students,
                DATE_FORMAT(c.dateCreated, '%Y-%m-%d') as dateCreated  # Format date to YYYY-MM-DD
            FROM tblcourse c 
            ORDER BY c.dateCreated DESC
        """)
        courses = cursor.fetchall()
        print("Fetched courses:", courses)  # Debug print
        
        # 2. Fetch units with course names
        cursor.execute("""
            SELECT 
                u.unitCode,
                u.name,
                c.name as course,
                (SELECT COUNT(*) FROM tblstudent WHERE courseCode = c.courseCode) as total_students,
                DATE_FORMAT(u.dateCreated, '%Y-%m-%d') as dateCreated
            FROM tblunit u
            LEFT JOIN tblcourse c ON u.courseID = c.courseCode
            ORDER BY u.dateCreated DESC
        """)
        units = cursor.fetchall()
        print("Fetched units:", units)  # Debug print
        
        # 3. Fetch faculties with counts
        cursor.execute("""
            SELECT 
                f.facultyCode as code,
                f.facultyName as name,
                (SELECT COUNT(*) FROM tblcourse WHERE facultyID = f.facultyCode) as total_courses,
                (SELECT COUNT(*) FROM tblstudent WHERE faculty = f.facultyCode) as total_students,
                (SELECT COUNT(*) FROM tbllecturer WHERE facultyCode = f.facultyCode) as total_lectures,
                DATE_FORMAT(f.dateRegistered, '%Y-%m-%d') as dateCreated
            FROM tblfaculty f
            ORDER BY f.dateRegistered DESC
        """)
        faculties = cursor.fetchall()
        print("Fetched faculties:", faculties)  # Debug print
        
        cursor.close()
        
        return render_template('course.html',
                             courses=courses,
                             units=units,
                             faculties=faculties)
                             
    except Exception as e:
        print(f"Error in manage_courses: {e}")
        return render_template('course.html',
                             courses=[],
                             units=[],
                             faculties=[])

@app.route('/manage_lectures')
def manage_lectures():
    if 'email' not in session:
        return redirect(url_for('login'))
    
    lecturers = get_lecturers()
    total_lecturers = get_total_lecturers()
    
    return render_template('lecturer.html',
                         lecturers=lecturers,
                         total_lecturers=total_lecturers)

@app.route('/manage_students')
def manage_students():
    if 'email' not in session:
        return redirect(url_for('login'))
    
    students = get_students()
    total_students = get_total_students()
    
    return render_template('student.html',
                         students=students,
                         total_students=total_students)

@app.route('/manage_venues')
def manage_venues():
    if 'email' not in session:
        return redirect(url_for('login'))
    
    venues = get_lecture_rooms()
    total_venues = len(venues)
    
    return render_template('venue.html',
                         venues=venues,
                         total_venues=total_venues)

@app.route('/add_faculty', methods=['POST'])
def add_faculty():
    if 'email' not in session:
        return redirect(url_for('login'))
    
    faculty_name = request.form.get('facultyName')
    faculty_code = request.form.get('facultyCode')
    
    if add_faculty_to_db(faculty_code, faculty_name):
        flash('Faculty added successfully!', 'success')
    else:
        flash('Error adding faculty', 'error')
    
    return redirect(url_for('manage_courses'))

@app.route('/add_course', methods=['POST'])
def add_course():
    try:
        data = request.get_json()
        
        # Debug print
        print("Received data:", data)
        
        course_name = data.get('courseName')
        course_code = data.get('courseCode')
        faculty_id = data.get('faculty')
        
        # Validate input
        if not all([course_name, course_code, faculty_id]):
            return jsonify({
                'success': False, 
                'message': 'Missing required fields'
            })
        
        # Try to add the course
        result = add_course_to_db(course_name, course_code, faculty_id)
        
        if result:
            return jsonify({'success': True})
        else:
            return jsonify({
                'success': False, 
                'message': 'Failed to add course to database'
            })
            
    except Exception as e:
        print(f"Error in add_course route: {e}")
        return jsonify({
            'success': False, 
            'message': f'Error: {str(e)}'
        })

@app.route('/add_unit', methods=['POST'])
def add_unit():
    try:
        data = request.get_json()
        unit_code = data.get('unitCode')
        unit_name = data.get('unitName')
        course_id = data.get('courseId')
        
        print(f"Adding unit - Code: {unit_code}, Name: {unit_name}, Course: {course_id}")  # Debug print
        
        # Verify the course exists first
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT courseCode FROM tblcourse WHERE courseCode = %s", (course_id,))
        course = cursor.fetchone()
        cursor.close()
        
        if not course:
            return jsonify({
                'success': False, 
                'message': f'Course with code {course_id} does not exist'
            })
        
        if add_unit_to_db(unit_code, unit_name, course_id):
            return jsonify({'success': True})
        else:
            return jsonify({
                'success': False, 
                'message': 'Failed to add unit to database'
            })
            
    except Exception as e:
        print(f"Error in add_unit route: {e}")  # Debug print
        return jsonify({
            'success': False, 
            'message': f'Error: {str(e)}'
        })

@app.route('/lec_dashboard')
def lec_dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    email = session.get('email')
    lecturer = get_lecturer_by_email(email)
    courses = get_courses()
    
    # Debug print
    print("Available courses:", courses)
    
    return render_template('lec_dashboard.html', lecturer=lecturer, courses=courses)

@app.route('/get_units_by_course/<course_id>')
def fetch_units_by_course(course_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    print(f"Fetching units for course ID: {course_id}")  # Debug print
    units = get_units_by_course(course_id)
    print(f"Found units: {units}")  # Debug print
    return jsonify(units)

@app.route('/get_students_by_course_unit')
def fetch_students_by_course_unit():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    course_id = request.args.get('course')
    unit_id = request.args.get('unit')
    
    if not course_id or not unit_id:
        return jsonify([])
    
    print(f"Fetching students for course {course_id} and unit {unit_id}")  # Debug print
    students = get_students_by_course_unit(course_id, unit_id)
    print(f"Found students: {students}")  # Debug print
    
    return jsonify(students)

@app.route('/get_students_by_course/<course_id>')
def fetch_students_by_course(course_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    print(f"Fetching students for course ID: {course_id}")  # Debug print
    students = get_students_by_course(course_id)
    print(f"Found students: {students}")  # Debug print
    return jsonify(students)

@app.route('/add_venue', methods=['GET', 'POST'])
def add_venue_route():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        data = request.get_json()
        
        try:
            result = add_venue(
                className=data['className'],
                currentStatus=data['currentStatus'],
                capacity=data['capacity'],
                classType=data['classType'],
                faculty_code=data['facultyCode']
            )
            
            if result:
                return jsonify({'success': True})
            else:
                return jsonify({'success': False, 'message': 'Failed to add venue'})
                
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)})

@app.route('/get_faculties')
def get_faculties_route():
    try:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("""
            SELECT 
                facultyCode,
                facultyName
            FROM tblfaculty
            ORDER BY facultyName
        """)
        faculties = cursor.fetchall()
        cursor.close()
        
        print("Fetched faculties:", faculties)  # Debug print
        return jsonify(faculties)
        
    except Exception as e:
        print(f"Error fetching faculties: {e}")
        return jsonify([])

@app.route('/add_lecturer', methods=['POST'])
def add_lecturer():
    try:
        data = request.get_json()
        print("Received lecturer data:", data)  # Debug print
        
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        
        # Insert using the correct column names that match your table structure
        cursor.execute("""
            INSERT INTO tbllecturer (
                firstName, 
                lastName, 
                emailAddress, 
                phoneNo,           # Changed from phoneNumber to phoneNo
                password,
                facultyCode
            ) VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            data['firstName'],
            data['lastName'],
            data['email'],
            data['phone'],
            data['password'],
            data['faculty']
        ))
        
        mysql.connection.commit()
        cursor.close()
        
        return jsonify({'success': True})
        
    except Exception as e:
        print(f"Error adding lecturer: {str(e)}")  # Debug print
        return jsonify({
            'success': False,
            'message': f'Failed to add lecturer: {str(e)}'
        })

@app.route('/get_courses_by_faculty/<faculty_code>')
def get_courses_by_faculty_route(faculty_code):
    try:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        
        # Updated query to get courses by faculty code
        cursor.execute("""
            SELECT 
                c.id,
                c.name,
                c.courseCode,
                f.facultyName
            FROM tblcourse c 
            LEFT JOIN tblfaculty f ON c.facultyID = f.facultyCode
            WHERE c.facultyID = %s
            ORDER BY c.name
        """, (faculty_code,))
        
        courses = cursor.fetchall()
        cursor.close()
        
        print(f"Fetched courses for faculty {faculty_code}:", courses)  # Debug print
        return jsonify(courses)
        
    except Exception as e:
        print(f"Error in get_courses_by_faculty_route: {e}")
        return jsonify([])

@app.route('/add_student', methods=['POST'])
def add_student():
    try:
        data = request.get_json()
        print("Received student data:", data)  # Debug print
        
        # Verify the course exists first
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT courseCode, facultyID 
            FROM tblcourse 
            WHERE courseCode = %s
        """, (data['courseId'],))
        course = cursor.fetchone()
        
        if not course:
            print(f"Course not found: {data['courseId']}")  # Debug print
            return jsonify({
                'success': False, 
                'message': f'Course with code {data["courseId"]} not found'
            })
        
        # Add the student
        result = add_student_to_db(
            first_name=data['firstName'],
            last_name=data['lastName'],
            email=data['email'],
            reg_no=data['registrationNumber'],
            course_id=data['courseId'],
            faculty=data['faculty']
        )
        
        if result:
            return jsonify({'success': True})
        else:
            return jsonify({
                'success': False, 
                'message': 'Failed to add student to database'
            })
            
    except Exception as e:
        print(f"Error in add_student route: {e}")  # Debug print
        return jsonify({'success': False, 'message': str(e)})
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'connection' in locals() and connection.is_connected():
            connection.close()

@app.route('/get_overview_counts')
def get_overview_counts():
    try:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        
        # Get real-time counts
        cursor.execute("""
            SELECT 
                (SELECT COUNT(*) FROM tblcourse) as total_courses,
                (SELECT COUNT(*) FROM tblunit) as total_units,
                (SELECT COUNT(*) FROM tblfaculty) as total_faculties
        """)
        
        counts = cursor.fetchone()
        cursor.close()
        
        # Since we're using DictCursor, we can access by column names
        return jsonify({
            'total_courses': counts['total_courses'],
            'total_units': counts['total_units'],
            'total_faculties': counts['total_faculties']
        })
    except Exception as e:
        print(f"Error getting overview counts: {e}")
        return jsonify({
            'total_courses': 0,
            'total_units': 0,
            'total_faculties': 0
        })

@app.route('/get_courses_list')
def get_courses_list():
    try:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        
        # Query to get all courses with their codes
        cursor.execute("""
            SELECT 
                id,
                name,
                courseCode,
                facultyID
            FROM tblcourse
            ORDER BY name
        """)
        
        courses = cursor.fetchall()
        cursor.close()
        
        print("Fetched courses for dropdown:", courses)
        return jsonify(courses)
        
    except Exception as e:
        print(f"Error fetching courses: {e}")
        return jsonify([])

@app.route('/get_courses_for_student')
def get_courses_for_student():
    try:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        
        # Updated query to get all necessary course information
        cursor.execute("""
            SELECT 
                c.id,
                c.name,
                c.courseCode,
                f.facultyName,
                f.facultyCode
            FROM tblcourse c 
            LEFT JOIN tblfaculty f ON c.facultyID = f.facultyCode
            WHERE c.courseCode IS NOT NULL  # Ensure courseCode exists
            ORDER BY c.name
        """)
        
        courses = cursor.fetchall()
        cursor.close()
        
        print("Fetched courses for student form:", courses)  # Debug print
        return jsonify(courses)
        
    except Exception as e:
        print(f"Error fetching courses: {e}")  # Debug print
        return jsonify([])

if __name__ == '__main__':
    app.run(debug=True)
