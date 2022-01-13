#!/usr/bin/env python3
 
import sys, os
from TSBr import TSBDaemon

if __name__ != "__main__":
  print("This must be executed directly.")
  sys.exit(3)

my_path = os.path.dirname(os.path.abspath(__file__))
with open(my_path + "/ts_br_config.json", "r") as config:
  daemon = TSBDaemon.from_json(config.read())

if len(sys.argv) == 2:
  if 'start' == sys.argv[1]:
    print("Starting...")
    daemon.start()
  elif 'stop' == sys.argv[1]:
    print("Stopping...")
    daemon.stop()
  elif 'restart' == sys.argv[1]:
    print("Restarting...")
    daemon.restart()
  elif 'testrun' == sys.argv[1]:
    daemon.run()
  elif 'nodaemon' == sys.argv[1]:
    daemon.run()
  else:
    print("Unknown command")
    sys.exit(2)
  sys.exit(0)
else:
  print("usage: %s start|stop|restart" % sys.argv[0])
  sys.exit(2)
