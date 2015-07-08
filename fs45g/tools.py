import hashlib
import base64
import time


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


