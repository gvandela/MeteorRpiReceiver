#!/usr/bin/env python2

'''
scheduler_v0.2.9 is a copy of v0.2.8.2:
    Added functionality to automatically handle changes in transmitted channels
    Since recent malfunctioning (May 2018) channels 1,2,3 are active instead of 1,2,5
    At other times, different infrared channels were enabled which were not processed before

	expected formatting of email_config.txt:
		displayed user name
		e-mail address (gmail)
		password

	expected formatting of user_location.txt:
		Longitude (East is positive)
		Latitude (North is positive)

	expected formatting of mail_list.txt:
		e-mail address on every line
'''
from __future__ import print_function
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
from os.path import isfile, join, getmtime, basename
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
#main_folder = os.path.dirname(__file__)	somehow, this doesn't seem to return the path on the rpi, so we have to find another way...

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

# Check if all expected directories exist & create them if not
if not os.path.exists(os.path.join(main_folder, 'Data')):
	os.makedirs(os.path.join(main_folder, 'Data'))
	logging.debug('Created Data directory')

if not os.path.exists(os.path.join(main_folder, 'Images')):
	os.makedirs(os.path.join(main_folder, 'Images'))
	logging.debug('Created Images directory')

if not os.path.exists(os.path.join(main_folder, 'TLE')):
	os.makedirs(os.path.join(main_folder, 'TLE'))
	logging.debug('Created TLE directory')

# GRC script to launch
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
            # if file == s_file:
                
                valid_file = True

                LRPT_soft = os.path.join(mypath, file)

                output_file_1 = os.path.join(mypath, file[:-2])	# remove .s extension
                output_file_2 = os.path.join(mypath, file[:-2]) + "_2" # remove .s extension
                os.chdir(main_folder)
                # since the rpi3 has 4 cores, we can run 2 medet instances to cover all 6 APIDs
                if platform.machine() == 'x86_64':
                    medet_command = './Decoder/medet' + " " + LRPT_soft + " " + \
                        output_file_1 + " -Q -b 64 -g 65 -r 68"	# if on linux64
                elif platform.machine().startswith('arm'):
                    medet_command = './Decoder/medet_arm' + " " + LRPT_soft + " " + \
                        output_file_1 + " -Q -b 64 -g 65 -r 68"	# if on rpi
                else:
                    logging.error('platform unsupported by decoder')
                    return ('none', 'none')		# I'm not sure what else to do here...
                logging.debug('running: ' + medet_command)
                medet_process_1 = subprocess.Popen([medet_command], shell = True)

                if platform.machine() == 'x86_64':
                    medet_command = './Decoder/medet' + " " + LRPT_soft + " " + \
                        output_file_2 + " -Q -b 66 -g 67 -r 69" # if on linux64
                elif platform.machine().startswith('arm'):
                    medet_command = './Decoder/medet_arm' + " " + LRPT_soft + " " + \
                        output_file_2 + " -Q -b 66 -g 67 -r 69" # if on rpi
                else:
                    logging.debug('platform unsupported by decoder')
                    return ('none', 'none')       # I'm not sure what else to do here...
                logging.debug('running: ' + medet_command)
                medet_process_2 = subprocess.Popen([medet_command], shell = True)

                returncode_1 = medet_process_1.wait()
                logging.debug('1st medet ran with returncode: %s' % returncode_1)

                returncode_2 = medet_process_2.wait()                    
                logging.debug('2nd medet ran with returncode: %s' % returncode_2)

            else:
                #remove old .s files
                os.remove(os.path.join(mypath, file))
                logging.debug('removed old file %s' % os.path.join(mypath, file))
                #logging.debug('would have removed old file %s' % os.path.join(mypath, file))

    if valid_file == True:
        file_name_1 = os.path.basename(output_file_1)
        file_name_2 = os.path.basename(output_file_2)
        logging.debug('decode_capture returned file name: %s & %s' % (file_name_1, file_name_2))
        return (file_name_1, file_name_2)
    else:
        logging.debug('decoding: no recent file was found')
        return ('none', 'none')

	
def detect_blanks(image):
    channels = [0,0,0]
    image_dir = os.path.join(main_folder, 'Data', image + '.bmp')
    try:
        image_raw = Image.open(image_dir)
    except:
        logging.debug('detecting blanks: no raw image was found')
        return 'none'
    else:
        r,g,b = image_raw.split()
        
        # red channel
        image = Image.merge("RGB", (r,r,r))
        extrema = image.convert("L").getextrema()
        if extrema <> (0,0):
            channels[2] += 1
        
        # green channel
        image = Image.merge("RGB", (g,g,g))
        extrema = image.convert("L").getextrema()
        if extrema <> (0,0):
            channels[1] += 1
            
        # blue channel
        image = Image.merge("RGB", (b,b,b))
        extrema = image.convert("L").getextrema()
        if extrema <> (0,0):
            channels[0] += 1
        
        image.close()
        
    return channels


def process_image(image_1, image_2):
    if image_1 <> 'none':
        # NS or SN pass?
        evening_pass = False
        pass_time = int(image_1[-4:])
        if ((pass_time > 1600) or (pass_time < 0400)):
            evening_pass = True

        # first check which channels were active
        active_channels = [0,0,0,0,0,0]

        active_decoded_channels = detect_blanks(image_1)
        if active_decoded_channels == 'none':
            return [], [0,0,0,0,0,0]   # no image was decoded from recording

        active_channels[0] = active_decoded_channels[0]
        active_channels[1] = active_decoded_channels[1]
        active_channels[4] = active_decoded_channels[2]
        
        active_decoded_channels = detect_blanks(image_2)
        active_channels[2] = active_decoded_channels[0]
        active_channels[3] = active_decoded_channels[1]
        active_channels[5] = active_decoded_channels[2]
            
        logging.debug('Detected active channels: ' + str(active_channels))
        if (sum(active_channels) <> 3):
            logging.debug('Amount of active channels incorrect (%.0f)' % active_channels)

        image_1_dir = os.path.join(main_folder, 'Data', image_1 + '.bmp')
        image_2_dir = os.path.join(main_folder, 'Data', image_2 + '.bmp')
        logging.debug('processing file %s' % image_1_dir)

        channels = [0] * 6
        image_125 = Image.open(image_1_dir)
        ch_4, ch_1, ch_0 = image_125.split()
        image_346 = Image.open(image_2_dir)
        ch_5, ch_3, ch_2 = image_346.split()

        list_of_images = []

        if (active_channels[:2] == [1,1]):
            image_dir = os.path.join(main_folder, 'Images', image_1 + '_122.jpg')
            image = Image.merge("RGB", (ch_1, ch_1, ch_0))
            image.save(image_dir, quality=90, subsampling=0)
            list_of_images.append(image_dir)
        
        if (active_channels == [1,1,1,0,0,0]):
            image_dir = os.path.join(main_folder, 'Images', image_1 + '_123.jpg')
            image = Image.merge("RGB", (ch_2, ch_1, ch_0))
            image.save(image_dir, quality=90, subsampling=0)
            list_of_images.append(image_dir)
        
        if (active_channels == [1,1,0,1,0,0]):
            image_dir = os.path.join(main_folder, 'Images', image_1 + '_124.jpg')
            image = Image.merge("RGB", (ch_3, ch_1, ch_0))
            image.save(image_dir, quality=90, subsampling=0)
            list_of_images.append(image_dir)
        
        if (active_channels[4] == 1):
            image_dir = os.path.join(main_folder, 'Images', image_1 + '_555.jpg')
            image = Image.merge("RGB", (ch_4, ch_4, ch_4))
            image = ImageOps.invert(image)
            image = ImageOps.autocontrast(image)      
            #thermal information gets lost here, but we get better looking images
            image.save(image_dir, quality=90, subsampling=0)
            list_of_images.append(image_dir)
        
        if (active_channels[5] == 1):
            image_dir = os.path.join(main_folder, 'Images', image_1 + '_666.jpg')
            image = Image.merge("RGB", (ch_5, ch_5, ch_5))
            image = ImageOps.invert(image)
            image = ImageOps.autocontrast(image)
            #thermal information gets lost here, but we get better looking images
            image.save(image_dir, quality=90, subsampling=0)
            list_of_images.append(image_dir)
        
        for image_dir in list_of_images:
            if (evening_pass):
                image = Image.open(image_dir)
                image = image.rotate(180)
                image.save(image_dir)
            logging.debug('Saved %s' % image_dir)

        return list_of_images, active_channels
    else:
        return [], [0,0,0,0,0,0]


def email_image(list_of_images, active_channels):

    if list_of_images:      # if there are images to be e-mailed
        with open(os.path.join(main_folder, 'mail_list.txt')) as f:
            mail_list = f.read().splitlines()

        with open(os.path.join(main_folder, 'email_config.txt')) as f:
            email_credentials = f.read().splitlines()

        msg = MIMEMultipart()
        msg['Subject'] = 'METEOR-M2 image'
        msg['From'] = email_credentials[0]
        msg.preamble = 'METEOR-M2 image: %s' % basename(list_of_images[0].split('_')[0])
        
        channel_comment = []
        channel_comment.append('Band No 1 (VIS= Visible)						0.50 +- 0.2 - 0.70 +- 0.2 um\n')
        channel_comment.append('Band No 2 (VNIR=Visible Near Infrared)			0.70 +- 0.2 - 1.10 +- 0.2 um\n')
        channel_comment.append('Band No 3 (SWIR= Short Wave Infrared)			1.60 +- 0.50 - 1.80 +- 0.50 um\n')
        channel_comment.append('Band No 4 (MWIR= Mid Wave Infrared)		    	3.50 +- 0.50 - 4.10 +- 0.50 um\n')
        channel_comment.append('Band No 5 (TIR = Thermal Infrared)				10.5 +- 0.50 - 11.5 +- 0.50 um\n')
        channel_comment.append('Band No 6 (TIR = Thermal Infrared)				11.5 +- 0.50 - 12.5 +- 0.50 um\n')
        
        # Add info about active channels to test body of e-mail        
        s = 'Satellite is transmitting channels: \n'
        for i in range(0,6):
            if active_channels[i] == 1:
                s += channel_comment[i]
        msg.attach(MIMEText(s))
        
        # Add images
        for image_dir in list_of_images:
            fp = open(image_dir, 'rb')
            img = MIMEImage(fp.read())
            img.add_header('Content-Disposition', 'attachment', filename=basename(image_dir))
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
            pass
    else:
        logging.debug('no e-mail sent as there was no decoded image')


try:
    os.system('setterm -cursor off')    # doesn't work in windows though...
except:
    print("Couldn't switch cursor off, elevation & azimuth might blink")
    
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
        print('elevation %4.2f deg, azimuth %5.2f deg                              ' \
            % (meteor_M2.alt * deg_per_rad, meteor_M2.az * deg_per_rad), end="\r", file=sys.stderr)
        # sys.stdout.flush()
        #print('velocity %4.2f m/s' % meteor_M2.range_velocity)
        #doppler_shift = doppler(meteor_M2.range_velocity)

        time.sleep(1)

	# 3) start GRC script
    logging.debug('start GRC script')

    grc_process = subprocess.Popen(SDR_capture, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    logging.debug('started ' + grc_script + ' with PID:' + str(grc_process.pid) + ' ' + str(SDR_capture)+ ' started at ' + str(datetime.datetime.now()))
    # however, no indication is given if the script was succesfully started...

    # 4) calculate & update Doppler while positive elevation
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

        print('elevation %4.2f deg, azimuth %5.2f deg                              ' \
            % (meteor_M2.alt * deg_per_rad, meteor_M2.az * deg_per_rad), end="\r", file=sys.stderr)
        # sys.stdout.flush()
        #print('velocity %4.2f m/s' % meteor_M2.range_velocity
        
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
    
    image_1, image_2 = decode_capture()	# since we don't know what file name the GRC script generated, we look for a file generated in the last 30min
    
	# 7) process decoded image
    image_list, act_channels = process_image(image_1, image_2)	# by default no wine on ARM devices (to use e.g. LrptImageProcessor.exe, so only basic RGB channel processing

	# 8) e-mail final images to mail list
    email_image(image_list, act_channels)

    logging.debug('all done, start over for next pass')
 
