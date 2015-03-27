[main]
DEBUG = 0

#show log events equal to or above this threshold
#DEBUG INFO WARNING ERROR EXCEPTION PANIC
LOGLEVEL = DEBUG

#amount that read temp can stray from target before we take action
active_pad = 1
inactive_pad = 1

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

[sensor]
#frequency to report temp to db in seconds
frequency = 60