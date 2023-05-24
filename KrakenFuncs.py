#!/usr/bin/env python3
"""
Module of functions used to interact with Kraken's cryptocurrency exchange API.

Functions
---------
kraken_order(price, side, altSymbol, altMarket)
	Places a market order on Kraken's exhchange and returns the server's response.
kraken_get_balance(altSymbol)
	Returns balance of currency in your Kraken account.
kraken_generate_signature(urlpath, data)
	Generates signature to create server request.
kraken_request(urlPath, data)
	Creates request for server.
kraken_get_assets()
	Returns all availbe assets on Kraken's exhchange.
"""

# Library imports
import base64
import hashlib
import hmac
import json
import requests
import time
import urllib.parse

# File imports
from auth_cred import (kraken_api_secret, kraken_api_key)


# ---------------------------------- Account functions ------------------------------------	

def kraken_order(price, side, altSymbol, altMarket, market):
	"""
	Places a market order on Kraken's exhchange and returns the server's response.

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

	Returns
	-------
	dict of {str : [str]}
		Server's request response as {"response-type", ["response"].
	"""

	if side == "sell":
		volume = float(kraken_get_balance(altSymbol)) * 0.99
	elif side == "buy":
		volume = float(kraken_get_balance(altMarket)) * 0.99 / price
	volume = str(volume)[:10]
	resp = kraken_request("/0/private/AddOrder", {
		"nonce": str(int(1000*time.time())),
		"ordertype": "market",
    	"type": side,
	    "volume": volume,
    	"pair": (altSymbol + market)
		})
	return resp.json()


def kraken_get_balance(altSymbol):
	"""
	Returns balance of currency in Kraken account.

	Parameters
	----------
	altSymbol : str
		Alternative symbol associated with the base currency of a trading pair.

	Returns
	-------
	dict of {str : [str]}
		Server's request response as {"response-type" : ["response"]}.
	"""

	resp = kraken_request('/0/private/Balance', {
	"nonce": str(int(1000*time.time()))})
	try:
		resp = resp.json()["result"][altSymbol]
		return resp
	except Exception as err:
		print(err)
		return None


# --------------------------------- Connection functions ----------------------------------

def kraken_generate_signature(urlPath, data):
	"""
	Generates signature to create server request.

	Parameters
	----------
	urlPath : str
		URL path for desired action.
	data : dict
		Information for desired action.

	Returns
	-------
	str
		Generated signature needed for server request.	
	"""

	postdata = urllib.parse.urlencode(data)
	encoded = (str(data['nonce']) + postdata).encode()
	message = urlPath.encode() + hashlib.sha256(encoded).digest()
	mac = hmac.new(base64.b64decode(kraken_api_secret), message, hashlib.sha512)
	sigdigest = base64.b64encode(mac.digest())
	return sigdigest.decode()


def kraken_request(urlPath, data):
	"""
	Creates request for server.

	Parameters
	----------
	urlPath : str
		URL path for desired action.
	data : dict
		Information for desired action.

	Returns
	-------
	requests.models.Response
		Response from server.
	"""

	apiUrl = "https://api.kraken.com"
	headers = {}
	headers["API-Key"] = kraken_api_key
	headers["API-Sign"] = kraken_generate_signature(urlPath, data)
	resp = requests.post((apiUrl + urlPath), headers=headers, data=data)
	return resp


# ---------------------------------- Exchange functions -----------------------------------

def kraken_get_assets():
	"""
	Returns all availbe assets on Kraken's exhchange.

	Returns
	-------
	dict of {"str" : {dict}}
		Avaible assets and asset information as {"symbol-name" : {symbol-information}}
	"""

	assets = requests.get('https://api.kraken.com/0/public/Assets').json()
	return assets['result']
