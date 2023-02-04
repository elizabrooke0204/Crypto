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
from SymbolList import symList
from auth_cred import (api_secret, api_key, api_pass)

# Set url and authticate client
url = "https://api.pro.coinbase.com"
#url = "https://api-public.sandbox.pro.coinbase.com"
client = cbpro.AuthenticatedClient(api_key, api_secret, api_pass, api_url=url)

# ------------------------------------ Analyze RSI BB -------------------------------------

# Analyze crpyto for current most accurate parameter combination
def analyze_rsi_bb(symbol, timeSlice, portion, stopLossPortion):
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
						stopLossUpper = 0.0
						stopLossLower = 0.0

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

						if (delta >= bestDelta):
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


def get_price_differences(symbol):
	rates5min = get_historic_rates(symbol, "5min")
	rates60min = get_historic_rates(symbol, "60min")

	series5minHl2 = pd.Series((rates5min["High"] + rates5min["Low"]).div(2).values, index=rates5min.index)
	series60minHl2 = pd.Series((rates60min["High"] + rates60min["Low"]).div(2).values, index=rates60min.index)

	list5min = series5minHl2.tolist()
	list60min = series60minHl2.tolist()

	now = list5min[-1]

	return ([symbol, get_delta(now, list5min[-2]), get_delta(now, list5min[-7]),
		get_delta(now, list5min[-13]), get_delta(now, list5min[-73]),
		get_delta(now, list5min[-145]), get_delta(now, list5min[-289]),
		get_delta(now, list60min[-120]), get_delta(now, list60min[-240]),
		get_delta(now, list60min[-480]), get_delta(now, list60min[-720])])


def get_all_price_differences():
	data = pd.DataFrame(client.get_products())
	dataList = data["id"].tolist()

	deltaList = []

	for sym in symList:
		try:
			#deltaList.append
			print(get_price_differences(sym))
			time.sleep(30)

		except Exception as err:
			print("not in list")
			time.sleep(30)

	for delta in deltaList:
		print(delta)

	
def get_delta(priceNow, priceOld):
	return round((priceNow - priceOld) * 100.0 / priceOld, 2)

# ------------------------------------- Test RSI BB ---------------------------------------

# Test specific most efficient parameters deteremined by analyze_rsi_bb()
def test_rsi_bb_parameters(symbol, timeSlice, rsiPeriodLength, rsiUpperBound, rsiLowerBound, bbPeriodLength, bbLevel):
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

	stopLossLower = 0.0
	stopLossUpper = 0.0
	stopLossPortion = 0.025

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
	portion = 0.99
	t1 = multiprocessing.Process(target=analyze_rsi_bb, args=(symbol, 5, portion, 0.010))
	t2 = multiprocessing.Process(target=analyze_rsi_bb, args=(symbol, 5, portion, 0.015))
	t3 = multiprocessing.Process(target=analyze_rsi_bb, args=(symbol, 15, portion, 0.010))
	t4 = multiprocessing.Process(target=analyze_rsi_bb, args=(symbol, 15, portion, 0.015))

	t1.start()
	t2.start()
	t3.start()
	t4.start()

	t1.join()
	t2.join()
	t3.join()
	t4.join()


def test_all():
	for sym in symList:
		print(sym)
		analyze_rsi_bb(sym, ["15min"], 0.99)

def multiprocess_test_all():

	for i in range(0, 56, 2):
		t1 = multiprocessing.Process(target=analyze_rsi_bb, args=(symList[i], 15, 0.99))
		t2 = multiprocessing.Process(target=analyze_rsi_bb, args=(symList[i + 1], 15, 0.99))
		
		t1.start()
		t2.start()

		t1.join()
		t2.join()


if __name__ == "__main__":
	#analyze_rsi_bb("BTC", 60, 0.995, 0.025)
	test_rsi_bb_parameters("BTC", 60, 4, 82, 16, 4, 3.0)
	#multiprocess_rsi_bb("BTC")

	#multiprocess_test_all()
	#print(get_price_differences("LINK"))
	#get_all_price_differences()

	#websocket()
	#get_orders()

