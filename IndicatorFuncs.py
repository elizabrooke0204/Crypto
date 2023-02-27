#!/usr/bin/env python3
"""
Module of functions that retrieve market rates and calculate indicator data.

Functions
---------
get_historic_rates(symbol, timeSlice)
	Given a cryptocurrency symbol and time-slice value, returns historic rates.
get_ema(rates, periodLength)
	Calculates and returns the exponential-moving-average of rates.
get_sma(rates, periodLength)
	Calculates and returns the simple-moving-average of rates.
get_macd(rates, periodShort, periodLong, periodEma)
	Calculates and returns the moving-average-convergence-divergence of rates.
get_rsi(rates, periodLength)
	Caluculates and returns the relatvie-strength-index of rates.
get_ichimoku(rates, periodConversion, periodBase, periodLeading)
	Calculates and returns the ichimoku-cloud of rates.
get_fibonacci_retrace()
	TODO - Calculates and returns the fibonacci-retrace of rates.
get_obv()
	TODO - Calculates and returns the on-balance-volume of rates.
get_vwap(rates)
	Calculates and returns the volume-weighted-average-price of rates.
get_bb(rates, periodLength, standardDevLevel)
	Calculates and returns the bollinger-bands of rates.
"""

# Library imports
import csv
import http.client
import json
import requests
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from datetime import datetime


# ---------------------------------- Historic rates ------------------------------------

def get_historic_rates(symbol, timeSlice):
	"""
	Given a cryptocurrency symbol and time-slice value, returns historic rates.

	Parameters
	----------
	symbol : str
		Symbol associated with the quote currency of a trading pair.
	timeSlice : int
		Time span in minutes for each data point. Must be 1, 5, 15, or 60.

	Returns
	-------
	pandas.DataFrame
		Most recent 300 data points for the given symbol and time-slice amount as 
		["Date", "Low", "High", "Open", "Close", "Volume"].
	"""

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

def get_ema(rates, periodLength):
	"""
	Calculates and returns the exponential-moving-average of rates.

	Parameters
	----------
	rates : pandas.DataFrame or pandas.Series
		Rates of a cryptocurrency in chronological order.
	periodLength : int
		Amount of datapoints used to calculate exponential-moving-average. Must be less 
		than amount of data points.


	Returns
	-------
	pandas.DataFrame or pandas.Series
		Exponential-moving-average values for the given rates and period length.
	"""

	return rates.ewm(span=periodLength, adjust=False).mean()


def get_sma(rates, periodLength):
	"""
	Calculates and returns the simple-moving-average of rates.

	Parameters
	----------
	rates : pandas.DataFrame or pandas.Series
		Rates of a cryptocurrency in chronological order.
	periodLength : int
		Amount of datapoints used to calculate simple-moving-average. Must be less than 
		amount of data points.


	Returns
	-------
	pandas.DataFrame or pandas.Series
		Simple-moving-average values for the given rates and period length.
	"""

	return rates.rolling(periodLength).mean()


# ------------------------- Momentum indicators (oscillators) --------------------------

def get_macd(rates, periodShort, periodLong, periodEma):
	"""
	Calculates and returns the moving-average-convergence-divergence of rates.

	Parameters
	----------
	rates : pandas.DataFrame or pandas.Series
		Rates of a cryptocurrency in chronological order.
	periodShort : int
		Amount of datapoints used to calculate the short-exponential-moving-average. Must 
		be less than amount of data points.
	periodLong : int
		Amount of datapoints used to calculate the long-exponential-moving-average. Must 
		be less than amount of data points.
	periodEma : int
		Amount of datapoints used to calculate the exponential-moving-average of the 
		moving-average-convergence-divergence data. Must be less than amount of data points.

	Returns
	-------
	pandas.DataFrame or pandas.Series
		Moving-average-convergence-divergence values for the given rates and period lengths.
	"""

	emaShort = get_ema(rates, periodShort)
	emaLong = get_ema(rates, periodLong)
	macd = emaShort - emaLong
	emaMacd = get_ema(macd, periodEma)
	return (macd, emaMacd)


def get_rsi(rates, periodLength):
	"""
	Caluculates and returns the relatvie-strength-index of rates.

	Parameters
	----------
	rates : pandas.Series
		Rates of a cryptocurrency in chronological order.
	periodLength : int
		Amount of datapoints used to calculate the relative-strength-index. Must be less 
		than amount of data points.

	Returns
	-------
	pandas.Series
		Relative-strength-index values for the given rates and period length.
	"""

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

def get_ichimoku(rates, periodConversion, periodBase, periodLeading):
	"""
	Calculates and returns the ichimoku-cloud of rates.

	Parameters
	----------
	rates : pandas.DataFrame
		Rates of a cryptocurrency in chronological order.
	periodConversion : int
		Amount of datapoints used to calculate the conversion line and leading-span-A data 
		points. Must be less than amount of data points.
	periodBase : int
		Amount of datapoints used to calculate the base line and leading-span-A data 
		points. Must be less than amount of data points.
	periodLeading : int
		Amount of datapoints used to calculate the leading-span-B data points. Must be 
		less than amount of data points.

	Returns
	-------
	tuple of (pandas.Series, pandas.Series, pandas.Series, pandas.Series, pandas.Series)
		Tuple of itchimoku cloud values for the given rates and period lengths as 
		(conversionLine, baseLine, leadingSpanA, leadingSpanB, chikouSpan)
	"""

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
	periodConversionHigh = rates["High"].rolling(window=periodConversion).max()
	periodConversionLow = rates["Low"].rolling(window=periodConversion).min()
	conversionLine = (periodConversionHigh + periodConversionLow) / 2
	conversionLine.name = "values"

	# Base Line: Kijun-sen
	periodBaseHigh = rates["High"].rolling(window=periodBase).max()
	periodBaseLow = rates["Low"].rolling(window=periodBase).min()
	baseLine = (periodBaseHigh + periodBaseLow) / 2
	baseLine.name = "values"

	# Leading Span A: Senkou Span A
	leadingSpanA = ((conversionLine + baseLine) / 2)
	leadingSpanA.name = "values"
	leadingSpanA = leadingSpanA.append(futureDates).shift(displace)

	# Leading Span B: Senkou Span B
	periodLeadingHigh = rates["High"].rolling(window=periodLeading).max()
	periodLeadingLow = rates["Low"].rolling(window=periodLeading).min()
	leadingSpanB = (periodLeadingHigh + periodLeadingLow) / 2
	leadingSpanB.name = "values"
	leadingSpanB = leadingSpanB.append(futureDates).shift(displace)

	# The most current closing price plotted 22 time periods behind
	chikouSpan = rates["Close"].shift(-22)
	chikouSpan.name = "values"

	return (conversionLine, baseLine, leadingSpanA, leadingSpanB, chikouSpan)


# ------------------------------ Technical indicators ----------------------------------

def get_fibonacci_retrace():
	"""
	TODO - Calculates and returns the fibonacci-retrace of rates.
	"""
	pass


# -------------------------------- Volume indicators -----------------------------------

def get_obv():
	"""
	TODO - Calculates and returns the on-balance-volume of rates.
	"""
	pass


def get_vwap(rates):
	"""
	Calculates and returns the volume-weighted-average-price of rates.

	Parameters
	----------
	rates : pandas.DataFrame
		Rates of a cryptocurrency in chronological order.

	Returns
	-------
	pandas.Series
		Volume-weighted-average-price values for the given rates and period length.
	"""

	volume = rates["Volume"].values
	hlc3 = (rates["High"] + rates["Low"] + rates["Close"]).div(3).values
	vwap = ((hlc3 * volume).cumsum() / volume.cumsum())
	return (pd.Series(vwap, index=rates.index))


# ------------------------------- Volatility indicators --------------------------------

def get_bb(rates, periodLength, standardDevLevel):
	"""
	Calculates and returns the bollinger-bands of rates.

	Parameters
	----------
	rates : pandas.DataFrame
		Rates of a cryptocurrency in chronological order.
	periodLength : int
		Amount of datapoints used to calculate bollinger-bands. Must be less than amount 
		of data points.
	standardDevLevel : int
		Standard deviation level used to calculate rolling standard deviation.

	Returns
	-------
	tuple of (pandas.Series, pandas.Series, pandas.Series)
		Tuple of bollinger-bands values for the given rates, period length, and deviation 
		level as (bbUpper, bbMiddle, bbLower).
	"""

	standardDev = rates.rolling(periodLength).std()
	bbMiddle = get_sma(rates, periodLength)
	bbUpper = bbMiddle + (standardDev * standardDevLevel)
	bbLower = bbMiddle - (standardDev * standardDevLevel)
	return(bbUpper, bbMiddle, bbLower)


