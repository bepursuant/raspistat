#! /usr/bin/python3

import sys
import subprocess
import os
import time
import RPi.GPIO as GPIO
from datetime import datetime
import configparser
from enum import Enum

import pymysql as mdb

from PythonDaemon import Daemon


#set working directory to where "thermDaemon.py" is
abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
# os.chdir(dname)

#read values from the config file
config = configparser.ConfigParser()
config.read(dname + "/rpi.conf")

LOGLEVEL = config.get('main', 'LOGLEVEL')

overshoot = config.getfloat('main', 'overshoot')
slump = config.getfloat('main', 'slump')

TEMP_ELAPSED = config.getfloat('main', 'TEMP_ELAPSED')

#R_PIN = config.getint('hardware', 'R_PIN') #24 AC Power
#B_PIN = config.getint('hardware', 'B_PIN') #24V AC Common
G_PIN = config.getint('hardware', 'G_PIN') #Indoor Fan
W_PIN = config.getint('hardware', 'W_PIN') #Heat
Y_PIN = config.getint('hardware', 'Y_PIN') #Cool

#commenting out reversing valve as I don't have one to test on
#O_PIN = config.getint('hardware', 'O_PIN') #RV in Cool
#B_PIN = config.getint('hardware', 'B_PIN') #RV in heat

DB_HOST = config.get('database', 'DB_HOST')
DB_PORT = config.getint('database', 'DB_PORT')
DB_USER = config.get('database', 'DB_USER')
DB_PASS = config.get('database', 'DB_PASS')
DB_NAME = config.get('database', 'DB_NAME')


#setup enums for code readability
LOGLEVELS = Enum('LOGLEVELS', 'DEBUG INFO WARNING ERROR EXCEPTION PANIC')

STATES = Enum('STATES', 'IDLE FAN HEAT COOL PANIC')

testTemp = 80


class raspistat(Daemon):

	def log(self, message, level):
		if level.value >= LOGLEVELS[LOGLEVEL].value:
			print(datetime.now().strftime("%FT%TZ") + (' [' + level.name + ']').ljust(11) + message );

		
	def configureGPIO(self):

		self.log("Configuring GPIO", LOGLEVELS.INFO)

		GPIO.setmode(GPIO.BCM)
		GPIO.setup(G_PIN, GPIO.OUT)
		GPIO.setup(W_PIN, GPIO.OUT)
		GPIO.setup(Y_PIN, GPIO.OUT)


		self.log("Exporting GPIO", LOGLEVELS.DEBUG)

		subprocess.Popen("echo " + str(G_PIN) + " > /sys/class/gpio/export", shell=True)
		subprocess.Popen("echo " + str(W_PIN) + " > /sys/class/gpio/export", shell=True)
		subprocess.Popen("echo " + str(Y_PIN) + " > /sys/class/gpio/export", shell=True)

		subprocess.Popen("echo " + str(G_PIN) + " > /sys/class/gpio/export", shell=True)  #Indoor Fan
		subprocess.Popen("echo " + str(W_PIN) + " > /sys/class/gpio/export", shell=True)  #Heat
		subprocess.Popen("echo " + str(Y_PIN) + " > /sys/class/gpio/export", shell=True)  #Cool


	def dbOpen(self):
		return mdb.connect(host=DB_HOST, port=DB_PORT, user=DB_USER, passwd=DB_PASS, db=DB_NAME)


	def readTemp(self):

		self.log("readTemp - pulling onboard sensor value", LOGLEVELS.DEBUG)

		return testTemp

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

		self.log("readState - pulling pin values", LOGLEVELS.DEBUG)

		GStatus = int(subprocess.Popen("cat /sys/class/gpio/gpio" + str(G_PIN) + "/value", shell=True, stdout=subprocess.PIPE).stdout.read().strip())
		WStatus = int(subprocess.Popen("cat /sys/class/gpio/gpio" + str(W_PIN) + "/value", shell=True, stdout=subprocess.PIPE).stdout.read().strip())
		YStatus = int(subprocess.Popen("cat /sys/class/gpio/gpio" + str(Y_PIN) + "/value", shell=True, stdout=subprocess.PIPE).stdout.read().strip())
		

		if GStatus == 1 and YStatus == 1:
			return STATES.COOL
		
		elif GStatus == 1 and WStatus == 1:
			return STATES.HEAT

		elif GStatus == 1 and YStatus == 0 and WStatus == 0:
			return STATES.FAN

		elif GStatus == 0 and WStatus == 0 and YStatus == 0:
			return STATES.IDLE

		else:
			self.log('readState - Panic state! Pin reads dont make sense...', LOGLEVELs.ERROR)
			return STATES.PANIC


	def cool(self):
		self.log('Outputting "COOL" command...', LOGLEVELS.DEBUG)

		GPIO.output(G_PIN, True) #Indoor Fan
		GPIO.output(W_PIN, False) #Heat
		GPIO.output(Y_PIN, True) #Cool

		#commenting out reversing valve as I don't have one to test on
		#GPIO.output(O_PIN, True) #RV in Cool
		#GPIO.output(B_PIN, False) #RV in heat
		return STATES.COOL


	def heat(self):
		self.log('Outputting "HEAT" command...', LOGLEVELS.DEBUG)

		GPIO.output(G_PIN, True) #Indoor Fan
		GPIO.output(W_PIN, True) #Heat
		GPIO.output(Y_PIN, False) #Cool

		#commenting out reversing valve as I don't have one to test on
		#GPIO.output(O_PIN, False) #RV in Cool
		#GPIO.output(B_PIN, True) #RV in heat
		return STATES.HEAT


	def fan(self): 
		self.log('Outputting "FAN" command...', LOGLEVELS.DEBUG)

		#to blow the rest of the heated / cooled air out of the system
		GPIO.output(G_PIN, True) #Indoor Fan
		GPIO.output(W_PIN, False) #Heat
		GPIO.output(Y_PIN, False) #Cool

		#commenting out reversing valve as I don't have one to test on
		#GPIO.output(O_PIN, False) #RV in Cool
		#GPIO.output(B_PIN, Fakse) #RV in heat
		return STATES.FAN


	def idle(self):
		self.log('Outputting "IDLE" command...', LOGLEVELS.DEBUG)

		GPIO.output(G_PIN, False) #Indoor Fan
		GPIO.output(W_PIN, False) #Heat
		GPIO.output(Y_PIN, False) #Cool

		#commenting out reversing valve as I don't have one to test on
		#GPIO.output(O_PIN, False) #RV in Cool
		#GPIO.output(B_PIN, False) #RV in heat

		time.sleep(10)	#to save pump
		return STATES.IDLE


	def getDBTargets(self):
		conDB = self.dbOpen()
		cursor = conDB.cursor()

		cursor.execute("SELECT * from ThermostatSet")

		targs = cursor.fetchall()[0]

		cursor.close()
		conDB.close()
		return targs[:-1]


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


	def logStatus(self, mode, moduleID, targetTemp, actualTemp, curState):
		conDB = self.dbOpen()
		cursor = conDB.cursor()


		cursor.execute("""INSERT ThermostatLog SET mode=%s, moduleID=%s, targetTemp=%s, actualTemp=%s,
						coolOn=%s, heatOn=%s, fanOn=%s, auxOn=%s"""%
						(str(mode),str(moduleID),str(targetTemp),str(actualTemp),
						str(curState[1]),str(curState[2]),str(curState[0]),str(curState[3])))

		cursor.close()
		conDB.commit()
		conDB.close()   


	def heatMode(self, auxBool=False):
		curState=self.readState()
		tempList = self.getTempList()

		setTime, moduleID, targetTemp, targetMode, expiryTime = self.getDBTargets()

		if curState == (0,0,0,0): #idle
			if tempList[moduleID-1] < targetTemp - inactive_hysteresis:
				curState = self.heat()

		elif curState == (1,0,1,0) or curState == (1,0,1,1): #heating
			if auxBool:
				curState = self.aux()
			else:
				curState = self.heat()

			if tempList[moduleID-1] > targetTemp + active_hysteresis:
				self.fan()
				time.sleep(30)
				curState = self.idle()

		elif curState == (1,1,0,0): # it's cold out, why is the AC running?
						curState = self.idle()
		return curState


	def coolMode(self):
		curState=self.readState()
		tempList = self.getTempList()

		setTime, moduleID, targetTemp, targetMode, expiryTime = self.getDBTargets()

		if curState == (0,0,0,0): #idle
			print(tempList[moduleID-1],targetTemp,inactive_hysteresis)
			if tempList[moduleID-1] > targetTemp + inactive_hysteresis:
				curState = self.cool()

		elif curState == (1,1,0,0): #cooling
			if tempList[moduleID-1] < targetTemp - active_hysteresis:
				self.fan()
				time.sleep(30)

				curState = self.idle()

		elif curState == (1,0,1,0) or curState == (1,0,1,1): # it's hot out, why is the heater on?
				curState = self.idle()
		return curState
	


	def run(self,debug=False):
		global testTemp

		abspath = os.path.abspath(__file__)
		dname = os.path.dirname(abspath)
		os.chdir(dname)

		lastRead = time.time()

		self.configureGPIO()

		#actMode = "'Off'"

		#enter the main loop, this is the heart of this daemon
		while True:
			now = time.time()

			#log temp from onboard sensor (module 1)
			elapsed = now - lastRead
			if elapsed > TEMP_ELAPSED:
				curTemp = self.readTemp()
				#write to DB
				lastRead = time.time()


			curTemp = self.readTemp() #find from DB
			targetTemp = 82 #find from DB

			curState = self.readState()

			self.log("State: " + curState.name + " Currently: " + str(curTemp) + " Targeting: " + str(targetTemp), LOGLEVELS.INFO)

			
			#are we too hot?
			if curTemp - overshoot > targetTemp:
				if curState == STATES.COOL or curState == STATES.IDLE:
					self.log('Going into cool mode', LOGLEVELS.INFO)
					curState = self.cool()
				else:
					self.log("curTemp - overshoot is greater than target, but we're in cool mode so ignore", LOGLEVELS.DEBUG)

			#are we too cold?
			elif curTemp + slump < targetTemp:
				if curState == STATES.HEAT or curState == STATES.IDLE:
					self.log('Going into heat mode', LOGLEVELS.INFO)
					curState = self.heat()
				else:
					self.log("curTemp + slump is less than target, but we're in heat mode so ignore", LOGLEVELS.DEBUG)

			else:
				self.log('Going into idle mode', LOGLEVELS.INFO)
				curState = self.idle();


			time.sleep(5)

			#simulation mode
			if curState == STATES.COOL:
				testTemp -= 0.5

			if curState == STATES.HEAT:
				testTemp += 0.5

			if curState == STATES.IDLE:
				testTemp -= 0.5




if __name__ == "__main__":
        daemon = raspistat(dname+'/raspistat.pid')
      

        if len(sys.argv) == 2:
                if 'start' == sys.argv[1]:
                        daemon.start()
                elif 'stop' == sys.argv[1]:
                        daemon.stop()
                elif 'restart' == sys.argv[1]:
                        daemon.restart()
                elif 'debug' == sys.argv[1]:
                        daemon.run(True)
                else:
                        print('Unknown command')
                        sys.exit(2)
                

                sys.exit(0)
        else:
                print("raspistat daemon usage: %s start|stop|restart|debug" % sys.argv[0])
                sys.exit(2)
