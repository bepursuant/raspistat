[main]
DEBUG = 0

#amount that read temp can stray from target before we take action
active_hysteresis = 1
inactive_hysteresis = 2

ORANGE_PIN = 17
YELLOW_PIN = 27
GREEN_PIN = 22
AUX_PIN = 23

#Module ID that you wish to control the Aux heat.  This is to avoid
#Aux heat coming on for temperature fluctuations that may occur from
# a door opening, etc. This should probably be the sensor that is in
# the same place as your original thermostat.
AUX_ID = 1


mysqlUser = root
mysqlPass = rootley
mysqlDatabase = raspistat
mysqlHost = 127.0.0.1
mysqlPort = 3306
