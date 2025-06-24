# app.py
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import mysql.connector
from datetime import datetime, timedelta
import random
import os

# Initialize Flask app
# This configuration tells Flask to look for static files (like your HTML, CSS, JS)
# in the 'static' folder and serve them directly from the root URL.
app = Flask(__name__, static_folder='static', static_url_path='/static')
CORS(app) # Enable CORS for frontend communication (less critical when served by Flask, but good practice)

# Database configuration (replace with your MySQL credentials)
# It's recommended to use environment variables for production
DB_CONFIG = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'user': os.environ.get('DB_USER', 'root'), # Replace with your MySQL username
    'password': os.environ.get('DB_PASSWORD', 'your_password'), # Replace with your MySQL password
    'database': os.environ.get('DB_DATABASE', 'realpage_donations')
}

# --- Database Connection Helper ---
def get_db_connection():
    """Establishes and returns a database connection."""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except mysql.connector.Error as err:
        print(f"Error connecting to MySQL: {err}")
        return None

# --- API Endpoints ---

@app.route('/')
def serve_html_app():
    """Serve the index.html for the root URL, which is your HTML/CSS/JS frontend."""
    # Flask will automatically find 'index.html' within the configured static_folder
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/api/login/send_otp', methods=['POST'])
def send_otp():
    """
    Endpoint to send an OTP to the provided email.
    It generates an OTP, stores it in the database with an expiration time,
    and simulates sending an email.
    """
    data = request.get_json()
    email = data.get('email')

    if not email:
        return jsonify({"message": "Email is required"}), 400

    # Basic email domain validation for Realpage
    if not email.endswith('@realpage.com'):
        return jsonify({"message": "Only Realpage email IDs are allowed."}), 403

    conn = get_db_connection()
    if conn is None:
        return jsonify({"message": "Database connection failed"}), 500

    cursor = conn.cursor()
    try:
        # Check if user exists, if not, create them (or handle based on your user management)
        cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
        user_exists = cursor.fetchone()
        if not user_exists:
            cursor.execute("INSERT INTO users (email) VALUES (%s)", (email,))
            conn.commit()
            print(f"New user registered: {email}") # Log for demonstration

        # Generate a 6-digit OTP
        otp_code = str(random.randint(100000, 999999))
        
        # Set OTP expiration time (120 seconds from now)
        expires_at = datetime.now() + timedelta(seconds=120)

        # Clear any existing OTPs for this email to ensure only one is active
        cursor.execute("DELETE FROM otps WHERE otps.email = %s", (email,))
        
        # Store OTP in the database
        cursor.execute(
            "INSERT INTO otps (email, otp_code, expires_at) VALUES (%s, %s, %s)",
            (email, otp_code, expires_at)
        )
        conn.commit()

        # --- Simulate Email Sending (IMPORTANT: For production, integrate a real email service) ---
        print(f"\n--- OTP for {email} ---")
        print(f"Your OTP is: {otp_code}")
        print(f"This OTP will expire in 120 seconds ({expires_at}).")
        print("--------------------------\n")
        # In a real application, use libraries like SendGrid, Mailgun, Flask-Mail etc.
        # to send actual emails via an SMTP server or API.

        return jsonify({"message": "OTP sent successfully!"}), 200

    except mysql.connector.Error as err:
        conn.rollback() # Rollback changes in case of error
        print(f"Error sending OTP: {err}")
        return jsonify({"message": "Failed to send OTP", "error": str(err)}), 500
    finally:
        cursor.close()
        conn.close()


@app.route('/api/login/verify_otp', methods=['POST'])
def verify_otp():
    """
    Endpoint to verify the provided OTP.
    It checks the OTP against the database and its expiration time.
    """
    data = request.get_json()
    email = data.get('email')
    otp_entered = data.get('otp')

    if not email or not otp_entered:
        return jsonify({"message": "Email and OTP are required"}), 400

    conn = get_db_connection()
    if conn is None:
        return jsonify({"message": "Database connection failed"}), 500

    cursor = conn.cursor(dictionary=True) # Return results as dictionaries
    try:
        # Retrieve the latest OTP for the given email
        cursor.execute(
            "SELECT otp_code, expires_at FROM otps WHERE email = %s ORDER BY created_at DESC LIMIT 1",
            (email,)
        )
        otp_record = cursor.fetchone()

        if not otp_record:
            return jsonify({"message": "No OTP found for this email. Please request a new one."}), 404

        stored_otp = otp_record['otp_code']
        expires_at = otp_record['expires_at']

        # Check if OTP has expired
        if datetime.now() > expires_at:
            # Optionally, delete expired OTP
            cursor.execute("DELETE FROM otps WHERE email = %s", (email,))
            conn.commit()
            return jsonify({"message": "OTP has expired. Please request a new one."}), 401

        # Check if OTP matches
        if otp_entered == stored_otp:
            # OTP is valid, delete it from the database to prevent reuse
            cursor.execute("DELETE FROM otps WHERE email = %s", (email,))
            conn.commit()
            # In a real app, you would generate a JWT token here and send it to the client
            # The client would then store this token and send it with subsequent requests
            return jsonify({"message": "Login successful!"}), 200
        else:
            return jsonify({"message": "Invalid OTP. Please try again."}), 401

    except mysql.connector.Error as err:
        print(f"Error verifying OTP: {err}")
        return jsonify({"message": "Failed to verify OTP", "error": str(err)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/api/ngos', methods=['GET'])
def get_ngos():
    """
    Endpoint to fetch all registered NGOs with their names and logos.
    """
    conn = get_db_connection()
    if conn is None:
        return jsonify({"message": "Database connection failed"}), 500

    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id, name, logo_url FROM ngos ORDER BY name")
        ngos = cursor.fetchall()
        return jsonify(ngos), 200
    except mysql.connector.Error as err:
        print(f"Error fetching NGOs: {err}")
        return jsonify({"message": "Failed to fetch NGOs", "error": str(err)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/api/donors/total', methods=['GET'])
def get_total_donors():
    """
    Endpoint to fetch the total number of donors.
    """
    conn = get_db_connection()
    if conn is None:
        return jsonify({"message": "Database connection failed"}), 500

    cursor = conn.cursor()
    try:
        # In this simple implementation, we assume a single row in donor_counts table
        cursor.execute("SELECT total_donors FROM donor_counts WHERE id = 1")
        result = cursor.fetchone()
        total_donors = result[0] if result else 0
        return jsonify({"total_donors": total_donors}), 200
    except mysql.connector.Error as err:
        print(f"Error fetching total donors: {err}")
        return jsonify({"message": "Failed to fetch total donors", "error": str(err)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/api/ngo_requirements/<int:ngo_id>', methods=['GET'])
def get_ngo_requirements(ngo_id):
    """
    Endpoint to fetch requirements for a specific NGO, grouped by category.
    """
    conn = get_db_connection()
    if conn is None:
        return jsonify({"message": "Database connection failed"}), 500

    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT name FROM ngos WHERE id = %s", (ngo_id,))
        ngo_name_result = cursor.fetchone()
        if not ngo_name_result:
            return jsonify({"message": "NGO not found"}), 404
        ngo_name = ngo_name_result['name']

        cursor.execute(
            "SELECT category, item_name FROM ngo_requirements WHERE ngo_id = %s ORDER BY category, item_name",
            (ngo_id,)
        )
        requirements = cursor.fetchall()

        # Group requirements by category
        grouped_requirements = {}
        for req in requirements:
            category = req['category']
            if category not in grouped_requirements:
                grouped_requirements[category] = []
            grouped_requirements[category].append(req['item_name'])

        return jsonify({
            "ngo_id": ngo_id,
            "ngo_name": ngo_name,
            "requirements": grouped_requirements
        }), 200
    except mysql.connector.Error as err:
        print(f"Error fetching NGO requirements: {err}")
        return jsonify({"message": "Failed to fetch NGO requirements", "error": str(err)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/api/donate', methods=['POST'])
def handle_donation():
    """
    Handles donate, give away, and resale actions.
    Updates the donations table and donor count.
    """
    data = request.get_json()
    user_email = data.get('user_email') # Assuming email is passed from frontend after login
    ngo_id = data.get('ngo_id')
    action_type = data.get('action_type') # 'donate', 'giveaway', 'resale'
    selected_items = data.get('selected_items') # List of {'category': '...', 'item': '...', 'quantity': int}
    
    # Optional fields for 'resale'
    original_cost = data.get('original_cost')
    purchase_year = data.get('purchase_year')

    if not all([user_email, ngo_id, action_type, selected_items]):
        return jsonify({"message": "Missing required data"}), 400

    conn = get_db_connection()
    if conn is None:
        return jsonify({"message": "Database connection failed"}), 500

    cursor = conn.cursor()
    try:
        # Get user_id from email
        cursor.execute("SELECT id FROM users WHERE email = %s", (user_email,))
        user_result = cursor.fetchone()
        if not user_result:
            return jsonify({"message": "User not found"}), 404
        user_id = user_result[0]

        resale_amount = None
        if action_type == 'resale':
            if not all([original_cost, purchase_year]):
                return jsonify({"message": "Original cost and purchase year are required for resale"}), 400
            
            try:
                original_cost = float(original_cost)
                purchase_year = int(purchase_year)
            except ValueError:
                return jsonify({"message": "Invalid original cost or purchase year"}), 400

            current_year = datetime.now().year
            item_age = current_year - purchase_year

            if item_age <= 2:
                resale_percentage = 0.30
            elif item_age == 3:
                resale_percentage = 0.20
            else: # More than 3 years
                resale_percentage = 0.10
            
            resale_amount = original_cost * resale_percentage

        # Insert each selected item as a separate donation record
        for item_data in selected_items:
            item_category = item_data.get('category')
            item_name = item_data.get('item')
            quantity = item_data.get('quantity', 1)

            cursor.execute(
                """
                INSERT INTO donations 
                (user_id, ngo_id, action_type, item_category, item_name, quantity, original_cost, purchase_year, resale_amount, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'completed')
                """,
                (user_id, ngo_id, action_type, item_category, item_name, quantity, original_cost, purchase_year, resale_amount)
            )
        
        # Update donor count (simple increment, could be more sophisticated)
        # If a single user makes multiple donations, you might want a distinct count.
        cursor.execute(
            """
            INSERT INTO donor_counts (id, total_donors) VALUES (1, 1)
            ON DUPLICATE KEY UPDATE total_donors = total_donors + 1
            """
        )
        conn.commit()

        return jsonify({"message": f"Thank you for your {action_type}! Your contribution has been recorded."}), 200

    except mysql.connector.Error as err:
        conn.rollback()
        print(f"Error handling donation: {err}")
        return jsonify({"message": f"Failed to process {action_type}", "error": str(err)}), 500
    finally:
        cursor.close()
        conn.close()

# --- Run the Flask app ---
if __name__ == '__main__':
    # You can set these environment variables in your terminal before running:
    # export DB_HOST='localhost'
    # export DB_USER='root'
    # export DB_PASSWORD='your_password'
    # export DB_DATABASE='realpage_donations'
    
    # For development, you can run: flask run
    # For production, use a WSGI server like Gunicorn or uWSGI
    app.run(debug=True, port=5000)










# # app.py
# from flask import Flask, request, jsonify
# from flask_cors import CORS
# import mysql.connector
# from datetime import datetime, timedelta
# import random
# import os

# # Initialize Flask app
# # app = Flask(__name__)
# app = Flask(__name__, static_folder='static', static_url_path='')
# CORS(app) # Enable CORS for frontend communication

# # Database configuration (replace with your MySQL credentials)
# # It's recommended to use environment variables for production
# DB_CONFIG = {
#     'host': os.environ.get('DB_HOST', 'localhost'),
#     'user': os.environ.get('DB_USER', 'root'), # Replace with your MySQL username
#     'password': os.environ.get('DB_PASSWORD', 'sawan'), # Replace with your MySQL password
#     'database': os.environ.get('DB_DATABASE', 'realpage_donations')
# }

# # --- Database Connection Helper ---
# def get_db_connection():
#     """Establishes and returns a database connection."""
#     try:
#         conn = mysql.connector.connect(**DB_CONFIG)
#         return conn
#     except mysql.connector.Error as err:
#         print(f"Error connecting to MySQL: {err}")
#         return None

# # --- API Endpoints ---

# @app.route('/')
# def home():
#     """Simple home route to confirm API is running."""
#     return "Welcome to the Realpage Donations Backend API!"

# @app.route('/')
# def serve_react_app(): # The name doesn't matter, but the functionality does
#     """Serve the React app's index.html for the root URL."""
#     return send_from_directory(app.static_folder, 'index.html')


# @app.route('/api/login/send_otp', methods=['POST'])
# def send_otp():
#     """
#     Endpoint to send an OTP to the provided email.
#     It generates an OTP, stores it in the database with an expiration time,
#     and simulates sending an email.
#     """
#     data = request.get_json()
#     email = data.get('email')

#     if not email:
#         return jsonify({"message": "Email is required"}), 400

#     # Basic email domain validation for Realpage
#     if not email.endswith('@realpage.com'):
#         return jsonify({"message": "Only Realpage email IDs are allowed."}), 403

#     conn = get_db_connection()
#     if conn is None:
#         return jsonify({"message": "Database connection failed"}), 500

#     cursor = conn.cursor()
#     try:
#         # Check if user exists, if not, create them (or handle based on your user management)
#         cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
#         user_exists = cursor.fetchone()
#         if not user_exists:
#             cursor.execute("INSERT INTO users (email) VALUES (%s)", (email,))
#             conn.commit()
#             print(f"New user registered: {email}") # Log for demonstration

#         # Generate a 6-digit OTP
#         otp_code = str(random.randint(100000, 999999))
        
#         # Set OTP expiration time (120 seconds from now)
#         expires_at = datetime.now() + timedelta(seconds=120)

#         # Clear any existing OTPs for this email to ensure only one is active
#         cursor.execute("DELETE FROM otps WHERE email = %s", (email,))
        
#         # Store OTP in the database
#         cursor.execute(
#             "INSERT INTO otps (email, otp_code, expires_at) VALUES (%s, %s, %s)",
#             (email, otp_code, expires_at)
#         )
#         conn.commit()

#         # --- Simulate Email Sending (IMPORTANT: For production, integrate a real email service) ---
#         print(f"\n--- OTP for {email} ---")
#         print(f"Your OTP is: {otp_code}")
#         print(f"This OTP will expire in 120 seconds ({expires_at}).")
#         print("--------------------------\n")
#         # In a real application, use libraries like SendGrid, Mailgun, Flask-Mail etc.
#         # to send actual emails via an SMTP server or API.

#         return jsonify({"message": "OTP sent successfully!"}), 200

#     except mysql.connector.Error as err:
#         conn.rollback() # Rollback changes in case of error
#         print(f"Error sending OTP: {err}")
#         return jsonify({"message": "Failed to send OTP", "error": str(err)}), 500
#     finally:
#         cursor.close()
#         conn.close()


# @app.route('/api/login/verify_otp', methods=['POST'])
# def verify_otp():
#     """
#     Endpoint to verify the provided OTP.
#     It checks the OTP against the database and its expiration time.
#     """
#     data = request.get_json()
#     email = data.get('email')
#     otp_entered = data.get('otp')

#     if not email or not otp_entered:
#         return jsonify({"message": "Email and OTP are required"}), 400

#     conn = get_db_connection()
#     if conn is None:
#         return jsonify({"message": "Database connection failed"}), 500

#     cursor = conn.cursor(dictionary=True) # Return results as dictionaries
#     try:
#         # Retrieve the latest OTP for the given email
#         cursor.execute(
#             "SELECT otp_code, expires_at FROM otps WHERE email = %s ORDER BY created_at DESC LIMIT 1",
#             (email,)
#         )
#         otp_record = cursor.fetchone()

#         if not otp_record:
#             return jsonify({"message": "No OTP found for this email. Please request a new one."}), 404

#         stored_otp = otp_record['otp_code']
#         expires_at = otp_record['expires_at']

#         # Check if OTP has expired
#         if datetime.now() > expires_at:
#             # Optionally, delete expired OTP
#             cursor.execute("DELETE FROM otps WHERE email = %s", (email,))
#             conn.commit()
#             return jsonify({"message": "OTP has expired. Please request a new one."}), 401

#         # Check if OTP matches
#         if otp_entered == stored_otp:
#             # OTP is valid, delete it from the database to prevent reuse
#             cursor.execute("DELETE FROM otps WHERE email = %s", (email,))
#             conn.commit()
#             # In a real app, you would generate a JWT token here and send it to the client
#             # The client would then store this token and send it with subsequent requests
#             return jsonify({"message": "Login successful!"}), 200
#         else:
#             return jsonify({"message": "Invalid OTP. Please try again."}), 401

#     except mysql.connector.Error as err:
#         print(f"Error verifying OTP: {err}")
#         return jsonify({"message": "Failed to verify OTP", "error": str(err)}), 500
#     finally:
#         cursor.close()
#         conn.close()

# @app.route('/api/ngos', methods=['GET'])
# def get_ngos():
#     """
#     Endpoint to fetch all registered NGOs with their names and logos.
#     """
#     conn = get_db_connection()
#     if conn is None:
#         return jsonify({"message": "Database connection failed"}), 500

#     cursor = conn.cursor(dictionary=True)
#     try:
#         cursor.execute("SELECT id, name, logo_url FROM ngos ORDER BY name")
#         ngos = cursor.fetchall()
#         return jsonify(ngos), 200
#     except mysql.connector.Error as err:
#         print(f"Error fetching NGOs: {err}")
#         return jsonify({"message": "Failed to fetch NGOs", "error": str(err)}), 500
#     finally:
#         cursor.close()
#         conn.close()

# @app.route('/api/donors/total', methods=['GET'])
# def get_total_donors():
#     """
#     Endpoint to fetch the total number of donors.
#     """
#     conn = get_db_connection()
#     if conn is None:
#         return jsonify({"message": "Database connection failed"}), 500

#     cursor = conn.cursor()
#     try:
#         # In this simple implementation, we assume a single row in donor_counts table
#         cursor.execute("SELECT total_donors FROM donor_counts WHERE id = 1")
#         result = cursor.fetchone()
#         total_donors = result[0] if result else 0
#         return jsonify({"total_donors": total_donors}), 200
#     except mysql.connector.Error as err:
#         print(f"Error fetching total donors: {err}")
#         return jsonify({"message": "Failed to fetch total donors", "error": str(err)}), 500
#     finally:
#         cursor.close()
#         conn.close()

# @app.route('/api/ngo_requirements/<int:ngo_id>', methods=['GET'])
# def get_ngo_requirements(ngo_id):
#     """
#     Endpoint to fetch requirements for a specific NGO, grouped by category.
#     """
#     conn = get_db_connection()
#     if conn is None:
#         return jsonify({"message": "Database connection failed"}), 500

#     cursor = conn.cursor(dictionary=True)
#     try:
#         cursor.execute("SELECT name FROM ngos WHERE id = %s", (ngo_id,))
#         ngo_name_result = cursor.fetchone()
#         if not ngo_name_result:
#             return jsonify({"message": "NGO not found"}), 404
#         ngo_name = ngo_name_result['name']

#         cursor.execute(
#             "SELECT category, item_name FROM ngo_requirements WHERE ngo_id = %s ORDER BY category, item_name",
#             (ngo_id,)
#         )
#         requirements = cursor.fetchall()

#         # Group requirements by category
#         grouped_requirements = {}
#         for req in requirements:
#             category = req['category']
#             if category not in grouped_requirements:
#                 grouped_requirements[category] = []
#             grouped_requirements[category].append(req['item_name'])

#         return jsonify({
#             "ngo_id": ngo_id,
#             "ngo_name": ngo_name,
#             "requirements": grouped_requirements
#         }), 200
#     except mysql.connector.Error as err:
#         print(f"Error fetching NGO requirements: {err}")
#         return jsonify({"message": "Failed to fetch NGO requirements", "error": str(err)}), 500
#     finally:
#         cursor.close()
#         conn.close()

# @app.route('/api/donate', methods=['POST'])
# def handle_donation():
#     """
#     Handles donate, give away, and resale actions.
#     Updates the donations table and donor count.
#     """
#     data = request.get_json()
#     user_email = data.get('user_email') # Assuming email is passed from frontend after login
#     ngo_id = data.get('ngo_id')
#     action_type = data.get('action_type') # 'donate', 'giveaway', 'resale'
#     selected_items = data.get('selected_items') # List of {'category': '...', 'item': '...', 'quantity': int}
    
#     # Optional fields for 'resale'
#     original_cost = data.get('original_cost')
#     purchase_year = data.get('purchase_year')

#     if not all([user_email, ngo_id, action_type, selected_items]):
#         return jsonify({"message": "Missing required data"}), 400

#     conn = get_db_connection()
#     if conn is None:
#         return jsonify({"message": "Database connection failed"}), 500

#     cursor = conn.cursor()
#     try:
#         # Get user_id from email
#         cursor.execute("SELECT id FROM users WHERE email = %s", (user_email,))
#         user_result = cursor.fetchone()
#         if not user_result:
#             return jsonify({"message": "User not found"}), 404
#         user_id = user_result[0]

#         resale_amount = None
#         if action_type == 'resale':
#             if not all([original_cost, purchase_year]):
#                 return jsonify({"message": "Original cost and purchase year are required for resale"}), 400
            
#             try:
#                 original_cost = float(original_cost)
#                 purchase_year = int(purchase_year)
#             except ValueError:
#                 return jsonify({"message": "Invalid original cost or purchase year"}), 400

#             current_year = datetime.now().year
#             item_age = current_year - purchase_year

#             if item_age <= 2:
#                 resale_percentage = 0.30
#             elif item_age == 3:
#                 resale_percentage = 0.20
#             else: # More than 3 years
#                 resale_percentage = 0.10
            
#             resale_amount = original_cost * resale_percentage

#         # Insert each selected item as a separate donation record
#         for item_data in selected_items:
#             item_category = item_data.get('category')
#             item_name = item_data.get('item')
#             quantity = item_data.get('quantity', 1)

#             cursor.execute(
#                 """
#                 INSERT INTO donations 
#                 (user_id, ngo_id, action_type, item_category, item_name, quantity, original_cost, purchase_year, resale_amount, status)
#                 VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'completed')
#                 """,
#                 (user_id, ngo_id, action_type, item_category, item_name, quantity, original_cost, purchase_year, resale_amount)
#             )
        
#         # Update donor count (simple increment, could be more sophisticated)
#         # This assumes a new unique donor for each transaction.
#         # If a single user makes multiple donations, you might want a distinct count.
#         cursor.execute(
#             """
#             INSERT INTO donor_counts (id, total_donors) VALUES (1, 1)
#             ON DUPLICATE KEY UPDATE total_donors = total_donors + 1
#             """
#         )
#         conn.commit()

#         return jsonify({"message": f"Thank you for your {action_type}! Your contribution has been recorded."}), 200

#     except mysql.connector.Error as err:
#         conn.rollback()
#         print(f"Error handling donation: {err}")
#         return jsonify({"message": f"Failed to process {action_type}", "error": str(err)}), 500
#     finally:
#         cursor.close()
#         conn.close()

# # --- Run the Flask app ---
# if __name__ == '__main__':
#     # You can set these environment variables in your terminal before running:
#     # export DB_HOST='localhost'
#     # export DB_USER='root'
#     # export DB_PASSWORD='your_password'
#     # export DB_DATABASE='realpage_donations'
    
#     # For development, you can run: flask run
#     # For production, use a WSGI server like Gunicorn or uWSGI
#     app.run(debug=True, port=5000)

