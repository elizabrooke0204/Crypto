#!/usr/bin/env python3
"""
Script to manually test strategy with different parameter combintations and data sets.

Functions
---------
analyze_rsi_bb(symbol, timeSlice, portion, stopLossPortion)
	Analyzes most recent market data and prints most profitable parameter combinations to terminal.
test_rsi_bb_parameters(symbol, timeSlice, rsiPeriodLength, rsiUpperBound, rsiLowerBound, bbPeriodLength, bbLevel)
	Tests specific combination and prints buy and sell actions that would have occurred with the given parameters.
multiprocess_rsi_bb(symbol)
	Multiprocesses "analyze_rsi_bb" for different time-slice or stop-loss parameters to compare strategy effectiveness.
"""

# Library imports
import time
import requests
import threading
import multiprocessing
import pandas as pd
from datetime import datetime, timedelta

# File imports
from HelperFuncs import *


# ------------------------------------ Analyze RSI BB -------------------------------------

# Analyze crpyto for current most accurate parameter combination
def analyze_rsi_bb(symbol, timeSlice, portion, stopLossPortion):
	"""
	Analyzes most recent market data and prints most profitable parameter combinations to 
	terminal.

	Parameters
	----------
	symbol : str
		Symbol associated with the base currency of a trading pair.
	timeSlice : int
		Time span in minutes for each data point. Must be 1, 5, 15, or 60.
	portion : float
		Percentage of asset be used in buy or sell action as decimal. Must be between 0.0 
		and 1.0.
	stopLossPortion : float
		Percentage of current price to set stop loss limit as decimal. Must be between 0.0 
		and 1.0.
	"""

	# Variable holders
	inSellPeriod = False
	inBuyPeriod = False

	bestDelta = 0.0
	stopLossLower = 0.0
	stopLossUpper = 0.0
	currentTopParameters = []
	topParameters = []

	rates = get_historic_rates(symbol, timeSlice).tail(150)
	ratesHl2Series = pd.Series((rates["High"] + rates["Low"]).div(2).values, index=rates.index)
	
	for rsiPeriodLength in range(3, 14):
		print(rsiPeriodLength)
		# Set RSI values
		ratesRsiSeries = get_rsi(ratesHl2Series, rsiPeriodLength)

		for rsiUpperBound in range(90, 66, -2):
			for rsiLowerBound in range(10, 34, 2):
				for bbPeriodLength in range(rsiPeriodLength, 36, 2):
					# Convert Pandas series to lists
					ratesHigh = rates["High"].tolist()[(bbPeriodLength - 1):]
					ratesLow = rates["Low"].tolist()[(bbPeriodLength - 1):]
					ratesHl2 = ratesHl2Series.tolist()[(bbPeriodLength - 1):]
					ratesRsi = ratesRsiSeries.tolist()[(bbPeriodLength - rsiPeriodLength):]
					dates = rates.index.tolist()[(bbPeriodLength - 1):]

			
					for bbLevelDouble in range(4, 14):
						# Start with 100USD and 100USD worth of crypto
						usdStart = 100.0
						cryptoStart = 100.0 / ratesHl2[0]
						usdEnd = usdStart
						cryptoEnd = cryptoStart

						# Set BB values
						bbLevel = float(bbLevelDouble) / 4.0
						(bbUpperSeries, bbMiddleSeries, bbLowerSeries) = get_bb(ratesHl2Series, bbPeriodLength, bbLevel)

						# Convert Pandas series to lists
						bbUpper = bbUpperSeries.tolist()[(bbPeriodLength - 1):]
						bbMiddle = bbMiddleSeries.tolist()[(bbPeriodLength - 1):]
						bbLower = bbLowerSeries.tolist()[(bbPeriodLength - 1):]
						stopLossUpper = bbMiddle[0] * (1.0 + stopLossPortion)
						stopLossLower = bbMiddle[0] * (1.0 - stopLossPortion)

						# Parse through data and determine buy or sell times and prices
						# Calculates endWallet
						for i in range(len(dates)):
							if not inSellPeriod:
								if (ratesRsi[i] > rsiUpperBound) and (ratesHigh[i] > bbUpper[i]):
									inSellPeriod = True
							else:
								if (ratesRsi[i] <= rsiUpperBound) and (ratesHigh[i] <= bbUpper[i]):
									usdEnd = usdEnd + (cryptoEnd * ratesHl2[i] * .995 * portion )
									cryptoEnd = cryptoEnd * (1.0 - portion)
									if stopLossUpper == 0.0:
										stopLossUpper = max(bbMiddle[i], ratesHigh[i]) * (1.0 + stopLossPortion)
									stopLossLower = 0.0
									inSellPeriod = False

							if not inBuyPeriod:
								if (ratesRsi[i] < rsiLowerBound) and (ratesLow[i] < bbLower[i]):
									inBuyPeriod = True
							else:
								if (ratesRsi[i] >= rsiLowerBound) and (ratesLow[i] >= bbLower[i]):
									cryptoEnd = cryptoEnd + (usdEnd * .995 * portion / ratesHl2[i])
									usdEnd = usdEnd * (1.0 - portion)
									if stopLossLower == 0.0:
										stopLossLower = min(bbMiddle[i], ratesLow[i]) * (1.0 - stopLossPortion)
									stopLossUpper = 0.0
									inBuyPeriod = False

							if stopLossLower > 0.0:
								if (min(bbMiddle[i], ratesLow[i]) * (1.0 - stopLossPortion)) > stopLossLower:
									stopLossLower = min(bbMiddle[i], ratesLow[i]) * (1.0 - stopLossPortion)
								if ratesLow[i] < stopLossLower:
									usdEnd = usdEnd + (cryptoEnd * ratesHl2[i] * .995 * portion )
									cryptoEnd = cryptoEnd * (1.0 - portion)
									stopLossUpper = max(bbMiddle[i], ratesHigh[i]) * (1.0 + stopLossPortion)
									stopLossLower = 0.0

							if stopLossUpper > 0.0:
								if (max(bbMiddle[i], ratesHigh[i]) * (1.0 + stopLossPortion)) < stopLossUpper:
									stopLossUpper = max(bbMiddle[i], ratesHigh[i]) * (1.0 + stopLossPortion)
								if ratesHigh[i] > stopLossUpper:
									cryptoEnd = cryptoEnd + (usdEnd * .995 * portion / ratesHl2[i])
									usdEnd = usdEnd * (1.0 - portion)
									stopLossLower = min(bbMiddle[i], ratesLow[i]) * (1.0 - stopLossPortion)
									stopLossUpper = 0.0

						walletStart = 200.0
						walletEnd = usdEnd + (cryptoEnd * ratesHl2[-1])

						# Calculates action and no-action gains and losses
						noActionGainLoss = (ratesHl2[-1] - ratesHl2[0]) / (2 * ratesHl2[0])
						actionGainLoss = (walletEnd - walletStart) / walletStart
						delta = actionGainLoss - noActionGainLoss

						if (delta > 0.0) and (delta >= bestDelta):
							bestDelta = delta
							currentTopParameters.append([actionGainLoss, delta, timeSlice, rsiPeriodLength, rsiUpperBound, rsiLowerBound, bbPeriodLength, bbLevel])

						inSellPeriod = False
						inBuyPeriod = False

		bestDelta = 0.0
		currentTopParameters.reverse()
		if len(currentTopParameters) > 3:
			numberOfParameters = 3
		else:
			numberOfParameters = len(currentTopParameters)

		for i in range(numberOfParameters):
			topParameters.append(currentTopParameters[i])
		currentTopParameters = []

	topParameters.sort()
	print(symbol + " SL-portion: " + str(stopLossPortion))
	print("actionGainLoss, delta, timeSlice, rsiP, rsiU, rsiL, bbP, bbLvl")
	for parameters in topParameters:
		print(parameters)


# ------------------------------------- Test RSI BB ---------------------------------------

# Test specific most efficient parameters deteremined by analyze_rsi_bb()
def test_rsi_bb_parameters(symbol, timeSlice, rsiPeriodLength, rsiUpperBound, rsiLowerBound, bbPeriodLength, bbLevel):
	"""
	Tests specific combination and prints buy and sell actions that would have occurred 
	with the given parameters.

	Parameters
	----------
	symbol : str
		Symbol associated with the base currency of a trading pair.
	timeSlice : int
		Time span in minutes for each data point. Must be 1, 5, 15, or 60.
	rsiPeriodLength : int
		Amount of datapoints used to calculate relative-strength-index. Must be less than 
		amount of data points.
	rsiUpperBound : int
		Upper threshold for overbought range. Must be between 50 and 100, recommended 
		between 60 and 90.
	rsiLowerBound : int
		Lower threshold for oversold range. Must be between 0 and 50, recommended between 
		10 and 40.
	bbPeriodLength : int
		Amount of datapoints used to calculate bollinger-bands. Must be less than amount 
		of data points.
	bbLevel : float
		Standard deviation level used to calculate upper and lower bolling-bands. 
		Must be greater than 0.0, recommended between 1.0 and 3.0.
	"""

	# Variable holders
	inSellPeriod = False
	inBuyPeriod = False

	# Get rates, high/low average, rsi values and bb bands
	rates = get_historic_rates(symbol, timeSlice).tail(150)
	ratesHl2 = pd.Series((rates["High"] + rates["Low"]).div(2).values, index=rates.index)

	ratesRsi = get_rsi(ratesHl2, rsiPeriodLength)
	(bbUpper, bbMiddle, bbLower) = get_bb(ratesHl2, bbPeriodLength, bbLevel)

	# Set series to lists of equal length
	dates = rates.index.tolist()[(bbPeriodLength - 1):]
	ratesHigh = rates["High"].tolist()[(bbPeriodLength - 1):]
	ratesLow = rates["Low"].tolist()[(bbPeriodLength - 1):]
	ratesHl2 = ratesHl2.tolist()[(bbPeriodLength - 1):]
	ratesRsi = ratesRsi.tolist()[(bbPeriodLength - rsiPeriodLength):]
	bbUpper = bbUpper.tolist()[(bbPeriodLength - 1):]
	bbMiddle = bbMiddle.tolist()[(bbPeriodLength - 1):]
	bbLower = bbLower.tolist()[(bbPeriodLength - 1):]

	# Start with 100USD and 100USD worth of crypto
	usdStart = 100.0
	usdEnd = usdStart
	cryptoStart = 100.0 / ratesHl2[0]
	cryptoEnd = cryptoStart
	portion = 0.99

	stopLossPortion = 0.008
	stopLossUpper = bbMiddle[0] * (1.0 + stopLossPortion)
	stopLossLower = bbMiddle[0] * (1.0 - stopLossPortion)

	# Parse through data and determine buy or sell times and prices
	print("from:" + dates[0])
	print("to:  " + dates[-1])
	for i in range(len(dates)):
		if not inSellPeriod:
			if (ratesRsi[i] > rsiUpperBound) and (ratesHigh[i] > bbUpper[i]):
				inSellPeriod = True
		else:
			if (ratesRsi[i] <= rsiUpperBound) and (ratesHigh[i] <= bbUpper[i]):
				usdEnd = usdEnd + (cryptoEnd * ratesHl2[i] * .995 * portion)
				cryptoEnd = cryptoEnd * (1.0 - portion)
				if stopLossUpper == 0.0:
					stopLossUpper = max(bbMiddle[i], ratesHigh[i]) * (1.0 + stopLossPortion)
				stopLossLower = 0.0
				print("SELL on {} at: {:.6f}".format(dates[i], ratesHl2[i]))
				print("   USD= {:.3f} | {}= {:.3f}".format(usdEnd, symbol, cryptoEnd))
				inSellPeriod = False

		if not inBuyPeriod:
			if (ratesRsi[i] < rsiLowerBound) and (ratesLow[i] < bbLower[i]):
				inBuyPeriod = True
		else:
			if (ratesRsi[i] >= rsiLowerBound) and (ratesLow[i] >= bbLower[i]):
				cryptoEnd = cryptoEnd + (usdEnd * .995 * portion / ratesHl2[i])
				usdEnd = usdEnd * (1.0 - portion)
				if stopLossLower == 0.0:
					stopLossLower = min(bbMiddle[i], ratesLow[i]) * (1.0 - stopLossPortion)
				stopLossUpper = 0.0
				print("BUY on {} at: {:.6f}".format(dates[i], ratesHl2[i]))
				print("   USD= {:.3f} | {}= {:.3f}".format(usdEnd, symbol, cryptoEnd))
				inBuyPeriod = False

		if stopLossLower > 0.0:
			if (min(bbMiddle[i], ratesLow[i]) * (1.0 - stopLossPortion)) > stopLossLower:
				stopLossLower = min(bbMiddle[i], ratesLow[i]) * (1.0 - stopLossPortion)
			if ratesLow[i] < stopLossLower:
				usdEnd = usdEnd + (cryptoEnd * ratesHl2[i] * .995 * portion )
				cryptoEnd = cryptoEnd * (1.0 - portion)
				stopLossUpper = max(bbMiddle[i], ratesHigh[i]) * (1.0 + stopLossPortion)
				stopLossLower = 0.0
				print("SL-SELL on {} at: {:.6f}".format(dates[i], ratesHl2[i]))
				print("   USD= {:.3f} | {}= {:.3f}".format(usdEnd, symbol, cryptoEnd))

		if stopLossUpper > 0.0:
			if (max(bbMiddle[i], ratesHigh[i]) * (1.0 + stopLossPortion)) < stopLossUpper:
				stopLossUpper = max(bbMiddle[i], ratesHigh[i]) * (1.0 + stopLossPortion)
			if ratesHigh[i] > stopLossUpper:
				cryptoEnd = cryptoEnd + (usdEnd * .995 * portion / ratesHl2[i])
				usdEnd = usdEnd * (1.0 - portion)
				stopLossLower = min(bbMiddle[i], ratesLow[i]) * (1.0 - stopLossPortion)
				stopLossUpper = 0.0
				print("SL-BUY on {} at: {:.6f}".format(dates[i], ratesHl2[i]))
				print("   USD= {:.3f} | {}= {:.3f}".format(usdEnd, symbol, cryptoEnd))


	# Calculates endWallet
	walletStart = 200.0
	walletEnd = usdEnd + (cryptoEnd * ratesHl2[-1])

	noActionGainLoss = (ratesHl2[-1] - ratesHl2[0]) / (2 * ratesHl2[0])
	actionGainLoss = (walletEnd - walletStart) / walletStart

	print("walletStart: {}, walletEnd: {}".format(walletStart, walletEnd))
	print("timeSlice, rsiPeriod, rsiUpper, rsiLower, bbPeriod, bbLevel")
	print("{},    {},    {},    {},    {},    {}".format(timeSlice, rsiPeriodLength, rsiUpperBound, rsiLowerBound, bbPeriodLength, bbLevel))
	print("actionGainLoss: {}, noActionGainLoss: {}".format(actionGainLoss, noActionGainLoss))


# ----------------------------- Multiprocess-Analyze RSI BB -------------------------------

def multiprocess_rsi_bb(symbol):
	"""
	Multiprocesses "analyze_rsi_bb" for different time-slice or stop-loss parameters to 
	compare strategy effectiveness.

	Parameters
	----------
	symbol : str
		Symbol associated with the base currency of a trading pair.
	"""

	portion = 0.99
	t1 = multiprocessing.Process(target=analyze_rsi_bb, args=(symbol, 60, portion, 0.014))
	t2 = multiprocessing.Process(target=analyze_rsi_bb, args=(symbol, 60, portion, 0.018))
	t3 = multiprocessing.Process(target=analyze_rsi_bb, args=(symbol, 60, portion, 0.022))
	t4 = multiprocessing.Process(target=analyze_rsi_bb, args=(symbol, 60, portion, 0.026))

	t1.start()
	t2.start()
	t3.start()
	t4.start()

	t1.join()
	t2.join()
	t3.join()
	t4.join()


if __name__ == "__main__":
	#analyze_rsi_bb("BTC", 60, 0.995, 0.025)
	test_rsi_bb_parameters("BTC", 60, 3, 82, 12, 3, 3.25)
	#multiprocess_rsi_bb("BTC")

