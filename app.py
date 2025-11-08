from flask import Flask, request, jsonify, render_template, redirect, url_for,session,flash
from db_config import get_db_connection
from werkzeug.security import generate_password_hash, check_password_hash
from decimal import Decimal
import decimal
import datetime
import traceback
app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/stats')
def stats():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 1) 
        cursor.execute("""
            SELECT a.category, COALESCE(SUM(ua.total_emission), 0)
            FROM activities a
            LEFT JOIN user_activity ua 
              ON a.activity_id = ua.activity_id AND ua.user_id = %s
            GROUP BY a.category
            ORDER BY a.category
        """, (user_id,))
        cat_rows = cursor.fetchall()
        
        categories = [row[0] if row[0] is not None else 'Unknown' for row in cat_rows]
        emissions = [float(row[1]) if row[1] is not None else 0.0 for row in cat_rows]

        # 2)
        cursor.execute("""
            SELECT DATE(ua.activity_date) AS day, SUM(ua.total_emission) AS total
            FROM user_activity ua
            WHERE ua.user_id = %s
            GROUP BY DATE(ua.activity_date)
            ORDER BY DATE(ua.activity_date) ASC
        """, (user_id,))
        daily_rows = cursor.fetchall()
        dates = []
        daily_emissions = []
        for row in daily_rows:
            raw_date = row[0]
            raw_total = row[1]
            
            if isinstance(raw_date, (datetime.date, datetime.datetime)):
                dates.append(raw_date.strftime('%Y-%m-%d'))
            elif raw_date is None:
                dates.append('unknown')
            else:
                dates.append(str(raw_date))
            daily_emissions.append(float(raw_total) if raw_total is not None else 0.0)

        # 3) 
        
        cursor.execute("""
            SELECT a.activity_name, SUM(ua.total_emission) AS total
            FROM activities a
            JOIN user_activity ua ON a.activity_id = ua.activity_id
            WHERE ua.user_id = %s
            GROUP BY a.activity_name
            ORDER BY total DESC
            LIMIT 5
        """, (user_id,))
        top_rows = cursor.fetchall()
        top_activities = [row[0] if row[0] is not None else 'Unknown' for row in top_rows]
        top_emissions = [float(row[1]) if row[1] is not None else 0.0 for row in top_rows]

        # 4) 
        cursor.execute("""
            SELECT 
              a.category,
              SUM(CASE WHEN ua.user_id = %s THEN ua.total_emission ELSE 0 END) AS user_emission,
              CASE WHEN COUNT(DISTINCT ua.user_id) = 0 THEN 0
                   ELSE SUM(ua.total_emission)::float / NULLIF(COUNT(DISTINCT ua.user_id),0)
              END AS avg_emission
            FROM activities a
            LEFT JOIN user_activity ua ON a.activity_id = ua.activity_id
            GROUP BY a.category
            ORDER BY a.category
        """, (user_id,))
        comp_rows = cursor.fetchall()
        compare_categories = [row[0] if row[0] is not None else 'Unknown' for row in comp_rows]
        user_emission_list = [float(row[1]) if row[1] is not None else 0.0 for row in comp_rows]
        avg_emission_list = [float(row[2]) if row[2] is not None else 0.0 for row in comp_rows]

        # 5) 
        cursor.execute("""
            SELECT user_id, SUM(total_emission) AS total_emission
            FROM user_activity
            GROUP BY user_id
            ORDER BY total_emission DESC
        """)
        ranking_rows = cursor.fetchall()
        rank = None
        total_users = len(ranking_rows)
        for i, row in enumerate(ranking_rows):
            try:
                uid = row[0]
            except Exception:
                continue
            if uid == user_id:
                rank = i + 1
                break

        
        cursor.close()
        conn.close()

        return render_template(
            'stats.html',
            categories=categories,
            emissions=emissions,
            dates=dates,
            daily_emissions=daily_emissions,
            top_activities=top_activities,
            top_emissions=top_emissions,
            compare_categories=compare_categories,
            user_emission=user_emission_list,
            avg_emission=avg_emission_list,
            rank=rank,
            total_users=total_users
        )

    except Exception as e:
        
        print("Error in /stats route:", e)
        traceback.print_exc()

        
        flash("An error occurred while loading statistics. Check server logs for details.", "danger")

        
        try:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
        except Exception:
            pass

        return redirect(url_for('dashboard'))
        
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        print(f"Entered email: {email}")
        print(f"Entered password: {password}")

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, name, email, password FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        print(f"🟢 User fetched from DB: {user}")

        if user and check_password_hash(user[3], password):
            session['user_id'] = user[0]
            session['user_name'] = user[1]
            print("✅ Login successful")
            return redirect(url_for('dashboard'))
        else:
            print("❌ Password mismatch or user not found.")
            flash("❌ Invalid email or password!")
            return render_template('login.html')

    return render_template('login.html')

  


@app.route('/reg')
def register():
    return render_template('reg.html')


@app.route('/dash')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor()

    
    cursor.execute("""
        SELECT ua.activity_id, ua.total_emission
        FROM user_activity ua
        JOIN activities a ON ua.activity_id = a.activity_id
        WHERE ua.user_id = %s
    """, (user_id,))
    rows = cursor.fetchall()

    
    transport_total = 0
    energy_total = 0
    food_total = 0
    daily_total = 0

    
    for row in rows:
        activity_id = row[0]
        emission = float(row[1])

        if 1 <= activity_id <= 4:
            transport_total += emission
        elif 5 <= activity_id <= 6:
            energy_total += emission
        elif 7 <= activity_id <= 8:
            food_total += emission
        else:
            daily_total += emission

    conn.close()

    return render_template(
        'dash.html',
        transport_total=transport_total,
        energy_total=energy_total,
        food_total=food_total,
        daily_total=daily_total
    )




@app.route('/add')
def add():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT activity_id, activity_name, unit FROM activities ORDER BY activity_id;")
    activities = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template('add.html', activities=activities)


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('user_name', None)
    return redirect(url_for('login'))



@app.route('/register', methods=['POST'])
def register_user():
    data = request.form
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')

   

    if not name or not email or not password:
        return "Missing fields", 400

    hashed_password = generate_password_hash(password)

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (name, email, password) VALUES (%s, %s, %s) RETURNING user_id",
            (name, email, hashed_password)
        )
        user_id = cursor.fetchone()[0]
        conn.commit()
        cursor.close()
        conn.close()

        flash("✅ Registered successfully! You can now log in.")
        return render_template('reg.html')

    except Exception as e:
        print("Error inserting user:", e)
        flash("❌ Registration failed. Try again.", "error")
        return render_template('reg.html')


@app.route('/add_activity', methods=['POST'])
def add_user_activity():
    
    if 'user_id' not in session:
        return redirect(url_for('login'))

    
    user_id = session['user_id']
    data = request.form
    activity_id = data.get('activity_id')
    quantity = float(data.get('quantity', 0))
    notes = data.get('notes', None)

    
    conn = get_db_connection()
    cursor = conn.cursor()

    
    cursor.execute("SELECT emission_factor FROM activities WHERE activity_id = %s", (activity_id,))
    row = cursor.fetchone()

    if not row:
        cursor.close()
        conn.close()
        return "Activity not found", 400

    emission_factor = float(row[0])
    total_emission = quantity * emission_factor

    
    cursor.execute("""
        INSERT INTO user_activity (user_id, activity_id, quantity, total_emission, activity_date, notes)
        VALUES (%s, %s, %s, %s, NOW(), %s)
    """, (user_id, activity_id, quantity, total_emission, notes))

    conn.commit()
    cursor.close()
    conn.close()

    
    return redirect(url_for('dashboard'))

@app.route('/solutions')
def solutions():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 
            a.category,
            SUM(ua.total_emission) AS total_emission
        FROM activities a
        JOIN user_activity ua ON a.activity_id = ua.activity_id
        WHERE ua.user_id = %s AND a.category != 'Water'
        GROUP BY a.category
        HAVING SUM(ua.total_emission) > 0
    """, (user_id,))
    
    user_data = cursor.fetchall()

    sustainable_limits = {
        "Transportation": 1.8,
        "Electricity": 1.5,
        "Food": 2.0,
        "Waste": 0.7
    }

    recommendations = {
        "Transportation": "Try carpooling, use public transport, or cycle short distances.",
        "Electricity": "Switch to LED bulbs, unplug idle devices, and reduce AC/heater use.",
        "Food": "Eat more local and plant-based foods. Reduce meat and dairy consumption.",
        "Waste": "Compost organic waste and reduce single-use plastics.",
    }

    comparison = []
    total_emission = 0.0

    for category, emission in user_data:
        emission = float(emission) if emission is not None else 0.0
        total_emission += emission
        limit = sustainable_limits.get(category, 0.0)
        difference = emission - limit

        if emission == 0:
            status = "— No data yet"
            suggestion = "Add your activities to see insights."
            reduction_msg = ""
        elif emission <= limit:
            status = "✅ Within Limit"
            suggestion = recommendations.get(category, "Keep up your eco-friendly habits!")
            reduction_msg = ""
        else:
            status = "⚠️ Exceeds Limit"
            suggestion = recommendations.get(category, "Try reducing your carbon footprint in this area.")
            reduction_msg = f"Reduce by {round(difference, 2)} kg CO₂ to reach the goal."

        comparison.append({
            "category": category,
            "emission": round(emission, 2),
            "limit": limit,
            "status": status,
            "suggestion": suggestion,
            "reduction_msg": reduction_msg
        })

    cursor.close()
    conn.close()

    return render_template('solutions.html', comparison=comparison)




if __name__ == '__main__':
    app.run(debug=True)
