#!/usr/bin/python
"""For two-host tcp(mptcp) experiments."""

import sys
import os
import getopt
import subprocess

from mininet.net import Mininet
from mininet.link import Link, TCLink
from mininet.util import *
from mininet.node import *
from mininet.topo import Topo
from mininet.cli  import *

import mpsche.dirmanager as dirmanager

class TwoHostExp(Topo):
	"""Two hosts directly connected by n paths:
         /--- s11 --- s12 ---\
    client--- ... --- ... ---server
         \--- sn1 --- sn2 ---/
	"""
	def __init__(self):
		"Create the topo."

		# Initialize topology
		Topo.__init__(self)
		self.path_num = 0
		self.setup = {}
		self.output_dir = ''


	def set_IPs(self, net, ip, host, itfidx='0'):
		h1 = net.get(host)
		itf = h1.intf(host+'-eth'+itfidx)
		h1.setIP(ip, prefixLen = 8, intf = itf)

	'''def block_cross(self, net, prefix1, prefix2, host1):
		h1 = net.get(host1)

		h1.cmd('iptables -A OUTPUT -s '+prefix1+' -d '+prefix2+' -j DROP')
		h1.cmd('iptables -A OUTPUT -s '+prefix2+' -d '+prefix1+' -j DROP')'''

	
	
	
	def __set_setup(self, delays, losses):
		"""Return a dictionary, including net(Mininet), delays(list) and losses(list).""" 
		assert len(delays) == len(losses) == self.path_num, 'The number of delays is different from that of losses.'
		self.setup = dict(zip(('delays', 'losses'), (delays, losses)))


	def limit_link(self, net, path, bw, delay, loss, max_latency = 2000, mtu = 1500):
		"""Configure the link parameters. The delay is defined by RTT."""

		s1 = net.get('s'+ path + '1')
		s2 = net.get('s'+ path + '2')

		itf1 = s1.intf(s1.name+'-eth2')
		itf2 = s2.intf(s2.name+'-eth1')

		max_queue_size = int(float(delay) * bw * 1024 * 1024 / (mtu * 8 * 1000))
		max_queue_size += int(float(max_latency) * bw * 1024 * 1024 / (mtu * 8 * 1000))
		if max_queue_size <= 10:
		    max_queue_size = 10

		itf1.config(bw = bw, delay = str(delay/2)+'ms', loss = loss, max_queue_size = max_queue_size, use_tbf = False)
		os.system("tc qdisc show dev "+s1.name+'-eth2')
		os.system("tc class show dev "+s1.name+'-eth2')

		itf2.config(bw = bw, delay = str(delay/2)+'ms',  loss = loss, max_queue_size = max_queue_size, use_tbf = False)
		os.system("tc qdisc show dev "+s2.name+'-eth1')
		os.system("tc class show dev "+s2.name+'-eth1')
		print '\n'

	def limit_links(self, net, delays, losses):
		self.__set_setup(delays, losses)
		for i in range(0, self.path_num):
			self.limit_link(net, str(i + 1), bw = 10, delay = self.setup['delays'][i], loss = self.setup['losses'][i], max_latency = 2000)

	def one_ping_another(self, h1, h2):
		"""Repeat 4 times to ensure at least one packet is received."""
		for i in range(0, self.path_num):
			for j in range(0, self.path_num):
				print h1.cmd("ping -I "+ h1.intf(h1.name+'-eth'+str(i)).IP() +" -c 2 "+ h2.intf(h2.name+'-eth'+str(j)).IP())

	def ping_all_intfs(self, net):
		"""To eliminate the extra delay introduced by flowtable establishment."""
		h1 = net.get('client')
		h2 = net.get('server')
		
		self.one_ping_another(h1, h2)
		self.one_ping_another(h2, h1)

	def set_output_dir(self, path):
		assert os.path.isdir(path), 'The main output directory does not exist.'
		self.output_dir = path

	def dump_start(self, net):
		cli = net.get('client')
		cmd_str = "tcpdump -i any -n -s 150 -w " + self.output_dir + "/dumpall.dat host "

		for i in range(0, self.path_num):
			cmd_str += cli.intf('client-eth'+str(i)+'').IP()
			if i != self.path_num - 1:
				cmd_str += " or host "
		cmd_str += " &"
		print cmd_str
		print cli.cmd(cmd_str)
		'''print cli.cmd('tcpdump -i any -n -s 150 -w ' + self.output_dir + '/dumpall.dat host '\
		+ cli.intf('client-eth0').IP() + ' or host ' + cli.intf('client-eth1').IP() +  ' &')
		'''
		#for i in range(0, self.path_num):
		#	os.system('tcpdump -i s' + str(i + 1) + '1-eth2 -n -s 150 -w ' + self.output_dir + '/dump' + str(i + 1) + '.dat host ' + cli.intf('client-eth'+str(i)).IP() + ' &')

	def syslog_start(self, net):
		self.log_popen = subprocess.Popen('rm ' + self.output_dir + '/klog; while true; do sudo dmesg -c >> ' + self.output_dir + '/klog;sleep 1; done', shell = True)

	def new_output_file(self):
		os.system('rm ' + self.output_dir + '/client.dat &')
		os.system('rm ' + self.output_dir + '/server.dat &')
		os.system('touch ' + self.output_dir + '/client.dat &')
		os.system('touch ' + self.output_dir + '/server.dat &')

	def run_app(self, net, app_time, data_size):
		cli = net.get('client')
		ser = net.get('server')
		ser.cmd(os.getcwd() + '/app/servernk ' + self.output_dir + '/server.dat '+str(data_size)+' &')
		cli.cmd(os.getcwd() + '/app/clientnk ' + ser.IP() + ' ' + self.output_dir + '/client.dat ' + str(app_time) + ' ' + str(data_size) + ' &')

	def run_app2(self, net, app_time, data_size):
		cli = net.get('client')
		ser = net.get('server')
		ser.cmd(os.getcwd() + '/app/servernk2 ' + self.output_dir + '/server.dat '+str(data_size)+' &')
		cli.cmd(os.getcwd() + '/app/clientnk2 ' + ser.IP() + ' ' + self.output_dir + '/client.dat ' + str(app_time) + ' ' + str(data_size) + ' &')

	def run_iperf(self, net, app_time):
		cli = net.get('client')
		ser = net.get('server')
		ser.cmd('iperf -s -i 5 > ' + self.output_dir + '/server.dat &')
		cli.cmd('iperf -c ' + ser.IP() + ' -t ' + str(app_time) + ' -i 5 > ' + self.output_dir + '/client.dat &')



	def stop_app_dump(self, net, dump, syslog):	
		os.system("killall -9 servernk")
		os.system("killall -9 clientnk")
		os.system("killall -9 servernk2")
		os.system("killall -9 clientnk2")
		os.system("killall iperf")
		
		if dump:
			cli = net.get('client')
			cli.cmd("killall tcpdump")
			os.system("killall tcpdump")
		if syslog:
			self.log_popen.kill()
		

	def record_info(self):
		with open(self.output_dir + '/info', 'w') as f:
			for key in self.setup.keys():
				f.write(key)
				f.write('\n')
				f.write(str(self.setup[key]))
				f.write('\n')
				
	def rm_all_data(self, dump):
		os.system('rm ' + self.output_dir + '/server.dat &')
		os.system('rm ' + self.output_dir + '/client.dat &')
		if dump:
			os.system('rm ' + self.output_dir + '/dumpall.dat &')



class TwoHostBurstCoverAllExp(TwoHostExp):
	""" """
	def __init__(self):
		#RTT
		self.del_min = 50
		self.del_max = 1000
		self.loss_min = 5
		self.loss_max = 40
		self.bt_min = 0
		self.bt_max = 20

	def set_delay_loss_range(self, del_min, del_max, loss_min, loss_max):
		self.del_min = del_min
		self.del_max = del_max
		self.loss_min = loss_min
		self.loss_max = loss_max

	def get_float(self, v, mini, maxi):
	    return round(float(mini) + (maxi - mini) * float(v), 1)

	def get_setup(self, d, l, b):
	    tup = (d, l, b)

	    setup = dict(zip(('d', 'l', 'b'), tup))
	    return setup

	def get_parameter(self):
		sets = open('wsp-' + str(self.path_num))
		delays = []
		losses = []
		bts = []
		for l in sets:
			l = l.rstrip("\n")
			s = l.split(' ')
			
			for i in range(0, self.path_num):
				delays.append(self.get_float(s[i], self.del_min, self.del_max))
				losses.append(self.get_float(s[i + self.path_num], self.loss_min, self.loss_max))
				bts.append(self.get_float(s[i + self.path_num * 2], self.bt_min, self.bt_max))

			yield self.get_setup(delays, losses, bts) 
		sets.close()

	def event_comp(self, a, b):
		if a['t'] < b['t']:
			return -1
		else:
			return 1

	def get_events(self, losses, bts, app_time):
		events = []
		print len(bts)
		for i in range(0, len(bts)):
			events.append(dict(zip(('t', 'pi', 'l'), (bts[i], i, losses[i]))))
			events.append(dict(zip(('t', 'pi', 'l'), (bts[i] + 10, i, 0))))
		events.append(dict(zip(('t', 'pi', 'l'), (app_time, 0, 0))))
		events.sort(self.event_comp)
		print events

		for i in range(len(events) - 1, 0, -1):
			events[i]['t'] = events[i]['t'] - events[i - 1]['t']
		print events
		return events
			

	def run_exp(self, setup, net, sche, base_dir, run_time, seq, first_exp, is_resume):
		exp = net.topo
		dump = True
		syslog = False

		set = {}
		set['d'] = setup['d'][-1*self.path_num:]
		set['l'] = setup['l'][-1*self.path_num:]
		set['b'] = setup['b'][-1*self.path_num:]

		if is_resume:
			start_time = first_exp
		else:
			start_time = 0
		
		for exp_time in range(start_time, run_time):

			work_dir = base_dir + '/' + str(seq) + '/' + str(exp_time)
			dirmanager.dir_ready(work_dir)
			exp.set_output_dir(work_dir)	
			
			if (is_resume):
				exp.rm_all_data(True)
				is_resume = False
			
				
			for time in range(0, 5):
				if dump:
					exp.dump_start(net)
				if syslog:
					exp.syslog_start(net)
				exp.new_output_file()

				app_time = 30
				data_size = 8
				print set['d'],set['l'],set['b']
				events = exp.get_events(set['l'], set['b'], app_time)

				sleep(2)
				
				exp.run_app(net, app_time, data_size)
				
				exp.limit_links(net, set['d'], [0] * self.path_num)
				'''l0 = 0
				l1 = 0
				for i in range(0, len(events)):
					sleep(events[i]['t'])
					if i == len(events) - 1:
						break
					if events[i]['pi'] == 0:
						exp.limit_links(net, set['d'], [events[i]['l'], l1])
						l0 = events[i]['l']
					else:
						exp.limit_links(net, set['d'], [l0, events[i]['l']])
						l1 = events[i]['l']
					print events[i]['t'], l0, l1'''
				ls = [0] * self.path_num
				for i in range(0, len(events)):
					sleep(events[i]['t'])
					if i == len(events) - 1:
						break
					pi = events[i]['pi']
					ls[pi] = events[i]['l']
					exp.limit_links(net, set['d'], ls)

					print events[i]['t'], ls
					
					
				
				exp.stop_app_dump(net, dump, syslog)

				if exp.is_multipath(dump = True):
					with open(base_dir + '/record', 'w') as record:
						record.writelines([str(seq), '\n', str(exp_time), '\n'])
					break
				else:
					exp.rm_all_data(dump = True)

			else:
				with open(base_dir + '/broken', 'a') as broken:
					broken.write(str(seq) + ' ' + str(exp_time)+'\n')

	def run_exps(self, net, sche, run_time):
		dicts = self.get_parameter()

		base_dir = 'output/cover-all/' + sche
		dirmanager.dir_ready(base_dir)
		dirmanager.file_ready(base_dir + '/record')
		dirmanager.file_ready(base_dir + '/broken')	

		seq = 0
		first_exp = 0 #for breakpoint resume 
		is_resume = False #for breakpoint resume 
		with open(base_dir + '/record') as record:
			lines = record.readlines()
			if len(lines) == 2:
				print lines
				seq = int(lines[0])
				first_exp = int(lines[1]) + 1
				if first_exp == run_time:
					first_exp = 0
					seq += 1
				is_resume = True

		counter = 0
		for dic in dicts:
			if counter < seq:
				counter += 1
				continue
			self.run_exp(dic, net, sche, base_dir, run_time, seq, first_exp, is_resume)
			is_resume = False
			first_exp = 0
			seq += 1
			counter = seq

class TwoHostBurstTimeVaryCoverAllExp(TwoHostExp):
	""" """
	def __init__(self):
		#RTT
		self.del_min = 50
		self.del_max = 1000
		self.loss_min = 5
		self.loss_max = 40
		self.bt_min = 0
		self.bt_max = 20
		self.dt_min = 0
		self.dt_max = 10

	def set_delay_loss_range(self, del_min, del_max, loss_min, loss_max):
		self.del_min = del_min
		self.del_max = del_max
		self.loss_min = loss_min
		self.loss_max = loss_max

	def get_float(self, v, mini, maxi):
	    return round(float(mini) + (maxi - mini) * float(v), 1)

	def get_setup(self, d, l, b, dt):
	    tup = (d, l, b, dt)

	    setup = dict(zip(('d', 'l', 'b', 'dt'), tup))
	    return setup

	def get_parameter(self):
		sets = open('wsp-' + str(self.path_num) + '-x')
		delays = []
		losses = []
		bts = []
		dts = []
		for l in sets:
			l = l.rstrip("\n")
			s = l.split(' ')
			print 'wsp value', float(s[0])
			for i in range(0, self.path_num):
				delays.append(self.get_float(s[i], self.del_min, self.del_max))
				losses.append(self.get_float(s[i + self.path_num], self.loss_min, self.loss_max))
				bts.append(self.get_float(s[i + self.path_num * 2], self.bt_min, self.bt_max))
				dts.append(self.get_float(s[i + self.path_num * 3], self.dt_min, self.dt_max))

			yield self.get_setup(delays, losses, bts, dts) 
		sets.close()

	def event_comp(self, a, b):
		if a['t'] < b['t']:
			return -1
		else:
			return 1

	def get_events(self, losses, bts, dts, app_time):
		events = []
		print len(bts)
		for i in range(0, len(bts)):
			events.append(dict(zip(('t', 'pi', 'l'), (bts[i], i, losses[i]))))
			events.append(dict(zip(('t', 'pi', 'l'), (bts[i] + dts[i], i, 0))))
		events.append(dict(zip(('t', 'pi', 'l'), (app_time, 0, 0))))
		events.sort(self.event_comp)
		print events

		for i in range(len(events) - 1, 0, -1):
			events[i]['t'] = events[i]['t'] - events[i - 1]['t']
		print events
		return events
			

	def run_exp(self, setup, net, sche, base_dir, run_time, seq, first_exp, is_resume):
		exp = net.topo
		dump = True
		syslog = False

		set = {}
		set['d'] = setup['d'][-1*self.path_num:]
		set['l'] = setup['l'][-1*self.path_num:]
		set['b'] = setup['b'][-1*self.path_num:]
		set['dt'] = setup['dt'][-1*self.path_num:]

		if is_resume:
			start_time = first_exp
		else:
			start_time = 0
		
		for exp_time in range(start_time, run_time):

			work_dir = base_dir + '/' + str(seq) + '/' + str(exp_time)
			dirmanager.dir_ready(work_dir)
			exp.set_output_dir(work_dir)	
			
			if (is_resume):
				exp.rm_all_data(True)
				is_resume = False
			
				
			for time in range(0, 5):
				if dump:
					exp.dump_start(net)
				if syslog:
					exp.syslog_start(net)
				exp.new_output_file()

				app_time = 30
				data_size = 8
				print set['d'],set['l'],set['b'],set['dt']
				events = exp.get_events(set['l'], set['b'],set['dt'], app_time)

				sleep(2)
				
				exp.run_app(net, app_time, data_size)
				
				exp.limit_links(net, set['d'], [0] * self.path_num)
				'''l0 = 0
				l1 = 0
				for i in range(0, len(events)):
					sleep(events[i]['t'])
					if i == len(events) - 1:
						break
					if events[i]['pi'] == 0:
						exp.limit_links(net, set['d'], [events[i]['l'], l1])
						l0 = events[i]['l']
					else:
						exp.limit_links(net, set['d'], [l0, events[i]['l']])
						l1 = events[i]['l']
					print events[i]['t'], l0, l1'''
				ls = [0] * self.path_num
				for i in range(0, len(events)):
					sleep(events[i]['t'])
					if i == len(events) - 1:
						break
					pi = events[i]['pi']
					ls[pi] = events[i]['l']
					exp.limit_links(net, set['d'], ls)

					print events[i]['t'], ls
					
					
				
				exp.stop_app_dump(net, dump, syslog)

				if exp.is_multipath(dump = True):
					with open(base_dir + '/record', 'w') as record:
						record.writelines([str(seq), '\n', str(exp_time), '\n'])
					break
				else:
					exp.rm_all_data(dump = True)

			else:
				with open(base_dir + '/broken', 'a') as broken:
					broken.write(str(seq) + ' ' + str(exp_time)+'\n')

	def run_exps(self, net, sche, run_time):
		dicts = self.get_parameter()

		base_dir = 'output/cover-all-x/' + sche
		dirmanager.dir_ready(base_dir)
		dirmanager.file_ready(base_dir + '/record')
		dirmanager.file_ready(base_dir + '/broken')	

		seq = 0
		first_exp = 0 #for breakpoint resume 
		is_resume = False #for breakpoint resume 
		with open(base_dir + '/record') as record:
			lines = record.readlines()
			if len(lines) == 2:
				print lines
				seq = int(lines[0])
				first_exp = int(lines[1]) + 1
				if first_exp == run_time:
					first_exp = 0
					seq += 1
				is_resume = True

		counter = 0
		for dic in dicts:
			if counter < seq:
				counter += 1
				continue
			self.run_exp(dic, net, sche, base_dir, run_time, seq, first_exp, is_resume)
			is_resume = False
			first_exp = 0
			seq += 1
			counter = seq
	
		
class TwoHostTwoPathExp(TwoHostExp):
	"""Two hosts directly connected by 2 paths:
         /--- s11 --- s12 ---\
    client                   server
         \--- sn1 --- sn2 ---/
	"""
	def __init__(self):
		"Create the topo."

		# Initialize topology
		TwoHostExp.__init__(self)
		self.path_num = 2

		# Add hosts and switches
		leftHost = self.addHost('client')
		rightHost = self.addHost('server')
		leftSwitch1 = self.addSwitch('s11')
		rightSwitch1 = self.addSwitch('s12')
		leftSwitch2 = self.addSwitch('s21')
		rightSwitch2 = self.addSwitch('s22')

		# Add links
		self.addLink(leftHost, leftSwitch1)
		self.addLink(leftSwitch1, rightSwitch1)
		self.addLink(rightSwitch1, rightHost)

		self.addLink(leftHost, leftSwitch2)
		self.addLink(leftSwitch2, rightSwitch2)
		self.addLink(rightSwitch2, rightHost)

	def set_IPs_policy_routes(self, net):
		# Setup IP configuration
		cli = net.get('client')
		ser = net.get('server')

		self.set_IPs(net, '10.0.0.1', 'client', '0')
		self.set_IPs(net, '10.0.0.2', 'server', '0')
		self.set_IPs(net, '10.1.0.1', 'client', '1')
		self.set_IPs(net, '10.1.0.2', 'server', '1')

		ser.cmd('ip rule add from 10.0.0.2 table 1')
		ser.cmd('ip rule add from 10.1.0.2 table 2')

		ser.cmd('ip route add 10.0.0.0/24 dev server-eth0 scope link table 1')
		ser.cmd('ip route add default via 10.0.0.2 dev server-eth0 table 1')
		ser.cmd('ip route add 10.0.0.0/24 dev server-eth1 scope link table 2')
		ser.cmd('ip route add default via 10.1.0.2 dev server-eth1 table 2')

		ser.cmd('ip route add scope global nexthop via 10.0.0.2 dev \
		    server-eth0')

		print ser.cmd('ifconfig')


		cli.cmd('ip rule add from 10.0.0.1 table 1')
		cli.cmd('ip rule add from 10.1.0.1 table 2')

		cli.cmd('ip route add 10.0.0.0/24 dev client-eth0 scope link table 1')
		cli.cmd('ip route add default via 10.0.0.1 dev client-eth0 table 1')
		cli.cmd('ip route add 10.0.0.0/24 dev client-eth1 scope link table 2')
		cli.cmd('ip route add default via 10.1.0.1 dev client-eth1 table 2')

		cli.cmd('ip route add default scope global nexthop via 10.0.0.1 dev \
		    client-eth0')

		print cli.cmd('ifconfig')

	def judge_exp_effective(self, dump):
		return os.path.getsize(self.output_dir + '/client.dat') > 50 and \
			os.path.getsize(self.output_dir + '/server.dat') > 50 and \
			os.path.getsize(self.output_dir + '/dumpall.dat') > 200 if dump else \
			os.path.getsize(self.output_dir + '/client.dat') > 50 and \
			os.path.getsize(self.output_dir + '/server.dat') > 50
				
	def is_multipath(self, dump):
		if self.judge_exp_effective(dump):
			self.record_info()
			return True
		else:
			return False

class TwoHostTwoPathBurstCoverAllExp(TwoHostTwoPathExp, TwoHostBurstCoverAllExp):
	def __init__(self):
		TwoHostTwoPathExp.__init__(self)
		TwoHostBurstCoverAllExp.__init__(self)

class TwoHostTwoPathBurstTimeVaryCoverAllExp(TwoHostTwoPathExp, TwoHostBurstTimeVaryCoverAllExp):
	def __init__(self):
		TwoHostTwoPathExp.__init__(self)
		TwoHostBurstTimeVaryCoverAllExp.__init__(self)
		

class TwoHostFourPathExp(TwoHostExp):
	"""Two hosts directly connected by 4 paths:
         /--- s11 --- s12 ---\
    client                   server
         \--- sn1 --- sn2 ---/
	"""
	def __init__(self):
		"Create the topo."

		# Initialize topology
		TwoHostExp.__init__(self)
		self.path_num = 4

		# Add hosts and switches
		leftHost = self.addHost('client')
		rightHost = self.addHost('server')
		leftSwitch1 = self.addSwitch('s11')
		rightSwitch1 = self.addSwitch('s12')
		leftSwitch2 = self.addSwitch('s21')
		rightSwitch2 = self.addSwitch('s22')
		leftSwitch3 = self.addSwitch('s31')
		rightSwitch3 = self.addSwitch('s32')
		leftSwitch4 = self.addSwitch('s41')
		rightSwitch4 = self.addSwitch('s42')

		# Add links
		self.addLink(leftHost, leftSwitch1)
		self.addLink(leftSwitch1, rightSwitch1)
		self.addLink(rightSwitch1, rightHost)

		self.addLink(leftHost, leftSwitch2)
		self.addLink(leftSwitch2, rightSwitch2)
		self.addLink(rightSwitch2, rightHost)
		
		self.addLink(leftHost, leftSwitch3)
		self.addLink(leftSwitch3, rightSwitch3)
		self.addLink(rightSwitch3, rightHost)
		
		self.addLink(leftHost, leftSwitch4)
		self.addLink(leftSwitch4, rightSwitch4)
		self.addLink(rightSwitch4, rightHost)
		
	def set_IPs_policy_routes(self, net):
		# Setup IP configuration
		cli = net.get('client')
		ser = net.get('server')

		self.set_IPs(net, '10.0.0.1', 'client', '0')
		self.set_IPs(net, '10.0.0.2', 'server', '0')
		self.set_IPs(net, '10.1.0.1', 'client', '1')
		self.set_IPs(net, '10.1.0.2', 'server', '1')
		self.set_IPs(net, '10.2.0.1', 'client', '2')
		self.set_IPs(net, '10.2.0.2', 'server', '2')
		self.set_IPs(net, '10.3.0.1', 'client', '3')
		self.set_IPs(net, '10.3.0.2', 'server', '3')

		ser.cmd('ip rule add from 10.0.0.2 table 1')
		ser.cmd('ip rule add from 10.1.0.2 table 2')
		ser.cmd('ip rule add from 10.2.0.2 table 3')
		ser.cmd('ip rule add from 10.3.0.2 table 4')
		

		ser.cmd('ip route add 10.0.0.0/24 dev server-eth0 scope link table 1')
		ser.cmd('ip route add default via 10.0.0.2 dev server-eth0 table 1')
		ser.cmd('ip route add 10.0.0.0/24 dev server-eth1 scope link table 2')
		ser.cmd('ip route add default via 10.1.0.2 dev server-eth1 table 2')
		ser.cmd('ip route add 10.0.0.0/24 dev server-eth2 scope link table 3')
		ser.cmd('ip route add default via 10.2.0.2 dev server-eth2 table 3')
		ser.cmd('ip route add 10.0.0.0/24 dev server-eth3 scope link table 4')
		ser.cmd('ip route add default via 10.3.0.2 dev server-eth3 table 4')

		ser.cmd('ip route add scope global nexthop via 10.0.0.2 dev \
		    server-eth0')

		print ser.cmd('ifconfig')


		cli.cmd('ip rule add from 10.0.0.1 table 1')
		cli.cmd('ip rule add from 10.1.0.1 table 2')
		cli.cmd('ip rule add from 10.2.0.1 table 3')
		cli.cmd('ip rule add from 10.3.0.1 table 4')

		cli.cmd('ip route add 10.0.0.0/24 dev client-eth0 scope link table 1')
		cli.cmd('ip route add default via 10.0.0.1 dev client-eth0 table 1')
		cli.cmd('ip route add 10.0.0.0/24 dev client-eth1 scope link table 2')
		cli.cmd('ip route add default via 10.1.0.1 dev client-eth1 table 2')
		cli.cmd('ip route add 10.0.0.0/24 dev client-eth2 scope link table 3')
		cli.cmd('ip route add default via 10.2.0.1 dev client-eth2 table 3')
		cli.cmd('ip route add 10.0.0.0/24 dev client-eth3 scope link table 4')
		cli.cmd('ip route add default via 10.3.0.1 dev client-eth3 table 4')

		cli.cmd('ip route add default scope global nexthop via 10.0.0.1 dev \
		    client-eth0')

		print cli.cmd('ifconfig')

	def judge_exp_effective(self, dump):
		return os.path.getsize(self.output_dir + '/client.dat') > 50 and \
			os.path.getsize(self.output_dir + '/server.dat') > 50 and \
			os.path.getsize(self.output_dir + '/dumpall.dat') > 200 if dump else \
			os.path.getsize(self.output_dir + '/client.dat') > 50 and \
			os.path.getsize(self.output_dir + '/server.dat') > 50
				
	def is_multipath(self, dump):
		if self.judge_exp_effective(dump):
			self.record_info()
			return True
		else:
			return False


class TwoHostFourPathBurstCoverAllExp(TwoHostFourPathExp, TwoHostBurstCoverAllExp):
	def __init__(self):
		TwoHostFourPathExp.__init__(self)
		TwoHostBurstCoverAllExp.__init__(self)

class TwoHostFourPathBurstTimeVaryCoverAllExp(TwoHostFourPathExp, TwoHostBurstTimeVaryCoverAllExp):
	def __init__(self):
		TwoHostFourPathExp.__init__(self)
		TwoHostBurstTimeVaryCoverAllExp.__init__(self)




class TwoHostThreePathExp(TwoHostExp):
	"""Two hosts directly connected by 3 paths:
         /--- s11 --- s12 ---\
    client                   server
         \--- sn1 --- sn2 ---/
	"""

	def __init__(self):
		"Create the topo."

		# Initialize topology
		TwoHostExp.__init__(self)
		self.path_num = 3

		# Add hosts and switches
		leftHost = self.addHost('client')
		rightHost = self.addHost('server')
		leftSwitch1 = self.addSwitch('s11')
		rightSwitch1 = self.addSwitch('s12')
		leftSwitch2 = self.addSwitch('s21')
		rightSwitch2 = self.addSwitch('s22')
		leftSwitch3 = self.addSwitch('s31')
		rightSwitch3 = self.addSwitch('s32')

		# Add links
		self.addLink(leftHost, leftSwitch1)
		self.addLink(leftSwitch1, rightSwitch1)
		self.addLink(rightSwitch1, rightHost)

		self.addLink(leftHost, leftSwitch2)
		self.addLink(leftSwitch2, rightSwitch2)
		self.addLink(rightSwitch2, rightHost)
		
		self.addLink(leftHost, leftSwitch3)
		self.addLink(leftSwitch3, rightSwitch3)
		self.addLink(rightSwitch3, rightHost)
		
	def set_IPs_policy_routes(self, net):
		# Setup IP configuration
		cli = net.get('client')
		ser = net.get('server')

		self.set_IPs(net, '10.0.0.1', 'client', '0')
		self.set_IPs(net, '10.0.0.2', 'server', '0')
		self.set_IPs(net, '10.1.0.1', 'client', '1')
		self.set_IPs(net, '10.1.0.2', 'server', '1')
		self.set_IPs(net, '10.2.0.1', 'client', '2')
		self.set_IPs(net, '10.2.0.2', 'server', '2')

		ser.cmd('ip rule add from 10.0.0.2 table 1')
		ser.cmd('ip rule add from 10.1.0.2 table 2')
		ser.cmd('ip rule add from 10.2.0.2 table 3')
		

		ser.cmd('ip route add 10.0.0.0/24 dev server-eth0 scope link table 1')
		ser.cmd('ip route add default via 10.0.0.2 dev server-eth0 table 1')
		ser.cmd('ip route add 10.0.0.0/24 dev server-eth1 scope link table 2')
		ser.cmd('ip route add default via 10.1.0.2 dev server-eth1 table 2')
		ser.cmd('ip route add 10.0.0.0/24 dev server-eth2 scope link table 3')
		ser.cmd('ip route add default via 10.2.0.2 dev server-eth2 table 3')

		ser.cmd('ip route add scope global nexthop via 10.0.0.2 dev \
		    server-eth0')

		print ser.cmd('ifconfig')


		cli.cmd('ip rule add from 10.0.0.1 table 1')
		cli.cmd('ip rule add from 10.1.0.1 table 2')
		cli.cmd('ip rule add from 10.2.0.1 table 3')

		cli.cmd('ip route add 10.0.0.0/24 dev client-eth0 scope link table 1')
		cli.cmd('ip route add default via 10.0.0.1 dev client-eth0 table 1')
		cli.cmd('ip route add 10.0.0.0/24 dev client-eth1 scope link table 2')
		cli.cmd('ip route add default via 10.1.0.1 dev client-eth1 table 2')
		cli.cmd('ip route add 10.0.0.0/24 dev client-eth2 scope link table 3')
		cli.cmd('ip route add default via 10.2.0.1 dev client-eth2 table 3')

		cli.cmd('ip route add default scope global nexthop via 10.0.0.1 dev \
		    client-eth0')

		print cli.cmd('ifconfig')

	def judge_exp_effective(self, dump):
		return os.path.getsize(self.output_dir + '/client.dat') > 50 and \
			os.path.getsize(self.output_dir + '/server.dat') > 50 and \
			os.path.getsize(self.output_dir + '/dumpall.dat') > 200 if dump else \
			os.path.getsize(self.output_dir + '/client.dat') > 50 and \
			os.path.getsize(self.output_dir + '/server.dat') > 50
				
	def is_multipath(self, dump):
		if self.judge_exp_effective(dump):
			self.record_info()
			return True
		else:
			return False

			
class TwoHostThreePathBurstCoverAllExp(TwoHostThreePathExp, TwoHostBurstCoverAllExp):
	def __init__(self):
		TwoHostThreePathExp.__init__(self)
		TwoHostBurstCoverAllExp.__init__(self)

class TwoHostThreePathBurstTimeVaryCoverAllExp(TwoHostThreePathExp, TwoHostBurstTimeVaryCoverAllExp):
	def __init__(self):
		TwoHostThreePathExp.__init__(self)
		TwoHostBurstTimeVaryCoverAllExp.__init__(self)

