#!/usr/bin/python
"""Custom topology example
Two directly connected switches plus a host for each switch:
         /--- s11 --- s12 ---\
    client                   server
         \--- s21 --- s22 ---/
"""

import sys
import os
import getopt

from mininet.net import Mininet
from mininet.link import Link, TCLink
from mininet.util import *
from mininet.node import *
from mininet.topo import Topo
from mininet.cli  import *


from mpsche.twohostexp import TwoHostTwoPathExp
import mpsche.dirmanager as dirmanager

lr = [0, 20, 0, 30, 0]
rtt_1 = 200
rtt_2 = 150
loss_1 = 0
loss_2 = 0

def usage():
	print "./cr.py [-s scheduler][-h][-a loss_1][-b loss_2][-c rtt_1][-d rtt_2]"
	print "-s specify the scheduler"
	print "avaliable scheduler: default, roundrobin, epq, lamp, llr"
	print "-h help"


def run_exp(net, sche, run_time, base_dir, traffic_type):
	dirmanager.dir_ready(base_dir)
	dirmanager.file_ready(base_dir + '/record')
	dump = True
	syslog = False
	
	
	exp = net.topo
	
	for exp_time in range(0, run_time):
		for time in range(0, 10):
			work_dir = base_dir + '/' + str(exp_time)
			dirmanager.dir_ready(work_dir)
			exp.set_output_dir(work_dir)
			
			if dump:
				exp.dump_start(net)
			if syslog:
				exp.syslog_start(net)
			exp.new_output_file()

			sleep(2)

			app_time = 150
			wait_time = 40
			data_size = 8

			if traffic_type == 'CBR':
				exp.run_app(net, app_time, data_size)
			else:
				exp.run_iperf(net, app_time)

			for l in lr:
				exp.limit_links(net, [rtt_1, rtt_2], [loss_1, l])
				sleep(10)

			exp.stop_app_dump(net, dump, syslog)

			if exp.is_multipath(dump):
				break
			else:
				exp.rm_all_data(dump)

		else:
			record = open(base_dir + '/record', 'a')
			record.write(str(exp_time)+'\n')
			record.close()

def config_system_parameters(sche):
	os.system('sysctl -w net.ipv4.tcp_no_metrics_save=1')
	os.system('sysctl -w net.mptcp.mptcp_enabled=1')
	os.system('sysctl -w net.ipv4.tcp_congestion_control=lia')
	os.system('sysctl -w net.mptcp.mptcp_scheduler=' + sche)
	os.system('sysctl -w net.mptcp.mptcp_debug=0')
	os.system('sysctl -w net.mptcp.mptcp_path_manager=fullmesh')
	os.system('echo 0 > /sys/module/mptcp_lamp/parameters/alpha')


if __name__ == '__main__':
	#RTT


	sche = 'lamp'
	run_time = 20
	traffic_type = 'CBR'

	a_scheduler = ['default', 'roundrobin', 'lamp', 'llr', 'redundant']
	opts, agrs = getopt.getopt(sys.argv[1:], "hs:a:b:c:d:")
	for o, v in opts:
		if o == "-s":
			sche = v
			if sche not in a_scheduler:
				usage()
				sys.exit()
		elif o == "-a":
			loss_1 = int(v)
		elif o == "-b":
			loss_2 = int(v)
		elif o == "-c":
			rtt_1 = int(v)
		elif o == "-d":
			rtt_2 = int(v)
		elif o == "-h":
			usage()
			sys.exit()

	exp = TwoHostTwoPathExp()
	net = Mininet(topo = exp, link = TCLink)
	net.start()

	dumpNetConnections(net)

	exp.set_IPs_policy_routes(net)
	exp.ping_all_intfs(net)	
	
	config_system_parameters(sche)

	base_dir = 'output/config-repeat/'+str(rtt_1)+str(rtt_2)+str(loss_1)+str(loss_2)+'/'+sche
	run_exp(net, sche, run_time, base_dir, traffic_type)
	net.stop()

	os.system('sysctl -w net.mptcp.mptcp_scheduler=default')
	os.system('sysctl -w net.mptcp.mptcp_enabled=0')













