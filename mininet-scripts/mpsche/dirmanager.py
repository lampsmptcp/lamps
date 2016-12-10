#!/usr/bin/python

import sys
import os

def dir_ready(path):
	if not os.path.exists(path):
		os.makedirs(path)

def file_ready(filename):
	if not os.path.isfile(filename):
		os.mknod(filename)
		

def dir_is_empty(path):
	return not len(os.listdir(path))
	