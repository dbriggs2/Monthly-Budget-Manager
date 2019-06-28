from flask import Flask
from flask import request
from flask import render_template
from decimal import Decimal
import sqlite3
import sys
import json
import datetime as dt

app = Flask(__name__)

db_name = 'budget_manager'
currentDate = dt.datetime.today()
availableYears = []
for i in range(currentDate.year - 5, currentDate.year + 1): #allow user to view and upload budgets from last 5 years
	availableYears.append(i)
months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']

def getNetIncome(variableExpenses, fixedExpenses, fixedIncome):
	netIncome = round(Decimal(0),2)
	for value in variableExpenses:
		netIncome -= round(Decimal(value),2)
	for value in fixedExpenses:
		netIncome -= round(Decimal(value),2)
	for value in fixedIncome:
		netIncome += round(Decimal(value),2)
	return netIncome

def getFixedPortion():
	fixedExpenses = {}
	fixedIncome = {}

	try:
		f = open("fixedExpenses.txt", "r")
		lines = f.readlines()
		for expense in lines:
			name,amount = expense.split(",")
			if name in fixedExpenses.keys():
				fixedExpenses[name] += round(Decimal(amount),2)
			else:
				fixedExpenses[name] = round(Decimal(amount),2)
		f.close()
	except FileNotFoundError:
		print("fixedExpenses.txt not found in directory", file=sys.stderr)

	try:
		f2 = open("fixedIncome.txt", "r")
		lines = f2.readlines()
		for income in lines:
			name,amount = income.split(",")
			if name in fixedIncome.keys():
				fixedIncome[name] += round(Decimal(amount),2)
			else:
				fixedIncome[name] = round(Decimal(amount),2)
		f2.close()
	except FileNotFoundError:
		print("fixedIncome.txt not found in directory", file=sys.stderr)

	return (fixedExpenses, fixedIncome)

def init_tables():
	conn = sqlite3.connect(db_name)
	c = conn.cursor()
	c.execute("""CREATE TABLE IF NOT EXISTS monthlyVariableExpenses(startingMonth VARCHAR(16), startingYear VARCHAR(4),spendingCategory VARCHAR(32),
		spendingAmount FLOAT(2))""")
	conn.commit()
	conn.close()

@app.route('/deleteBudget', methods=['GET'])
def deleteBudget():
	month = request.args.get('month')
	month = '0' + month[-1] #ensures there is a leading 0 for single digit months
	year = request.args.get('year')

	conn = sqlite3.connect(db_name)
	c = conn.cursor()

	c.execute("DELETE FROM monthlyVariableExpenses WHERE startingMonth = ? AND startingYear = ?", [month,year])
	conn.commit()
	conn.close()
	
	return render_template('index.html',month=int(month), year=int(year), months=months, years = availableYears)

@app.route('/newBudget', methods=['POST'])
def newBudget():
	transactionFile = request.files['transactionFile']
	text = str(transactionFile.read())
	textNoNewlines = text.replace("\\n",",");
	splits = textNoNewlines.split(',')

	categorySums = {}
	categoryKeys = []
	categoryValues = []

	month,day,year = splits[10].split('/') #get a date that the budget includes to use in database

	conn = sqlite3.connect(db_name)
	c = conn.cursor()
	c.execute("SELECT startingMonth, startingYEAR FROM monthlyVariableExpenses WHERE startingMonth = ? AND startingYEAR = ?", [month,year])
	results = c.fetchall()

	if len(results) != 0:
		return render_template('index.html', month=currentDate.month, year = currentDate.year, months = months, years = availableYears, error=True)
	
	#8 header columns so start on 8 to skip headers, but each row has 7 columns since only one of debit/credit is filled 
	for i in range(9,len(splits),8):
		if splits[i+4] == "Payment": #represents credit card payment, so skip it
			continue
		if splits[i+4] in categorySums.keys():
			categorySums[splits[i+4]] += round(Decimal(splits[i+5]),2)
		else:
			categoryKeys.append(splits[i+4])
			categorySums[splits[i+4]] = round(Decimal(splits[i+5]),2)

	for k in categoryKeys:
		categoryValues.append(float(categorySums[k]))

	for k in categorySums.keys():
		c.execute("INSERT INTO monthlyVariableExpenses VALUES(?,?,?,?)", [month, year, str(k), str(categorySums[k])])
		conn.commit()
	conn.close()

	fixedExpenses, fixedIncome = getFixedPortion()
	netIncome = getNetIncome(categoryValues, fixedExpenses.values(), fixedIncome.values())


	return render_template('index.html',data=categorySums, keys = categoryKeys, values = categoryValues, month=int(month),
 	  year=int(year), months=months, years = availableYears, fixedIncome = fixedIncome, fixedExpenses = fixedExpenses, netIncome = netIncome)

@app.route('/', methods=['GET','POST'])
def index():
	init_tables()
	
	if request.method == 'POST': #triggers once user selects month / year to view budget for
		requestedMonth = request.form['month']
		requestedMonth = '0' + requestedMonth[-1] #ensures there is a leading 0 for single digit months
		requestedYear = request.form['year']

		conn = sqlite3.connect(db_name)
		c = conn.cursor()
		c.execute("SELECT spendingCategory, spendingAmount FROM monthlyVariableExpenses WHERE startingMonth = ? AND startingYear = ?",
		 [requestedMonth,requestedYear])
		results = c.fetchall()

		if len(results) == 0: #no existing budget for selected month, just display generic page
			return render_template('index.html', month=int(requestedMonth), year = int(requestedYear), months = months, years = availableYears,
				noBudgetFound = True)
		else: #existing budget found, display transaction table and chart
			categorySums = {}
			categoryKeys = []
			categoryValues = []
			for result in results:
				categorySums[result[0]] = result[1]
				categoryKeys.append(result[0])
				categoryValues.append(result[1])

			fixedExpenses, fixedIncome = getFixedPortion()
			netIncome = getNetIncome(categoryValues, fixedExpenses.values(), fixedIncome.values())

			return render_template('index.html',data=categorySums, keys = categoryKeys, values = categoryValues, month=int(requestedMonth),
 	  		  year=int(requestedYear), months=months, years = availableYears, fixedExpenses = fixedExpenses, fixedIncome = fixedIncome,
 	  		  netIncome = netIncome)
	else: #triggers on initial loading of page
		return render_template('index.html', month=currentDate.month, year = currentDate.year, months = months, years = availableYears)