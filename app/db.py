import psycopg2
 
def get_connection():  # creates a fresh connection each time it's called
    return psycopg2.connect(
        host="localhost",  # the app and Postgres run on the same Linux VM
        port=5432,
        dbname="banking",
        user="postgres",
        password="bankpass123",
    )
