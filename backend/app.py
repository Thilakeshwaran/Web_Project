from flask import Flask, request, jsonify
import pandas as pd
from flask_cors import CORS
import traceback, difflib
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Load the Excel file with all sheets
file_path = "C:/Users/admin/webnew1/backend/updateddata2.xlsx"
excel_sheets = pd.read_excel(file_path, sheet_name=None)
online_courses_sheet = excel_sheets.get("Online Courses(SCOFT)")


# Mapping department codes to Excel sheet names
DEPARTMENT_SHEETS = {
    "23": "AIDS - Mapped",
    "24": "AIML - Mapped",
    "06": "IOT - Mapped",
    "10": "Cyber Security(CS) - Mapped",
    "01": {
        "year_1_2": "CSE - II Years",
        "year_3_4": "CSE - Mapped, III & IV Years"
    },
    "07": {
        "year_1_2": "IT - II Years",
        "year_3_4": "IT - Mapped III & IV Years"
    }
    # Add more department code and sheet mappings here
}

# Mapping department codes to department names (for student info)
DEPARTMENT_MAPPINGS = {
    "23": "Artificial Intelligence and Data Science (AIDS)",
    "24": "Artificial Intelligence and Machine Learning (AIML)",
    "10": "CSE (Cyber Security)",
    "06": "CSE (Internet of Things)",
    "01": "Computer Science and Engineering",
    "07": "Information Technology"
}

# Regulation Mapping Function
def get_regulation_mapping(admission_year):
    """Determine regulation based on the admission year."""
    admission_year = int(admission_year)
    if 19 <= admission_year <= 22:
        return "R2019"
    elif admission_year >= 23:
        return "R2024"
    else:
        return None

# Function to get department info based on the register number
def get_department_info(register_number):
    department_code = register_number[6:8]  # Extract department code from register number
    return DEPARTMENT_MAPPINGS.get(department_code, None)

# Function to get the sheet name based on the register number and student year
def get_department_sheet(register_number, student_year):
    department_code = register_number[6:8]  # Extract department code from register number

    # Check if the department code exists in the DEPARTMENT_SHEETS dictionary
    if department_code not in DEPARTMENT_SHEETS:
        print(f"Department code {department_code} not found in DEPARTMENT_SHEETS")  # Debugging log
        return None

    department_sheets = DEPARTMENT_SHEETS[department_code]

    # If the value for the department is a dictionary (with different sheets for different years)
    if isinstance(department_sheets, dict):
        if student_year in [1, 2]:
            sheet_name = department_sheets.get("year_1_2")
            if sheet_name:
                return sheet_name
            else:
                print(f"Sheet for year_1_2 not found in department {department_code}")  # Debugging log
        elif student_year in [3, 4]:
            sheet_name = department_sheets.get("year_3_4")
            if sheet_name:
                return sheet_name
            else:
                print(f"Sheet for year_3_4 not found in department {department_code}")  # Debugging log
    else:
        # If the value is a string, return it (same sheet for all years)
        return department_sheets

    # If no valid sheet is found, return None
    print(f"No valid sheet found for department {department_code} and student year {student_year}")  # Debugging log
    return None


# Function to determine the curriculum regulation based on admission year
def get_regulation_column(admission_year):
    """Return the correct course code column based on the admission year."""
    regulation = get_regulation_mapping(admission_year)
    if regulation:
        return f"Course Code {regulation}"
    return None

# Function to calculate the student's current year of study
def get_student_year(admission_year):
    """Calculate student's current year of study based on admission year."""
    current_year = datetime.now().year % 100  # Get last two digits of the current year
    admission_year = int(admission_year)
    student_year = current_year - admission_year + 1

    # Ensure the student year is valid (1 to 4), or return "Graduated"
    if 1 <= student_year <= 4:
        return student_year
    elif student_year > 4:
        return "Graduated"
    else:
        return None  # Invalid admission year

# API to fetch student info based on register number
@app.route('/get_student_info', methods=['POST'])
def get_student_info():
    try:
        data = request.json
        register_number = data.get('register_number')

        # Validate register number
        if not register_number or len(register_number) != 12:
            return jsonify({"message": "Invalid Register Number", "status": "failure"}), 400

        # Get department info based on register number
        department = get_department_info(register_number)
        if not department:
            return jsonify({"message": "Invalid Department Code", "status": "failure"}), 400

        # Extract admission year from register number (5th and 6th digits)
        admission_year = register_number[4:6]

        # Get student's year of study
        student_year = get_student_year(admission_year)

        # Get regulation based on admission year
        regulation = get_regulation_column(admission_year)
        if not regulation:
            return jsonify({"message": "Invalid Admission Year", "status": "failure"}), 400

        # Return student info (department, student year, regulation)
        return jsonify({
            "department": department,
            "student_year": student_year,
            "regulation": regulation,
            "status": "success"
        }), 200

    except Exception as e:
        traceback.print_exc()
        return jsonify({"message": f"Error occurred: {str(e)}", "status": "error"}), 500

# API to check course eligibility based on register number and course title
@app.route('/check_eligibility', methods=['POST'])
def check_eligibility():
    try:
        data = request.json
        register_number = data.get('register_number')
        course_title = data.get('course_title')

        # Validate register number and course title
        if not register_number or len(register_number) != 12:
            return jsonify({"message": "Invalid Register Number", "status": "failure"}), 400
        if not course_title:
            return jsonify({"message": "Course title is required", "status": "failure"}), 400

        # Extract admission year from register number (5th and 6th digits)
        admission_year = register_number[4:6]

        # Calculate student's year of study based on the admission year
        student_year = get_student_year(admission_year)

        # Get the correct sheet based on the department and year of study
        sheet_name = get_department_sheet(register_number, student_year)
        if not sheet_name:
            return jsonify({"message": "Invalid Department or Register Number", "status": "failure"}), 400

        # Get the correct column name based on the admission year
        regulation_column = get_regulation_column(admission_year)
        if not regulation_column:
            return jsonify({"message": "Invalid Admission Year", "status": "failure"}), 400

        # Load the specific sheet for the department
        df = excel_sheets[sheet_name]
        df.columns = df.columns.str.strip().str.replace('\n', ' ')
        regulation_column = regulation_column.replace('\n', ' ')

        # Check if the regulation column exists in the sheet
        if regulation_column not in df.columns:
            return jsonify({"message": f"Column '{regulation_column}' not found in the sheet", "status": "failure"}), 400

        # Search for the course in the "Course Title" column
        course_row = df[df['Course Title'].str.strip().str.lower() == course_title.strip().lower()]
        if course_row.empty:
            # Get the list of available course titles in the sheet
            available_titles = df['Course Title'].dropna().astype(str).str.strip().str.lower().tolist()

            # Find the closest match using difflib (we can set a similarity threshold)
            closest_matches = difflib.get_close_matches(course_title.strip().lower(), available_titles, n=1, cutoff=0.7)

            if closest_matches:
                # If a partial match is found, retrieve the course row
                course_row = df[df['Course Title'].str.strip().str.lower() == closest_matches[0]]
            else:
                # No relevant course found (exact or partial), consider it eligible
                return jsonify({"message": "Course is eligible (not found in the sheet)", "status": "success"}), 200

        # Check if the course is a Professional Core (PC) based on the Category column
        if 'Category' not in df.columns:
            return jsonify({"message": "'Category' column not found in the sheet", "status": "failure"}), 400

        category_value = course_row['Category'].values[0]
        
        # If the category is "PC" (Professional Core), the course is not eligible
        if str(category_value).strip().upper() == "PC":
            # Fetch relevant courses from the "Online Courses(SCOFT)" sheet
            online_df = online_courses_sheet
            online_df.columns = online_df.columns.str.strip().str.replace('\n', ' ')

            # Find relevant courses from the "Online Courses(SCOFT)" sheet based on partial match
            relevant_courses = online_df[online_df['Course_Title'].str.contains(course_title, case=False, na=False)]

            # If relevant courses are found, return them
            if not relevant_courses.empty:
                relevant_course_titles = relevant_courses['Course_Title'].tolist()
                return jsonify({
                    "message": "Course not eligible (Professional Core - PC), but here are some relevant courses",
                    "relevant_courses": relevant_course_titles,
                    "status": "failure"
                }), 404

            # If no relevant courses found
            return jsonify({
                "message": "Course not eligible (Professional Core - PC), no relevant courses found",
                "status": "failure"
            }), 404
        else:
            return jsonify({"message": "Course is eligible", "status": "success"}), 200

    except Exception as e:
        traceback.print_exc()
        return jsonify({"message": f"Error occurred: {str(e)}", "status": "error"}), 500

    

# API to fetch course suggestions based on register number and partial course title
@app.route('/get_course_suggestions', methods=['POST'])
def get_course_suggestions():
    try:
        data = request.json
        register_number = data.get('register_number')
        partial_course_title = data.get('partial_course_title')

        # Validate register number and partial course title
        if not register_number or len(register_number) != 12:
            print(f"Invalid Register Number: {register_number}")  # Debugging log
            return jsonify({"message": "Invalid Register Number", "status": "failure"}), 400
        if not partial_course_title:
            print("Course title is required")  # Debugging log
            return jsonify({"message": "Course title is required", "status": "failure"}), 400


        # Get the relevant sheet name based on the Register Number (department code)
        sheet_name = "Online Courses(SCOFT)"
        if not sheet_name:
            print(f"Sheet name not found for department with register number: {register_number}")  # Debugging log
            return jsonify({"message": "Invalid Department or Register Number", "status": "failure"}), 400

        # Load the specific sheet for the department
        df = excel_sheets[sheet_name]
        df.columns = df.columns.str.strip().str.replace('\n', ' ')
        print(f"Loaded sheet: {sheet_name}")  # Debugging log

        # Search for course titles that contain the partial course title (case insensitive)
        matching_courses = df[df['Course_Title'].str.contains(partial_course_title, case=False, na=False)]
        
        # Strip any leading/trailing whitespaces from course titles to avoid subtle differences
        matching_courses['Course_Title'] = matching_courses['Course_Title'].str.strip()
        print(f"Found matching courses: {matching_courses}")  # Debugging log

        # Return a list of matching course titles
        course_suggestions = matching_courses['Course_Title'].unique().tolist()

        return jsonify({"suggestions": course_suggestions, "status": "success"}), 200

    except Exception as e:
        traceback.print_exc()
        return jsonify({"message": f"Error occurred: {str(e)}", "status": "error"}), 500


if __name__ == '__main__':
    app.run(debug=True, port=5001)

