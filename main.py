from flask import Flask,render_template,flash,redirect,url_for,session,logging,request
from flask_mysqldb import MySQL
import mysql.connector
from mysql.connector import Error

app = Flask(__name__)


mysql = MySQL(app)


if __name__ == "__main__":
    app.run(debug=True)