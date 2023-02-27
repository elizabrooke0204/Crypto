#!/usr/bin/env python3
"""
Module for function to send email.

Functions
---------
send_msg(msg)
	Send an MMS message to the designated email address.
"""
# Library imports
import smtplib

# File imports
from auth_cred import (gmail_account, gmail_password, phone_number)

def send_msg(msg):
	"""
	Send an MMS message to the designated email address.

	Parameters
	----------
	msg : str
		Message to be sent.
	"""

	try:
		server = smtplib.SMTP("smtp.gmail.com", 587)
		server.starttls()
		server.login(gmail_account, gmail_password)
		server.sendmail(gmail_account, phone_number, msg)
		server.quit()
	except Exception as err:
		print("COULD NOT SEND NOTIFICATION MESSAGE")
