# Crypto Trading Bot 

This project is a single page application that analyzes a specified cryptocurrency trading pair, graphs market data, and automates buy and sell orders.

![Bot screen shot](https://raw.githubusercontent.com/BrockBasil/Crypto/master/assets/images/BotScreenShot.png)

## Table of Contents
* [Description](https://github.com/BrockBasil/Crypto#description)
*  [Install and Setup](https://github.com/BrockBasil/Crypto#install-and-setup)
* [Configure and Run](https://github.com/BrockBasil/Crypto#configure-and-run)
* [Exchanges](https://github.com/BrockBasil/Crypto#exchanges)
* [Disclaimer](https://github.com/BrockBasil/Crypto#disclaimer)

## Description
This bot implements a Relative Strength Index (RSI) and Bollinger Band (BB) strategy with a trailing stop-loss percentage (read more about strategy below). Recent historic rates, RSI, and BB data is plotted in a graph on the left side of the window and most current values are displayed in a table to the right. The bot will periodically analyze the recent historic rates with different parameter combinations and reconfigure the strategy parameters with the current, most efficient combination. When buy or sell conditions are met the bot will place an appropriate market order and send a text message to the user with the action and price. The GUI is constructed using the Kivy framework and currently includes the following API's for various functionalities:
- **Coinbase Exchange**
- **Coinbase Pro (Deprecated)**
- **Kraken**

Please consult the following articles on Investopedia's website if you would like to learn more about the different components used in this strategy:
- [RSI indicator - Investopedia](https://www.investopedia.com/terms/r/rsi.asp)
- [BB indicator - Investopedia](https://www.investopedia.com/terms/b/bollingerbands.asp)
- [Trailing Stop Loss - Investopedia](https://www.investopedia.com/articles/trading/08/trailing-stop-loss.asp)

## Install and Setup
1. Please start by opening a terminal window and cloning the repository to your local machine.
```
git clone https://github.com/BrockBasil/Crypto.git
```
2. Create a new file named 'auth_cred.py' and save it inside the Crypto folder. This will hold the credentials needed to connect to the various APIs.

3. Create Kraken account and API key.
	- Navigate to Kraken's website at [Kraken](https://www.kraken.com/) and create an account. Kraken provides further assistance for account setup at [Account Setup - Kraken](https://support.kraken.com/hc/en-us/articles/226090548-How-to-create-an-account-on-Kraken).
	- After creating and activating your account you can now make your initial deposit to start trading. Kraken gives more explaination for depositing a currency at [Deposit Local Currency - Kraken](https://support.kraken.com/hc/en-us/articles/360049073651-How-do-I-deposit-my-local-currency-to-Kraken-). Most markets have a minimum order size roughly equivalent to $5 - $15 USD. Please refer to Kraken's article at [Order Minimum - Kraken](https://support.kraken.com/hc/en-us/articles/205893708-Minimum-order-size-volume-for-trading) to assure you have enough of your desired currency.
	- Create an API key and set the appropriate configurations by following Kraken's guide at [API Key Setup - Kraken](https://support.kraken.com/hc/en-us/articles/360000919966-How-to-create-an-API-key) and make sure the following permissions are allowed:
	
		- :ballot_box_with_check: **Query Funds**
		- :ballot_box_with_check: **Query Open Orders & Trades**
		- :ballot_box_with_check: **Query Closed Orders & Trades**
		- :ballot_box_with_check: **Modify Orders**
		- :ballot_box_with_check: **Cancel/Close Orders**
	- After generating, save your API key and private key in 'auth_cred.py'	as string variables.
```python
kraken_api_key = "<YOUR_API_KEY>"
kraken_api_secret = "<YOUR_PRIVATE_KEY>"
```
4. Create Gmail account and App Password.
	- Navigate to Google's website at [Gmail Account Setup](https://accounts.google.com/signup/v2/webcreateaccount?biz=false&cc=US&continue=https%3A%2F%2Fmail.google.com%2Fmail%2Fu%2F0%2F&dsh=S1074751825%3A1675891081117751&emr=1&flowEntry=SignUp&flowName=GlifWebSignIn&followup=https%3A%2F%2Fmail.google.com%2Fmail%2Fu%2F0%2F&ifkv=AWnogHfIJZsjYmsdrz2_4_skT0VDbQAPssPrmrL2pezBK9cppfPuutqTv9dX-kOlhr00sa0_mzRJcA&osid=1&service=mail) to create a Gmail account that will be used to send messages.
	-  After creating account and signing in, click your account icon in the top right corner of the page and select 'Manage your Google Account'.
	- Next navigate to the 'Security' section using the navigation bar on the left side of the page.
	- Under 'Signing in to Google' click 'App passwords' and generate a password on the next page after entering 'Select App' and 'Select device'.
	- After generating a password, save your email address and app password in 'auth_cred.py'	as string variables.
	- Finally, identify your mobile phone carrier's MMS gateway address. Major US carriers can be found at Lifewire's website [Lifewire SMS and MMS Gateways](https://www.lifewire.com/sms-gateway-from-email-to-sms-text-message-2495456), other carriers will have to be searched for online. Save your phone number and carrier MMS gateway as string variable in 'auth_cred.py' in the format <phone_number@mms_address>.
example: '1234567890@vzwpix.com'.
```python
gmail_account = "<YOUR_GMAIL>@gmail.com"
gmail_password = "<YOUR_APP_PASSWORD>"
phone_number = "<YOUR_PHONE_NUMBER>@<MMS_GATEWAY>"
```

## Configure and Run
1. Open the 'config.ini' file to enter your preferred market information by following Kraken's symbol (asset code) naming convention found at [Kraken Asset Codes](https://support.kraken.com/hc/en-us/articles/360001185506-How-to-interpret-asset-codes).
	- Please review Krakens note at the top of the page when entering the alternative asset codes in to 'altSymbol' and 'altMarket':
	
		> Asset codes starting with '**X**' represent **cryptocurrencies**, though this convention is no longer followed for newer coin listings.
		>
		> Asset codes starting with '**Z**' represent  **cash**.
	- Enter regular asset codes in to 'symbol' and 'market', choose between 1, 5, 15, or 60 minutes for 'timeSlice', and pick your trailing stop-loss percentage in decimal form for 'stopLossPortion'.
	- Example of 'config.ini' file trading in the bitcoin - US dollar (BTC-USD) market using 60-minute candlestick chart with a 3% trailing stop-loss.
```ini
[settings]
symbol = BTC
altSymbol = XXBT
market = USD
altMarket = ZUSD
timeSlice = 60
stopLossPortion = 0.03
```
2. Install the required packages and the specified versions listed in 'requirements.txt' if you haven't already done so.
```
cbpro==1.1.4
colorama==0.4.4
Kivy==2.1.0
kivymd==1.0.0.dev0
matplotlib==3.1.3
numpy==1.20.0
pandas==1.2.1
requests==2.28.2
```
3. Finally, open a terminal window and navigate to the 'Crypto' folder, modify BotGui.py to be an executable file, and run the program to deploy the bot.
```
chmod +x BotGui.py
./BotGui.py
```

## Exchanges
* Coinbase Pro (Deprecated)
* Kraken

## Disclaimer
**DO NOT RISK MONEY THAT YOU CANNOT AFFORD TO LOSE.** Trading cryptocurrency is a highly volatile market that holds just as much opportunity for loss as it does for profit. Always research a market pair in depth before deciding to invest any amount of money into it. Please feel free to run this bot on any market pair of your choosing **BEFORE** depositing money into your account to test how it will perform. You will continue to be notified on the prices at which it would have bought or sold.