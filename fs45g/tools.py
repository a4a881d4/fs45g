import hashlib
import base64
import time
import os

def fmode( strmode ):
	mode = 0
	if len(strmode) != 3:
		raise "Error format of file mode"
		return 0	
	for i in range(3):
		mode *= 8
		mode += int(strmode[i])
	return mode

def hashpath( path ):
	sh = hashlib.sha256()
	sh.update(path)
	dir_hash = base64.urlsafe_b64encode(sh.digest())
	return dir_hash

def flag2mode(flags):
	md = {os.O_RDONLY: 'r', os.O_WRONLY: 'w', os.O_RDWR: 'w+'}
	m = md[flags & (os.O_RDONLY | os.O_WRONLY | os.O_RDWR)]

	if flags | os.O_APPEND:
		m = m.replace('w', 'a', 1)

	return m

def makefilename(hashkey,dir):
	path = dir + '/' + hashkey[:2]
	if not os.path.isdir(path):
		os.mkdir(path)
	filename = path + '/' + hashkey
	return filename
