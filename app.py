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
    
    if 'message' not in session:
        session['message'] = 'There is an update on the website! you can now select your name from the list, try it now'  # Set the one-time message in the session

    message = session.pop('message', None)  # Retrieve and remove the message from the session
    
    firstnames = db.users.find({}, {'fname': 1})
    surnames = db.users.find({}, {'sname': 1})
    fnames = [doc['fname'] for doc in firstnames]
    snames = [doc['sname'] for doc in surnames]
    
    adminfirstnames = db.admins.find({}, {'fname': 1})
    adminsurnames = db.admins.find({}, {'sname': 1})
    adminfnames = [doc['fname'] for doc in adminfirstnames]
    adminsnames = [doc['sname'] for doc in adminsurnames]
    return render_template("index.html",fnames=fnames,snames=snames,adminfnames=adminfnames,adminsnames=adminsnames,message=message)

@app.route("/login", methods=["POST"])
def login():
    f_name = request.form.get('fname')
    s_name = request.form.get('sname')
    entered_password = request.form.get('password')
    f_name = f_name.strip()
    s_name = s_name.strip()
    
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
            your_record = df_filled[(df_filled.iloc[:, 0] == f_name) & (df_filled.iloc[:, 1] == s_name)]
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
    f_name = request.form.get('adminfname')
    s_name = request.form.get('adminsname')
    entered_password = request.form.get('adminpassword')
    f_name = f_name.strip()
    s_name = s_name.strip()
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
    print("Reached the /record_payment route")
    if 'userIDadmin' in session:
        return render_template("make records.html")
    
@app.route('/record_payment_template',methods=["POST"])
def payment():
    fname = request.form.get('f_name')
    sname = request.form.get('s_name')
    month = request.form.get('month')
    amount = request.form.get('amount')
    fname = fname.strip()
    sname = sname.strip()
    
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
    f_name = request.form.get('fname')
    s_name = request.form.get('sname')
    password1 = request.form.get('password1')
    password2 = request.form.get('password2')
    f_name = f_name.strip()
    s_name = s_name.strip()
    
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
                user = {'membership_id': club_member['_id'],'fname': f_name, 'sname': s_name, 'password': hashed_password}
                db.users.insert_one(user)
                flash('Member registered')
                return redirect('/registration')
            else:
                flash('Member already registered')
                return redirect('/registration')

if __name__ == '__main__':
    app.run()
