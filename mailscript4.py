#!/usr/bin/env python
#coding=utf8
from cStringIO import StringIO
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.header import Header
from email import Charset
from email.generator import Generator
from email.utils import formataddr 
from configobj import ConfigObj
from os.path import splitext
import sys
import smtplib
import codecs
import getpass

def AppendFilename(filename, appendix):
	splitFilename = splitext(filename)
	return splitFilename[0] + appendix + splitFilename[1]

def ParseAddresses(addresses):
	"""Parse display names and email addresses from a string.

	The single input is a string containing addresses formated Microsoft
	Outlook-style, e.g.:

	John Doe <jdoe@somewhere.com>; Anderson, Dale <danderson@another.com>;
	Julie Roe <jroe@somewhere.org>

	The string of addresses must consist of display names and email addresses;
	the email addresses must be contained within angle brackets.

	Addresses pairs are separated by a semicolon and a space.

	The function returns a list of tuples. The first item in tuple is the
	display name, and the second item in the tuple is the email address.
	"""
	# Strip extra leading and trailing space from the string
	addresses = addresses.strip()

	# Split the addresses into a list, using the semicolon as a
	# delimiter
	addresses = addresses.split(';')

	# Create a new list to hold the formatted name and address pairs
	addressPairs = []

	for x in addresses:
		x = x.strip()
		if x != '':	# If a list item is not an empty string, parse it
			# Split out the display name from the address
			addressParts = x.split(' <')
			displayName = addressParts[0]
			# The address will have a '>' on the end of it, so take it out
			address = addressParts[1].split('>')[0]
			# Add the address to the list
			addressPairs.append((displayName, address))

	# Return the dictionary
	return addressPairs

def FormatAddresses(displayName, address):
	"""Format display name-address pairs for an email header.


	"""
	return '"{0}" <{1}>'.format(Header(displayName, 'utf-8'), address)

def RFC_AddressString(addresses, *numberNeeded):
	"""Output a string of Outlook-formatted addresses formatted for an RFC header.

	"""
	listOfAddressPairs = []
	for addressPair in ParseAddresses(addresses):
		displayName = addressPair[0]
		email = addressPair[1]
		addressPairStr = FormatAddresses(displayName, email)
		listOfAddressPairs.append(addressPairStr)
	
	if numberNeeded == ():
		return ', '.join(listOfAddressPairs)
	else:
		index = numberNeeded[0]
		if (isinstance(index, int) == True):
			if index < 1:
				print "ERROR: Number of addresses needed is less than 1"
			else:
				return ', '.join(listOfAddressPairs[:index])
		else:
			print "ERROR: Number of addresses isn't an int"

def AddressList(addresses):
	"""Create a list of email addresses from an Outlook-formatted string
	"""
	listOfAddresses = []
	for addressPair in ParseAddresses(addresses):
		listOfAddresses.append(addressPair[1])
	
	return listOfAddresses
	
# Create a dictionary for all the filenames
filenames = {}

# Read settings from an INI file
filenames['Settings'] = sys.argv[1]
settings = ConfigObj(filenames['Settings'])

filenames['Original'] = settings['original_HTML']
filenames['Mail'] = AppendFilename(filenames['Original'],"-mail")
filenames['Text'] = splitext(filenames['Original'])[0] + ".txt"

# Tip: To generate a plain-text version of the HTML file:
# $ lynx -display_charset=utf-8 -width=1024 -dump htmlnewsletter.html > htmlnewsletter.txt

# Default encoding mode set to Quoted Printable. Acts globally!
Charset.add_charset('utf-8', Charset.QP, Charset.QP, 'utf-8')
 
# 'alternative' MIME type --- HTML and plain text bundled in one e-mail message
msg = MIMEMultipart('alternative')

# Create subject line. This is converted to non-Unicode because of the use of str().
msg['Subject'] = str(Header(settings['Subject'], 'utf-8'))

# Create and format From line
msg['From'] = RFC_AddressString(settings['From'], 1) # Only take the first pair

# Create To line
msg['To'] = RFC_AddressString(settings['To'])

if ('Reply-To' in settings) & (settings['Reply-To'] != ''):
	msg['Reply-To'] = RFC_AddressString(settings['Reply-To'])

# Read in data for the message body from files
text = codecs.open(filenames['Text'], 'r', 'utf-8').read()
html = codecs.open(filenames['Mail'], 'r', 'utf-8').read()

# Use this if you don't want to use UTF-8
# html = open(htmlcontent, 'r').read()
 
# Encode and attach both parts to the message. The text part should come first.
textpart = MIMEText(text.encode('utf-8'), 'plain', 'UTF-8')
htmlpart = MIMEText(html.encode('utf-8'), 'html', 'UTF-8')
msg.attach(textpart)
msg.attach(htmlpart)

# Parse out the username from the From address
fromUser = ParseAddresses(settings['From'])[0][1].split('@')[0]

# Parse out the email address from the From address
fromEmail = ParseAddresses(settings['From'])[0][1]

# Make a list of addresses
emailList = AddressList(settings['To'])

if settings.as_bool('send_message') == True:
	# Get the password from the user
	pw = getpass.getpass('Enter e-mail account password for ' + fromUser + ':')
	 
	# Send the message
	s = smtplib.SMTP(settings['server'], settings.as_int('port'))
	s.set_debuglevel(0)
	s.ehlo()
	s.starttls()
	s.ehlo()
	s.login(fromUser, pw)
	s.sendmail(str(fromEmail), emailList, msg.as_string())
