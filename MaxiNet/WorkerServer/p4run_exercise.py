#!/usr/bin/env python2
# Copyright 2013-present Barefoot Networks, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Adapted by Robert MacDavid (macdavid@cs.princeton.edu) from scripts found in
# the p4app repository (https://github.com/p4lang/p4app)
#
# We encourage you to dissect this script to better understand the BMv2/Mininet
# environment used by the P4 tutorial.
#
import os, sys, json, subprocess, re, argparse
from time import sleep

from p4_mininet import P4Switch, P4Host # Modified by RB

from mininet.net import Mininet
from mininet.topo import Topo
from mininet.link import TCLink
from mininet.cli import CLI
import tempfile

from p4runtime_switch import P4RuntimeSwitch # Modified by RB

from mygraph import MyTopoGraph   # Added by RB
from parse_exp_cfg import *
import pdb

#TK imports
import timekeeper_functions
from timekeeper_functions import *
script_dir = os.path.dirname(os.path.realpath(__file__))


def configureP4Switch(tk_args,**switch_args):
    """ Helper class that is called by mininet to initialize
        the virtual P4 switches. The purpose is to ensure each
        switch's thrift server is using a unique port.
    """
    if "sw_path" in switch_args and 'grpc' in switch_args['sw_path']:
        # If grpc appears in the BMv2 switch target, we assume will start P4 Runtime
        class ConfiguredP4RuntimeSwitch(P4RuntimeSwitch):
            def __init__(self, *opts, **kwargs):
                kwargs.update(switch_args)
                P4RuntimeSwitch.__init__(self, *opts, **kwargs)

            def describe(self):
                print "%s -> gRPC port: %d" % (self.name, self.grpc_port)

        return ConfiguredP4RuntimeSwitch
    else:
        class ConfiguredP4Switch(P4Switch):
            next_thrift_port = 9090
            def __init__(self, *opts, **kwargs):
                global next_thrift_port
                kwargs.update(switch_args)

                if "operating_mode" in tk_args :
                    kwargs["operating_mode"] = tk_args["operating_mode"]
                if "rel_cpu_speed" in tk_args :
                    kwargs["rel_cpu_speed"] = tk_args["rel_cpu_speed"]
                if "n_round_insns" in tk_args :
                    kwargs["n_round_insns"] = tk_args["n_round_insns"]

                kwargs['thrift_port'] = ConfiguredP4Switch.next_thrift_port
                ConfiguredP4Switch.next_thrift_port += 1
                P4Switch.__init__(self, *opts, **kwargs)

            def describe(self):
                print "%s -> Thrift port: %d" % (self.name, self.thrift_port)

        return ConfiguredP4Switch


class ExerciseTopo(Topo):
    """ The mininet topology class for the P4 tutorial exercises.
        A custom class is used because the exercises make a few topology
        assumptions, mostly about the IP and MAC addresses.
    """
    def __init__(self, hosts, switches, links, log_dir, **opts):
        Topo.__init__(self, **opts)
        self.host_links = []   # Modified by RB
        self.switch_links = []   # Modified by RB
        self.sw_port_mapping = {}

        for link in links:
            if link['node1'][0] == 'h':
                # Here selectively add only links for hosts in my
                # partitioned topology. The input links has global
                # topology view. This is to prevent unwanted hosts
                # getting created in the worker space
                for tmp_host in hosts:
                    if ( tmp_host == link['node1'] ):
                        # This corresponds to host link of our parition
                        # print "Adding Host link...", link
                        self.host_links.append(link)
                    else:
                        # print "Skipping Host link...", link
                        pass
            else:
                self.switch_links.append(link)

        # Commented by RB to get normal ascending sort
        # link_sort_key = lambda x: x['node1'] + x['node2']
        # Links must be added in a sorted order so bmv2 port numbers are predictable
        # host_links.sort(key=link_sort_key)
        self.host_links.sort()
        # switch_links.sort(key=link_sort_key)
        self.switch_links.sort()

        for sw in switches:
            self.addSwitch(sw, log_file="%s/%s.log" %(log_dir, sw))

        for link in self.host_links:
            host_name = link['node1']
            host_sw   = link['node2']
            host_num = int(host_name[1:])
            sw_num   = int(host_sw[1:])
            host_ip = "10.0.%d.10" % (host_num)
            # host_ip = "10.0.%d.%d" % (sw_num, host_num)
            host_mac = '00:00:00:00:%02x:%02x' % (sw_num, host_num)
            # Each host IP should be /24, so all exercise traffic will use the
            # default gateway (the switch) without sending ARP requests.
            self.addHost(host_name, ip=host_ip+'/24', mac=host_mac)
            # self.addLink(host_name, host_sw,
                         # delay=link['latency'], bw=link['bandwidth'],
                         # addr1=host_mac, addr2=host_mac)
            # self.addSwitchPort(host_sw, host_name)
            # Masked by RB


        # for link in switch_links:
            # self.addLink(link['node1'], link['node2'],
                        # delay=link['latency'], bw=link['bandwidth'])
            # self.addSwitchPort(link['node1'], link['node2'])
            # self.addSwitchPort(link['node2'], link['node1'])
            # Masked by RB

        self.printPortMapping()

    # Added by RB
    def get_topo_hostlinks( self ):
        tmp_links = []
        tmp_links = self.host_links
        return tmp_links

    # Added by RB
    def addMyHostLinkToSwitch(self, hname, swname, link_entry, mac_addr):
        # print "Adding Host Link to my switch ..", swname, hname
        # print "Adding Delay ..", link_entry['latency'] 
        # print "Adding Bandwidth ..", link_entry['bandwidth'] 
        # print "Host Mac addr ..", mac_addr
        if(link_entry['node1'] == hname):
            self.addLink(link_entry['node1'], link_entry['node2'],
                            delay=link_entry['latency'], bw=link_entry['bandwidth'], addr1=mac_addr, addr2=mac_addr)
            # print "Entry Added ..", link_entry['node1'], link_entry['node2']
        else:
            self.addLink(link_entry['node2'], link_entry['node1'],
                            delay=link_entry['latency'], bw=link_entry['bandwidth'], addr1=mac_addr, addr=mac_addr)
            # print "Entry Added ..", link_entry['node2'], link_entry['node1']

    # Added by RB
    def addMyLinkToSwitch(self, swname, link_entry):
        # print "Adding Link to my switch ..", swname
        # print "Adding Delay ..", link_entry['latency'] 
        # print "Adding Bandwidth ..", link_entry['bandwidth'] 
        if(link_entry['node1'] == swname):
            self.addLink(link_entry['node1'], link_entry['node2'],
                            delay=link_entry['latency'], bw=link_entry['bandwidth'])
            # print "Entry Added ..", link_entry['node1'], link_entry['node2']
        else:
            self.addLink(link_entry['node2'], link_entry['node1'],
                            delay=link_entry['latency'], bw=link_entry['bandwidth'])
            # print "Entry Added ..", link_entry['node2'], link_entry['node1']


    # Added by RB
    def addToSwitchAtPort(self, sw, portno, node2):
        # print "Adding to Switch ..", sw, "At port ..", portno, "Node ..",node2
        if sw not in self.sw_port_mapping:
            self.sw_port_mapping[sw] = []
        if node2 not in self.sw_port_mapping[sw]:
            indx = int(portno)
            self.sw_port_mapping[sw].insert(indx, (portno, node2))

    def addSwitchPort(self, sw, node2):
        if sw not in self.sw_port_mapping:
            self.sw_port_mapping[sw] = []
        portno = len(self.sw_port_mapping[sw])+1
        self.sw_port_mapping[sw].append((portno, node2))

    def printPortMapping(self):
        print "Switch port mapping:"
        for sw in sorted(self.sw_port_mapping.keys()):
            print "%s: " % sw,
            for portno, node2 in self.sw_port_mapping[sw]:
                print "%d:%s\t" % (portno, node2),
            print

    # Added by RB
    def getPortMapping(self):
        # print "My Switch Port Mapping..."

        sw_pmaplist = {}
        for sw in sorted(self.sw_port_mapping.keys()):
            if sw not in sw_pmaplist:
                sw_pmaplist[sw] = []
            for portno, node2 in self.sw_port_mapping[sw]:
                host_num = int(node2[1:])
                sw_num   = int(sw[1:])
                host_ip = "10.0.%d.10" % (host_num)
                # host_ip = "10.0.%d.%d" % (sw_num, host_num)
                host_mac = '00:00:00:00:%02x:%02x' % (sw_num, host_num)

                sw_pmaplist[sw].append((portno, node2,host_ip,host_mac))
        return sw_pmaplist


class ExerciseRunner:
    """
        Attributes:
            topo_file : string  // File name which has full topo in JSON form RB
            log_dir  : string   // directory for mininet log files
            pcap_dir : string   // directory for mininet switch pcap files
            quiet    : bool     // determines if we print logger messages

            hosts    : list<string>       // list of mininet host names
            switches : dict<string, dict> // mininet host names and their associated properties
            links    : list<dict>         // list of mininet link properties

            switch_json : string // json of the compiled p4 example
            bmv2_exe    : string // name or path of the p4 switch binary

            topo : Topo object   // The mininet topology instance
            net : Mininet object // The mininet instance

    """
    def logger(self, *items):
        if not self.quiet:
            print(' '.join(items))

    def formatLatency(self, l):
        """ Helper method for parsing link latencies from the topology json. """
        if isinstance(l, (str, unicode)):
            return l
        else:
            return str(l) + "ms"


    def __init__(self, topo_file, log_dir, pcap_dir,
                       switch_json, bmv2_exe='simple_switch',tk_args={}, quiet=False):
        """ Initializes some attributes and reads the topology json. Does not
            actually run the exercise. Use run_exercise() for that.

            Arguments:
                topo_file : string    // A json file which describes the exercise's
                                         mininet topology.
                log_dir  : string     // Path to a directory for storing exercise logs
                pcap_dir : string     // Ditto, but for mininet switch pcap files
                switch_json : string  // Path to a compiled p4 json for bmv2
                bmv2_exe    : string  // Path to the p4 behavioral binary
                quiet : bool          // Enable/disable script debug messages
        """

        self.quiet = quiet
        self.topo_file = topo_file # Added by RB
        self.logger('Reading topology file.')
        with open('/tmp/topology.json', 'r') as f:   # Hard code by RB
            topo = json.load(f)
        self.hosts = topo['hosts']

        # Modified by RB ****
        # Here read the global topology of switches and links instead of
        # topology corresponding to the parition

        with open(self.topo_file, 'r') as f:
            tmp_topo = json.load(f)

        self.switches = tmp_topo['switches']
        self.links = self.parse_links(tmp_topo['links'])
        # print "Exercise Links ... Parsed..."
        # print self.links

        # Ensure all the needed directories exist and are directories
        for dir_name in [log_dir, pcap_dir]:
            if not os.path.isdir(dir_name):
                if os.path.exists(dir_name):
                    raise Exception("'%s' exists and is not a directory!" % dir_name)
                os.mkdir(dir_name)
        self.log_dir = log_dir
        self.pcap_dir = pcap_dir
        self.switch_json = switch_json
        self.bmv2_exe = bmv2_exe
        if "operating_mode" in tk_args :
            self.operating_mode = tk_args["operating_mode"]
        else :
            self.operating_mode = "NORMAL"

        if "rel_cpu_speed" in tk_args :
            self.rel_cpu_speed = tk_args["rel_cpu_speed"]
        else :
            self.rel_cpu_speed = 1.0

        if "n_round_insns" in tk_args :
            self.n_round_insns = tk_args["n_round_insns"]
        else :
            self.n_round_insns = 1000000

        self.tk_args = tk_args

        self.sswitch_cli_pids = []
        self.host_pids = {}
        self.switch_pids = {}
        self.n_rounds_progressed = 0


    def run_exercise(self):
        """ Sets up the mininet instance, programs the switches,
            and starts the mininet CLI. This is the main method to run after
            initializing the object.
        """
        # Initialize mininet with the topology specified by the config
        print "Creating Network .."
        if self.operating_mode == "INS_VT" :
            print "Initializing Local TimeKeeper Instance for Exercise Run ..."
            ret = initializeExp(1);
            if ret < 0 :
                print "TimeKeeper Initialization Failed. Exiting ..."
                sys.exit(-1)

        self.create_network()
        # print "Starting Network .."
        # self.net.start()
        sleep(1)

        # some programming that must happen after the net has started
        # print "Program Hosts .."
        # self.program_hosts()
        # print "Program Switches .."
        # self.program_switches()

        # wait for that to finish. Not sure how to do this better
        sleep(1)

        # self.do_net_cli() # We can mask the CLI for Client to have full cntrl
        # stop right after the CLI is exited
        # self.net.stop()   # Here return to the main program for it to control


    def parse_links(self, unparsed_links):
        """ Given a list of links descriptions of the form [node1, node2, latency, bandwidth]
            with the latency and bandwidth being optional, parses these descriptions
            into dictionaries and store them as self.links
        """
        links = []
        for link in unparsed_links:
            # make sure each link's endpoints are ordered alphabetically
            s, t, = link[0], link[1]
            if s > t:
                s,t = t,s

            link_dict = {'node1':s,
                        'node2':t,
                        'latency':'0ms',
                        'bandwidth':None
                        }
            if len(link) > 2:
                link_dict['latency'] = self.formatLatency(link[2])
            if len(link) > 3:
                link_dict['bandwidth'] = link[3]

            if link_dict['node1'][0] == 'h':
                assert link_dict['node2'][0] == 's', 'Hosts should be connected to switches, not ' + str(link_dict['node2'])
            links.append(link_dict)
        return links


    # Added by RB
    def build_exercise_topo(self):

        self.logger("Building mininet topology.")

        self.topo = ExerciseTopo(self.hosts, self.switches.keys(), self.links, self.log_dir)


    # Added by RB
    def set_tunnel_delay(self, sw_1, sw_2, tun_name ):

        exercise_links = self.get_links_in_exercise()
        delay = 0
        for link_entry in exercise_links:
            if( (( link_entry['node1'] == sw_1) and (link_entry['node2'] == sw_2))  or (( link_entry['node1'] == sw_2) and (link_entry['node2'] == sw_1)) ) :
                delay = link_entry['latency']
                break

        delay_str = str(delay)
        cmd_str = "tc qdisc add dev " + str(tun_name) + " root netem delay " + delay_str
        print "Going to execute command ...", cmd_str, "On..", sw_1
        sw = self.net.get( str(sw_1) )
        result = sw.cmd(cmd_str)
        print "Result ...", result

    # Added by RB
    def get_links_in_exercise(self):
        tmp_links = {}
        tmp_links = self.links
        return tmp_links

    def create_network(self):
        """ Create the mininet network object, and store it as self.net.

            Side effects:
                - Mininet topology instance stored as self.topo
                - Mininet instance stored as self.net
        """
        # self.logger("Building mininet topology.")

        # self.topo = ExerciseTopo(self.hosts, self.switches.keys(), self.links, self.log_dir)

        print "Configuring p4 switches .."
        switchClass = configureP4Switch(
                self.tk_args,
                sw_path=self.bmv2_exe,
                json_path=self.switch_json,
                log_console=True,
                pcap_dump=self.pcap_dir)

        print "Configuring Mininet .."
        self.net = Mininet(topo = self.topo,
                      link = TCLink,
                      host = P4Host,
                      switch = switchClass,
                      controller = None)
        print "Configuring Mininet Completed .."


    # Added by RB
    def program_myswitch(self,my_swname):
        """ This method will start up the CLI on the given switch and use the
            contents of the command files as input.

            Assumes:
                - A mininet instance is stored as self.net and self.net.start() has
                  been called.
        """
        cli = 'simple_switch_CLI'
        for sw_name, sw_dict in self.switches.iteritems():
            if (sw_name != my_swname):
                continue
            if 'cli_input' not in sw_dict: continue


            # get the port for this particular switch's thrift server
            sw_obj = self.net.get(sw_name)
            thrift_port = sw_obj.thrift_port

            if sw_obj.switch_pid not in self.switch_pids :
                self.switch_pids[sw_obj.switch_pid] = sw_obj
            # print "Programming Switch ..",sw_name, "Thrift Port : ",thrift_port
   

            tracer_path = "/usr/bin/tracer"

            #if self.operating_mode == "NORMAL" :
            if True :

                cli_input_commands = sw_dict['cli_input']
                self.logger('Configuring switch %s with file %s' % (sw_name, cli_input_commands))
                with open(cli_input_commands, 'r') as fin:
                    cli_outfile = '%s/%s_cli_output.log'%(self.log_dir, sw_name)
                    with open(cli_outfile, 'w') as fout:
                        subprocess.Popen([cli, '--thrift-port', str(thrift_port)],
                                         stdin=fin, stdout=fout)
            else :
                
                sswitch_cli_id = sw_obj.device_id + len(self.switches) + len(self.self.topo.hosts())
                print "Simple Switch CLI for Switch %d is %d" %(sw_obj.device_id,sswitch_cli_id)
                logfile = "/tmp/sswitch_cli_" + str(sswitch_cli_id) + ".txt"
                tracer_args = [tracer_path]
                tracer_args.extend(["-i", str(sswitch_cli_id)])
                tracer_args.extend(["-r", str(self.rel_cpu_speed)])
                tracer_args.extend(["-n", str(self.n_round_insns)])
                
                cli_input_commands = sw_dict['cli_input']
                sswitch_cli_cmd = cli + " --thrift-port " + str(thrift_port) + " < " + cli_input_commands
                tracer_args.extend(['-c', "\"" +  sswitch_cli_cmd + "\""])
                self.logger('Configuring switch %s with file %s' % (sw_name, cli_input_commands))
                with tempfile.NamedTemporaryFile() as f:
                    os.system(' '.join(tracer_args) + ' >' + logfile + ' 2>&1 & echo $! >> ' + f.name)
                    pid = int(f.read())
                    self.sswitch_cli_pids.append(pid)
                
            break

    def program_switches(self):
        """ If any command files were provided for the switches,
            this method will start up the CLI on each switch and use the
            contents of the command files as input.

            Assumes:
                - A mininet instance is stored as self.net and self.net.start() has
                  been called.
        """

        if( get_exp_p4switch_init() == "AtStart") :
            cli = 'simple_switch_CLI'
            for sw_name, sw_dict in self.switches.iteritems():
                if 'cli_input' not in sw_dict: continue
                # get the port for this particular switch's thrift server
                sw_obj = self.net.get(sw_name)
                thrift_port = sw_obj.thrift_port


                if sw_obj.switch_pid not in self.switch_pids :
                    self.switch_pids[sw_obj.switch_pid] = sw_obj

                tracer_path = "/usr/bin/tracer"

                #if self.operating_mode == "NORMAL" :
                if True :

                    cli_input_commands = sw_dict['cli_input']
                    self.logger('Configuring switch %s with file %s' % (sw_name, cli_input_commands))
                    with open(cli_input_commands, 'r') as fin:
                        cli_outfile = '%s/%s_cli_output.log'%(self.log_dir, sw_name)
                        with open(cli_outfile, 'w') as fout:
                            subprocess.Popen([cli, '--thrift-port', str(thrift_port)],
                                             stdin=fin, stdout=fout)
                else :
                    
                    sswitch_cli_id = sw_obj.device_id + len(self.switches) + len(self.topo.hosts())
                    print "Simple Switch CLI for Switch %d is %d" %(sw_obj.device_id,sswitch_cli_id)
                    logfile = "/tmp/sswitch_cli_" + str(sswitch_cli_id) + ".txt"
                    tracer_args = [tracer_path]
                    tracer_args.extend(["-i", str(sswitch_cli_id)])
                    tracer_args.extend(["-r", str(self.rel_cpu_speed)])
                    tracer_args.extend(["-n", str(self.n_round_insns)])
                    
                    cli_input_commands = sw_dict['cli_input']
                    sswitch_cli_cmd = cli + " --thrift-port " + str(thrift_port) + " < " + cli_input_commands
                    tracer_args.extend(['-c', "\"" +  sswitch_cli_cmd + "\""])
                    self.logger('Configuring switch %s with file %s' % (sw_name, cli_input_commands))
                    with tempfile.NamedTemporaryFile() as f:
                        os.system(' '.join(tracer_args) + ' >' + logfile + ' 2>&1 & echo $! >> ' + f.name)
                        pid = int(f.read())
                        self.sswitch_cli_pids.append(pid)
        else :
            print "Skipping Switch Initialization At Startup ..."

    def program_hosts(self):
        """ Adds static ARP entries and default routes to each mininet host.

            Assumes:
                - A mininet instance is stored as self.net and self.net.start() has
                  been called.
        """
        for host_name in self.topo.hosts():
            h = self.net.get(host_name)
            h_iface = h.intfs.values()[0]
            link = h_iface.link

            sw_iface = link.intf1 if link.intf1 != h_iface else link.intf2
            # phony IP to lie to the host about
            host_id = int(host_name[1:]) - 1
            sw_ip = '10.0.%d.1' % host_id
            # sw_ip = '10.0.%d.254' % host_id ## Modified by RB

            # Ensure each host's interface name is unique, or else
            # mininet cannot shutdown gracefully
            h.defaultIntf().rename('%s-eth0' % host_name)
            # static arp entries and default routes
            h.cmd('arp -i %s -s %s %s' % (h_iface.name, sw_ip, sw_iface.mac))
            h.cmd('ethtool --offload %s rx off tx off' % h_iface.name)
            h.cmd('ip route add %s dev %s' % (sw_ip, h_iface.name))
            h.setDefaultRoute("via %s" % sw_ip)

            if self.operating_mode != "NORMAL" :
                
                logfile = "/tmp/h{}.log".format(h.name)
                tracer_path = "/usr/bin/tracer"
                monitor_command = "python " + script_dir + "/new_cmd_monitor.py --cmd_file=/tmp/h" + str(h.name[1:]) + "_cmnds.txt" 
                #monitor_command = "python " + script_dir + "/new_cmd_monitor.py --cmd_file=/tmp/h" + str(host_id) + "_cmnds.txt > " + logfile
                host_id += len(self.switches)
                tracer_args = [tracer_path]
                tracer_args.extend(["-i", str(host_id)])
                tracer_args.extend(["-r", str(self.rel_cpu_speed)])
                tracer_args.extend(["-n", str(self.n_round_insns)])
                tracer_args.extend(["-c", "\"" + monitor_command + "\""])
                tracer_args.append("-s")
                with tempfile.NamedTemporaryFile() as f:
                    tracer_cmd = ' '.join(tracer_args) + ' >' + logfile + ' 2>&1 & echo $! >> ' + f.name
                    print "Host %s Tracer cmd %s " %(h.name,tracer_cmd) 
                    h.cmd(tracer_cmd)
                    #h.cmd(' '.join(tracer_args) + ' & echo $! >> ' + f.name)
                    pid = int(f.read())
                    self.host_pids[pid] = h
                    print "Host %s Startup monitor pid %d. Tracer-id: %d" %(h.name, pid, host_id)
            else :
                logfile = "/tmp/h{}.log".format(h.name)
                monitor_command = "python " + script_dir + "/new_cmd_monitor.py --cmd_file=/tmp/h" + str(h.name[1:]) + "_cmnds.txt"
                with tempfile.NamedTemporaryFile() as f:
                    h.cmd(monitor_command + ' >' + logfile + ' 2>&1 & echo $! >> ' + f.name)
                    pid = int(f.read())
                    print "Host %s Startup monitor pid %d" %(h.name, pid)
                

    def synchronize_and_freeze(self) :

        if self.operating_mode == "INS_VT" :
            for sw_name, sw_dict in self.switches.iteritems():
                sw_obj = self.net.get(sw_name)
                if sw_obj.switch_pid not in self.switch_pids :
                    self.switch_pids[sw_obj.switch_pid] = sw_obj


            print "Synchronize and Freezing"
            sleep(2)

            while synchronizeAndFreeze(len(self.host_pids.keys()) + len(self.switch_pids.keys()) + len(self.sswitch_cli_pids)) <= 0 :
                print "Sync and Freeze Failed. Retrying in 1 sec"
                sleep(1)
            

            print "Synchronize and Freeze succeeded !"
            sleep(1)      

    def set_netdevice_owners(self) :
        if self.operating_mode == "INS_VT" :
            print "Setting Net dev owners for hosts: "
            for host_pid in self.host_pids :
                host_obj = self.host_pids[host_pid]
                for name in host_obj.intfNames():
                    if name != "lo" :
                        print "Host: ", host_pid, " Interface: ", name
                        set_netdevice_owner(host_pid,name)

            sleep(1)

            print "Setting Net dev owners for switches: "
            for sw_pid in self.switch_pids :
                sw_obj = self.switch_pids[sw_pid]
                for name in sw_obj.intfNames():
                    if name != "lo" :
                        print "Switch: ", sw_pid, " Interface: ", name
                        set_netdevice_owner(sw_pid,name)

            sleep(1)

    def progress_by_n_rounds(self, n) :
        if n > 0 and self.operating_mode == "INS_VT" :
            progress_n_rounds(n)
            self.n_rounds_progressed = self.n_rounds_progressed + n
            print "Total number of rounds progressed: %d " %(self.n_rounds_progressed)

    def stop_tk_experiment(self) :
        if self.operating_mode == "INS_VT" :
            print "Stopping Tk Experiment Run ..."
            stopExp()
            sleep(2)
            print "Tk Experiment Stopped ..."

    def fire_link_intf_timers(self) :
        if self.operating_mode == "INS_VT" :
            fire_timers()


    def do_net_cli(self):
        """ Starts up the mininet CLI and prints some helpful output.

            Assumes:
                - A mininet instance is stored as self.net and self.net.start() has
                  been called.
        """
        for s in self.net.switches:
            s.describe()
        for h in self.net.hosts:
            h.describe()
        self.logger("Starting mininet CLI")
        # Generate a message that will be printed by the Mininet CLI to make
        # interacting with the simple switch a little easier.
        print('')
        print('======================================================================')
        print('Welcome to the BMV2 Mininet CLI!')
        print('======================================================================')
        print('Your P4 program is installed into the BMV2 software switch')
        print('and your initial configuration is loaded. You can interact')
        print('with the network using the mininet CLI below.')
        print('')
        if self.switch_json:
            print('To inspect or change the switch configuration, connect to')
            print('its CLI from your host operating system using this command:')
            print('  simple_switch_CLI --thrift-port <switch thrift port>')
            print('')
        print('To view a switch log, run this command from your host OS:')
        print('  tail -f %s/<switchname>.log' %  self.log_dir)
        print('')
        print('To view the switch output pcap, check the pcap files in %s:' % self.pcap_dir)
        print(' for example run:  sudo tcpdump -xxx -r s1-eth1.pcap')
        print('')

        CLI(self.net)


def get_args():
    cwd = os.getcwd()
    default_logs = os.path.join(cwd, 'logs')
    default_pcaps = os.path.join(cwd, 'pcaps')
    parser = argparse.ArgumentParser()
    parser.add_argument('-q', '--quiet', help='Suppress log messages.',
                        action='store_true', required=False, default=False)
    parser.add_argument('-t', '--topo', help='Path to topology json',
                        type=str, required=False, default='./topology.json')
    parser.add_argument('-l', '--log-dir', type=str, required=False, default=default_logs)
    parser.add_argument('-p', '--pcap-dir', type=str, required=False, default=default_pcaps)
    parser.add_argument('-j', '--switch_json', type=str, required=False)
    parser.add_argument('-b', '--behavioral-exe', help='Path to behavioral executable',
                                type=str, required=False, default='simple_switch')
    return parser.parse_args()


if __name__ == '__main__':
    # from mininet.log import setLogLevel
    # setLogLevel("info")

    # args = get_args()
    # exercise = ExerciseRunner(args.topo, args.log_dir, args.pcap_dir,
                              # args.switch_json, args.behavioral_exe, args.quiet)

    # exercise.run_exercise()
    print "Hello World..."

