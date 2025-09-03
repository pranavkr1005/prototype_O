from flask import Flask, request, jsonify, render_template, flash
from flask import Flask, request, jsonify
from backend import preprocess, recommendInternship
import mysql.connector
import PyPDF2
import io

app = Flask(__name__)
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'qwerty',
    'database': 'internship_db'
}

def DBConnection():
    return mysql.connector.connect(**DB_CONFIG)

# Initializing db
def init_db():
    conn = DBConnection()
    cursor = conn.cursor()
    cursor.execute("CREATE DATABASE IF NOT EXISTS internship_db")
    cursor.execute("USE internship_db")
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS internships (
        id INT AUTO_INCREMENT PRIMARY KEY,
        title VARCHAR(255),
        description TEXT,
        required_skills TEXT,
        company VARCHAR(255),
        duration VARCHAR(50),
        stipend INT,
        popularity INT,
        rating FLOAT,
        company_prestige INT
    )
    """)
    
    #insert sample data
    cursor.execute("SELECT COUNT(*) FROM internships")
    if cursor.fetchone()[0] == 0:
        sample_internships = [
            ("AI Research Intern", "machine learning deep learning neural networks python research", "python machine learning tensorflow", "Tech Corp", "3 months", 5000, 90, 4.8, 9),
            ("Web Development Intern", "javascript react node js web development frontend", "javascript html css react", "Web Solutions", "6 months", 3000, 75, 4.2, 7),
        ]
        insert_query = """
        INSERT INTO internships (title, description, required_skills, company, duration, stipend, popularity, rating, company_prestige)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.executemany(insert_query, sample_internships)
    
    conn.commit()
    cursor.close()
    conn.close()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload')
def upload_resume():
    return render_template('upload.html')

@app.route('/add')
def add_internship_page():
    return render_template('add_internship.html')

@app.route('/dashboard')
def dashboard():
    conn = DBConnection()
    cursor = conn.cursor(dictionary=True)
    
    #get dashboard stats
    cursor.execute("SELECT COUNT(*) as total FROM internships")
    total_internships = cursor.fetchone()['total']
    cursor.execute("SELECT AVG(rating) as avg_rating, AVG(stipend) as avg_stipend FROM internships")
    stats = cursor.fetchone()
    avg_rating = stats['avg_rating'] or 0
    avg_stipend = stats['avg_stipend'] or 0
    cursor.execute("SELECT * FROM internships ORDER BY id DESC LIMIT 5")
    recent_internships = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('dashboard.html',total_internships=total_internships, avg_rating=float(avg_rating),
                           avg_stipend=float(avg_stipend),recent_internships=recent_internships)



@app.route('/add_internship', methods=['POST'])
def add_internship():
    data = request.json
    required_fields = ['title', 'description', 'required_skills', 'company', 'duration', 'stipend', 'popularity', 'rating', 'company_prestige']
    
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required fields'}), 400

    conn = DBConnection()
    cursor = conn.cursor()
    
    sql = """
    INSERT INTO internships (title, description, required_skills, company, duration, stipend, popularity, rating, company_prestige)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    values = (
        data['title'], data['description'], data['required_skills'], data['company'],
        data['duration'], data['stipend'], data['popularity'], data['rating'], data['company_prestige']
    )
    
    try:
        cursor.execute(sql, values)
        conn.commit()
        return jsonify({'message': 'Internship added successfully', 'id': cursor.lastrowid}), 201
    except mysql.connector.Error as err:
        return jsonify({'error': str(err)}), 500
    finally:
        cursor.close()
        conn.close()


@app.route('/recommend', methods=['POST'])
def recommend():
    if 'resume' not in request.files:
        return jsonify({'error': 'No resume file provided'}), 400
    
    file = request.files['resume']
    if not file.filename.endswith('.pdf'):
        return jsonify({'error': 'Only PDF files are supported'}), 400
    
    #extract text from PDF
    try:
        pdf_content = io.BytesIO(file.read())
        reader = PyPDF2.PdfReader(pdf_content)
        resume_text = ''
        for page in reader.pages:
            resume_text += page.extract_text() or ''
    except Exception as e:
        return jsonify({'error': f'Error parsing PDF: {str(e)}'}), 500
    
    #treat resume text as skills + interests (basic parsing)
    student = {
        "skills": resume_text,
        "interests": "", 
        "field": ""  
    }
    conn = DBConnection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM internships")
    internships = cursor.fetchall()
    cursor.close()
    conn.close()
    if not internships:
        return jsonify({'message': 'No internships available in the database'}), 404
    
    recommendations = recommendInternship(student, internships, top_n=5)
    response = []
    for score, internship, explanation in recommendations:
        response.append({
            'score': round(score, 4),
            'internship': internship,
            'explanation': explanation
        })
    
    return jsonify(response)

if __name__ == '__main__':
    init_db()
    app.run(debug=True)