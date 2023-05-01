from flask import Flask, render_template, request, redirect, url_for, session, flash
import secrets
import datetime
import io
import base64
import pandas as pd
import requests
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt

app = Flask(__name__, static_folder='static')

app.secret_key = secrets.token_hex(16)

@app.route("/")
def index():
   return render_template("index.html")

@app.route("/",methods=["GET","POST"])
def login():
   sheet_id = '1GjX5JtXysgmX7eFSUZBJ3dv8whBcQmxYQuNI5Be448w'
   xls_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=xlsx"

   response = requests.get(xls_url)
   with open('spreadsheet.xlsx', 'wb') as f:
      f.write(response.content)
   records = pd.read_excel('spreadsheet.xlsx')
   fname = request.form['fname']
   sname = request.form['sname']
   name = sname+' '+fname
   
   username = name.upper()

   if username in map(str.upper, records.iloc[:, 0].values):
      flash('Login was successful')
      session.permanent = False
      session['username'] = username
      return redirect(url_for('profile',username=username))
   else:
      flash('Check membership name and try again')
      return render_template('index.html')

@app.route("/sugdata")
def profile():
   
   username = request.args.get('username')
   records = pd.read_excel('spreadsheet.xlsx')
      
   your_record = records[(records.iloc[:, 0] == username) & (records.iloc[:, -1] != 0)]
   your_table_html = your_record.to_html(classes="table")
      
   row_sums = np.sum(records.iloc[:18, 1:13], axis=1)
   fig1, ax1 = plt.subplots()
   ax1 = sns.barplot(x=records.NAME, y=row_sums, data=records)
   plt.xticks(rotation=90)
   xticks = range(len(records.iloc[:18,0]))
   xticklabels = records.iloc[:-1, 0]
   ax1.set_xticks(xticks)
   ax1.set_xticklabels(xticklabels)
   plt.title("Chart for member's saving contributions")
   plt.ylabel('Amount in UGX')
   plt.xlabel('Member')

   for p in ax1.patches:
      ax1.annotate(f"{p.get_height():.0f}", (p.get_x() + p.get_width() / 2., p.get_height()),
                   ha='center', va='center', fontsize=6, color='black', xytext=(0, 5),
                   textcoords='offset points')
      
   col_sums = records.iloc[:18, 1:13].sum()
   col_sums
   fig2, ax2 = plt.subplots()
   ax2 = sns.barplot(x = col_sums.index, y=col_sums)
   plt.xticks(rotation=90)
   xticks2 = range(len(records.iloc[0,:13]))
   xticklabels2 = records.iloc[0, :-1]
   ax1.set_xticks(xticks2)
   ax1.set_xticklabels(xticklabels2)
   plt.title("Chart for monthly savings")
   plt.ylabel('Amount in UGX')
   plt.xlabel('Month')

   for p in ax2.patches:
      ax2.annotate(f"{p.get_height():.0f}", (p.get_x() + p.get_width() / 2., p.get_height()),
                   ha='center', va='center', fontsize=6, color='black', xytext=(0, 5),
                   textcoords='offset points')
      
   buffer1 = io.BytesIO()
   fig1.savefig(buffer1,format='png',bbox_inches='tight')
   buffer1.seek(0)
   chart1_png = base64.b64encode(buffer1.getvalue()).decode('utf-8')
   buffer1.close()
      
   buffer2 = io.BytesIO()
   fig2.savefig(buffer2,format='png',bbox_inches='tight')
   buffer2.seek(0)
   chart2_png = base64.b64encode(buffer2.getvalue()).decode('utf-8')
   buffer2.close()
      
   return render_template("sug_data.html",image1=chart1_png,image2=chart2_png,username=username,your_table_html=your_table_html)

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('index'))

@app.before_request
def before_request():
    session.permanent = True
    app.permanent_session_lifetime = datetime.timedelta(minutes=5)
    session.modified = True

if __name__ == "__main__":
    app.run(debug=True)