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

# from daemon import runner
from getIndoorTemp import getIndoorTemp

#set working directory to where "thermDaemon.py" is
abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
# os.chdir(dname)

#read values from the config file
config = configparser.ConfigParser()
config.read(dname+"/rpi.conf")

active_hysteresis = config.getfloat('main','active_hysteresis')
inactive_hysteresis = config.getfloat('main','inactive_hysteresis')


ORANGE_PIN = int(config.get('main','ORANGE_PIN'))
YELLOW_PIN = int(config.get('main','YELLOW_PIN'))
GREEN_PIN = int(config.get('main','GREEN_PIN'))
AUX_PIN = int(config.get('main','AUX_PIN'))

AUX_ID = int(config.get('main','AUX_ID'))

AUX_TIMER = 10 #minutes
AUX_THRESH = 0.2 #degrees

CONN_PARAMS = (config.get('main','mysqlHost'), config.get('main','mysqlUser'),
               config.get('main','mysqlPass'), config.get('main','mysqlDatabase'),
               int(config.get('main','mysqlPort')))

LOGLEVELS = Enum('LOGLEVELS', 'INFO WARNING EXCEPTION ERROR PANIC DEBUG')


class raspistat(Daemon):

	def log(self, message, level):
		print('[' + level.name + '] ' + message );

		
	def configureGPIO(self):

		self.log("Configuring GPIO", LOGLEVELS.INFO)

		GPIO.setmode(GPIO.BCM)
		GPIO.setup(ORANGE_PIN, GPIO.OUT)
		GPIO.setup(YELLOW_PIN, GPIO.OUT)
		GPIO.setup(GREEN_PIN, GPIO.OUT)
		GPIO.setup(AUX_PIN, GPIO.OUT)

		self.log("Exporting GPIO", LOGLEVELS.DEBUG)

		subprocess.Popen("echo " + str(ORANGE_PIN) + " > /sys/class/gpio/export", shell=True)
		subprocess.Popen("echo " + str(YELLOW_PIN) + " > /sys/class/gpio/export", shell=True)
		subprocess.Popen("echo " + str(GREEN_PIN) + " > /sys/class/gpio/export", shell=True)
		subprocess.Popen("echo " + str(AUX_PIN) + " > /sys/class/gpio/export", shell=True)


	def getHVACState(self):

		self.log("getHVACState - pulling pin values", LOGLEVELS.DEBUG)
		
		orangeStatus = int(subprocess.Popen("cat /sys/class/gpio/gpio" + str(ORANGE_PIN) + "/value", shell=True, stdout=subprocess.PIPE).stdout.read().strip())
		yellowStatus = int(subprocess.Popen("cat /sys/class/gpio/gpio" + str(YELLOW_PIN) + "/value", shell=True, stdout=subprocess.PIPE).stdout.read().strip())
		greenStatus = int(subprocess.Popen("cat /sys/class/gpio/gpio" + str(GREEN_PIN) + "/value", shell=True, stdout=subprocess.PIPE).stdout.read().strip())
		auxStatus = int(subprocess.Popen("cat /sys/class/gpio/gpio" + str(AUX_PIN) + "/value", shell=True, stdout=subprocess.PIPE).stdout.read().strip())
		

		if orangeStatus == 1 and yellowStatus == 1 and greenStatus == 1 and auxStatus == 0:
		   #cooling
			return (1, 1, 0, 0)
		
		elif yellowStatus == 1 and greenStatus == 1:
			 #heating
			if auxStatus == 0:
				return (1, 0, 1, 0)
			else:
				return (1, 0, 1, 1)

		elif orangeStatus == 0 and yellowStatus == 0 and greenStatus == 0 and auxStatus == 0:
			#idle
			return (0, 0, 0, 0)

		elif orangeStatus == 0 and yellowStatus == 0 and greenStatus == 1 and auxStatus == 0:
			#fan
			return (1, 0 , 0, 0)

		else:
			#broken
			return (1, 1, 1, 1)

	def cool(self):
		GPIO.output(ORANGE_PIN, True)
		GPIO.output(YELLOW_PIN, True)
		GPIO.output(GREEN_PIN, True)
		GPIO.output(AUX_PIN, False)
		return (1, 1, 0, 0)

	def heat(self):
		GPIO.output(ORANGE_PIN, False)
		GPIO.output(YELLOW_PIN, True)
		GPIO.output(GREEN_PIN, True)
		GPIO.output(AUX_PIN, False)
		return (1, 0, 1, 0)

	def aux(self):
		GPIO.output(ORANGE_PIN, False)
		GPIO.output(YELLOW_PIN, True)
		GPIO.output(GREEN_PIN, True)
		GPIO.output(AUX_PIN, True)
		return (1, 0, 1, 1)

	def fan(self): 
		#to blow the rest of the heated / cooled air out of the system
		GPIO.output(ORANGE_PIN, False)
		GPIO.output(YELLOW_PIN, False)
		GPIO.output(GREEN_PIN, True)
		GPIO.output(AUX_PIN, False)
		return (1, 0, 0, 0)

	def idle(self):
		GPIO.output(ORANGE_PIN, False)
		GPIO.output(YELLOW_PIN, False)
		GPIO.output(GREEN_PIN, False)
		GPIO.output(AUX_PIN, False)
		#delay to preserve compressor
		print('Idling...')
		time.sleep(360)
		return (0, 0, 0, 0)

	def off(self):
		GPIO.output(ORANGE_PIN, False)
		GPIO.output(YELLOW_PIN, False)
		GPIO.output(GREEN_PIN, False)
		GPIO.output(AUX_PIN, False)
	
		return (0, 0, 0, 0)


	def getDBTargets(self):
		conDB = mdb.connect(CONN_PARAMS[0],CONN_PARAMS[1],CONN_PARAMS[2],CONN_PARAMS[3],port=CONN_PARAMS[4])
		cursor = conDB.cursor()

		cursor.execute("SELECT * from ThermostatSet")

		targs = cursor.fetchall()[0]

		cursor.close()
		conDB.close()
		return targs[:-1]


	def getTempList(self):
		conDB = mdb.connect(CONN_PARAMS[0],CONN_PARAMS[1],CONN_PARAMS[2],CONN_PARAMS[3],port=CONN_PARAMS[4])
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

	def logStatus(self, mode, moduleID, targetTemp,actualTemp,hvacState):
		conDB = mdb.connect(CONN_PARAMS[0],CONN_PARAMS[1],CONN_PARAMS[2],CONN_PARAMS[3],port=CONN_PARAMS[4])
		cursor = conDB.cursor()


		cursor.execute("""INSERT ThermostatLog SET mode=%s, moduleID=%s, targetTemp=%s, actualTemp=%s,
						coolOn=%s, heatOn=%s, fanOn=%s, auxOn=%s"""%
						(str(mode),str(moduleID),str(targetTemp),str(actualTemp),
						str(hvacState[1]),str(hvacState[2]),str(hvacState[0]),str(hvacState[3])))

		cursor.close()
		conDB.commit()
		conDB.close()   

	def heatMode(self,auxBool=False):
		hvacState=self.getHVACState()
		tempList = self.getTempList()

		setTime, moduleID, targetTemp, targetMode, expiryTime = self.getDBTargets()

		if hvacState == (0,0,0,0): #idle
			if tempList[moduleID-1] < targetTemp - inactive_hysteresis:
				hvacState = self.heat()

		elif hvacState == (1,0,1,0) or hvacState == (1,0,1,1): #heating
			if auxBool:
				hvacState = self.aux()
			else:
				hvacState = self.heat()

			if tempList[moduleID-1] > targetTemp + active_hysteresis:
				self.fan()
				time.sleep(30)
				hvacState = self.idle()

		elif hvacState == (1,1,0,0): # it's cold out, why is the AC running?
						hvacState = self.idle()
		return hvacState

	def coolMode(self):
		hvacState=self.getHVACState()
		tempList = self.getTempList()

		setTime, moduleID, targetTemp, targetMode, expiryTime = self.getDBTargets()

		if hvacState == (0,0,0,0): #idle
			print(tempList[moduleID-1],targetTemp,inactive_hysteresis)
			if tempList[moduleID-1] > targetTemp + inactive_hysteresis:
				hvacState = self.cool()

		elif hvacState == (1,1,0,0): #cooling
			if tempList[moduleID-1] < targetTemp - active_hysteresis:
				self.fan()
				time.sleep(30)

				hvacState = self.idle()

		elif hvacState == (1,0,1,0) or hvacState == (1,0,1,1): # it's hot out, why is the heater on?
				hvacState = self.idle()
		return hvacState
	


	def run(self,debug=False):
		lastDB = time.time()
		lastAux = time.time()
		auxTemp = 0
		auxBool = False
		trueCount = 0
		self.configureGPIO()
		actMode = "'Off'"
		while True:
			abspath = os.path.abspath(__file__)
			dname = os.path.dirname(abspath)

			os.chdir(dname)

			now = time.time()

			dbElapsed = now - lastDB
				
			if self.getHVACState()[2] == 1: 
				auxElapsed = now - lastAux
			else:
				auxElapsed = 0


			setTime, moduleID, targetTemp, targetMode, expiryTime = self.getDBTargets()
			moduleID = int(moduleID)
			targetTemp = int(targetTemp)

			tempList = self.getTempList()


			if auxElapsed > AUX_TIMER*60:
				
				curTemp = tempList[AUX_ID-1]
				delta = float(curTemp)-float(auxTemp)
				auxTemp = curTemp
				lastAux = time.time()

				if delta < AUX_THRESH and self.getHVACState()[2] == 1:
					trueCount += 1
					if auxBool is True or trueCount == 3:
						auxBool = True
						trueCount = 0
					else:
						auxBool = False
				else:
					auxBool = False
					



			if dbElapsed > 60:
				getIndoorTemp(sendToDB=True)
				self.logStatus(actMode,moduleID,targetTemp,tempList[moduleID-1],self.getHVACState())
				lastDB = time.time()

				hvacState = self.getHVACState()
				

				if actMode[1:-1] not in targetMode:
					hvacState = self.idle()
				# heater mode
				if targetMode == 'Heat':
					self.heatMode(auxBool)
					actMode = "'Heat'"

				# ac mode
				elif targetMode == 'Cool':
					self.coolMode()
					actMode ="'Cool'"

				# fan mode
				elif targetMode == 'Fan':
					hvacState = self.fan()
					actMode="'Fan'"
					

				elif targetMode == 'Off':
					hvacState = self.off()
					actMode="'Off'"
				else:
					self.log('It Broke?', LOGLEVELS.PANIC)

				self.log('Pin Value State:' + self.getHVACState(), LOGLEVELS.INFO)
				self.log('Target Mode:' + targetMode)
				self.log('Actual Mode:' + actMode)
				self.log('Temp from DB:' + tempList)
				self.log('Target Temp:' + targetTemp)



				time.sleep(5)

			#except Exception as e:
			#	if debug==True:
			#		self.log('An overall exception occurred. Check the logs!', LOGLEVELS.EXCEPTION)
			#		# raise
			#	exc_type, exc_obj, exc_tb = sys.exc_info()
			#	fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
			#	fobj = open(dname+'/rpi.log','at')
			#
			#	fobj.write(datetime.now().strftime('%c') + '\n')
			#	fobj.write(str(exc_type.__name__)+'\n')
			#	fobj.write(str(fname)+'\n')
			#	fobj.write(str(exc_tb.tb_lineno)+'\n\n')




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
