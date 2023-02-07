#!/usr/bin/env python3

#Library imports
import csv
import pandas as pd
from datetime import datetime
from colorama import Fore
from colorama import Back
from colorama import Style
from Contact import *
from KrakenFuncs import *


# ------------------------------- Bot-helper functions ---------------------------------

def create_order(price, side, altSymbol, altMarket):
		now = datetime.now()
		send_msg(side + " - " + str(price))
		print(Fore.RED + "---" + side + " at {}---".format(now) + Style.RESET_ALL)
		print(kraken_order(price, side, altSymbol, altMarket))
		append_order_to_csv(now.strftime("%m/%d - %H:%M:%S"), price, side)


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





