#! /usr/bin/python3

import os
import sys
from RaspistatDaemon import RaspistatDaemon

#set working directory to where "thermDaemon.py" is
abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
# os.chdir(dname)


if __name__ == "__main__":
    daemon = RaspistatDaemon(dname+'/raspistat.pid')
  

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
