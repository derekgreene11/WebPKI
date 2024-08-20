import threading
from flask import Flask, render_template
import pymysql
import whois
import websocket
import asyncio
import json
import subprocess
import time
import os
import re
from datetime import datetime
import pymysql
from dotenv import load_dotenv, find_dotenv

app = Flask(__name__)

load_dotenv(find_dotenv())

host = os.environ.get("DB_HOST")
user = os.environ.get("DB_USER")
passwd = os.environ.get("DB_PASSWD")
db = os.environ.get("DB_NAME")

def connect_to_database(host=host, user=user, passwd=passwd, db=db):
    db_connection = pymysql.connect(host=host, user=user, password=passwd, database=db, cursorclass=pymysql.cursors.DictCursor)
    print("Connected to SQL database")
    return db_connection

def execute_query(db_connection=None, query=None, query_params=()):
    cursor = db_connection.cursor()
    cursor.execute(query, query_params)
    db_connection.commit()
    return cursor

@app.route('/')
def home():
    db_connection = connect_to_database()
    query = "SELECT COUNT(*) AS total_records FROM domains_data;"
    cursor = execute_query(db_connection=db_connection, query=query)
    result = cursor.fetchone()
    total_records = result['total_records']
    db_connection.close()
    return render_template('index.html', total_records=total_records)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=81, debug=True)
