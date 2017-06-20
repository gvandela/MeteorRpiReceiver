#!/usr/bin/env python2

'''
scheduler_v0.2.8 is a copy of v0.2:
	but running w/o doppler correction
	grouped all that is required in seperate directory
	launching decoder after capture
	removing old .s files
	launching image processing after decoding
	send e-mail with processed images
	improved logging & console printing
	added mail list
	added seperate file for personal info

	expected formatting of email_config.txt:
		displayed username
		e-mail address (gmail)
		password

	expected formatting of user_location.txt:
		Longitude (East is positive)
		Latitude (North is positive)

	expected formatting of mail_list.txt:
		e-mail address on every line
'''

import sys
import os
import subprocess
import time
import datetime
import ephem
import urllib2
import math
import xmlrpclib
import logging
from logging.handlers import RotatingFileHandler
from logging import handlers
import psutil
import smtplib
import platform
from os import listdir
from os.path import isfile, join, getmtime
from PIL import Image, ImageOps
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# general
script_name = os.path.splitext(os.path.basename(__file__))[0]
log_filename = script_name + '.log'
deg_per_rad = 180 / math.pi
speed_of_light = 299792458 #m/s
main_folder = os.path.join(os.path.expanduser('~'),'Projects/Python_projects/Meteor_receiver')
#main_folder = os.path.dirname(__file__)	somehow, this doesn't seem to return the path on the rpi
#print 'main_folder was found to be: %s' % main_folder

# configure logging
log = logging.getLogger('')
log.setLevel(logging.DEBUG)
format = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
# print logging to console
ch = logging.StreamHandler(sys.stdout)
ch.setFormatter(format)
log.addHandler(ch)
# save logging to file
fh = handlers.RotatingFileHandler(log_filename, maxBytes=(1048576*5), backupCount=7)
fh.setFormatter(format)
log.addHandler(fh)
# first logging lines
logging.debug("-----------------------------------------------------------------------------------------------")
logging.debug(datetime.datetime.now().strftime(script_name + ' (no doppler) started on %d/%m/%y at local %H:%M'))

# GRC script to launch
#grc_script = './GRC/METEOR_M2_v05.py'
#grc_script = './GRC/METEOR_M2_v05_noGUI.py'
grc_script = 'GRC/METEOR_M2_v04_noGUI.py'
grc_script = os.path.join(main_folder, grc_script)
SDR_capture = [sys.executable, grc_script]
logging.debug('GRC script: ' + grc_script)

# doppler server address & port
# grc_server = xmlrpclib.Server("http://localhost:8080")
# logging.debug(grc_server)

# set observer location
with open(os.path.join(main_folder, 'user_location.txt')) as f:
	user_loc = f.read().splitlines()
location = ephem.Observer()
location.lon = user_loc[0]		# +E
location.lat = user_loc[1]		# +N
location.elevation = 10
logging.debug('Location: ' + str(location.lat) + 'N, ' + str(location.lon) + 'E, ' + str(location.elevation) + 'm elevation')

# url to fetch TLE info from
TLE_url = 'http://www.celestrak.com/NORAD/elements/weather.txt'
TLE_offline_path = os.path.join(main_folder, 'TLE/weather.txt')

# NORAD sat name
sat_name = 'METEOR-M 2 '
logging.debug('Sat name: ' + sat_name)



def retrieve_tle(satellite):
	logging.debug('trying TLE download...')
	try:
		tle_file = urllib2.urlopen(TLE_url, timeout = 10).readlines()
	except:
		logging.debug('No internet access, using offline TLE file')
		with open(TLE_offline_path) as f:
			tle_file = f.readlines()
	else:
		logging.debug('Download successful, storing TLE file offline')
		logging.debug(datetime.datetime.now().strftime('TLE file downloaded & saved %d/%m/%y %H:%M'))
		with open(TLE_offline_path, 'w') as f:
			for line in tle_file:
				f.write(line)
	
	for i in range (0, len(tle_file)):
		line = tle_file[i]
		if line[:11] == satellite:
			print('TLE data: \n')
			print(tle_file[i])
			print(tle_file[i + 1])
			print(tle_file[i + 2])
			line_1 = tle_file[i]
			line_2 = tle_file[i + 1]
			line_3 = tle_file[i + 2]

	return ephem.readtle(line_1, line_2, line_3)


def doppler(velocity):
	frequency = 137900000
	return (speed_of_light/(speed_of_light + velocity)) * frequency

# decodes the .s file that was generated in the last 30 minutes, removes older .s files, returns the BMP file name
def decode_capture():
	mypath = os.path.join(main_folder, 'Data')

	onlyfiles = [file for file in listdir(mypath) if isfile(join(mypath, file))]

	valid_file = False

	for file in onlyfiles:
		if str(file).endswith('.s'):
			mod_time = getmtime(join(mypath, file))
			date = datetime.datetime.fromtimestamp(mod_time)
			if date > (datetime.datetime.now() - datetime.timedelta(minutes=30)):
				
				valid_file = True

				LRPT_soft = os.path.join(mypath, file)
				output_file = os.path.join(mypath, file[:-2])	# remove last 2 characters, i.e. the .s extension
				os.chdir(main_folder)
				if platform.machine() == 'x86_64':
					medet_command = './Decoder/medet' + " " + LRPT_soft + " " + output_file	# if on linux64
				elif platform.machine().startswith('arm'):
					medet_command = './Decoder/medet_arm' + " " + LRPT_soft + " " + output_file	# if on rpi
				else:
					logging.error('platform unsupported by decoder')
					return 'none'		# I'm not sure what else to do here...

				logging.debug('running: ' + medet_command)

				medet_process = subprocess.Popen([medet_command], shell = True)
				returncode = medet_process.wait()

				logging.debug('medet ran with returncode: %s' % returncode)

			else:
				#remove old .s files
				os.remove(os.path.join(mypath, file))
				logging.debug('removed old file %s' % os.path.join(mypath, file))

	if valid_file == True:
		file_name = os.path.basename(output_file)
		logging.debug('decode_capture returned file name: ' + file_name)
		return file_name
	else:
		logging.debug('decoding: no recent file was found')
		return 'none'
	

def process_image(file_name):
	if file_name <> 'none':
		# NS or SN pass?
		evening_pass = False
		pass_time = int(file_name[-4:])
		if ((pass_time > 1600) or (pass_time < 0400)):
			evening_pass = True

		image_dir = os.path.join(main_folder, 'Data', file_name + '.bmp')
		try:
			image_raw = Image.open(image_dir)
		except:
			logging.debug('no raw image was found')
			return 'none'
		else:
			r,g,b = image_raw.split()

			image_dir = os.path.join(main_folder, 'Images', file_name + '_122.jpg')
			image_122 = Image.merge("RGB", (g,g,b))
			if (evening_pass):
				image_122 = image_122.rotate(180)
			image_122.save(image_dir)
			logging.debug('Saved %s' % image_dir)

			image_dir = os.path.join(main_folder, 'Images', file_name + '_555_IR.jpg')
			image_ir = Image.merge("RGB", (r,r,r))
			image_ir = ImageOps.invert(image_ir)
			image_ir = ImageOps.autocontrast(image_ir)		#thermal information gets lost here, but we get better looking images
			if (evening_pass):
				image_ir = image_ir.rotate(180)
			image_ir.save(image_dir)
			logging.debug('Saved %s' % image_dir)
	return file_name 	# if no raw image was decoded, the above exception will have returned 'none' already


def email_image(file_name):

	if file_name <> 'none':

		with open(os.path.join(main_folder, 'mail_list.txt')) as f:
			mail_list = f.read().splitlines()

		with open(os.path.join(main_folder, 'email_config.txt')) as f:
			email_credentials = f.read().splitlines()

		msg = MIMEMultipart()
		msg['Subject'] = 'METEOR-M2 image'
		msg['From'] = email_credentials[0]
		msg.preamble = 'METEOR-M2 image: %s' % file_name

		msg.attach(MIMEText(file_name))
		
		image_122 = os.path.join(main_folder, 'Images', file_name + '_122.jpg')
		fp = open(image_122, 'rb')
		img = MIMEImage(fp.read())
		fp.close()
		msg.attach(img)

		image_555 = os.path.join(main_folder, 'Images', file_name + '_555_IR.jpg')
		fp = open(image_555, 'rb')
		img = MIMEImage(fp.read())
		fp.close()
		msg.attach(img)

		try:
			mail_server = smtplib.SMTP_SSL('smtp.gmail.com')
			logging.debug('logging into mail server')

			mail_server.login(email_credentials[1], email_credentials[2])
			logging.debug('logged in, sending e-mail')
			
			mail_server.sendmail(email_credentials[1], mail_list, msg.as_string())
			logging.debug('e-mail sent, logging out')
			
			mail_server.quit()
			logging.debug('logged out of mail server')
		except:
			logging.debug('There was a problem sending the e-mail')
	else:
		logging.debug('no e-mail sent as there was no decoded image')




while True:
	# 1) download & extract TLE
	meteor_M2 = retrieve_tle(sat_name)

	# 2) wait for positive elevation
	location.date = datetime.datetime.utcnow()
	meteor_M2.compute(location)

	logging.debug('waiting for positive satellite elevation')

	while meteor_M2.alt < 0:
		location.date = datetime.datetime.utcnow()
		meteor_M2.compute(location)
		print('elevation %4.2f deg, azimuth %5.2f deg' % (meteor_M2.alt * deg_per_rad, meteor_M2.az * deg_per_rad))
		#print('velocity %4.2f m/s' % meteor_M2.range_velocity)
		#doppler_shift = doppler(meteor_M2.range_velocity)

		time.sleep(1)

	# 3) start GRC script
	logging.debug('start GRC script')

	grc_process = subprocess.Popen(SDR_capture, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	logging.debug('started ' + grc_script + ' with PID:' + str(grc_process.pid) + ' ' + str(SDR_capture)+ ' started at ' + str(datetime.datetime.now()))
	# however, no indication is given if the script was succesfully started...

	# 4) calculate & update doppler while positive elevation
	#server_error_counter = 0
	maximum_elevation = 0.0
	while meteor_M2.alt > 0:
		location.date = datetime.datetime.utcnow()
		meteor_M2.compute(location)

		# doppler_shift = doppler(meteor_M2.range_velocity)
		# print(doppler_shift)
		# try:
		# 	grc_server.set_doppler_freq(doppler_shift)
		# except:
		# 	print('error setting doppler shift')	# we will see errors when grc script is not running
		# 	server_error_counter = server_error_counter + 1
		# 	print(server_error_counter)		# we're curious when things go wrong
		# 	pass
		#time.sleep(0.1)		# why do we crash after a while when sleeping only 100ms but not when sleeping 1s?
		#time.sleep(0.3)		# crashes with 300ms as well
		# moreover, why does rpi crash and PC doesn't?

		print('elevation %4.2f deg, azimuth %5.2f deg' % (meteor_M2.alt * deg_per_rad, meteor_M2.az * deg_per_rad))
		#print('velocity %4.2f m/s' % meteor_M2.range_velocity)
		
		time.sleep(1)


	# 5) stop GRC script
	logging.debug('stopping GRC script')

	try:
		grc_process.send_signal(subprocess.signal.SIGINT)		# don't use shell !
	except:
		logging.debug("script didn't seem to be running anymore")
	else:
		returncode = grc_process.wait()
		logging.debug('GRC script ended with return code: %s' % returncode)

	# 6) decode image with medet
	#we already waited for the GRC process to finish, no need to wait some more, right?
	time.sleep(20)
	file_name = decode_capture()	# since we don't know what file name the GRC script generated, we look for a file generated in the last 30min

	# 7) process decoded image
	image_file_name = process_image(file_name)			# by default no wine on ARM devices (to use e.g. LrptImageProcessor.exe, so only basic RGB channel processing

	# 8) e-mail final images to mail list
	email_image(image_file_name)

	logging.debug('all done, start over for next pass')
