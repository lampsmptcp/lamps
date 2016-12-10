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


from mpsche.twohostexp import TwoHostTwoPathBurstTimeVaryCoverAllExp
import mpsche.dirmanager as dirmanager

def config_system_parameters(sche):
	os.system('sysctl -w net.ipv4.tcp_no_metrics_save=1')
	os.system('sysctl -w net.mptcp.mptcp_enabled=1')
	os.system('sysctl -w net.ipv4.tcp_congestion_control=lia')
	os.system('sysctl -w net.mptcp.mptcp_scheduler=' + sche)
	os.system('sysctl -w net.mptcp.mptcp_debug=0')
	os.system('sysctl -w net.mptcp.mptcp_path_manager=fullmesh')
	os.system('echo 0 > /sys/module/mptcp_lamp/parameters/alpha')



def usage():
	print "./two-ca.py [-s scheduler][-h][-v data size][-t each run time]"
	print "-s specify the scheduler"
	print "-v specify the data size, unit kB"
	print "avaliable scheduler: default, roundrobin, lamp, llr"
	print "-h help"

if __name__ == '__main__':
	sche = 'lamp'
	data_size = 8
	a_scheduler = ['default', 'roundrobin', 'lamp', 'redundant']
	run_time = 1
	
	opts, agrs = getopt.getopt(sys.argv[1:], "hs:t:")
	for o, v in opts:
		if o == "-s":
			sche = v
			if sche not in a_scheduler:
				usage()
				sys.exit()
		elif o == "-h":
			usage()
			sys.exit()
		elif o == "-t":
			run_time = int(v)

	exp = TwoHostTwoPathBurstTimeVaryCoverAllExp()
	net = Mininet(topo = exp, link = TCLink)
	net.start()

	dumpNetConnections(net)

	exp.set_IPs_policy_routes(net)
	exp.ping_all_intfs(net)	
	
	config_system_parameters(sche)


	exp.set_delay_loss_range(del_min = 50, del_max = 1000, loss_min = 0, loss_max = 30)
	exp.run_exps(net, sche, run_time)
	net.stop()


