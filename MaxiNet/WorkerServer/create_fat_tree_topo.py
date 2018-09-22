import json
import argparse
import logging
import os
import sys
import pprint
import random

random.seed(1234)

parser = argparse.ArgumentParser()


parser.add_argument('--fanout', dest="fanout", default=2, help = "Fanout")
parser.add_argument('--nhosts_per_switch', dest="nhosts_per_switch", default=2, help = "Num hosts per switch")
parser.add_argument('--link_delay', dest="link_delay",default=1, help="Link delay")
parser.add_argument('--grpc_path', dest="grpc_path", default="/home/moses/grpc/examples/cpp/helloworld")

args = parser.parse_args()

fanout = int(args.fanout)
nhosts_per_switch = int(args.nhosts_per_switch)
link_delay = int(args.link_delay)

n_hosts = fanout*fanout*nhosts_per_switch
n_switches = fanout + (fanout*fanout) + 1

json_data = {}

client_hosts = []
server_hosts = []
all_hosts = []
for i in xrange(1, n_hosts + 1):
	if i % 2 == 1 :
		client_hosts.append(i)
	else:
		server_hosts.append(i)
	all_hosts.append("h" + str(i))

all_switches = {}
for i in xrange(1, n_switches + 1):
	all_switches["s" + str(i)] = {"cli_input" : "s" + str(i) + "-cmnds.txt"}
all_links = []
switches = range(1, n_switches + 1)
for i in xrange(0, fanout + 1):
	for j in xrange(fanout*i+1, fanout*i+1+fanout):
		all_links.append(["s" + str(i+1), "s" + str(j+1), link_delay])
for i in xrange(fanout + 1, n_switches):
	idx = i - (fanout + 1)
	for j in xrange(idx*nhosts_per_switch, (idx+1)*nhosts_per_switch):
		all_links.append(["s" + str(i+1), all_hosts[j], link_delay])

all_host_cmnds = []

for i in xrange(0, len(client_hosts)):
	cli_host_name = "h" + str(client_hosts[i])
	#server_ip = "10.0." + str(server_hosts[random.randint(0,len(server_hosts) - 1)]) + ".10"
	#server_ip = "10.0." + str(server_hosts[(i + fanout) % len(server_hosts)]) + ".10"
	server_ip = "10.0." + str(server_hosts[i % len(server_hosts)]) + ".10"
	cmd = args.grpc_path + "/greeter_client -i " + server_ip + " -n 500"
	all_host_cmnds.append([cli_host_name, cmd])
for i in xrange(0, len(server_hosts)):
	server_host_name = "h" + str(server_hosts[i])
	server_ip = "10.0." + str(server_hosts[i]) + ".10"
	cmd = args.grpc_path + "/greeter_server -i " + server_ip
	all_host_cmnds.append([server_host_name, cmd])

json_data["hosts"] = all_hosts
json_data["switches"] = all_switches
json_data["links"] = all_links
json_data["host_cmnds"] = all_host_cmnds
json_data["allowed_paths"] = {}

with open('fat_tree.json', 'w') as f:
	json.dump(json_data, f, indent=4)


pprint.pprint(json_data)
