#!/usr/bin/env python3

#Library imports
import requests
import csv
import json
import http.client
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime
from KrakenFuncs import *


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


# --------------------------------- Trend indicators -----------------------------------

def get_sma(rates, periodLength):
	return rates.rolling(periodLength).mean()

def get_ema(rates, periodLength):
	return rates.ewm(span=periodLength, adjust=False).mean()


# ------------------------- Momentum indicators (oscillators) --------------------------

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

