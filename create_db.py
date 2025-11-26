import mysql.connector
from configs import db_host, db_password, db_user, db_name

try:
    mydb = mysql.connector.connect(
        host=db_host,
        user=db_user,
        port=3306,
        password=db_password,
        auth_plugin='caching_sha2_password'
    )
    
    mycursor = mydb.cursor()

    mycursor.execute(f"CREATE DATABASE {db_name}")
    print(f"Database {db_name} created")
    
except Exception as err:
    print("There was an error creating the database: ", err)