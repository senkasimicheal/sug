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
    email = request.form.get('email')
    entered_password = request.form.get('password')
    
    password = entered_password.encode('utf-8')
    
    user = db.users.find_one({'email':email})
    if user is None:
        flash('Wrong username')
        return redirect('/')
    else:
        stored_password = user['password']
        f_name = user['fname']
        s_name = user['sname']
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
            
            capitalized_documents = []
            for document in ordered_documents:
                capitalized_document = {}
                for key, value in document.items():
                    if isinstance(value, str):
                        capitalized_document[key.capitalize()] = value.capitalize()
                    else:
                        capitalized_document[key.capitalize()] = value
                capitalized_documents.append(capitalized_document)

            df = pd.DataFrame(capitalized_documents)
            df_filled = df.fillna(0)       
            your_record = df_filled[(df_filled.iloc[:, 0] == f_name.capitalize()) & (df_filled.iloc[:, 1] == s_name.capitalize())]
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

@app.route("/record_payment_login",methods=["GET","POST"])
def record_payment_login():
    adminemail = request.form.get('adminemail')
    entered_password = request.form.get('adminpassword')
    password = entered_password.encode('utf-8')
    
    user = db.admins.find_one({'email':adminemail})
    if user is None:
        flash('Wrong username')
        return redirect('/')
    else:
        stored_password = user['password'].encode('utf-8')
        userIDadmin = str(user['_id'])
        if bcrypt.checkpw(password, stored_password):
            session.permanent = False
            session['userIDadmin'] = userIDadmin
            return redirect('/record_payment')
        else:
            flash('Wrong Password')
            return redirect('/')

@app.route('/logoutAdmin')
def logoutAdmin():
    session.pop('userIDadmin', None)
    return redirect(url_for('index'))

@app.route('/record_payment',methods=["GET","POST"])
def get_payment_template():
    if 'userIDadmin' in session:
        firstnames = db.records.find({}, {'fname': 1})
        surnames = db.records.find({}, {'sname': 1})
        fnames = [doc['fname'] for doc in firstnames]
        snames = [doc['sname'] for doc in surnames]
        return render_template("make records.html",fnames=fnames,snames=snames)
    
@app.route('/record_payment_template',methods=["POST"])
def payment():
    fname = request.form.get('f_name')
    sname = request.form.get('s_name')
    month = request.form.get('month')
    amount = request.form.get('amount')
    
    amount = int(amount)
    
    db.records.create_index([('fname', 1), ('sname', 1)], unique=True)
    result = db.records.find_one({'fname': fname, 'sname': sname})
    if result:
        month_amount = result.get(month, None)
        if month_amount is not None:
            if month_amount == 30000:
                flash('Month already updated')
                return redirect('/record_payment')
            elif month_amount < 30000:
                db.records.update_one({'fname': fname, 'sname': sname}, {'$set': {month: amount}})
                flash('Record updated')
                return redirect('/record_payment')
        else:
            db.records.update_one({'fname': fname, 'sname': sname}, {'$set': {month: amount}})
            flash('Record updated')
            return redirect('/record_payment')
    else:
        flash('Entered name is not in member documents')
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
    
    capitalized_documents = []
    for document in ordered_documents:
        capitalized_document = {}
        for key, value in document.items():
            if isinstance(value, str):
                capitalized_document[key.capitalize()] = value.capitalize()
            else:
                capitalized_document[key.capitalize()] = value
        capitalized_documents.append(capitalized_document)
                
    df = pd.DataFrame(capitalized_documents)
    csv_data = df.to_csv(index=False)
    response = Response(csv_data, mimetype='text/csv')
    response.headers['Content-Disposition'] = 'attachment; filename=sug_financial_records.csv'

    return response

@app.route('/registration',methods=["GET", "POST"])
def register_page():
    return render_template("registration.html")
    
@app.route('/registration_page', methods=["GET","POST"])
def register():
    f_name = request.form.get('fname')
    s_name = request.form.get('sname')
    email = request.form.get('email')
    email1 = request.form.get('email1')
    password1 = request.form.get('password1')
    password2 = request.form.get('password2')
    f_name = f_name.strip()
    s_name = s_name.strip()
    
    if email != email1:
        flash('Emails do not match')
        return redirect('/registration')
    else:
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
                    user = {'membership_id': club_member['_id'], 'email': email, 'fname': f_name, 'sname': s_name, 'password': hashed_password}
                    db.users.insert_one(user)
                    flash('Member registered')
                    return redirect('/registration')
                else:
                    flash('Member already registered')
                    return redirect('/registration')

if __name__ == '__main__':
    app.run()
