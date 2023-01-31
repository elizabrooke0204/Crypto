#!/usr/bin/env python3

#Library imports
import time
import requests
import cbpro
import json
import http.client
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime, timedelta
from auth_cred import (api_secret, api_key, api_pass)

# Set url and authticate client
url = "https://api.pro.coinbase.com"
#url = "https://api-public.sandbox.pro.coinbase.com"
client = cbpro.AuthenticatedClient(api_key, api_secret, api_pass, api_url=url)


# --------------------------------- Trend indicators -----------------------------------

def get_sma(rates, periodLength):
	return rates.rolling(periodLength).mean()

def get_ema(rates, periodLength):
	return rates.ewm(span=periodLength, adjust=False).mean()


# ------------------------- Momentum indicators (oscillators) --------------------------

#recieves rates as pandas Series and performs rsi calculations
def get_macd(rates, periodShort, periodLong, periodEma):
	emaShort = get_ema(rates, periodShort)
	emaLong = get_ema(rates, periodLong)
	macd = emaShort - emaLong
	emaMacd = get_ema(macd, periodEma)
	return (macd, emaMacd)


def get_rsi(rates, periodLength):
	rsiValues = []
	currentPrice = 0.0
	previousPrice = 0.0

	gains = 0.0
	losses = 0.0
	delta = 0.0
	counter = 0

	for index, value in rates.items():
		# Calculates first step of RSI.
		if counter == 0:
			currentPrice = float(value)
		elif counter < periodLength:
			previousPrice = currentPrice
			currentPrice = float(value)
			delta = currentPrice - previousPrice

			if delta >= 0:
				gains += (delta / periodLength)
			else:
				losses += (abs(delta) / periodLength)

		if counter == periodLength:
			if (losses == 0.0):
				rsiValues.append(100.0)
			else:
				rsiValues.append(100.0 - (100.0 / (1 + (gains / losses))))

		# Calculats second step of RSI.
		if counter >= periodLength:
			previousPrice = currentPrice
			currentPrice = float(value)
			delta = currentPrice - previousPrice

			if delta >= 0:
				gains = ((gains * (periodLength - 1)) + delta) / periodLength
				losses = losses * (periodLength - 1) / periodLength
			else:
				gains = gains * (periodLength - 1) / periodLength
				losses = ((losses * (periodLength - 1)) + abs(delta)) / periodLength

			if (losses == 0.0):
				rsiValues.append(100.0)
			else:
				rsiValues.append(100.0 - (100.0 / (1 + (gains / losses))))

		counter+=1
	
	return (pd.Series(rsiValues, index = rates.index[periodLength - 1:]))


# ---------------------- Trend/Momentum indicators (oscillators) -----------------------

def get_ichimoku(rates, conversionPeriod, basePeriod, leadingPeriod):
	futureDates = []
	blankValues = []
	displace = 26
	minutes = 15

	# Blank pandas series to append new dates for shift
	startDate = rates.index[-1]
	startDate = datetime.strptime(startDate, "%Y-%m-%d %H:%M:%S")
	for i in range(displace):
		futureDates.append((startDate + timedelta(minutes=minutes)).strftime("%Y-%m-%d %H:%M:%S"))
		blankValues.append(0.0)
		minutes += 15
	futureDates = pd.Series(blankValues, index=futureDates)

	# Conversion Line: Tenkan-sen
	conversionPeriodHigh = rates["High"].rolling(window=conversionPeriod).max()
	conversionPeriodLow = rates["Low"].rolling(window=conversionPeriod).min()
	conversionLine = (conversionPeriodHigh + conversionPeriodLow) / 2
	conversionLine.name = "values"

	# Base Line: Kijun-sen
	basePeriodHigh = rates["High"].rolling(window=basePeriod).max()
	basePeriodLow = rates["Low"].rolling(window=basePeriod).min()
	baseLine = (basePeriodHigh + basePeriodLow) / 2
	baseLine.name = "values"

	# Leading Span A: Senkou Span A
	leadingSpanA = ((conversionLine + baseLine) / 2)
	leadingSpanA.name = "values"
	leadingSpanA = leadingSpanA.append(futureDates).shift(displace)

	# Leading Span B: Senkou Span B
	leadingPeriodHigh = rates["High"].rolling(window=leadingPeriod).max()
	leadingPeriodLow = rates["Low"].rolling(window=leadingPeriod).min()
	leadingSpanB = (leadingPeriodHigh + leadingPeriodLow) / 2
	leadingSpanB.name = "values"
	leadingSpanB = leadingSpanB.append(futureDates).shift(displace)

	# The most current closing price plotted 22 time periods behind
	chikou_span = rates["Close"].shift(-22)
	chikou_span.name = "values"

	return (conversionLine, baseLine, leadingSpanA, leadingSpanB, chikou_span)


# ------------------------------ Technical indicators ----------------------------------

def get_fibonacci_retrace():
	pass


# -------------------------------- Volume indicators -----------------------------------

def get_obv():
	pass


def get_vwap(rates):
	volume = rates["Volume"].values
	hlc3 = (rates["High"] + rates["Low"] + rates["Close"]).div(3).values
	vwap = ((hlc3 * volume).cumsum() / volume.cumsum())
	return (pd.Series(vwap, index=rates.index))


# ------------------------------- Volatility indicators --------------------------------

def get_bb(rates, periodLength, standardDevLevel):
	standardDev = rates.rolling(periodLength).std()
	bbMiddle = get_sma(rates, periodLength)
	bbUpper = bbMiddle + (standardDev * standardDevLevel)
	bbLower = bbMiddle - (standardDev * standardDevLevel)
	return(bbUpper, bbMiddle, bbLower)


# -------------------------------- get historic rates ----------------------------------

def get_historic_rates(symbol, timeSlice):
	granularity = timeSlice * 60
	conn = http.client.HTTPSConnection("api.exchange.coinbase.com")
	payload = ""
	headers = {"User-Agent": "LS", "Content-Type": "application/json"}
	conn.request("GET", "/products/" + symbol + "-USD/candles?granularity=" + str(granularity), payload, headers)
	res = conn.getresponse()
	data = res.read().decode("utf-8")
	rates = json.loads(data)
	rates = pd.DataFrame(rates).set_axis(["Date", "Low", "High", "Open", "Close", "Volume"], axis="columns")
	rates = rates.iloc[::-1]
	rates["Date"] = pd.to_datetime(rates["Date"], unit="s").dt.strftime("%m-%d %H:%M")
	rates = rates.set_index("Date")
	return rates


# --------------------------------- Plot indicators ------------------------------------

def plot_bb(rates, bbUpper, bbMiddle, bbLower):
	plt.plot(bbUpper, label="Bollinger Up", c="b")
	plt.plot(bbMiddle, label="Bollinger Middle", c="black")
	plt.plot(bbLower, label="Bollinger Down", c="b")
	plt.plot(rates, label="Rates", c="g")
	plt.legend()
	plt.xticks(np.arange(0, len(rates) + 1, 20), rotation=10)
	return plt


def plot_inchimoku(conversionLine, baseLine, leadingSpanA, leadingSpanB, chikou_span):
	plt.plot(conversionLine, label="tenkan-sen", c="b")
	plt.plot(baseLine, label="kijun_sen", c="r")
	plt.plot(leadingSpanA, label="senkou span-A", c="purple")
	plt.plot(leadingSpanB, label="senkou span-B", c="orange")
	plt.plot(chikou_span, label="chikou-span", c="g")
	plt.fill_between(leadingSpanA.index, leadingSpanA, leadingSpanB, facecolor="grey")
	plt.legend()
	return plt


def plot_macd(macd, emaMacd):
	plt.plot(macd, label="macd", c="black")
	plt.plot(emaMacd, label="signal", c="r")
	plt.legend()
	return plt


def plot_vwap(rates, vwap):
	plt.plot(vwap, label="VWAP", c="g")
	plt.plot(rates, label="Rates", c="b")
	plt.legend()
	return plt


def plot_rsi(rsi, rsiUpperBound, rsiLowerBound):
	plt.plot(rsi, label="RSI", c="r")
	plt.axhline(y=rsiUpperBound, color='r', linestyle='--')
	plt.axhline(y=rsiLowerBound, color='r', linestyle='--')
	return plt


# ---------------------------------- Sell/Buy functions -----------------------------------

def sellBTC(portion):
	trade = client.sell(price=str(getAskPrice("BTC-USD")),
		size=str(getAvailableBTC(portion)),
		order_type="limit",
		product_id="BTC-USD",
		post_only=True)
	print(trade)


def sellLRC(portion):
	trade = client.sell(price=str(getAskPrice("LRC-USD")),
		size=str(getAvailableLRC(portion)),
		order_type="limit",
		product_id="LRC-USD",
		post_only=True)
	print(trade)


def buyBTC(portion):
	trade = client.buy(price=str(getBidPrice("BTC-USD")),
		size=str(round(getAvailableUSD(portion) / getBidPrice("BTC-USD"), 4)),
		order_type="limit",
		product_id="BTC-USD",
		post_only=True)
	print(trade)


def buyLRC(portion):
	trade = client.buy(price=str(getBidPrice("LRC-USD")),
		size=str(round(getAvailableUSD(portion) / getBidPrice("LRC-USD"), 6)),
		order_type="limit",
		product_id="LRC-USD",
		post_only=True)
	print(trade)


# ------------------------------- Get-available functions ---------------------------------

def get_currency(symbol):
	currencies = get_currencies()
	try:
		return currencies.loc[symbol].to_dict()
	except Exception as err:
		print("could not retrieve currency in wallet")


def get_currencies():
	try:
		ts = str(int(time.time()))
		path_url = "/api/v3/brokerage/accounts"
		signature = generate_signature(ts, "GET", path_url)
		conn = http.client.HTTPSConnection("api.coinbase.com")
		payload = ''
		headers = {
			"User-Agent": "LS",
			"CB-ACCESS-KEY": cb_api_key,
			"CB-ACCESS-TIMESTAMP": ts,
			"CB-ACCESS-SIGN": signature,
			"Content-Type": "application/json"}

		conn.request("GET", path_url, payload, headers)
		res = conn.getresponse()
		data = res.read().decode("utf-8")
		accounts = pd.DataFrame(json.loads(data))
		accounts = pd.json_normalize(accounts.accounts)
		accounts = accounts.drop(columns=["active", "available_balance.currency", "created_at",
			"deleted_at", "default", "hold.currency", "hold.value", "name", "ready", "type", "updated_at"])
		accounts = accounts.rename(columns={"currency": "name", "available_balance.value": "balance"})
		accounts = accounts.set_index("name")
		return accounts
	except Exception as err:
		print("could not retrieve currencies in wallet")


def generate_signature(ts, method, url):
	message = ts + method + url
	return hmac.new(cb_api_secret.encode('utf-8'), message.encode('utf-8'), hashlib.sha256).hexdigest()


def get_orders():
	orders = client.get_orders()
	for order in orders:
		print(order)


def append_order_to_csv(date, price, side):
	with open("order_history.csv", "a") as f:
		writerObj = csv.writer(f)
		writerObj.writerow([date, price, side])
		f.close()


def get_order_history():
	try:
		orders = pd.read_csv("order_history.csv", index_col=0)
		print(orders)
	except Exception as err:
		print("CSV is empty or does not exist")


def getAskPrice(symbolPair):
	price = client.get_product_ticker(product_id=symbolPair)["ask"]
	return (round(float(price) * 0.9995, 4))


def getBidPrice(symbolPair):
	price = client.get_product_ticker(product_id=symbolPair)["bid"]
	return (round(float(price) * 1.0005, 4))


def getAvailableBTC(portion):
	accounts = client.get_accounts()
	for account in accounts:
		if (account["currency"] == "BTC"):
			return (round(float(account["available"]) * portion, 5))


def getAvailableLRC(portion):
	accounts = client.get_accounts()
	for account in accounts:
		if (account["currency"] == "LRC"):
			return (round(float(account["available"]) * portion, 6))


def getAvailableUSD(portion):
	accounts = client.get_accounts()
	for account in accounts:
		if (account["currency"] == "USD"):
			return (round(float(account["available"]) * portion, 2))




