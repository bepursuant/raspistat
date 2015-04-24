[main]
DEBUG = 1

#show log events equal to or above this threshold
#DEBUG INFO WARNING ERROR EXCEPTION PANIC
LOGLEVEL = ERROR

#amount that read temp can stray from target before we take action
active_pad = 1
inactive_pad = 1

[database]
type = sqlite
file = raspistat.sqlite3

#example for mysql
#type = mysql
#host = 127.0.0.1
#port = 3306
#user = USER
#pass = PASS
#name = raspistat

[hardware]
#R_PIN = 21
#B_PIN = 22
G_PIN = 12
W_PIN = 13
Y_PIN = 14

#commenting out reversing valve as I don't have one to test on
#O_PIN = 23
#B_PIN = 24

[sensor]
#frequency to report temp to db in seconds
frequency = 60