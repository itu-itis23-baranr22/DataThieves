from flask import Flask,render_template,flash,redirect,url_for,session,logging,request
from flask_mysqldb import MySQL
import mysql.connector
from mysql.connector import Error

app = Flask(__name__)


mysql = MySQL(app)
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/tables")
def tables():
    return render_template("tables.html")

if __name__ == "__main__":

    app.run(debug=True)
