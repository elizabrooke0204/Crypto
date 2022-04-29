#!/usr/bin/env python3

#Library imports
import time
import requests
import cbpro
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime, timedelta
from auth_cred import (api_secret, api_key, api_pass, alpha_api_key)

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

def get_historic_rates(symbol, timeSlice, output_size):
	compactOrFull = "full"
	url = ("https://www.alphavantage.co/query?function=CRYPTO_INTRADAY&symbol=" + symbol
		+ "&market=USD&interval=" + timeSlice
		+ "&outputsize=" + output_size
		+ "&apikey=" + alpha_api_key)
	#pd.set_option("display.max_rows", None, "display.max_colwidth", None)

	# Reads in data, parse into json format, save only time series data eliminating meta data
	rates = requests.get(url)
	rates = rates.json()
	rates = rates["Time Series Crypto (" + timeSlice + ")"]

	# Change from json to pandas data frame, transpose data row and columns
	rates = pd.DataFrame(rates)
	rates = rates.transpose()

	# Set index and row names, sort data from latest to most recent rates
	rates.index.name="Date"
	rates.index = rates.index.str[5:-3]
	rates.columns = ["Open","High","Low","Close","Volume"]
	rates.sort_values(by="Date", ascending=True, inplace=True)

	# Changes data from strings to floats
	rates["Open"] = pd.to_numeric(rates["Open"], downcast="float")
	rates["High"] = pd.to_numeric(rates["High"], downcast="float")
	rates["Low"] = pd.to_numeric(rates["Low"], downcast="float")
	rates["Close"] = pd.to_numeric(rates["Close"], downcast="float")
	rates["Volume"] = pd.to_numeric(rates["Volume"], downcast="float")

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

def getAskPrice(symbolPair):
	price = client.get_product_ticker(product_id=symbolPair)["ask"]
	return (round(float(price) * 1.0005, 4))


def getBidPrice(symbolPair):
	price = client.get_product_ticker(product_id=symbolPair)["bid"]
	return (round(float(price) * 0.9995, 4))


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




