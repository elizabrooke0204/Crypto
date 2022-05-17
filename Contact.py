#!/usr/bin/env python3

import smtplib
from auth_cred import (gmail_account, gmail_password, phone_number)

def send_msg(msg):
	try:
		server = smtplib.SMTP( "smtp.gmail.com", 587 )
		server.starttls()
		server.login(gmail_account, gmail_password)
		server.sendmail("LeavingSnail", phone_number, msg)
		server.quit()
	except Exception as err:
		print("COULD NOT SEND NOTIFICATION MESSAGE")
