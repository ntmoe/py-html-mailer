#!/usr/bin/env python
#coding=utf8

import fileinput
import sys, traceback
import re
import httplib, urllib, urllib2
from urlparse import urljoin, urlparse, urlsplit, urlunparse, ParseResult
import json
import os
from os.path import splitext
from PIL import Image, ImageDraw
from BeautifulSoup import BeautifulSoup, Tag, NavigableString
import subprocess
import cStringIO
from configobj import ConfigObj
import errno
import shutil

# TODO:
# - Create publish option
#		- Copy files to web location (before sending to Premailer)
#		- Set proper permissions
#		- Change src attributes to the new locations via Premailer

def FileExists(filename):
	try:
		fp = open(filename)
	except IOError as e:
		if e.errno == errno.ENOENT: # If the file does not exist
			print "Warning: {0} does not exist".format(filename)
			return False
		elif e.errno == errno.EACCES: # If you don't have permission
			print "Warning: Permission denied to access {0}".format(filename)
		else:
			raise
	else:
		fp.close()
		return True

def AppendFilename(filename, appendix):
	splitFilename = splitext(filename)
	return splitFilename[0] + appendix + splitFilename[1]

def TidyHTML(fileAsString, optDict):
	optDictList = []
	for key, value in optDict.iteritems():
		optDictList.append(key)
		if value != '':
			optDictList.append(value)

	tidy = subprocess.Popen(['tidy'] + optDictList,
													stdin=subprocess.PIPE,
													stdout=subprocess.PIPE,
													stderr=subprocess.PIPE)
	results = tidy.communicate(fileAsString)[0]
	# Remove CDATA tags and return
	return results.replace('/*<![CDATA[*/\n', '').replace('/*]]>*/\n','')

def CleanDirPath(path):
	""" Return a directory path that is terminated by '/'.
	"""
	def CleanPath(path):
		if (os.path.split(path)[1] != ''):
			return path + '/'
		else:
			return path
	
	if urlparse(path).scheme == '': # This means that the path is local
		return CleanPath(path)
	else:
		parsedURL = urlparse(path)
		return urlunparse(ParseResult(
			parsedURL.scheme,
			parsedURL.netloc,
			CleanPath(parsedURL.path),
			'', '', ''
		))

def PathWalk(basePath, targetPath):
	for dirpath, dirnames, filenames in os.walk(basePath):
		if targetPath.startswith(dirpath):
			yield dirpath, dirnames, filenames

def WebDirPerms(basePath, targetPath):
	for dirpath, dirnames, filenames in \
			PathWalk(basePath, targetPath):
		os.chmod(dirpath, 0755)


# Create a dictionary to hold tidy options:
tidyOptions = {
	'-i': '',
	'--tab-size': '2',
	'--wrap': '0',
	'--tidy-mark': 'n',
	'--merge-divs': 'n',
	'--doctype': 'strict',
	'--char-encoding': 'utf8',
	'--hide-comments': 'n',
	'--drop-proprietary-attributes': 'y',
	'--preserve-entities': 'y'
}

# Create a dictionary for all the filenames
filenames = {}

# Read settings from an INI file
filenames['Settings'] = sys.argv[1]
settings = ConfigObj(filenames['Settings'])

# Clean paths from INI file
settings['www-docs_root'] = os.path.expanduser(CleanDirPath(settings['www-docs_root']))
settings['web_path_root'] = CleanDirPath(settings['web_path_root'])
settings['path_to_site_folder'] = CleanDirPath(settings['path_to_site_folder'])

filenames['Original'] = settings['original_HTML']
filenames['Archive'] = AppendFilename(filenames['Original'],"-archive")
filenames['Mail'] = AppendFilename(filenames['Original'],"-mail")
filenames['Text'] = splitext(filenames['Original'])[0] + ".txt"
filenames['Tracking GIF'] = splitext(filenames['Original'])[0] + ".gif"
#linkListFilename = splitext(filename)[0] + "-links.txt"

# Create a dictionary for URLs
urls = {}

# Set up the URL for the Archive page and images
if settings.as_bool('publish_files') == True:
	archivePath = urljoin(settings['web_path_root'], settings['path_to_site_folder'])
	urls['Archive'] = urljoin(archivePath, filenames['Archive'])
	urls['Base'] = urljoin(settings['web_path_root'], settings['path_to_site_folder'])
else:
	urls['Archive'] = "./" + filenames['Archive']
	urls['Base'] = "./"

# Set up the URL for the images

# Create a dictionary for all the files
files = {}

files['Original'] = open(filenames['Original'], 'r')
files['Archive'] = open(filenames['Archive'],'w')
files['Mail'] = open(filenames['Mail'],'w')

# Read in the Original file
files['Original'] = files['Original'].read()

# Insert the link to the archive version
files['Original'] = files['Original'].replace('*|ARCHIVE|*', urls['Archive'])

files['Original'] = TidyHTML(files['Original'], tidyOptions)

# Create a tracking pixel
img = Image.new('RGBA',(1,1))
draw = ImageDraw.Draw(img)
img.save(filenames['Tracking GIF'], 'GIF', transparency=0)

print "Adding a tracking pixel with name",
print '"' + filenames['Tracking GIF'] + '"...'
# Make the file into a Beautiful Soup
soup = BeautifulSoup(files['Original'])

# Replace the title of the document with the subject
titleTag = Tag(soup, "title")
titleTag.insert(0, settings['Subject'])
soup.title.replaceWith(titleTag)

# Make an image tag for the tracking pixel
trackingTag = Tag(soup, "img")
trackingTag['src'] = filenames['Tracking GIF']
#trackingTag['src'] = urljoin('./', filenames['Tracking GIF'])

# Insert the tag into the soup, right before the closing body tag
soup.body.insert(len(soup.body.contents), trackingTag)

# Find all img tags in the soup and add height and width attributes.
# If th file is local (relative), add the src to a list so that we
# know which files to publish.
filesToPublish = []
print "Adding image dimensions to all <img /> tags..."
for img in soup.findAll('img'):
	imgURL = img['src']
	# urlopen doesn't work with relative urls, so we have to test to see if imgURL is relative or not
	if urlparse(imgURL).scheme == '': # This means that the image URL is relative (and local)
		if FileExists(imgURL):
			dimens = Image.open(imgURL).size
			filesToPublish.append(imgURL)

	else:
		imgFile = cStringIO.StringIO(urllib2.urlopen(imgURL).read())
		dimens = Image.open(imgFile).size

	# set image width and height
	img['width'] = dimens[0]
	img['height'] = dimens[1]

# Find all a tags in the soup. If the link is local, add the href to
# a list so we know which files to publish.
print "Finding other files to publish..."
for a in soup.findAll('a'):
	aURL = a['href']
	if urlparse(aURL).scheme == '':
		if FileExists(aURL):
			filesToPublish.append(aURL)
	
# Turn the soup back into a string
print 'Reformatting original HTML file...'
files['Original'] = str(soup)

searchRegex = "<!-- \*\|IFNOT:ARCHIVE_PAGE\|\* -->.*<!-- \*\|END:IF\|\* -->"

m = re.search(searchRegex, files['Original'], re.DOTALL)

archiveVersion = files['Original'][:m.start(0)] + files['Original'][m.end(0):]
files['Archive'].write(TidyHTML(archiveVersion, tidyOptions))

archiveSoup = BeautifulSoup(m.group(0))
for a in archiveSoup.findAll('a'):
			a['href'] = urls['Archive']

files['Original'] = TidyHTML(files['Original'][:m.start(0)] + \
										str(archiveSoup) + \
										files['Original'][m.end(0):], \
										tidyOptions)

# Close the files so that we can read some of them
for value in files.itervalues():
	if isinstance(value, file): # If it's a file object, close it
		value.close()

# Create the content to send to Premailer
	content = files['Original']

if settings.as_bool('use_premailer') == True:
		# Premailer will put xmlns="http://www.w3.org/1999/xhtml" into the html tag no matter
	# if it's already there or not, so remove it from the content we're sending.
	#content = content.replace(' xmlns="http://www.w3.org/1999/xhtml"', '')

	# Now, send the email version to Premailer:
	print "Sending to Premailer..."
	urls['Premailer'] = "http://premailer.dialect.ca/api/0.1/documents"
	parameterDict = {'html': content, 'remove_comments': 'true', 
										'base_url': urls['Base']}
	if settings.as_bool('publish_files') == False:
		del parameterDict['base_url']
	params = urllib.urlencode(parameterDict)
	conn = httplib.HTTPConnection("premailer.dialect.ca")
	conn.request("POST", urls['Premailer'], params)
	response = conn.getresponse()
	print "Response from Premailer received with status:",
	print response.status, response.reason
	premailerData = response.read()
	conn.close()

	# The premailerData is a JSON. Convert it to a Python dict.
	premailerDict = json.loads(premailerData)
	urls['Premailer HTML'] = premailerDict['documents']['html']
	urls['Premailer Text'] = premailerDict['documents']['txt']

	files['Premailer HTML'] = urllib2.urlopen(urls['Premailer HTML'])
	files['Premailer Text'] = urllib2.urlopen(urls['Premailer Text'])

	# We have to clean the CDATA tags from what we get from Premailer.
	CDATAmsgCount = 0
	with open(filenames['Mail'], 'w') as f:
		withinStyle = False
		for line in files['Premailer HTML']:
			# Only look for CDATA tags within the <style></style> section
			if line.strip().startswith('<style'):
				withinStyle = True # We're in the style section

			if '</style>' in line:
				withinStyle = False # We're not in the style section anymore
			
			if (withinStyle == True):
				# If neither of these two tags are in the line, write the line.
				# This, in effect, "deletes" the two tags from the copy.
				if ('<![CDATA[' not in line) & (']]>' not in line):
					f.write(line)
				else:
					CDATAmsgCount = CDATAmsgCount + 1
					if CDATAmsgCount == 1:
						print "Removing <![CDATA[...]]>..."

			else:	# If we're not in the style section, write everything.
				f.write(line) 
	
else:
	with open(filenames['Mail'], 'w') as f:
		print "Copying original HTML file to a file for mailing..."
		f.write(content)

# Write plain text versions
if (settings.as_bool('use_premailer') == True) & \
		(settings.as_bool('use_lynx_for_text') == False):
	with open(filenames['Text'], 'w') as f:
		print "Creating plain text version from Premailer..."
		text = files['Premailer Text'].read()
		f.write(text)
else:
	optList = [
		'-display_charset=utf-8', 
		'-width=1024',
		'-dump',
		'-stdin'
	]
	htmlAsString = ''.join(files['Original'])
	print "Creating plain text version from lynx..."
	lynx = subprocess.Popen(['lynx'] + optList,
													stdin=subprocess.PIPE,
													stdout=subprocess.PIPE,
													stderr=subprocess.PIPE)
	text = lynx.communicate(htmlAsString)[0]
	with open(filenames['Text'], 'w') as f:
		f.write(text)

### End Premailer section

# Close the files

for value in files.itervalues():
	if isinstance(value, file): # If it's a file object, close it
		value.close()

filesToPublish.append(filenames['Archive'])

### Publish the files
print "Publishing files..."
sourcePath = os.getcwd()

publishPath = os.path.join(settings['www-docs_root'],
							settings['path_to_site_folder'])

if os.path.exists(publishPath) == False:
	os.makedirs(publishPath)

# Walk the directories and make them web-viewable
WebDirPerms(settings['www-docs_root'], publishPath)

# Copy the files to the published directory
for item in filesToPublish:
	dirpath = os.path.dirname(item)
	filename = os.path.basename(item)
	publishDirpath = os.path.join(publishPath, dirpath)
	# Make directories in publishPath
	if os.path.exists(publishDirpath) == False:
		os.makedirs(publishDirpath)
		
	WebDirPerms(publishPath, publishDirpath)
	publishFilepath = os.path.join(publishDirpath, filename)
	shutil.copy(item, publishDirpath)
	os.chmod(publishFilepath, 0644)

print "Done."

# Display URL of Archive version (for debugging)
print '\nURL for Archive version:\n{0}\n'.format(urls['Archive'])
		
# sys.exit(0)


		
		


