import os
import sys
import subprocess
import glob
import time
import configparser
import collections
import RPi.GPIO as GPIO
from datetime import datetime
from collections import namedtuple
from decimal import Decimal
from enum import Enum


from PythonDaemon import PythonDaemon


#set working directory to where "thermDaemon.py" is
abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
# os.chdir(dname)

#setup enums for code readability
LOGLEVELS = Enum('LOGLEVELS', 'DEBUG INFO WARNING ERROR EXCEPTION PANIC')
STATES = Enum('STATES', 'IDLE FAN HEAT COOL')

class RaspistatDaemon(PythonDaemon):


	def __init__(self, pidfile, configfile):
		
		#read values from the config file
		cfg = configparser.ConfigParser()
		cfg.read(configfile)

		self.config = {}

		self.config['LOGLEVEL'] = cfg.get('main', 'LOGLEVEL')

		self.config['precision'] = cfg.getfloat('main', 'precision')

		### SENSOR ###
		# how often should we record the temp sensor value
		self.config['frequency'] = cfg.getint('sensor', 'frequency')
		self.config['places'] = cfg.getint('sensor','places')


		### HARDWARE ###
		#self.config['R_PIN'] = cfg.getint('hardware', 'R_PIN') #24 AC Power
		#self.config['B_PIN'] = cfg.getint('hardware', 'B_PIN') #24V AC Common
		self.config['G_PIN'] = cfg.getint('hardware', 'G_PIN') #Indoor Fan
		self.config['W_PIN'] = cfg.getint('hardware', 'W_PIN') #Heat
		self.config['Y_PIN'] = cfg.getint('hardware', 'Y_PIN') #Cool

		#commenting out reversing valve as I don't have one to test on
		#self.config['O_PIN'] = cfg.getint('hardware', 'O_PIN') #RV in Cool
		#self.config['B_PIN'] = cfg.getint('hardware', 'B_PIN') #RV in heat

		self.log(">> INIT - Welcome to Raspistat", LOGLEVELS.INFO)

		self.log(">> Config Loaded", LOGLEVELS.INFO)

		dbType = cfg.get('database','type')
		if dbType == 'sqlite':
			import sqlite3 as mdb

			dbFile = cfg.get('database', 'file')

			self.db = mdb.connect(dbFile)
			self.db.row_factory = namedtuple_factory
		
			self.log(">> Connected to Database /" + str(dbFile), LOGLEVELS.INFO)

		elif dbType == 'mysql':
			import pymysql as mdb

			dbHost = cfg.get('database', 'host')
			dbPort = cfg.getint('database', 'port')
			dbUser = cfg.get('database', 'user')
			dbPass = cfg.get('database', 'pass')
			dbName = cfg.get('database', 'name')

			self.db = mdb.connect(host=dbHost, port=dbPort, user=dbUser, passwd=DB_PASS, db=dbName)


		super().__init__(pidfile)

	def atexit(self):
		self.db.close()
		GPIO.cleanup()


	def log(self, message, level):
		if level.value >= LOGLEVELS[self.config['LOGLEVEL']].value:
			print(datetime.now().strftime("%FT%TZ") + (' [' + level.name + ']').ljust(11), message);

		
	def configureGPIO(self):

		self.log(">> Configuring GPIO", LOGLEVELS.INFO)

		if(self.config['LOGLEVEL'] != LOGLEVELS.DEBUG):
			GPIO.setwarnings(False)

		GPIO.setmode(GPIO.BCM)
		GPIO.setup(self.config['G_PIN'], GPIO.OUT)
		GPIO.setup(self.config['W_PIN'], GPIO.OUT)
		GPIO.setup(self.config['Y_PIN'], GPIO.OUT)


		self.log(">> Exporting GPIO", LOGLEVELS.DEBUG)

		subprocess.Popen("echo " + str(self.config['G_PIN']) + " > /sys/class/gpio/export", shell=True)
		subprocess.Popen("echo " + str(self.config['W_PIN']) + " > /sys/class/gpio/export", shell=True)
		subprocess.Popen("echo " + str(self.config['Y_PIN']) + " > /sys/class/gpio/export", shell=True)

		subprocess.Popen("echo " + str(self.config['G_PIN']) + " > /sys/class/gpio/export", shell=True)  #Indoor Fan
		subprocess.Popen("echo " + str(self.config['W_PIN']) + " > /sys/class/gpio/export", shell=True)  #Heat
		subprocess.Popen("echo " + str(self.config['Y_PIN']) + " > /sys/class/gpio/export", shell=True)  #Cool

		self.log(">> Setting up W1 Device", LOGLEVELS.DEBUG)
		os.system('modprobe w1-gpio')
		os.system('modprobe w1-therm')




	def readTemp(self):

		self.log("readTemp() pulling onboard sensor value", LOGLEVELS.DEBUG)

		temp = read_temp()

		# round to configured places
		temp = round(temp, self.config['places'])		

		self.log("readTemp() result:" + str(temp), LOGLEVELS.DEBUG)

		return temp



	def readState(self):

		GStatus = GPIO.input(self.config['G_PIN']) #subprocess.Popen("cat /sys/class/gpio/gpio" + str(self.config['G_PIN']) + "/value", shell=True, stdout=subprocess.PIPE).stdout.read().strip()
		WStatus = GPIO.input(self.config['W_PIN']) #subprocess.Popen("cat /sys/class/gpio/gpio" + str(self.config['W_PIN']) + "/value", shell=True, stdout=subprocess.PIPE).stdout.read().strip()
		YStatus = GPIO.input(self.config['Y_PIN']) #subprocess.Popen("cat /sys/class/gpio/gpio" + str(self.config['Y_PIN']) + "/value", shell=True, stdout=subprocess.PIPE).stdout.read().strip()

		self.log(">> readState Result - G: '" + str(GStatus) + "' W: '" + str(WStatus) + "' Y: '" + str(YStatus) + "'", LOGLEVELS.DEBUG)

		if GStatus == True and YStatus == True:
			return STATES.COOL
		
		elif GStatus == True and WStatus == True:
			return STATES.HEAT

		elif GStatus == True and YStatus == False and WStatus == False:
			return STATES.FAN

		elif GStatus == False and WStatus == False and YStatus == False:
			return STATES.IDLE

		else:
			self.log('readState() Panic state! Pin reads dont make sense...', LOGLEVELS.ERROR)
			return STATES.PANIC


	def cool(self):
		self.log(">> Outputting 'COOL' command...", LOGLEVELS.DEBUG)

		GPIO.output(self.config['G_PIN'], True) #Indoor Fan
		GPIO.output(self.config['W_PIN'], False) #Heat
		GPIO.output(self.config['Y_PIN'], True) #Cool

		#commenting out reversing valve as I don't have one to test on
		#GPIO.output(self.config['O_PIN'], True) #RV in Cool
		#GPIO.output(self.config['B_PIN'], False) #RV in heat
		self.setState(STATES.COOL)

	def heat(self):
		self.log(">> Outputting 'HEAT' command...", LOGLEVELS.DEBUG)

		GPIO.output(self.config['G_PIN'], True) #Indoor Fan
		GPIO.output(self.config['W_PIN'], True) #Heat
		GPIO.output(self.config['Y_PIN'], False) #Cool

		#commenting out reversing valve as I don't have one to test on
		#GPIO.output(self.config['O_PIN'], False) #RV in Cool
		#GPIO.output(self.config['B_PIN'], True) #RV in heat
		self.setState(STATES.HEAT)


	def fan(self): 
		self.log(">> Outputting 'FAN' command...", LOGLEVELS.DEBUG)

		#to blow the rest of the heated / cooled air out of the system
		GPIO.output(self.config['G_PIN'], True) #Indoor Fan
		GPIO.output(self.config['W_PIN'], False) #Heat
		GPIO.output(self.config['Y_PIN'], False) #Cool

		#commenting out reversing valve as I don't have one to test on
		#GPIO.output(self.config['O_PIN'], False) #RV in Cool
		#GPIO.output(self.config['B_PIN'], Fakse) #RV in heat
		self.setState(STATES.FAN)


	def idle(self):
		self.log(">> Outputting 'IDLE' command...", LOGLEVELS.DEBUG)

		GPIO.output(self.config['G_PIN'], False) #Indoor Fan
		GPIO.output(self.config['W_PIN'], False) #Heat
		GPIO.output(self.config['Y_PIN'], False) #Cool

		#commenting out reversing valve as I don't have one to test on
		#GPIO.output(self.config['O_PIN'], False) #RV in Cool
		#GPIO.output(self.config['B_PIN'], False) #RV in heat

		#time.sleep(10)	#to save pump #fix this... put somwehere else
		self.setState(STATES.IDLE)


	def getTarget(self):
		self.log(">> getTarget()", LOGLEVELS.DEBUG)

		cursor = self.db.cursor()

		#lets grab the latest target from the db
		cursor.execute("SELECT * FROM targets ORDER BY `created` DESC LIMIT 1")

		target = cursor.fetchone()

		#pull in the default value from the config, so we dont have to implement the logic in our loop code
		if(target.precision == None):
			target = target._replace(precision=self.config['precision'])

		cursor.close()

		self.log(">> getTarget result " + str(target), LOGLEVELS.DEBUG)

		return target



	def setTarget(self, temp, precision=None):
		self.log(">> setTarget(" + str(temp) + "," + str(precision) + ")", LOGLEVELS.DEBUG)

		cursor = self.db.cursor()

		obj = (temp, precision, time.time())

		cursor.execute("INSERT INTO targets(temp, precision, created) VALUES (?,?,?)", obj)

		self.db.commit()

		self.log(">> setTarget result: " + str(obj), LOGLEVELS.DEBUG)



	def getMode(self):
		self.log(">> getMode()", LOGLEVELS.DEBUG)

		cursor = self.db.cursor()

		cursor.execute("SELECT * FROM modes ORDER BY `created` DESC LIMIT 1")

		mode = cursor.fetchone()

		cursor.close()

		self.log(">> getMode result:" + str(mode), LOGLEVELS.DEBUG)

		return mode


	def setMode(self, name):
		self.log(">> setMode(" + str(name) + ")", LOGLEVELS.DEBUG)
		cursor = self.db.cursor()

		obj = (name, time.time())

		cursor.execute("INSERT INTO modes(name, created) VALUES (?,?)", obj)

		self.db.commit()

		self.log(">> setMode result: " + str(obj), LOGLEVELS.DEBUG)

	def getReading(self):
		self.log(">> getReading()", LOGLEVELS.DEBUG)

		cursor = self.db.cursor()

		cursor.execute("SELECT * FROM readings ORDER BY `created` DESC LIMIT 1")

		reading = cursor.fetchone()

		cursor.close()

		self.log(">> getReading result:" + str(reading), LOGLEVELS.DEBUG)
		
		return reading


	def setReading(self, temp):
		self.log(">> setReading(" + str(temp) + ")", LOGLEVELS.DEBUG)
		cursor = self.db.cursor()

		obj = (temp, time.time())

		reading = cursor.execute("INSERT INTO readings(temp, created) VALUES (?,?)", obj)

		self.db.commit()

		self.log(">> setReading result: " + str(obj), LOGLEVELS.DEBUG)

		return self.getReading()

	def getState(self):
		self.log(">> getState()", LOGLEVELS.DEBUG)

		cursor = self.db.cursor()

		cursor.execute("SELECT * FROM states ORDER BY `created` DESC LIMIT 1")

		state = cursor.fetchone()

		cursor.close()

		self.log(">> getState result:" + str(state), LOGLEVELS.DEBUG)

		return state


	def setState(self, state):
		self.log(">> setState(" + str(state) + ")", LOGLEVELS.DEBUG)

		curState = self.getState()

		#no reason to record every 5 seconds the state... let's only write it to the DB if it has changed
		if(curState.name != state.name):
			cursor = self.db.cursor()

			obj = (state.name, time.time())

			cursor.execute("INSERT INTO states(name, created) VALUES (?,?)", obj)

			self.db.commit()

			self.log(">> setState result: " + str(obj), LOGLEVELS.DEBUG)

		else:
			self.log(">> setState result: State not written to db because it has not changed from " + curState.name, LOGLEVELS.DEBUG)


	def run(self, debug = False):

		abspath = os.path.abspath(__file__)
		dname = os.path.dirname(abspath)
		os.chdir(dname)

		LAST = {
			"sensor": 0,
			"process": 0}

		self.configureGPIO()


		#enter the main loop, this is the heart of this daemon
		self.log(">> Entering the main loop -- here we go!", LOGLEVELS.INFO)

		while True:
			now = time.time()

			#log temp from onboard sensor (module 1)
			elapsed = now - LAST['sensor']
			lastReading = self.getReading()
			if elapsed > self.config['frequency']:
				
				temp = self.readTemp()
				
				if(temp != lastReading.temp):
					lastReading = self.setReading(temp);
				
				LAST['sensor'] = time.time()


			#instead of sleep(5)ing, let's run this loop as fast as possible, but only process the temp if a certain amount of time has elapsed
			#this seems unnecessary, as what would be the problem with processing faster?... must think about this
			elapsed = now - LAST['process']
	
			if elapsed > 5:

				mode = self.getMode()
				reading = self.getReading()
				target = self.getTarget()

				self.log("Mode: " + str(mode) + " Reading: " + str(reading) + " Target: " + str(target), LOGLEVELS.DEBUG)				
				if mode.name == "HEAT":	#if we are in manual HEAT mode

					if reading.temp < target.temp - target.precision:
						self.heat()

					if reading.temp >= target.temp + target.precision:
						self.idle()


				elif mode.name  == "COOL": #if we are in manual COOL mode

					if reading.temp > target.temp + target.precision:
						self.cool()

					if reading.temp <= target.temp - target.precision:
						self.idle()
	

				else:

					self.log("This is weird, the current mode is not valid.", LOGLEVELS.PANIC)

				LAST['process'] = time.time()

				expectedState = self.getState()
				actualState = self.readState()
				self.log("Mode: " + str(mode.name) + " State: (" + str(expectedState.name) + "/" + str(actualState.name) + ") Currently: " + str(reading.temp) + " Targeting: " + str(target.temp) + " ~ " + str(target.precision),  LOGLEVELS.INFO)

def namedtuple_factory(cursor, row):
    """
    Usage:
    con.row_factory = namedtuple_factory
    """
    fields = [col[0] for col in cursor.description]
    Row = namedtuple("Row", fields)
    return Row(*row)

def read_temp_raw():
    base_dir = '/sys/bus/w1/devices/'
    device_folder = glob.glob(base_dir + '28*')[0]
    device_file = device_folder + '/w1_slave'

    f = open(device_file, 'r')
    lines = f.readlines()
    f.close()
    return lines

def read_temp():
    lines = read_temp_raw()
    while lines[0].strip()[-3:] != 'YES':
        time.sleep(0.2)
        lines = read_temp_raw()
    equals_pos = lines[1].find('t=')
    if equals_pos != -1:
        temp_string = lines[1][equals_pos+2:]
        temp_c = float(temp_string) / 1000.0
        temp_f = temp_c * 9.0 / 5.0 + 32.0

        return temp_f
