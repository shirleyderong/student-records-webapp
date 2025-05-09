from flask import Flask, render_template, request, redirect, Response
import sqlite3
from cryptography.fernet import Fernet
import os
import re
import csv
from io import StringIO

app = Flask(__name__)

# Load encryption key
with open('keys/secret.key', 'rb') as file:
    key = file.read()
fernet = Fernet(key)

# Initialize database
def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        id_number TEXT,
        name TEXT,
        program TEXT,
        year_level TEXT
    )''')
    conn.commit()
    conn.close()

init_db()

# Validate and sanitize inputs
def validate_id_number(id_number):
    pattern = r'^\d{4}-\d{4}$'
    return bool(re.match(pattern, id_number))

def sanitize_input(input_string):
    if input_string is None:
        return ''
    return input_string.strip()

def validate_year_level(year_level):
    valid_year_levels = ["1st Year", "2nd Year", "3rd Year", "4th Year"]
    return year_level in valid_year_levels

def combine_id_number(form_data):
    return f"{form_data['id_number_1']}{form_data['id_number_2']}{form_data['id_number_3']}{form_data['id_number_4']}-{form_data['id_number_5']}{form_data['id_number_6']}{form_data['id_number_7']}{form_data['id_number_8']}"

def format_middle_initial(middle_initial):
    if not middle_initial:
        return ''
    middle_initial = middle_initial.strip().upper()
    if middle_initial and not middle_initial.endswith('.'):
        return middle_initial + '.'
    return middle_initial

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/add', methods=['GET', 'POST'])
def add():
    if request.method == 'POST':
        id_number = combine_id_number(request.form)
        
        # Extract the new name fields
        first_name = sanitize_input(request.form.get('first_name'))
        last_name = sanitize_input(request.form.get('last_name'))
        program = sanitize_input(request.form.get('program'))
        year_level = sanitize_input(request.form.get('year_level'))

        # Optional middle initial
        raw_mi = request.form.get('middle_initial')  # May be None or empty
        middle_initial = format_middle_initial(raw_mi)

        # Validate ID number format
        if not validate_id_number(id_number):
            error = "ID number must be in the format YYYY-XXXX (e.g., 2023-0866)."
            return render_template('add.html', error=error)

        # Validate Year Level
        if not validate_year_level(year_level):
            error = "Invalid Year Level selected."
            return render_template('add.html', error=error)

        # Construct full name and clean up extra spaces
        full_name = f"{first_name} {middle_initial} {last_name}".strip()
        full_name = re.sub(' +', ' ', full_name)  # Removes double spaces if MI is blank
        
        # Encrypt the full name and year level
        encrypted_name = fernet.encrypt(full_name.encode()).decode()
        encrypted_year_level = fernet.encrypt(year_level.encode()).decode()

        conn = sqlite3.connect('database.db')
        c = conn.cursor()

        # Check if the student already exists
        c.execute("SELECT * FROM students WHERE id_number = ?", (id_number,))
        existing_student = c.fetchone()

        if existing_student:
            conn.close()
            error = "This student has already been added."
            return render_template('add.html', error=error)
        else:
            # Insert the new student record
            c.execute("INSERT INTO students (id_number, name, program, year_level) VALUES (?, ?, ?, ?)",
                      (id_number, encrypted_name, program, encrypted_year_level))
            conn.commit()
            conn.close()
            success = "Student successfully added!"
            return render_template('add.html', success=success)

    return render_template('add.html')


@app.route('/search', methods=['GET', 'POST'])
def search():
    results = []
    error = None  # To pass error messages

    if request.method == 'POST':
        search_field = request.form.get('search_field')

        # Default keyword (for name, program, year_level)
        keyword = sanitize_input(request.form.get('keyword'))

        # Special handling if searching by ID number
        if search_field == 'id_number':
            id_number_parts = [
                request.form.get('id_number_1', ''),
                request.form.get('id_number_2', ''),
                request.form.get('id_number_3', ''),
                request.form.get('id_number_4', ''),
                request.form.get('id_number_5', ''),
                request.form.get('id_number_6', ''),
                request.form.get('id_number_7', ''),
                request.form.get('id_number_8', '')
            ]

            # If all parts are filled, construct the full id_number
            if all(id_number_parts):
                keyword = sanitize_input(''.join(id_number_parts[:4]) + '-' + ''.join(id_number_parts[4:]))
            else:
                keyword = ''  # Treat incomplete input as no keyword

        if not keyword:
            error = "Please enter a search keyword."
            return render_template('search.html', error=error)

        conn = sqlite3.connect('database.db')
        c = conn.cursor()

        if search_field == "id_number":
            if validate_id_number(keyword):
                c.execute("SELECT * FROM students WHERE id_number = ?", (keyword,))
                student = c.fetchone()
                if student:
                    decrypted_name = fernet.decrypt(student[2].encode()).decode()
                    decrypted_year_level = fernet.decrypt(student[4].encode()).decode()
                    results = [{
                        'id_number': student[1],
                        'name': decrypted_name,
                        'program': student[3],
                        'year_level': decrypted_year_level
                    }]
            else:
                conn.close()
                error = "Invalid ID number format. It must be in the format YYYY-XXXX."
                return render_template('search.html', error=error)

        elif search_field == "name" or search_field == "year_level":
            c.execute("SELECT * FROM students")
            all_students = c.fetchall()
            decrypted_results = []
            for student in all_students:
                decrypted_name = fernet.decrypt(student[2].encode()).decode()
                decrypted_year_level = fernet.decrypt(student[4].encode()).decode()
                if search_field == "name" and keyword.lower() in decrypted_name.lower():
                    decrypted_results.append({
                        'id_number': student[1],
                        'name': decrypted_name,
                        'program': student[3],
                        'year_level': decrypted_year_level
                    })
                if search_field == "year_level" and keyword.lower() in decrypted_year_level.lower():
                    decrypted_results.append({
                        'id_number': student[1],
                        'name': decrypted_name,
                        'program': student[3],
                        'year_level': decrypted_year_level
                    })
            results = decrypted_results

        elif search_field == "program":
            c.execute("SELECT * FROM students WHERE program LIKE ?", ('%' + keyword + '%',))
            students = c.fetchall()
            decrypted_results = []
            for student in students:
                decrypted_name = fernet.decrypt(student[2].encode()).decode()
                decrypted_year_level = fernet.decrypt(student[4].encode()).decode()
                decrypted_results.append({
                    'id_number': student[1],
                    'name': decrypted_name,
                    'program': student[3],
                    'year_level': decrypted_year_level
                })
            results = decrypted_results

        conn.close()

    return render_template('search.html', results=results, error=error)


@app.route('/update', methods=['GET', 'POST'])
def update():
    if request.method == 'POST':
        id_number = combine_id_number(request.form)
        first_name = sanitize_input(request.form.get('first_name'))
        middle_initial = format_middle_initial(sanitize_input(request.form.get('middle_initial', '')))  # Optional
        last_name = sanitize_input(request.form.get('last_name'))
        program = sanitize_input(request.form.get('program'))
        year_level = sanitize_input(request.form.get('year_level'))

        if not validate_id_number(id_number):
            error = "ID number must be in the format YYYY-XXXX (e.g., 2023-0866)."
            return render_template('update.html', error=error)

        if not validate_year_level(year_level):
            error = "Invalid Year Level selected."
            return render_template('update.html', error=error)

        # Concatenate the name components (first_name, middle_initial, last_name)
        full_name = f"{first_name} {middle_initial} {last_name}".strip()

        encrypted_name = fernet.encrypt(full_name.encode()).decode()
        encrypted_year_level = fernet.encrypt(year_level.encode()).decode()

        conn = sqlite3.connect('database.db')
        c = conn.cursor()

        c.execute("SELECT * FROM students WHERE id_number = ?", (id_number,))
        student = c.fetchone()

        if student is None:
            conn.close()
            error = "Student with this ID number does not exist."
            return render_template('update.html', error=error)

        c.execute("UPDATE students SET name = ?, program = ?, year_level = ? WHERE id_number = ?",
                  (encrypted_name, program, encrypted_year_level, id_number))
        conn.commit()
        conn.close()

        success = "Student information updated successfully!"
        return render_template('update.html', success=success)

    return render_template('update.html')


@app.route('/delete', methods=['GET', 'POST'])
def delete():
    if request.method == 'POST':
        id_number = combine_id_number(request.form)

        if not validate_id_number(id_number):
            error = "ID number must be in the format YYYY-XXXX (e.g., 2023-0866)."
            return render_template('delete.html', error=error)

        conn = sqlite3.connect('database.db')
        c = conn.cursor()

        # Check if the student exists
        c.execute("SELECT * FROM students WHERE id_number = ?", (id_number,))
        student = c.fetchone()

        if student is None:
            conn.close()
            error = "Student with this ID number does not exist."
            return render_template('delete.html', error=error)

        # Proceed with deletion if the student exists
        c.execute("DELETE FROM students WHERE id_number = ?", (id_number,))
        conn.commit()
        conn.close()

        success = "Student deleted successfully!"
        return render_template('delete.html', success=success)

    return render_template('delete.html')


@app.route('/students')
def students():
    page = request.args.get('page', default=1, type=int)
    per_page = 10  # You can change how many records per page

    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT * FROM students")
    all_students = c.fetchall()
    conn.close()

    students_list = []
    for student in all_students:
        decrypted_name = fernet.decrypt(student[2].encode()).decode()
        decrypted_year_level = fernet.decrypt(student[4].encode()).decode()
        students_list.append({
            'id_number': student[1],
            'name': decrypted_name,
            'program': student[3],
            'year_level': decrypted_year_level
        })

    total_students = len(students_list)
    total_pages = (total_students + per_page - 1) // per_page
    paginated_students = students_list[(page - 1) * per_page: page * per_page]

    return render_template('students_list.html',
                           students=paginated_students,
                           page=page,
                           total_pages=total_pages)

@app.route('/export_csv')
def export_csv():
    # Fetch all student records from the database
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT * FROM students")
    all_students = c.fetchall()
    conn.close()

    # Prepare CSV data
    csv_data = StringIO()
    csv_writer = csv.writer(csv_data)
    
    # Write CSV header
    csv_writer.writerow(['ID Number', 'Name', 'Program', 'Year Level'])

    # Write data rows (decrypting name and year level)
    for student in all_students:
        decrypted_name = fernet.decrypt(student[2].encode()).decode()
        decrypted_year_level = fernet.decrypt(student[4].encode()).decode()
        csv_writer.writerow([student[1], decrypted_name, student[3], decrypted_year_level])

    # Set the correct HTTP headers for CSV file download
    csv_data.seek(0)  # Reset the cursor to the beginning of the StringIO object
    return app.response_class(
        csv_data,
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment;filename=students_list.csv'}
    )

if __name__ == '__main__':
    app.run(debug=True)