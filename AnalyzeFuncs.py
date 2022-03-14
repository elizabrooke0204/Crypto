#!/usr/bin/env python3

#Library imports
import time
import requests
import threading
import multiprocessing
import cbpro
import pandas as pd
from datetime import datetime, timedelta

#File imports
from HelperFuncs import *


# ------------------------------------ Analyze RSI BB -------------------------------------

# Analyze crpyto for current most accurate parameter combination
def analyze_rsi_bb(symbol, timeSliceList, outputSize, portion):
	# Variable holders
	rsiSignals = []
	bbSignals = []

	inSellPeriod = False
	inBuyPeriod = False

	bestDelta = 0.0
	currentTopParameters = []
	topParameters = []

	for timeSlice in timeSliceList:
		rates = get_historic_rates(symbol, timeSlice, outputSize)
		ratesHl2Series = pd.Series((rates["High"] + rates["Low"]).div(2).values, index=rates.index)

		timeSlicePerDay = float(timeSlice[:len(timeSlice) - 3])
		timeSlicePerDay = timeSlicePerDay * 200 / (60 * 24)
		
		for rsiPeriodLength in range(5, 18):
			# Set RSI values
			print("timeSlice: {}, RSI: {}".format(timeSlice, rsiPeriodLength))
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

				
						for bbLevelDouble in range(3, 9):
							# Start with 100USD and 100USD worth of crypto
							usdStart = 100.0
							cryptoStart = 100.0 / ratesHl2[0]
							usdEnd = usdStart
							cryptoEnd = cryptoStart

							# Set BB values
							bbLevel = float(bbLevelDouble) / 2.0
							(bbUpperSeries, bbMiddleSeries, bbLowerSeries) = get_bb(ratesHl2Series, bbPeriodLength, bbLevel)

							# Convert Pandas series to lists
							bbUpper = bbUpperSeries.tolist()[(bbPeriodLength - 1):]
							bbLower = bbLowerSeries.tolist()[(bbPeriodLength - 1):]

							# Parse through data and determine sell, buy and hold signals for RSI and BB
							for i in range(len(dates)):
								if ratesRsi[i] > rsiUpperBound:
									rsiSignals.append("sell")
								elif ratesRsi[i] < rsiLowerBound:
									rsiSignals.append("buy")
								else:
									rsiSignals.append("hold")

								if ratesHigh[i] > bbUpper[i]:
									bbSignals.append("sell")
								elif ratesLow[i] < bbLower[i]:
									bbSignals.append("buy")
								else:
									bbSignals.append("hold")

							# Parse through data and determine buy or sell times and prices
							# Calculates endWallet
							for i in range(len(dates)):
								if not inSellPeriod:
									if (rsiSignals[i] == "sell") and (bbSignals[i] == "sell"):
										inSellPeriod = True
								else:
									if (rsiSignals[i] != "sell") and (bbSignals[i] != "sell"):
										usdEnd = usdEnd + (cryptoEnd * ratesHl2[i] * .995 * portion )
										cryptoEnd = cryptoEnd * (1.0 - portion)
										inSellPeriod = False

								if not inBuyPeriod:
									if (rsiSignals[i] == "buy") and (bbSignals[i] == "buy"):
										inBuyPeriod = True
								else:
									if (rsiSignals[i] != "buy") and (bbSignals[i] != "buy"):
										cryptoEnd = cryptoEnd + (usdEnd * .995 * portion / ratesHl2[i])
										usdEnd = usdEnd * (1.0 - portion)
										inBuyPeriod = False

							walletStart = 200.0
							walletEnd = usdEnd + (cryptoEnd * ratesHl2[-1])

							# Calculates action and no-action gains and losses
							noActionGainLoss = (ratesHl2[-1] - ratesHl2[0]) / ratesHl2[0]
							actionGainLoss = (walletEnd - walletStart) / walletStart
							delta = actionGainLoss - noActionGainLoss

							if (delta >= bestDelta):
								bestDelta = delta
								deltaPerDay = delta / timeSlicePerDay
								currentTopParameters.append([deltaPerDay, delta, timeSlice, rsiPeriodLength, rsiUpperBound, rsiLowerBound, bbPeriodLength, bbLevel])

							rsiSignals = []
							bbSignals = []
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

	topParameters.sort(reverse=True)
	print("deltaPerDay, delta, timeSlice, rsiP, rsiU, rsiL, bbP, bbLvl")
	for parameters in topParameters[-15:]:
		print(parameters)


# ------------------------------------- Test RSI BB ---------------------------------------

# Test specific most efficient parameters deteremined by analyze_rsi_bb()
def test_rsi_bb_parameters(symbol, timeSlice, outputSize, rsiPeriodLength, rsiUpperBound, rsiLowerBound, bbPeriodLength, bbLevel):
	# Variable holders
	rsiSignals = []
	bbSignals = []

	inSellPeriod = False
	inBuyPeriod = False

	# Get rates, high/low average, rsi values and bb bands
	rates = get_historic_rates(symbol, timeSlice, outputSize)
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
	bbLower = bbLower.tolist()[(bbPeriodLength - 1):]

	# Start with 100USD and 100USD worth of crypto
	usdStart = 100.0
	usdEnd = usdStart
	cryptoStart = 100.0 / ratesHl2[0]
	cryptoEnd = cryptoStart

	# Parse through data and determine sell, buy and hold signals for rsi and bb
	for i in range(len(dates)):
		if ratesRsi[i] > rsiUpperBound:
			rsiSignals.append("sell")
		elif ratesRsi[i] < rsiLowerBound:
			rsiSignals.append("buy")
		else:
			rsiSignals.append("hold")

		if ratesHigh[i] > bbUpper[i]:
			bbSignals.append("sell")
		elif ratesLow[i] < bbLower[i]:
			bbSignals.append("buy")
		else:
			bbSignals.append("hold")

	# Parse through data and determine buy or sell times and prices
	print("from:" + dates[0])
	print("to:  " + dates[-1])
	for i in range(len(dates)):
		if not inSellPeriod:
			if (rsiSignals[i] == "sell") and (bbSignals[i] == "sell"):
				inSellPeriod = True
		else:
			if (rsiSignals[i] != "sell") and (bbSignals[i] != "sell"):
				usdEnd = usdEnd + (cryptoEnd * ratesHl2[i] * .995 * .75)
				cryptoEnd = cryptoEnd * .25
				print("SELL on {} at: {:.6f}".format(dates[i], ratesHl2[i]))
				print("   USD= {:.3f} | {}= {:.3f}".format(usdEnd, symbol, cryptoEnd))
				inSellPeriod = False

		if not inBuyPeriod:
			if (rsiSignals[i] == "buy") and (bbSignals[i] == "buy"):
				inBuyPeriod = True
		else:
			if (rsiSignals[i] != "buy") and (bbSignals[i] != "buy"):
				cryptoEnd = cryptoEnd + (usdEnd * .995 * .75 / ratesHl2[i])
				usdEnd = usdEnd * .25
				print("BUY on {} at: {:.6f}".format(dates[i], ratesHl2[i]))
				print("   USD= {:.3f} | {}= {:.3f}".format(usdEnd, symbol, cryptoEnd))
				inBuyPeriod = False

	# Calculates endWallet
	walletStart = 200.0
	walletEnd = usdEnd + (cryptoEnd * ratesHl2[-1])

	noActionGainLoss = (ratesHl2[-1] - ratesHl2[0]) / ratesHl2[0]
	actionGainLoss = (walletEnd - walletStart) / walletStart

	print("walletStart: {}, walletEnd: {}".format(walletStart, walletEnd))
	print("timeSlice, rsiPeriod, rsiUpper, rsiLower, bbPeriod, bbLevel")
	print("{},    {},    {},    {},    {},    {}".format(timeSlice, rsiPeriodLength, rsiUpperBound, rsiLowerBound, bbPeriodLength, bbLevel))
	print("actionGainLoss: {}, noActionGainLoss: {}".format(actionGainLoss, noActionGainLoss / 2.0))


# ----------------------------- Multiprocess-Analyze RSI BB -------------------------------

def multiprocess_rsi_bb(symbol, outputSize):
	t1 = multiprocessing.Process(target=analyze_rsi_bb, args=(symbol, ["5min"], outputSize))
	t2 = multiprocessing.Process(target=analyze_rsi_bb, args=(symbol, ["15min"], outputSize))
	t3 = multiprocessing.Process(target=analyze_rsi_bb, args=(symbol, ["30min"], outputSize))
	t4 = multiprocessing.Process(target=analyze_rsi_bb, args=(symbol, ["60min"], outputSize))

	t1.start()
	t2.start()
	t3.start()
	t4.start()

	t1.join()
	t2.join()
	t3.join()
	t4.join()

if __name__ == "__main__":
	#analyze_rsi_bb("LRC", ["15min"], "compact", 0.75)
	test_rsi_bb_parameters("LRC", "15min", "compact", 5, 70, 18, 5, 2.5)
	#multiprocess_rsi_bb("LRC", "compact")


