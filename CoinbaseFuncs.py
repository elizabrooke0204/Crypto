#!/usr/bin/env python3

#Library imports
import time
import cbpro
import csv
import json
import http.client
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from auth_cred import (cbp_api_secret, cbp_api_key, cbp_api_pass)
from auth_cred import (cb_api_secret, cb_api_key)

# Set url and authticate client
url = "https://api.pro.coinbase.com"
cbpClient = cbpro.AuthenticatedClient(cbp_api_key, cbp_api_secret, cbp_api_pass, api_url=url)


def cb_generate_signature(ts, method, url):
	message = ts + method + url
	return hmac.new(cb_api_secret.encode('utf-8'), message.encode('utf-8'), hashlib.sha256).hexdigest()


# ---------------------------------- Sell/Buy functions -----------------------------------

def cbp_sell_BTC(portion):
	trade = cbpClient.sell(price=str(cbp_get_ask_price("BTC-USD")),
		size=str(cbp_get_available_BTC(portion)),
		order_type="limit",
		product_id="BTC-USD",
		post_only=True)
	print(trade)


def cbp_sell_LRC(portion):
	trade = cbpClient.sell(price=str(cbp_get_ask_price("LRC-USD")),
		size=str(cbp_get_available_LRC(portion)),
		order_type="limit",
		product_id="LRC-USD",
		post_only=True)
	print(trade)


def cbp_buy_BTC(portion):
	trade = cbpClient.buy(price=str(cbp_get_bid_price("BTC-USD")),
		size=str(round(cbp_get_available_USD(portion) / cbp_get_bid_price("BTC-USD"), 4)),
		order_type="limit",
		product_id="BTC-USD",
		post_only=True)
	print(trade)


def cbp_buy_LRC(portion):
	trade = cbpClient.buy(price=str(cbp_get_bid_price("LRC-USD")),
		size=str(round(cbp_get_available_USD(portion) / cbp_get_bid_price("LRC-USD"), 6)),
		order_type="limit",
		product_id="LRC-USD",
		post_only=True)
	print(trade)


# ------------------------------------ Get-Functions -------------------------------------

def cbp_get_ask_price(symbolPair):
	price = cbpClient.get_product_ticker(product_id=symbolPair)["ask"]
	return (round(float(price) * 0.9995, 4))


def cbp_get_bid_price(symbolPair):
	price = cbpClient.get_product_ticker(product_id=symbolPair)["bid"]
	return (round(float(price) * 1.0005, 4))


def cbp_get_available_BTC(portion):
	accounts = cbpClient.get_accounts()
	for account in accounts:
		if (account["currency"] == "BTC"):
			return (round(float(account["available"]) * portion, 5))


def cbp_get_available_LRC(portion):
	accounts = cbpClient.get_accounts()
	for account in accounts:
		if (account["currency"] == "LRC"):
			return (round(float(account["available"]) * portion, 6))


def cbp_get_available_USD(portion):
	accounts = cbpClient.get_accounts()
	for account in accounts:
		if (account["currency"] == "USD"):
			return (round(float(account["available"]) * portion, 2))


def cbp_get_orders():
	orders = cbpClient.get_orders()
	for order in orders:
		print(order)


def cb_get_currency(symbol):
	currencies = get_currencies()
	try:
		return currencies.loc[symbol].to_dict()
	except Exception as err:
		print("could not retrieve currency in wallet")


def cb_get_currencies():
	try:
		ts = str(int(time.time()))
		path_url = "/api/v3/brokerage/accounts"
		signature = cb_generate_signature(ts, "GET", path_url)
		conn = http.client.HTTPSConnection("api.coinbase.com")
		payload = ''
		headers = {
			"User-Agent": "LS",
			"CB-ACCESS-KEY": cb_api_key,
			"CB-ACCESS-TIMESTAMP": ts,
			"CB-ACCESS-SIGN": signature,
			"Content-Type": "application/json"}

		conn.request("GET", path_url, payload, headers)
		res = conn.getresponse()
		data = res.read().decode("utf-8")
		accounts = pd.DataFrame(json.loads(data))
		accounts = pd.json_normalize(accounts.accounts)
		accounts = accounts.drop(columns=["active", "available_balance.currency", "created_at",
			"deleted_at", "default", "hold.currency", "hold.value", "name", "ready", "type", "updated_at"])
		accounts = accounts.rename(columns={"currency": "name", "available_balance.value": "balance"})
		accounts = accounts.set_index("name")
		return accounts
	except Exception as err:
		print("could not retrieve currencies in wallet")

