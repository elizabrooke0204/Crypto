#!/usr/bin/env python3
"""
Module of functions to create and keep records of cryptocurrency orders.

Functions
---------
create_order(price, side, altSymbol, altMarket)
	Places a market order.
append_order_to_csv(date, price, side)
	Appends order information to csv file.
get_order_history()
	Returns order history from csv as pandas.DataFrame.
"""

# Library imports
import csv
import pandas as pd
from colorama import Fore
from colorama import Back
from colorama import Style
from datetime import datetime

# File imports
from Contact import *
from KrakenFuncs import *


# ------------------------------- Bot-helper functions ---------------------------------

def create_order(price, side, altSymbol, altMarket):
	"""
	Places a market order. 

	Places an order through Kraken, prints order information to screen, sends email 
	notifcation to user, and appends order information to csv file.

	Parameters
	----------
	price : float
		The current price of the cryptocurrency.
	side : str
		Either "buy" or "sell" for order side.
	altSymbol : str
		Alternative symbol associated with the base currency of a trading pair.
	altMarket : str
		Alternative symbol associated with the quote currency of a trading pair.
	"""

	now = datetime.now()
	print(kraken_order(price, side, altSymbol, altMarket))
	print(Fore.RED + "---" + side + " at {}---".format(now) + Style.RESET_ALL)
	send_msg(side + " - " + str(price))
	append_order_to_csv(now.strftime("%m/%d - %H:%M:%S"), price, side)


def append_order_to_csv(date, price, side):
	"""
	Appends order information to csv file.

	Parameters
	----------
	date : str
		Date and time of placed order.
	price : float
		The current cryptocurrency price.
	side : str
		Either "buy" or "sell" for order side.
	"""

	with open("order_history.csv", "a") as f:
		writerObj = csv.writer(f)
		writerObj.writerow([date, price, side])
		f.close()


def get_order_history():
	"""
	Returns past order history from csv file as pandas.DataFrame.

	Returns
	-------
	pandas.DataFrame of [str, numpy.float64, str]
		History of past order information as ["Date", Price, "Side"].
	"""

	try:
		orders = pd.read_csv("order_history.csv", index_col=0)
		return orders
	except Exception as err:
		print("CSV is empty or does not exist")





