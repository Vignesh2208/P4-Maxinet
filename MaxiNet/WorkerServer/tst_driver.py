#!/usr/bin/python2

#
# This is a sample program to emulate P4 Switches in Distributed environment
# using Maxinet. The skeleton application program should be like this 
# 


import argparse
import atexit
import logging
import os
import signal
import subprocess
import sys
import tempfile
import time

import Pyro4
import threading
import traceback

import json 

import mininet.term
from mininet.topo import Topo
from mininet.node import OVSSwitch
from mininet.node import UserSwitch, OVSSwitch
from mininet.link import Link, TCIntf
from mininet.net import Mininet

# from MaxiNet.Frontend import maxinet
from MaxiNet.tools import Tools, MaxiNetConfig
from MaxiNet.WorkerServer.ssh_manager import SSH_Manager
from run_exercise import ExerciseRunner
from p4_mininet import P4Switch

from shutil import *
import pdb

script_dir = os.path.dirname(os.path.realpath(__file__))


def install_cmnds_to_run_on_hosts(my_workers, data) :
    for host, my_cmd in data["host_cmnds"] :
        #print "Setting Command on Host ...", host, " Cmd: ", my_cmd
        with open("/tmp/tmp_" + str(host) + "_cmnds.txt", "w") as f :
            f.write(my_cmd + "\n")
        for worker in my_workers :
            worker.put_file("/tmp/tmp_" + str(host) + "_cmnds.txt", "/tmp/" + str(host) + "_cmnds.txt") 
    raw_input("[Continue...]")

# Include Project Directory in PYTHONPATH
# This is done to pickup changes done by us in MaxiNet Frontend

curr_path = os.getcwd()
parent_path = os.path.abspath(os.path.join(os.getcwd(), '..'))
parent_dir = os.path.basename(os.path.abspath(parent_path))
sys.path.insert(1,parent_path)

from Frontend import  maxinet


# create topology
myglobalTopo = Topo()

parser = argparse.ArgumentParser()

parser.add_argument('--topo', dest="topo_fname", default="in_topo.json", help = "Input Topology file for Experiment")

parser.add_argument('--swlog_dir', dest="swlog_dir", default="/tmp", help = "Directory path for Switch Log files ")

parser.add_argument('--pcap_dir', dest="pcap_dir", default="/tmp", help = "Directory path for Switch pcap files ")

parser.add_argument('--switch_json', dest="switch_json", default="/tmp/routernew.json", help = "P4 Switch Parser JSON")

parser.add_argument('--switch_exe', dest="switch_exe",default="/home/moses/behavioral-model/targets/simple_switch/.libs/simple_switch",  help="P4 Switch Executable")

#parser.add_argument('--switch_exe', dest="switch_exe",default="simple_switch",  help="P4 Switch Executable")

#parser.add_argument('--switch_exe', dest="switch_exe",default="/home/moses/behavioral-model/targets/simple_router/.libs/simple_router",  help="P4 Switch Executable")

parser.add_argument('--mininet_cli', dest="cli_opt", default="False", help = "Invoke at Mininet CLI in the Workers")

parser.add_argument('--switch_init', dest="swinit_opt", default="ByApp", help = "Switch Initialization AtStart | ByApp")

parser.add_argument('--num_workers', dest="num_workers", default=1, help = "Number of Workers for the Experiment : (Default 1) ")

parser.add_argument('--operating_mode', dest="operating_mode", default="NORMAL", help = "Operating Mode: NORMAL/INS_VT/VT ")

parser.add_argument('--host_rel_cpu_speed', dest="host_rel_cpu_speed", default=3, help = "Rel cpu speed for INS_VT ")

parser.add_argument('--switch_rel_cpu_speed', dest="switch_rel_cpu_speed", default=3, help = "Rel cpu speed for INS_VT ")


parser.add_argument('--n_round_insns', dest="n_round_insns", default=100000, help = "N instructions per round for INS_VT ")

parser.add_argument('--progress_duration', dest="progress_duration", default=2, help = "Progress duration in sec INS_VT ")

parser.add_argument('--n_constrained_cpus', dest="n_constrained_cpus", default=0, help = "Number of cpus to constrain in NORMAL mode")

parser.add_argument('--tdf', dest="tdf", default=1.0, help = "TDF for VT mode")

parser.add_argument('--TIMESLICE', dest="TIMESLICE", default=1000000, help = "TIMESLICE for VT mode")

args = parser.parse_args()

if args.topo_fname :
    topo_fname = str(args.topo_fname)
    #print "Input Topo File Name is ...", topo_fname

if args.swlog_dir :
    swlog_dir = str(args.swlog_dir)
    #print "Switch Log Dir ...", swlog_dir

if args.pcap_dir :
    pcap_dir = str(args.pcap_dir)
    #print "Pcap Dir ...", pcap_dir

if args.switch_json :
    switch_json = str(args.switch_json)
    #print "Switch Parser JSON File Name ...", switch_json

if args.switch_exe :
    switch_exe = str(args.switch_exe)
    #print "Switch EXE Name ...", switch_exe

if args.cli_opt :
    cli_opt = str(args.cli_opt)
    #print "Mininet CLI Option ...", cli_opt

if args.swinit_opt :
    swinit_opt = str(args.swinit_opt)
    #print "Switch Init Option ...", swinit_opt

if args.num_workers :
    num_workers = int(args.num_workers)
    #print "Number of Workers ...", num_workers

PER_ITER_ADVANCE = 1
n_rounds_for_progress_duration = int(int(args.progress_duration)*1000000000/(int(args.n_round_insns)*PER_ITER_ADVANCE))

tk_args = {
    "operating_mode" : args.operating_mode,
    "host_rel_cpu_speed"  : float(args.host_rel_cpu_speed),
    "switch_rel_cpu_speed"  : float(args.switch_rel_cpu_speed),
    "n_round_insns"  : int(args.n_round_insns),
    "progress_n_rounds" : int(n_rounds_for_progress_duration),
    "tdf" : float(args.tdf),
    "TIMESLICE" : int(args.TIMESLICE),
    "n_constrained_cpus": int(args.n_constrained_cpus),
}

# Now save the Input CLI arguments in experiment.cfg file
# Num workers argument is not saved in experiment.cfg file

f = open("t1_experiment.cfg", "w")

out_line="topo_file_name=/tmp/in_topo.json"  # This is going to be hardcoded
print >>f, out_line
out_line="swlog_dir="+str(swlog_dir)
print >>f, out_line
out_line="pcap_dir="+str(pcap_dir)
print >>f, out_line
out_line="p4_switch_json="+str(switch_json)
print >>f, out_line
out_line="bmv2_exe="+str(switch_exe)
print >>f, out_line
out_line="Invoke_mininet_cli="+str(cli_opt)
print >>f, out_line
out_line="p4_switch_initialization="+str(swinit_opt)
print >>f, out_line

f.close()

# Rename the file t1_experiment.cfg -> experiment.cfg
os.rename("t1_experiment.cfg", "experiment.cfg")

# Now also copy the given input topo file as in_topo.json in each of worker
copy2(topo_fname,'in_topo.json')
print "File sucessfully copied as in_topo.json..."


with open('in_topo.json') as data_file:
    data = json.load(data_file)

hnames = data["hosts"]
hlen = len(hnames)
cnt = 1
for x in range(0,hlen) :
    tmp = str(hnames[x])
    myglobalTopo.addHost(tmp, ip=Tools.makeIP(cnt), mac=Tools.makeMAC(cnt))
    cnt = cnt + 1

my_swlist=[]
for key, value in dict.items(data["switches"]):
    my_swlist.append(key) # Add to list of switches in topology
    cnt = 1
    for value1, value2 in dict.items(data["switches"][key]):
        tmp = str(key)
        myglobalTopo.addSwitch(tmp, dpid=Tools.makeDPID(cnt))
        cnt = cnt + 1

#hnames = data["hosts"]
hnames = data["links"]
hlen = len(hnames)
for x in range(0,hlen) :
    tmp = str(hnames[x][0])
    tmp1 = str(hnames[x][1])
    myglobalTopo.addLink(tmp, tmp1)



print "Finished Loading Topology..."
print "Creating Cluster ..."

# start cluster

cluster = maxinet.Cluster(minWorkers=1, maxWorkers=num_workers, tk_args=tk_args)

# start experiment with P4Switch on cluster

exp = maxinet.Experiment(cluster, myglobalTopo, switch=P4Switch)

# We can copy experiment.cfg, in_topo.json files to the respective workers

my_allowed_paths = []
for item in dict.items( data["allowed_paths"] ):
    my_allowed_paths.append(item)

allowed_paths_len = len(my_allowed_paths)

my_workers = cluster.workers()
for worker in my_workers :
    print "Copying to Worker 1...", worker
    worker.put_file("experiment.cfg", "/tmp/experiment.cfg")
    worker.put_file("in_topo.json", "/tmp/in_topo.json")

    if (allowed_paths_len <= 0):
        #print "No Need to Create switch JSON file..."
        worker.put_file("simple_router.json", "/tmp/routernew.json")
    else :
        #print "Create New switch JSON file..."
        # Assumption is that the input topo is in file named in_topo.json
        os.system('python gen_router_json.py')
        worker.put_file("routernew.json", "/tmp/routernew.json")


print "***** Experiment Setup Start *****"
exp.setup()


#print "waiting 10 seconds for routing algorithms on the controller to converge"
#time.sleep(10)


#print "Start Program Switch objects as per topology ..."
#raw_input("[Continue...]")
#for sw in my_swlist :
#    exp.program_myswitch(sw)


if tk_args["operating_mode"] == "INS_VT" or tk_args["operating_mode"] == "VT" :

    """
    for sw in my_swlist :
        exp.program_myswitch(sw)

    print "Loading Cmds to Run on Hosts ..."
    install_cmnds_to_run_on_hosts(my_workers, data)

    print "Running for 30 secs ..."
    time.sleep(30)

    os.system("sudo killall tracer")
    """


       
    n_rounds_for_1sec = int(1000000000/(int(args.n_round_insns)*PER_ITER_ADVANCE))

    print "Initializing Tk Instances ..."
    exp.initializeTkInstances()
    raw_input("[Continue...]")

    for i in xrange(0,n_rounds_for_1sec):
        exp.advanceByNRounds(PER_ITER_ADVANCE)
        exp.fireLinkTimers()

    print "Start Program Switch objects as per topology ..."
    raw_input("[Continue...]")
    for sw in my_swlist :
        exp.program_myswitch(sw)

    
    for i in xrange(0,n_rounds_for_1sec):
        exp.advanceByNRounds(PER_ITER_ADVANCE)
        exp.fireLinkTimers()
        
    print "Loading Cmds to Run on Hosts ..."
    install_cmnds_to_run_on_hosts(my_workers, data)

    print "Advancing Tk Instances By %d " %(tk_args["progress_n_rounds"])
    #exp.advanceByNRounds(tk_args["progress_n_rounds"])
    n_iters_run = 0
    while (n_iters_run < tk_args["progress_n_rounds"]) :
        exp.advanceByNRounds(PER_ITER_ADVANCE)
        exp.fireLinkTimers()
        if n_iters_run % 100 == 0:
            sys.stdout.write(str(n_iters_run) + " ")
            sys.stdout.flush()
         
        n_iters_run += 1
        sys.stdout.flush()

    raw_input("\n[Continue...]")

    print "Stopping Tk Instances ..."
    #On each worker call StopExperiment
    exp.stopTkInstances()
    raw_input("[Continue...]")
    if tk_args["operating_mode"] == "VT" :
        os.system("sudo killall client_n")
        os.system("sudo killall server_n")

else :

    print "Start Program Switch objects as per topology ..."
    raw_input("[Continue...]")
    for sw in my_swlist :
        exp.program_myswitch(sw)
    print "Finished Programming P4 Switches as per topology ..."
    raw_input("[Continue...]")
    exp.initializeTkInstances()
    
    print "Loading Cmds to Run on Hosts ..."
    install_cmnds_to_run_on_hosts(my_workers, data)

    exp.CLI(locals(),globals())
    

    print "Running for 5 secs ..."
    time.sleep(5)
    raw_input("[Continue...]")

print "Tearing Down Worker Mininet Instances ..."
exp.stop()
raw_input("[Continue]")  # wait for user to acknowledge network connectivity
os.system("rm *.txt")
os.system("rm *.cfg")

