#!/usr/bin/env python3

##############################################################################
# Description
#-----------------------------------------------------------------------------
# This file calls the HAL Time Series Bridge directly without need for the
# daemonization script.  This is to allow systemd to control the process
# without need for calling the weird daemonization things and allows us to log
# directly to syslog without needing to use libraries that allow us to do the
# same thing.
#
# If this works correctly, daemonization will be deprecated and eventually
# removed.
##############################################################################

import sys, os
from TSBr import TSB

if __name__ != "__main__":
    print("This script must be executed directly.")
    sys.exit(3)

my_path = os.path.dirname(os.path.abspath(__file__))
ts_bridge = TSB()
with open(my_path + "/ts_br_config.json", "r") as config:
    ts_bridge.config = ts_bridge.config.from_json(config.read())

ts_bridge.run()
