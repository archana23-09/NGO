from flask import Flask, request, jsonify, session
from flask_cors import CORS
import mysql.connector
import hashlib
import secrets

app = Flask(__name__, static_folder='static')
app.secret_key = secrets.token_hex(16)
CORS(app)

# -----------------------
# DATABASE CONNECTION
# -----------------------
def get_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="Nous@12345",  # 🔴 CHANGE THIS
        database="ngo_dbb"
    )

# -----------------------
# INITIALIZE DATABASE
# -----------------------
def init_database():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Create users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                email VARCHAR(255) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Drop program column if it exists (replaced by support)
        cursor.execute("SHOW COLUMNS FROM beneficiariess LIKE 'program'")
        if cursor.fetchone():
            cursor.execute("ALTER TABLE beneficiariess DROP COLUMN program")
        
        # Add columns to beneficiariess if they don't exist
        cursor.execute("SHOW COLUMNS FROM beneficiariess LIKE 'user_id'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE beneficiariess ADD COLUMN user_id INT")
        
        cursor.execute("SHOW COLUMNS FROM beneficiariess LIKE 'email'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE beneficiariess ADD COLUMN email VARCHAR(255)")
        
        cursor.execute("SHOW COLUMNS FROM beneficiariess LIKE 'phone'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE beneficiariess ADD COLUMN phone VARCHAR(20)")
        
        cursor.execute("SHOW COLUMNS FROM beneficiariess LIKE 'amount'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE beneficiariess ADD COLUMN amount DECIMAL(10,2)")
        
        conn.commit()
        cursor.close()
        conn.close()
        print("✅ Database initialized successfully")
    except Exception as e:
        print(f"⚠️ Database initialization message: {e}")

# Initialize database on startup
init_database()

# -----------------------
# HOME
# -----------------------
@app.route('/')
def home():
    return app.send_static_file('index.html')

# -----------------------
# LOGIN
# -----------------------
@app.route('/login', methods=['POST'])
def login():
    try:
        data = request.json
        email = data.get('email')
        password = data.get('password')

        if not email or not password:
            return jsonify({"error": "Email and password required"})

        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user and user['password'] == hashlib.sha256(password.encode()).hexdigest():
            session['user_id'] = user['id']
            session['email'] = user['email']
            return jsonify({"message": "Login successful", "user_id": user['id']})
        else:
            return jsonify({"error": "Invalid email or password"})

    except Exception as e:
        print("ERROR:", e)
        return jsonify({"error": str(e)})

# -----------------------
# REGISTER
# -----------------------
@app.route('/register', methods=['POST'])
def register():
    try:
        data = request.json
        email = data.get('email')
        password = data.get('password')

        if not email or not password:
            return jsonify({"error": "Email and password required"})

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({"error": "Email already registered"})

        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        sql = "INSERT INTO users (email, password) VALUES (%s, %s)"
        cursor.execute(sql, (email, hashed_password))
        conn.commit()

        user_id = cursor.lastrowid
        cursor.close()
        conn.close()

        session['user_id'] = user_id
        session['email'] = email
        return jsonify({"message": "Registration successful", "user_id": user_id})

    except Exception as e:
        print("ERROR:", e)
        return jsonify({"error": str(e)})

# -----------------------
# LOGOUT
# -----------------------
@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({"message": "Logged out successfully"})

# -----------------------
# ADD
# -----------------------
@app.route('/add', methods=['POST'])
def add_beneficiary():
    try:
        data = request.json

        name = data.get('name')
        email = data.get('email')
        phone = data.get('phone')
        amount = data.get('amount')
        support = data.get('support')
        status = data.get('status', 'Active')
        user_id = session.get('user_id')

        if not all([name, email, phone, amount, support]):
            return jsonify({"error": "All fields are required"})

        conn = get_connection()
        cursor = conn.cursor()

        sql = """
        INSERT INTO beneficiariess (user_id, name, email, phone, amount, support, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(sql, (user_id, name, email, phone, amount, support, status))
        conn.commit()

        cursor.close()
        conn.close()

        return jsonify({"message": "Beneficiary Added Successfully"})

    except Exception as e:
        print("ERROR:", e)
        return jsonify({"error": str(e)})

# -----------------------
# VIEW
# -----------------------
@app.route('/view', methods=['GET'])
def view_beneficiaries():
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({"error": "Not logged in"})

        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT * FROM beneficiariess WHERE user_id=%s", (user_id,))
        data = cursor.fetchall()

        cursor.close()
        conn.close()

        return jsonify(data)

    except Exception as e:
        return jsonify({"error": str(e)})

# -----------------------
# UPDATE
# -----------------------
@app.route('/update/<int:id>', methods=['PUT'])
def update_beneficiary(id):
    try:
        data = request.json

        name = data.get('name')
        email = data.get('email')
        phone = data.get('phone')
        amount = data.get('amount')
        support = data.get('support')
        status = data.get('status')

        conn = get_connection()
        cursor = conn.cursor()

        sql = """
        UPDATE beneficiariess
        SET name=%s, email=%s, phone=%s, amount=%s, support=%s, status=%s
        WHERE id=%s
        """
        cursor.execute(sql, (name, email, phone, amount, support, status, id))
        conn.commit()

        cursor.close()
        conn.close()

        return jsonify({"message": "Updated Successfully"})

    except Exception as e:
        return jsonify({"error": str(e)})

# -----------------------
# DELETE
# -----------------------
@app.route('/delete/<int:id>', methods=['DELETE'])
def delete_beneficiary(id):
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM beneficiariess WHERE id=%s", (id,))
        conn.commit()

        cursor.close()
        conn.close()

        return jsonify({"message": "Deleted Successfully"})

    except Exception as e:
        return jsonify({"error": str(e)})

# -----------------------
# RUN
# -----------------------
if __name__ == '__main__':
    app.run(debug=True)