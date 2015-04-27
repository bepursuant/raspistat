#! /usr/bin/python3

import os
import sys
from RaspistatDaemon import RaspistatDaemon

#set working directory to where "thermDaemon.py" is
abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
# os.chdir(dname)

if __name__ == "__main__":
    
    daemon = RaspistatDaemon(pidfile=dname+'/raspistat.pid',
        configfile=dname+'/raspistat.cfg')
  

    if len(sys.argv) >= 2:
        if 'start' == sys.argv[1]:
            daemon.start()

        elif 'stop' == sys.argv[1]:
            daemon.stop()

        elif 'restart' == sys.argv[1]:
            daemon.restart()

        elif 'debug' == sys.argv[1]:
            daemon.run(True)

        elif 'setTarget' == sys.argv[1]:
            target = sys.argv[2]

            if(len(sys.argv) >= 4):
                precision = sys.argv[3]
            else:
                precision = None

            daemon.setTarget(target, precision)

        elif 'setMode' == sys.argv[1]:
            mode = sys.argv[2]

            daemon.setMode(mode)

        elif 'setTemp' == sys.argv[1]:
            temp = sys.argv[2]

            daemon.setTemp(temp)

        else:
            print('Unknown command')
            sys.exit(2)
            

        sys.exit(0)

    else:
        print("raspistat daemon usage: %s start|stop|restart|debug" % sys.argv[0])
        sys.exit(2)