#!/usr/bin/env python3

import base64
import hashlib
import hmac
import json
import requests
import time
import urllib.parse
from auth_cred import (kraken_api_secret, kraken_api_key)

api_url = "https://api.kraken.com"


def kraken_order(price, side, altSymbol, altMarket):
	if side == "sell":
		volume = kraken_get_balance(altSymbol)
	elif side == "buy":
		volume = float(kraken_get_balance(altMarket)) / price
		volume = str(volume)[:10]
	resp = kraken_request("/0/private/AddOrder", {
		"nonce": str(int(1000*time.time())),
		"ordertype": "market",
    	"type": side,
	    "volume": volume,
    	"pair": (altSymbol + altMarket)
		})
	return resp.json()


def kraken_get_balance(altSymbol):
	resp = kraken_request('/0/private/Balance', {
	"nonce": str(int(1000*time.time()))})
	try:
		resp = resp.json()["result"][altSymbol]
		return resp
	except Exception as err:
		print(err)
		return None


def kraken_get_assets():
	assets = requests.get('https://api.kraken.com/0/public/Assets').json()
	return assets['result']


def kraken_request(uri_path, data):
	headers = {}
	headers["API-Key"] = kraken_api_key
	headers["API-Sign"] = kraken_generate_signature(uri_path, data)
	req = requests.post((api_url + uri_path), headers=headers, data=data)
	return req


def kraken_generate_signature(urlpath, data):
	postdata = urllib.parse.urlencode(data)
	encoded = (str(data['nonce']) + postdata).encode()
	message = urlpath.encode() + hashlib.sha256(encoded).digest()
	mac = hmac.new(base64.b64decode(kraken_api_secret), message, hashlib.sha512)
	sigdigest = base64.b64encode(mac.digest())
	return sigdigest.decode()