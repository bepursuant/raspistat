import sys
import subprocess
import os
import time
import configparser
import collections
import RPi.GPIO as GPIO
from datetime import datetime
from collections import namedtuple
from enum import Enum

from PythonDaemon import PythonDaemon


#set working directory to where "thermDaemon.py" is
abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
# os.chdir(dname)

#setup enums for code readability
LOGLEVELS = Enum('LOGLEVELS', 'DEBUG INFO WARNING ERROR EXCEPTION PANIC')
STATES = Enum('STATES', 'IDLE FAN HEAT COOL PANIC')
MODES = Enum('MODES', 'HEAT COOL SMART')


class RaspistatDaemon(PythonDaemon):


	def __init__(self, pidfile, configfile):
		self.STATE = STATES.IDLE
		self.MODE = MODES.HEAT #TODO change this to use a file!

		#read values from the config file
		cfg = configparser.ConfigParser()
		cfg.read(configfile)

		self.config = {}


		self.config['LOGLEVEL'] = cfg.get('main', 'LOGLEVEL')

		self.config['active_pad'] = cfg.getfloat('main', 'active_pad')
		self.config['inactive_pad']  = cfg.getfloat('main', 'inactive_pad')

		### SENSOR ###
		# how often should we record the temp sensor value
		self.config['frequency'] = cfg.getfloat('sensor', 'frequency')

		#self.config['R_PIN'] = cfg.getint('hardware', 'R_PIN') #24 AC Power
		#self.config['B_PIN'] = cfg.getint('hardware', 'B_PIN') #24V AC Common
		self.config['G_PIN'] = cfg.getint('hardware', 'G_PIN') #Indoor Fan
		self.config['W_PIN'] = cfg.getint('hardware', 'W_PIN') #Heat
		self.config['Y_PIN'] = cfg.getint('hardware', 'Y_PIN') #Cool

		#commenting out reversing valve as I don't have one to test on
		#self.config['O_PIN'] = cfg.getint('hardware', 'O_PIN') #RV in Cool
		#self.config['B_PIN'] = cfg.getint('hardware', 'B_PIN') #RV in heat


		dbType = cfg.get('database','type')
		if dbType == 'sqlite':
			import sqlite3 as mdb

			dbFile = cfg.get('database', 'file')

			self.db = mdb.connect(dbFile)
			self.db.row_factory = namedtuple_factory

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


	def log(self, message, level):
		if level.value >= LOGLEVELS[self.config['LOGLEVEL']].value:
			print(datetime.now().strftime("%FT%TZ") + (' [' + level.name + ']').ljust(11), message);

		
	def configureGPIO(self):

		self.log(">> Configuring GPIO", LOGLEVELS.INFO)

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





	def readTemp(self):

		self.log("readTemp() pulling onboard sensor value", LOGLEVELS.DEBUG)

		return 82

		#setup probe
		subprocess.Popen('modprobe w1-gpio', shell=True)
		subprocess.Popen('modprobe w1-therm', shell=True)
		base_dir = '/sys/bus/w1/devices/'
		device_folder = glob.glob(base_dir + '28*')[0]
		device_file = device_folder + '/w1_slave'

		#read temp
		f = open(device_file, 'r')
		lines = f.readlines()
		f.close()

		while lines[0].strip()[-3:] != 'YES':
			time.sleep(0.2)
			f = open(device_file, 'r')
			lines = f.readlines()
			f.close()
			equals_pos = lines[1].find('t=')
			if equals_pos != -1:
				temp_string = lines[1][equals_pos+2:]
				temp_c = float(temp_string) / 1000.0
				temp_f = temp_c * 9.0 / 5.0 + 32.0

				return temp_f

		#return cpu temp... probably not a great idea
		return read_temp()


	def readState(self):

		self.log("readState() pulling pin values", LOGLEVELS.DEBUG)

		GStatus = int(subprocess.Popen("cat /sys/class/gpio/gpio" + str(self.config['G_PIN']) + "/value", shell=True, stdout=subprocess.PIPE).stdout.read().strip())
		WStatus = int(subprocess.Popen("cat /sys/class/gpio/gpio" + str(self.config['W_PIN']) + "/value", shell=True, stdout=subprocess.PIPE).stdout.read().strip())
		YStatus = int(subprocess.Popen("cat /sys/class/gpio/gpio" + str(self.config['Y_PIN']) + "/value", shell=True, stdout=subprocess.PIPE).stdout.read().strip())
		

		if GStatus == 1 and YStatus == 1:
			return STATES.COOL
		
		elif GStatus == 1 and WStatus == 1:
			return STATES.HEAT

		elif GStatus == 1 and YStatus == 0 and WStatus == 0:
			return STATES.FAN

		elif GStatus == 0 and WStatus == 0 and YStatus == 0:
			return STATES.IDLE

		else:
			self.log('readState() Panic state! Pin reads dont make sense...', LOGLEVELs.ERROR)
			return STATES.PANIC


	def cool(self):
		self.log(">> Outputting 'COOL' command...", LOGLEVELS.DEBUG)

		GPIO.output(self.config['G_PIN'], True) #Indoor Fan
		GPIO.output(self.config['W_PIN'], False) #Heat
		GPIO.output(self.config['Y_PIN'], True) #Cool

		#commenting out reversing valve as I don't have one to test on
		#GPIO.output(self.config['O_PIN'], True) #RV in Cool
		#GPIO.output(self.config['B_PIN'], False) #RV in heat
		return STATES.COOL


	def heat(self):
		self.log(">> Outputting 'HEAT' command...", LOGLEVELS.DEBUG)

		GPIO.output(self.config['G_PIN'], True) #Indoor Fan
		GPIO.output(self.config['W_PIN'], True) #Heat
		GPIO.output(self.config['Y_PIN'], False) #Cool

		#commenting out reversing valve as I don't have one to test on
		#GPIO.output(self.config['O_PIN'], False) #RV in Cool
		#GPIO.output(self.config['B_PIN'], True) #RV in heat
		return STATES.HEAT


	def fan(self): 
		self.log(">> Outputting 'FAN' command...", LOGLEVELS.DEBUG)

		#to blow the rest of the heated / cooled air out of the system
		GPIO.output(self.config['G_PIN'], True) #Indoor Fan
		GPIO.output(self.config['W_PIN'], False) #Heat
		GPIO.output(self.config['Y_PIN'], False) #Cool

		#commenting out reversing valve as I don't have one to test on
		#GPIO.output(self.config['O_PIN'], False) #RV in Cool
		#GPIO.output(self.config['B_PIN'], Fakse) #RV in heat
		return STATES.FAN


	def idle(self):
		self.log(">> Outputting 'IDLE' command...", LOGLEVELS.DEBUG)

		GPIO.output(self.config['G_PIN'], False) #Indoor Fan
		GPIO.output(self.config['W_PIN'], False) #Heat
		GPIO.output(self.config['Y_PIN'], False) #Cool

		#commenting out reversing valve as I don't have one to test on
		#GPIO.output(self.config['O_PIN'], False) #RV in Cool
		#GPIO.output(self.config['B_PIN'], False) #RV in heat

		#time.sleep(10)	#to save pump #fix this... put somwehere else
		return STATES.IDLE


	def getTempTarget(self):
		self.log("getTempTarget()", LOGLEVELS.DEBUG)

		cursor = self.db.cursor()

		#lets grab the latest temp target from the db
		cursor.execute("SELECT * FROM TempTargets ORDER BY `created` DESC")

		targ = cursor.fetchone()

		cursor.close()

		return targ.temp

		self.log(">> getTempTarget result " + str(targs), LOGLEVELS.INFO)


	def setTempTarget(self, target):
		self.log("setTempTarget(" + str(target) + ")", LOGLEVELS.DEBUG)
		cursor = self.db.cursor()

		obj = (None, target, time.time())

		cursor.execute("INSERT INTO TempTargets VALUES (?,?,?)", obj)

		self.db.commit()

		self.log(">> setTempTarget result: " + str(obj), LOGLEVELS.INFO)


	def getTempList(self):
		conDB = self.dbOpen()
		cursor = conDB.cursor()

		cursor.execute("SELECT MAX(moduleID) FROM ModuleInfo")
		totSensors = int(cursor.fetchall()[0][0])


		allModTemps=[]
		for modID in range(totSensors):
			try:
				queryStr = ("SELECT * FROM SensorData WHERE moduleID=%s ORDER BY readingID DESC LIMIT 1" % str(modID+1))
				cursor.execute(queryStr)
				allModTemps.append(float(cursor.fetchall()[0][4]))
			except:
				pass

		cursor.close()
		conDB.close()

		return allModTemps


	def logStatus(self, mode, moduleID, tempTarget, actualTemp, curState):
		conDB = self.dbOpen()
		cursor = conDB.cursor()


		cursor.execute("""INSERT ThermostatLog SET mode=%s, moduleID=%s, tempTarget=%s, actualTemp=%s,
						coolOn=%s, heatOn=%s, fanOn=%s, auxOn=%s"""%
						(str(mode),str(moduleID),str(tempTarget),str(actualTemp),
						str(curState[1]),str(curState[2]),str(curState[0]),str(curState[3])))

		cursor.close()
		conDB.commit()
		conDB.close()   



	def run(self, debug = False):

		abspath = os.path.abspath(__file__)
		dname = os.path.dirname(abspath)
		os.chdir(dname)

		LAST = {
			"sensor": time.time(),
			"process": time.time()}

		self.configureGPIO()


		#enter the main loop, this is the heart of this daemon
		while True:
			now = time.time()

			#log temp from onboard sensor (module 1)
			elapsed = now - LAST['sensor']
			if elapsed > self.config['frequency']:
				curTemp = self.readTemp()
				#write to DB
				LAST['sensor'] = time.time()


			#instead of sleep(5)ing, let's run this loop as fast as possible, but only process the temp if a certain amount of time has elapsed
			#this seems unnecessary, as what would be the problem with processing faster?... must think about this
			elapsed = now - LAST['process']
			if elapsed > 5:

				tempTarget = self.getTempTarget() #pulling temp from db
				curTemp = 80

				curState = self.readState()
				curMode = self.MODE

				self.log("Mode: "+ curMode.name + " State: " + curState.name + " Currently: " + str(curTemp) + " Targeting: " + str(tempTarget), LOGLEVELS.INFO)


				if curMode== MODES.HEAT:	#if we are in manual HEAT mode

					if curTemp < tempTarget:
						self.STATE = self.heat()

					if curTemp >= tempTarget:
						self.STATE = self.idle()


				elif curMode == MODES.COOL: #if we are in manual COOL mode

					if curTemp > tempTarget:
						self.STATE = self.cool()

					if curTemp <= tempTarget:
						self.STATE = self.idle()
				

				else:

					self.log("This is weird, the current mode is not valid.", LOGLEVELS.PANIC)

				LAST['process'] = time.time()


def namedtuple_factory(cursor, row):
    """
    Usage:
    con.row_factory = namedtuple_factory
    """
    fields = [col[0] for col in cursor.description]
    Row = namedtuple("Row", fields)
    return Row(*row)
