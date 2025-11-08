import psycopg2

def get_db_connection():
    conn = psycopg2.connect(
        host="localhost",
        database="carbon_tracker",
        user="postgres",
        password="Navya@123"  # 🔹 replace with your actual password
    )
    return conn
