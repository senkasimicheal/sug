from flask import Flask, jsonify, render_template, send_file, flash, session, redirect, request, url_for
import secrets
from bson import ObjectId
from pymongo import MongoClient
import bcrypt
import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
from flask import Response
import io
import base64

app = Flask(__name__, static_folder='static')
app.secret_key = secrets.token_hex(16)
client = MongoClient('mongodb+srv://micheal:QCKh2uCbPTdZ5sqS@cluster0.rivod.mongodb.net/SUG?retryWrites=true&w=majority')
db = client.SUG

desired_order = ["_id", "fname", "sname", "january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"]

@app.route("/", methods=["GET", "POST"])
def index():
   return render_template("index.html")

@app.route("/login", methods=["POST"])
def login():
    fname = request.form.get('fname')
    sname = request.form.get('sname')
    entered_password = request.form.get('password')
    fname = fname.strip()
    sname = sname.strip()
    
    f_name = fname.lower()
    s_name = sname.lower()
    
    password = entered_password.encode('utf-8')
    
    user = db.users.find_one({'fname':f_name, 'sname':s_name})
    if user is None:
        flash('Wrong username')
        return redirect('/')
    else:
        stored_password = user['password']
        userID = str(user['_id'])
        if bcrypt.checkpw(password, stored_password):
            documents = db.records.find({}, {'_id': 0, 'fname': 1, 'sname': 1, 'january': 1, 'february': 1,
                                        'march': 1, 'april': 1, 'may': 1, 'june': 1, 'july': 1, 'august': 1,
                                        'september': 1, 'october': 1, 'november': 1, 'december': 1})
            ordered_documents = []
            for document in documents:
                ordered_document = {}
                sorted_keys = sorted(document.keys(), key=lambda k: desired_order.index(k) if k in desired_order else float('inf'))
                for key in sorted_keys:
                    ordered_document[key] = document[key]
                ordered_documents.append(ordered_document)
            df = pd.DataFrame(ordered_documents)
            df_filled = df.fillna(0)       
            your_record = df_filled[(df_filled.iloc[:, 0] == fname) & (df_filled.iloc[:, 1] == sname)]
            table_html = your_record.to_html(classes="table")
            session.permanent = False
            session['userID'] = userID
            return render_template("your_record.html",table_html=table_html)
        else:
            flash('Wrong Password')
            return redirect('/')

@app.route('/logout')
def logout():
    session.pop('userID', None)
    return redirect(url_for('index'))

@app.route("/record_payment_login",methods=["POST"])
def record_payment_login():
    fname = request.form.get('adminfname')
    sname = request.form.get('adminsname')
    entered_password = request.form.get('adminpassword')
    
    fname = fname.strip()
    sname = sname.strip()
    f_name = fname.lower()
    s_name = sname.lower()
    password = entered_password.encode('utf-8')
    
    user = db.admins.find_one({'fname':f_name, 'sname':s_name})
    if user is None:
        flash('Wrong username')
        return redirect('/')
    else:
        stored_password = user['password'].encode('utf-8')
        userIDadmin = str(user['_id'])
        if bcrypt.checkpw(password, stored_password):
            session.permanent = False
            session['userIDadmin'] = userIDadmin
            return render_template("make records.html")
        else:
            flash('Wrong Password')
            return redirect('/')

@app.route('/logoutAdmin')
def logoutAdmin():
    session.pop('userIDadmin', None)
    return redirect(url_for('index'))

@app.route('/record_payment',methods=["GET","POST"])
def payment():
    fname = request.form.get('fname')
    sname = request.form.get('sname')
    month = request.form.get('month')
    amount = request.form.get('amount')
    f_name = fname.lower()
    s_name = sname.lower()
    
    if amount > 30000:
        flash('value should be lower or equal to 30000')
        return redirect('/record_payment')
    
    db.records.create_index([('fname', 1), ('sname', 1)], unique=True)
    result = db.records.find_one({'fname': f_name, 'sname': s_name})
    if result:
        if result[month] == 30000:
            flash('Month already updated')
            return redirect('/record_payment')
        elif result[month] < 30000:
            db.records.update_one({'fname': f_name, 'sname': s_name}, {'$set': {month: amount}})
            flash('Record updated')
            return redirect('/record_payment')
    else:
        user_record = {'fname': f_name, 'sname': s_name, month: amount}
        db.records.update_one({'fname': f_name, 'sname': s_name}, {'$set': user_record}, upsert=True)
        flash('Record created')
        return redirect('/record_payment')

@app.route("/download_csv", methods=["GET"])
def download_csv():
    documents = db.records.find({}, {'_id': 0, 'fname': 1, 'sname': 1, 'january': 1, 'february': 1,
                                        'march': 1, 'april': 1, 'may': 1, 'june': 1, 'july': 1, 'august': 1,
                                        'september': 1, 'october': 1, 'november': 1, 'december': 1})
    ordered_documents = []
    for document in documents:
        ordered_document = {}
        sorted_keys = sorted(document.keys(), key=lambda k: desired_order.index(k) if k in desired_order else float('inf'))
        for key in sorted_keys:
            ordered_document[key] = document[key]
        ordered_documents.append(ordered_document)
    df = pd.DataFrame(ordered_documents)
    csv_data = df.to_csv(index=False)
    response = Response(csv_data, mimetype='text/csv')
    response.headers['Content-Disposition'] = 'attachment; filename=sug_financial_records.csv'

    return response

@app.route('/registration',methods=["GET", "POST"])
def register_page():
    return render_template("registration.html")
    
@app.route('/registration_page', methods=["GET","POST"])
def register():
    fname = request.form.get('fname')
    sname = request.form.get('sname')
    password1 = request.form.get('password1')
    password2 = request.form.get('password2')
    f_name = fname.lower()
    s_name = sname.lower()
    
    if password1 != password2:
        flash('Passwords do not match')
        return redirect('/registration')
    else:
        club_member = db.members.find_one({'fname':f_name, 'sname':s_name})
    
        if club_member is None:
            flash('Not member of the club')
            return redirect('/registration')
        else:
            member_registered = db.users.find_one({'membership_id': club_member['_id']})
            if member_registered is None:
                hashed_password = bcrypt.hashpw(password2.encode('utf-8'), bcrypt.gensalt())
                user = {'membership_id': club_member['_id'],'fname': fname, 'sname': sname, 'password': hashed_password}
                db.users.insert_one(user)
                flash('Member registered')
                return redirect('/registration')
            else:
                flash('Member already registered')
                return redirect('/registration')

if __name__ == '__main__':
    app.run()
