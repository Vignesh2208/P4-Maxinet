import os
import time
import sys
time.sleep(0.5)
os.system("iperf -c "+ str(sys.argv[1]) + " -t 10 -u -b 300m -l 1400B")
#os.system("/home/moses/qos_synthesis/traffic_generation/udp_client/client "+ str(sys.argv[1]) + " 100000 5000 1000")

