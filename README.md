# MeteorRpiReceiver
A set of python scripts to automatically capture, decode &amp; e-mail Meteor-M2 satellite images

These scripts have been written to run on a Raspberry Pi 3 model B.

This project uses a good ol' DVB-T stick and gnuradio to capture the raw data. The processing of the raw data is performed by 'medet' (medet_arm in this case) developed by Artlav.

The only part which is a bit harder to get over-the-counter is the antenna. I would recommend a QFH antenna, but e.g. crossed dipoles seem to render good results for others. Plans to build them are scattered across the internet.

The 'scheduler' python script is all you need to run. For now, it does need to be in a specific directory, but edit to suit your wishes:
"~/Projects/Python_projects/Meteor_receiver"
The script will:
- create a log file
- create the Data, Images and TLE directories if they don't exist
- load the user location from user_location.txt (you need to modify this file with your location)
- calculate the current position of Meteor-M2 and wait for it to appear above the horizon
- launch the GRC script (some paths might need to be modified in the GRC script to match your wishes)
- wait for the satellite to disappear under the horizon again
- stop the GRC script
- decode the raw data using medet_arm by Artlav
- process the raw image (if any was decoded) into a daytime and nighttime image (122 & 555)
- e-mail the processed images from an e-mail address specified in 'email_config.txt' (you need to modify this file)
  to all e-mail addresses listed in mail_list.txt (you need to modify this file as well)
- calculate and wait for the satellite to appear above the horizon again
- etc.

Have fun!

Notes: 
- In a couple of weeks time, I only had to reboot my rPi once as the GRC script was not producing any data. No idea what the issue was, but just a heads up. It was obvious by the generation of .s files with 0Bytes size.
- This is/was my introduction to Python, all improvements are most welcome!
