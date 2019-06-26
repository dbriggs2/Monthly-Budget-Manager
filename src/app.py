from flask import Flask
from flask import request
from flask import render_template
from decimal import Decimal
import sqlite3
import sys
import json

app = Flask(__name__)

def init_tables(db_name):
	conn = sqlite3.connect(db_name)
	c = conn.cursor
	c.execute("""CREATE TABLE IF NOT EXISTS monthlyVariableExpenses(startingDate DATE PRIMARY KEY,spendingCategory VARCHAR(32), spendingAmount FLOAT(2));
				 CREATE TABLE IF NOT EXISTS monthlyVariableIncome(startingDate DATE PRIMARY KEY, incomeCategory VARCHAR(32), incomeAmount FLOAT(2));
				 CREATE TABLE IF NOT EXISTS fixedExpenses(expenseName VARCHAR(32), spendingCategory VARCHAR(32), spendingAmount FLOAT(2));
				 CREATE TABLE IF NOT EXISTS fixedIncome(incomeName VARCHAR(32), incomeCategory VARCHAR(32), incomeAmount FLOAT(2));
				 CREATE TABLE IF NOT EXISTS categoryAdjustments(transactionRegex VARCHAR(32), newCategory VARCHAR(32));""")
	conn.close()

@app.route('/', methods=['GET','POST'])
def index():
	if request.method == 'POST': #triggers once user uploads transaction data
		transactionFile = request.files['transactionFile']
		text = str(transactionFile.read())
		textNoNewlines = text.replace("\\n",",");
		splits = textNoNewlines.split(',')
		categorySums = {}
		categoryKeys = []
		categoryValues = []
		#8 header columns so start on 8 to skip headers, but each row either has 7 or 8 
		#columns since credit/debit could be omitted (if credit is filled) or left blank (if debit is filled) 
		for i in range(9,len(splits),8):
			advance = 1
			if splits[i+4] == "Payment": #amount is in last column of table (debit)
				advance = 2

			if splits[i+4] in categorySums.keys():
				categorySums[splits[i+4]] += round(Decimal(splits[i+4+advance]),2)
			else:
				categoryKeys.append(splits[i+4])
				categorySums[splits[i+4]] = round(Decimal(splits[i+4+advance]),2)

			if advance == 2: #advances counter 1 more since there is an extra column since debit was left blank
				i += 1

		for k in categoryKeys:
			categoryValues.append(float(categorySums[k]))

		return render_template('index.html',data=categorySums, keys = categoryKeys, values = categoryValues)
	else: #triggers on initial loading of page
		return render_template('index.html', error=False)