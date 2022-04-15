#!/usr/bin/env python3

# Library imports
import time
import requests
import threading
import cbpro
import pandas as pd
from datetime import datetime, timedelta
from colorama import Fore, Back, Style

# File imports
from HelperFuncs import *
from auth_cred import (api_secret, api_key, api_pass)

# Set url and authticate client
url = "https://api.pro.coinbase.com"
#url = "https://api-public.sandbox.pro.coinbase.com"
client = cbpro.AuthenticatedClient(api_key, api_secret, api_pass, api_url=url)

# global variables initial parameters
symbol = "LRC"
timeSlice = "60min"
outputSize = "compact"

rsiPeriodLength = 4
rsiUpperBound = 82.0
rsiLowerBound = 30.0
bbPeriodLength = 4
bbLevel = 3.0

inSellPeriod = False
inBuyPeriod = False
rsiSignal = "hold"
bbSignal = "hold"


# ----------------------------------- Strategy thread -------------------------------------

def run_strategy_rsi_bb(symbol, timeSlice, output_size):
	global rsiPeriodLength
	global rsiUpperBound
	global rsiLowerBound
	global bbPeriodLength
	global bbLevel
	global inSellPeriod
	global inBuyPeriod
	global rsiSignal
	global bbSignal
	sellLevel = 1
	buyLevel = 1
	stopLossUpper = 0.0
	stopLossLower = 0.0

	print("Strategy thread started")
	while(1):
		now = datetime.now()
		try:
			# Runs strategy every 5 minutes
			if (now.minute % 5) == 0:

				# Get rates, high/low average, rsi values and bb bands
				rates = get_historic_rates(symbol, timeSlice, outputSize)
				ratesHl2 = pd.Series((rates["High"] + rates["Low"]).div(2).values, index=rates.index)
				ratesRsi = get_rsi(ratesHl2, rsiPeriodLength)
				(bbUpper, bbMiddle, bbLower) = get_bb(ratesHl2, bbPeriodLength, bbLevel)

				# Sets rates, high/low average, rsi values and bb bands to lists of equal length
				ratesHigh = rates["High"].tolist()[(bbPeriodLength - 1):]
				ratesLow = rates["Low"].tolist()[(bbPeriodLength - 1):]
				ratesRsi = ratesRsi.tolist()[(bbPeriodLength - rsiPeriodLength):]
				bbUpper = bbUpper.tolist()[(bbPeriodLength - 1):]
				bbLower = bbLower.tolist()[(bbPeriodLength - 1):]

				# Determines sell, buy, or hold signals for rsi and bb
				if ratesRsi[-1] > rsiUpperBound:
					rsiSignal = "sell"
				elif ratesRsi[-1] < rsiLowerBound:
					rsiSignal = "buy"
				else:
					rsiSignal = "hold"

				if ratesHigh[-1] > bbUpper[-1]:
					bbSignal = "sell"
				elif ratesLow[-1] < bbLower[-1]:
					bbSignal = "buy"
				else:
					bbSignal = "hold"

				# Determines sell, buy, or hold action for bot
				if not inSellPeriod:
					if (rsiSignal == "sell") and (bbSignal == "sell"):
						inSellPeriod = True
						print(Fore.GREEN + "Sell signal" + Style.RESET_ALL)
				else:
					if (rsiSignal != "sell") and (bbSignal != "sell"):
						print(Fore.GREEN + "---Sell at {}---".format(now) + Style.RESET_ALL)
						print("level: {}".format(sellLevel))
						inSellPeriod = False

						if sellLevel == 1:
							sellLRC(1.0/3.0)
							buyLevel = 1
						elif sellLevel == 2:
							sellLRC(1.0/2.0)
							buyLevel = 1
						elif sellLevel >= 3:
							sellLRC(99.0/100.0)
							buyLevel = 2 

						stopLossUpper = ratesHigh[-1] * 1.02
						stopLossLower = 0.0
						sellLevel += 1

				if not inBuyPeriod:
					if (rsiSignal == "buy") and (bbSignal == "buy"):
						inBuyPeriod = True
						print(Fore.GREEN + "Buy signal" + Style.RESET_ALL)
				else:
					if (rsiSignal != "buy") and (bbSignal != "buy"):
						print(Fore.GREEN + "---Buy at {}---".format(now) + Style.RESET_ALL)
						print("level: {}:".format(buyLevel))
						inBuyPeriod = False

						if buyLevel == 1:
							buyLRC(1.0/3.0)
							sellLevel = 1
						elif buyLevel == 2:
							buyLRC(1.0/2.0)
							sellLevel = 1
						elif buyLevel >= 3:
							buyLRC(99.0/100.0)
							sellLevel = 2
							
						stopLossLower = ratesLow[-1] * 0.98
						stopLossUpper = 0.0
						buyLevel += 1

				if stopLossLower > 0.0:
					if (ratesLow[-1] * 0.975) > stopLossLower:
						stopLossLower = ratesLow[-1] * 0.98
					if ratesLow[-1] < stopLossLower:
						print(Fore.RED + "---StopLoss Sell at {}---".format(now) + Style.RESET_ALL)
						sellLRC(99.0 / 100.0)
						stopLossUpper = ratesHigh[-1] * 1.02
						stopLossLower = 0.0
						sellLevel = 1
						buyLevel = 1

				if stopLossUpper > 0.0:
					if (ratesHigh[-1] * 1.025) < stopLossUpper:
						stopLossUpper = ratesHigh[-1] * 1.02
					if ratesHigh[-1] > stopLossUpper:
						print(Fore.RED + "---StopLoss Buy at {}---".format(now) + Style.RESET_ALL)
						buyLRC(99.0 / 100.0)
						stopLossLower = ratesLow[-1] * 0.98
						stopLossUpper = 0.0
						sellLevel = 1
						buyLevel = 1

				
				print(Fore.YELLOW +
					"{} - RSI: {} BB: {}".format(now.strftime("%m/%d - %H:%M:%S"),rsiSignal, bbSignal) +
					Style.RESET_ALL)
				print("   RSI: {:.3f}, Upper: {}, Lower: {}".format(ratesRsi[-1], rsiUpperBound, rsiLowerBound))
				print("   bbUpper: {:.3f} - High: {:.3f} | Low: {:.3f} - bbLower: {:.3f}".format(bbUpper[-1], ratesHigh[-1], ratesLow[-1], bbLower[-1]))
				print("   StopLossUpper: {:.3f} | StopLossLower: {:.3f}".format(stopLossUpper, stopLossLower))

				time.sleep((60 * 4) - 10)
			else:
				time.sleep(2)

		# Catches error in Strategy thread and prints to screen
		except Exception as err:
			print(Fore.RED + "STRATEGY-ERROR. Reattempting in 10 seconds." + Style.RESET_ALL)
			print(err)
			time.sleep(10)


# ------------------------------------ Analyze thread -------------------------------------

def analyze_rsi_bb(symbol, timeSlice, output_size):
	global rsiPeriodLength
	global rsiUpperBound
	global rsiLowerBound
	global bbPeriodLength
	global bbLevel
	global inSellPeriod
	global inBuyPeriod

	print("Analyze thread started")
	while(1):
		now = datetime.now()
		try:
			# Runs analyze every hour
			if (now.minute == 0):
				print("Analyzing data")
				# Variable holders
				bestDelta = 0.0
				thisInSellPeriod = False
				thisInBuyPeriod = False

				rsiSignals = []
				bbSignals = []
				currentTopParameters = []
				topParameters = []

				rates = get_historic_rates(symbol, timeSlice, outputSize)
				ratesHl2Series = pd.Series((rates["High"] + rates["Low"]).div(2).values, index=rates.index)
				
				for thisRsiPeriodLength in range(3, 12):
					# Set RSI values
					ratesRsiSeries = get_rsi(ratesHl2Series, thisRsiPeriodLength)

					for thisRsiUpperBound in range(84, 62, -2):
						for thisRsiLowerBound in range(16, 38, 2):
							for thisBbPeriodLength in range(thisRsiPeriodLength, 26, 2):
								# Convert Pandas series to lists
								ratesHigh = rates["High"].tolist()[(thisBbPeriodLength - 1):]
								ratesLow = rates["Low"].tolist()[(thisBbPeriodLength - 1):]
								ratesHl2 = ratesHl2Series.tolist()[(thisBbPeriodLength - 1):]
								ratesRsi = ratesRsiSeries.tolist()[(thisBbPeriodLength - thisRsiPeriodLength):]
								dates = rates.index.tolist()[(thisBbPeriodLength - 1):]
						
								for bbLevelDouble in range(7, 14):
									usdStart = 100.0
									cryptoStart = 100.0 / ratesHl2[0]
									usdEnd = usdStart
									cryptoEnd = cryptoStart

									# Set BB values
									thisBbLevel = float(bbLevelDouble) / 4.0
									(bbUpperSeries, bbMiddleSeries, bbLowerSeries) = get_bb(ratesHl2Series, thisBbPeriodLength, thisBbLevel)

									# Convert Pandas series to lists
									bbUpper = bbUpperSeries.tolist()[(thisBbPeriodLength - 1):]
									bbLower = bbLowerSeries.tolist()[(thisBbPeriodLength - 1):]

									# Parse through data and determine sell, buy and hold signals for RSI and BB
									for i in range(len(dates)):
										if ratesRsi[i] > thisRsiUpperBound:
											rsiSignals.append("sell")
										elif ratesRsi[i] < thisRsiLowerBound:
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
										if not thisInSellPeriod:
											if (rsiSignals[i] == "sell") and (bbSignals[i] == "sell"):
												thisInSellPeriod = True
										else:
											if (rsiSignals[i] != "sell") and (bbSignals[i] != "sell"):
												usdEnd = usdEnd + (cryptoEnd * ratesHl2[i] * .995 * .95 )
												cryptoEnd = cryptoEnd * .05
												thisInSellPeriod = False

										if not thisInBuyPeriod:
											if (rsiSignals[i] == "buy") and (bbSignals[i] == "buy"):
												thisInBuyPeriod = True
										else:
											if (rsiSignals[i] != "buy") and (bbSignals[i] != "buy"):
												cryptoEnd = cryptoEnd + (usdEnd * .995 * .95 / ratesHl2[i])
												usdEnd = usdEnd * .05
												thisInBuyPeriod = False

									walletStart = 200.0
									walletEnd = usdEnd + (cryptoEnd * ratesHl2[-1])

									# Calculates action and no-action gains and losses
									noActionGainLoss = (ratesHl2[-1] - ratesHl2[0]) / (2 * ratesHl2[0])
									actionGainLoss = (walletEnd - walletStart) / walletStart
									delta = actionGainLoss - noActionGainLoss

									# Append newest top parameter combination
									if (delta > 0.0) and (delta >= bestDelta):
										bestDelta = delta
										currentTopParameters.append([delta, thisRsiPeriodLength, thisRsiUpperBound, thisRsiLowerBound,
											thisBbPeriodLength, thisBbLevel, thisInSellPeriod, thisInBuyPeriod])

									# Reset variable holders
									rsiSignals = []
									bbSignals = []
									thisInSellPeriod = False
									thisInBuyPeriod = False

					# Append top 3 parameter combinations for rsiPeriodLength
					currentTopParameters.reverse()
					if len(currentTopParameters) > 3:
						numberOfParameters = 3
					else:
						numberOfParameters = len(currentTopParameters)

					for i in range(numberOfParameters):
						topParameters.append(currentTopParameters[i])

					# Reset variable holders
					bestDelta = 0.0
					currentTopParameters = []

				# Print top parameter combinations if found
				if len(topParameters) > 0:
					print("delta, rsiP, rsiU, rsiL, bbP, bbLvl, sellAcPer, BuyActPer")
					topParameters.sort(reverse=True)
					for parameters in topParameters:
						print(parameters)

					# Updates parameters with new values
					rsiPeriodLength = topParameters[0][1]
					rsiUpperBound = topParameters[0][2]
					rsiLowerBound = topParameters[0][3]
					bbPeriodLength = topParameters[0][4]
					bbLevel = topParameters[0][5]
					if not inSellPeriod:
						inSellPeriod = topParameters[0][6]
					if not inBuyPeriod:
						inBuyPeriod = topParameters[0][7]

					print("Parameters updated to:")
					print(topParameters[0])

				else:
					print(Fore.RED +
						"No adequate parameters found. Reattempting analysis next hour." +
						Style.RESET_ALL)

				time.sleep(60 *30)

			else:
				time.sleep(10)

		# Catches error in Analyze thread and prints to screen
		except Exception as err:
			print(Fore.RED + "ANALYZE-ERROR. Reattempting in 10 seconds." + Style.RESET_ALL)
			print(err)
			time.sleep(10)


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
	return (round(float(price) * 1.001, 4))


def getBidPrice(symbolPair):
	price = client.get_product_ticker(product_id=symbolPair)["bid"]
	return (round(float(price) * 0.999, 4))


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


# ----------------------------------- Main functions -------------------------------------

def thread_analyze_and_strategy():
	strategyThread = threading.Thread(target=run_strategy_rsi_bb, args=(symbol, timeSlice, outputSize))
	analyzeThread = threading.Thread(target=analyze_rsi_bb, args=(symbol, timeSlice, outputSize))

	strategyThread.start()
	analyzeThread.start()


if __name__ == "__main__":
	thread_analyze_and_strategy()

