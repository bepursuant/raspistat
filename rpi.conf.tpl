[main]
DEBUG = 0

#show log events equal to or above this threshold
#DEBUG INFO WARNING ERROR EXCEPTION PANIC
LOGLEVEL = DEBUG

#amount that read temp can stray from target before we take action
overshoot = 1
slump = 1

#how long should we wait before reading/recording temp from onboard sensor (module 1) in seconds
TEMP_ELAPSED = 60

[database]
DB_HOST = 127.0.0.1
DB_PORT = 3306
DB_USER = USER
DB_PASS = PASS
DB_NAME = raspistat

[hardware]
R_PIN = 2
B_PIN = 3
G_PIN = 4
W_PIN = 17
Y_PIN = 27

#commenting out reversing valve as I don't have one to test on
#O_PIN = 22
#B_PIN = 10