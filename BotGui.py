#!/usr/bin/env python3

# Kivy library imports
from kivy.lang import Builder
from kivymd.app import MDApp
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.properties import StringProperty
from kivy.properties import ObjectProperty
from kivy.properties import NumericProperty
from kivy.properties import BooleanProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.garden.matplotlib.backend_kivyagg import FigureCanvasKivyAgg

# Library imports
import time
import requests
import threading
import cbpro
import pandas as pd
from datetime import datetime, timedelta
from colorama import Fore, Back, Style
import matplotlib.pyplot as plt

# File imports
from HelperFuncs import *
from Contact import *
from auth_cred import (api_secret, api_key, api_pass)

# Set url and authticate client
url = "https://api.pro.coinbase.com"
#url = "https://api-public.sandbox.pro.coinbase.com"
client = cbpro.AuthenticatedClient(api_key, api_secret, api_pass, api_url=url)

fig, (ax1, ax2) = plt.subplots(2)
Window.size = (1000, 700)

# global variables initial parameters
symbol = "LRC"
timeSlice = "15min"
outputSize = "full"


class Bot(BoxLayout):
	# sets properties
	seconds_string = StringProperty("")
	rsiPeriodLength = NumericProperty(3)
	rsiUpperBound = NumericProperty(76.0)
	rsiLowerBound = NumericProperty(16.0)
	bbPeriodLength = NumericProperty(5)
	bbLevel = NumericProperty(2.5)
	inSellPeriod = BooleanProperty(False)
	inBuyPeriod = BooleanProperty(False)
	rsiSignal = StringProperty("hold")
	bbSignal = StringProperty("hold")

	sellLevel = 1
	buyLevel = 1
	stopLossUpper = 0.0
	stopLossLower = 0.0
	stopLossPortion = 0.0235

	def __init__(self, **kwargs):
		super().__init__(**kwargs)

		# Adds graph box
		self.graphBox = self.ids.graphBox
		self.graphBox.add_widget(FigureCanvasKivyAgg(plt.gcf()))


	def run_strategy_rsi_bb(self, rates):
		try:
			# Get rates, high/low average, rsi values and bb bands
			now = datetime.now()
			ratesHl2 = pd.Series((rates["High"] + rates["Low"]).div(2).values, index=rates.index)
			ratesRsi = get_rsi(ratesHl2, self.rsiPeriodLength)
			(bbUpper, bbMiddle, bbLower) = get_bb(ratesHl2, self.bbPeriodLength, self.bbLevel)

			# Sets rates, high/low average, rsi values and bb bands to lists of equal length
			ratesHigh = rates["High"].tolist()[(self.bbPeriodLength - 1):]
			ratesLow = rates["Low"].tolist()[(self.bbPeriodLength - 1):]
			ratesRsi = ratesRsi.tolist()[(self.bbPeriodLength - self.rsiPeriodLength):]
			bbUpper = bbUpper.tolist()[(self.bbPeriodLength - 1):]
			bbMiddle = bbMiddle.tolist()[(self.bbPeriodLength - 1):]
			bbLower = bbLower.tolist()[(self.bbPeriodLength - 1):]

			# Determines sell, buy, or hold signals for rsi and bb
			if ratesRsi[-1] > self.rsiUpperBound:
				self.rsiSignal = "sell"
			elif ratesRsi[-1] < self.rsiLowerBound:
				self.rsiSignal = "buy"
			else:
				self.rsiSignal = "hold"

			if ratesHigh[-1] > bbUpper[-1]:
				self.bbSignal = "sell"
			elif ratesLow[-1] < bbLower[-1]:
				self.bbSignal = "buy"
			else:
				self.bbSignal = "hold"

			# Determines sell, buy, or hold action for bot
			if not self.inSellPeriod:
				if (self.rsiSignal == "sell") and (self.bbSignal == "sell"):
					self.inSellPeriod = True
					send_msg("Sell signal triggered")
					print(Fore.GREEN + "Sell signal" + Style.RESET_ALL)
			else:
				if (self.rsiSignal != "sell") and (self.bbSignal != "sell"):
					send_msg("SELL - {}\nlevel: {}".format(ratesLow[-1], self.sellLevel))
					print(Fore.GREEN + "---Sell at {}---".format(now) + Style.RESET_ALL)
					print("level: {}".format(self.sellLevel))
					self.inSellPeriod = False

					if self.sellLevel == 1:
						sellLRC(1.0/2.0)
						self.buyLevel = 1
					elif self.sellLevel == 2:
						sellLRC(99.0/100.0)

					if self.sellLevel < 3:
						self.stopLossUpper = bbMiddle[-1] * (1.0 + self.stopLossPortion)
						self.stopLossLower = 0.0
						self.sellLevel += 1

			if not self.inBuyPeriod:
				if (self.rsiSignal == "buy") and (self.bbSignal == "buy"):
					self.inBuyPeriod = True
					send_msg("Buy signal triggered")
					print(Fore.GREEN + "Buy signal" + Style.RESET_ALL)
			else:
				if (self.rsiSignal != "buy") and (self.bbSignal != "buy"):
					send_msg("BUY - {}\nlevel: {}".format(ratesHigh[-1], self.sellLevel))
					print(Fore.GREEN + "---Buy at {}---".format(now) + Style.RESET_ALL)
					print("level: {}:".format(self.buyLevel))
					self.inBuyPeriod = False

					if self.buyLevel == 1:
						buyLRC(1.0/2.0)
						self.sellLevel = 1
					elif self.buyLevel == 2:
						buyLRC(99.0/100.0)

					if self.buyLevel < 3:	
						self.stopLossLower = bbMiddle[-1] * (1.0 - self.stopLossPortion)
						self.stopLossUpper = 0.0
						self.buyLevel += 1

			if self.stopLossLower > 0.0:
				if (bbMiddle[-2] * (1.0 - self.stopLossPortion)) > self.stopLossLower:
					self.stopLossLower = bbMiddle[-2] * (1.0 - self.stopLossPortion)
				if ratesLow[-1] < self.stopLossLower:
					send_msg("STOPLOSS SELL - {}".format(ratesLow[-1]))
					print(Fore.RED + "---StopLoss Sell at {}---".format(now) + Style.RESET_ALL)
					sellLRC(99.0 / 100.0)
					self.stopLossUpper = bbMiddle[-1] * (1.0 + self.stopLossPortion)
					self.stopLossLower = 0.0
					self.sellLevel = 1
					self.buyLevel = 1

			if self.stopLossUpper > 0.0:
				if (bbMiddle[-2] * (1.0 + self.stopLossPortion)) < self.stopLossUpper:
					self.stopLossUpper = bbMiddle[-2] * (1.0 + self.stopLossPortion)
				if ratesHigh[-1] > self.stopLossUpper:
					send_msg("STOPLOSS SELL - {}".format(ratesLow[-1]))
					print(Fore.RED + "---StopLoss Buy at {}---".format(now) + Style.RESET_ALL)
					buyLRC(99.0 / 100.0)
					self.stopLossLower = bbMiddle[-1] * (1.0 - self.stopLossPortion)
					self.stopLossUpper = 0.0
					self.sellLevel = 1
					self.buyLevel = 1
			
			print(Fore.YELLOW +
				"{} - RSI: {} BB: {}".format(now.strftime("%m/%d - %H:%M:%S"),self.rsiSignal, self.bbSignal) +
				Style.RESET_ALL)
			print("   RSI: {:.3f}, Upper: {}, Lower: {}".format(ratesRsi[-1], self.rsiUpperBound, self.rsiLowerBound))
			print("   bbUpper: {:.3f} - High: {:.3f} | Low: {:.3f} - bbLower: {:.3f}".format(bbUpper[-1], ratesHigh[-1], ratesLow[-1], bbLower[-1]))
			print("   self.stopLossUpper: {:.3f} | self.stopLossLower: {:.3f}".format(self.stopLossUpper, self.stopLossLower))

		# Catches error in Strategy thread and prints to screen
		except Exception as err:
			send_msg("STRATEGY-ERROR\nCheck to see if bot is functioning")
			print(Fore.RED + "STRATEGY-ERROR." + Style.RESET_ALL)
			print(err)


	def analyze_rsi_bb(self):
		print("Analyze thread started")
		now = datetime.now()
		try:
			# Runs analyze every hour
			print("Analyzing data")
			# Variable holders
			bestDelta = 0.0
			portion = 0.95

			stopLossLower = 0.0
			stopLossUpper = 0.0
			stopLossPortion = 0.0235
			thisInSellPeriod = False
			thisInBuyPeriod = False

			rsiSignals = []
			bbSignals = []
			currentTopParameters = []
			topParameters = []

			rates = get_historic_rates(symbol, timeSlice, outputSize)
			rates = rates.tail(250)
			ratesHl2Series = pd.Series((rates["High"] + rates["Low"]).div(2).values, index=rates.index)
			
			for thisRsiPeriodLength in range(3, 11):
				# Set RSI values
				ratesRsiSeries = get_rsi(ratesHl2Series, thisRsiPeriodLength)

				for thisRsiUpperBound in range(84, 62, -2):
					for thisRsiLowerBound in range(16, 38, 2):
						for thisBbPeriodLength in range(thisRsiPeriodLength, 18, 2):
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
								bbMiddle = bbMiddleSeries.tolist()[(thisBbPeriodLength - 1):]
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
											usdEnd = usdEnd + (cryptoEnd * ratesHl2[i] * .995 * portion)
											cryptoEnd = cryptoEnd * (1.0 - portion)
											stopLossUpper = bbMiddle[i] * (1.0 + stopLossPortion)
											stopLossLower = 0.0
											thisInSellPeriod = False

									if not thisInBuyPeriod:
										if (rsiSignals[i] == "buy") and (bbSignals[i] == "buy"):
											thisInBuyPeriod = True
									else:
										if (rsiSignals[i] != "buy") and (bbSignals[i] != "buy"):
											cryptoEnd = cryptoEnd + (usdEnd * .995 * portion / ratesHl2[i])
											usdEnd = usdEnd * (1.0 - portion)
											stopLossLower = bbMiddle[i] * (1.0 - stopLossPortion)
											stopLossUpper = 0.0
											thisInBuyPeriod = False

									if stopLossLower > 0.0:
										if (bbMiddle[i] * (1.0 - stopLossPortion)) > stopLossLower:
											stopLossLower = bbMiddle[i] * (1.0 - stopLossPortion)
										if ratesLow[i] < stopLossLower:
											usdEnd = usdEnd + (cryptoEnd * ratesHl2[i] * .995 * portion)
											cryptoEnd = cryptoEnd * (1.0 - portion)
											stopLossUpper = bbMiddle[i] * (1.0 + stopLossPortion)
											stopLossLower = 0.0

									if stopLossUpper > 0.0:
										if (bbMiddle[i] * (1.0 + stopLossPortion)) < stopLossUpper:
											stopLossUpper = bbMiddle[i] * (1.0 + stopLossPortion)
										if ratesHigh[i] > stopLossUpper:
											cryptoEnd = cryptoEnd + (usdEnd * .995 * portion / ratesHl2[i])
											usdEnd = usdEnd * (1.0 - portion)
											stopLossLower = bbMiddle[i] * (1.0 - stopLossPortion)
											stopLossUpper = 0.0

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
				self.rsiPeriodLength = topParameters[0][1]
				self.rsiUpperBound = topParameters[0][2]
				self.rsiLowerBound = topParameters[0][3]
				self.bbPeriodLength = topParameters[0][4]
				self.bbLevel = topParameters[0][5]

				print("Parameters updated to:")
				print(topParameters[0])

			else:
				print(Fore.RED +
					"No adequate parameters found. Reattempting analysis next hour." +
					Style.RESET_ALL)

		# Catches error in Analyze thread and prints to screen
		except Exception as err:
			send_msg("ANALYZE-ERROR\nCheck to see if bot is functioning")
			print(Fore.RED + "ANALYZE-ERROR." + Style.RESET_ALL)
			print(err)


	def update_variables(self, rates):
		ratesHl2 = pd.Series((rates["High"] + rates["Low"]).div(2).values, index=rates.index)
		ratesRsi = get_rsi(ratesHl2, self.rsiPeriodLength)
		(bbUpper, bbMiddle, bbLower) = get_bb(ratesHl2, self.bbPeriodLength, self.bbLevel)

		self.ids.open_var.text = (str(rates["Open"].iloc[-1]))[:5]
		self.ids.high_var.text = (str(rates["High"].iloc[-1]))[:5]
		self.ids.low_var.text = (str(rates["Low"].iloc[-1]))[:5]
		self.ids.close_var.text = (str(rates["Close"].iloc[-1]))[:5]

		self.ids.bb_upper_var.text = (str(bbUpper.iloc[-1]))[:5]
		self.ids.bb_lower_var.text = (str(bbLower.iloc[-1]))[:5]
		self.ids.rsi_upper_var.text = (str(self.rsiUpperBound))[:5]
		self.ids.rsi_var.text = (str(ratesRsi.iloc[-1]))[:5]
		self.ids.rsi_lower_var.text = (str(self.rsiLowerBound))[:5]

		self.ids.stoploss_upper_var.text = (str(self.stopLossUpper))[:5]
		self.ids.stoploss_lower_var.text = (str(self.stopLossLower))[:5]

		# Clear plot and widget, set new plot and widget
		plt.cla()
		ax1.cla()
		ax2.cla()
		self.graphBox.clear_widgets()
		Bot.add_plot(self, ratesHl2)
		Bot.add_rsi_plot(self, ratesHl2)
		self.graphBox.add_widget(FigureCanvasKivyAgg(plt.gcf()))


	# Adds new data to plt
	def add_plot(self, ratesHl2):
		size = 150
		(bbUpper, bbMiddle, bbLower) = get_bb(ratesHl2, self.bbPeriodLength, self.bbLevel)
		ax1.plot(bbUpper.tail(size), label="Bollinger Up", c="b")
		ax1.plot(bbMiddle.tail(size), label="Bollinger Middle", c="black")
		ax1.plot(bbLower.tail(size), label="Bollinger Down", c="b")
		ax1.plot(ratesHl2.tail(size), label="Rates", c="g")
		ax1.set_xticks([0,
			int(size / 5) - 1,
			int(size * 2 / 5) - 1,
			int(size * 3 / 5) - 1,
			int(size * 4 / 5) - 1,
			size - 1])
		ax1.tick_params(labelsize=5, labelrotation=0)
		ax1.grid()

	def add_rsi_plot(self, ratesHl2):
		size = 150
		rsi = get_rsi(ratesHl2, self.rsiPeriodLength)
		#plt = plot_rsi(rsi, self.rsiUpperBound, self.rsiLowerBound)
		ax2.plot(rsi.tail(size), label="RSI", c="r")
		ax2.axhline(y=self.rsiUpperBound, color='r', linestyle='--')
		ax2.axhline(y=self.rsiLowerBound, color='r', linestyle='--')
		ax2.set_xticks([0,
			int(size / 5) - 1,
			int(size * 2 / 5) - 1,
			int(size * 3 / 5) - 1,
			int(size * 4 / 5) - 1,
			size - 1])
		ax2.tick_params(labelsize=5, labelrotation=0)
		ax2.grid()


class MainApp(MDApp):
	def build(self):
		# Runs every designated amount of seconds
		Clock.schedule_interval(lambda dt: self.update_screen(), 1)
		self.theme_cls.theme_style = "Dark"
		self.theme_cls.primary_palette = "BlueGray"
		Builder.load_file("Bot.kv")
		send_msg("Bot started")
		return Bot()

	def update_screen(self):
		self.root.seconds_string = time.strftime("%S")
		# STATEGY THREAD
		if time.strftime("%S") == "00":
			if float(time.strftime("%-M")) % 5 == 0:
				try:
					rates = get_historic_rates(symbol, timeSlice, outputSize)

					# ANALYZE THREAD
					if time.strftime("%M") == "00":
						analyzeThread = threading.Thread(target=self.root.analyze_rsi_bb, daemon=True)
						analyzeThread.start()

					self.root.run_strategy_rsi_bb(rates.tail(500))
					self.root.update_variables(rates.tail(500))
				except Exception as err:
					print(Fore.RED + "UPDATE-SCREEN-ERROR." + Style.RESET_ALL)
					print(err)


if __name__ == "__main__":
	MainApp().run()
