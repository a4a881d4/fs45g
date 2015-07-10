import os
import stat
from keylayoutelement import KeyLayoutElement
from fs45gstat import fs45gStat,fs45gROStat
import tools

class fs45gFile(object):

	myFS = None

	def __init__(self, path, flags, *mode):
		self.file = None
		self.direct_io = True 
		self.keep_cache = "no" 
		self.node = None
		node = self.myFS.FSData.findNode(path)
		nodetok = path.split('/')
		dir=""
		filename = nodetok[len(nodetok)-1]
		nodetok.remove(filename)
		for i in nodetok:
			if i != '':
				dir = dir + "/" + i
		if dir == "":
			dir = "/"

		dirnode = self.myFS.FSData.findNode(dir)
		if dirnode == None:
			return None 

		if node == None:
			#Check to see if we are supposed to be creating a file
			if (flags & os.O_CREAT) == os.O_CREAT:
				node = KeyLayoutElement(filename)
				node.runtimeSetup()
				node.stat.st_mode = stat.S_IFREG | 0755
				node.sha_sum = tools.hashpath('')
				dirnode.addChild(node)
			else:
				return None 
		else:
			if (flags & os.O_EXCL) == os.O_EXCL:
				return None

		self.file = node.open(self.myFS, os.O_RDWR)
		self.fd = self.file.fileno()
		self.node = node
		return None 


	def read(self, length, offset):
		self.file.seek(offset)
		buf = self.file.read(length)
		return buf 

	def write(self, buf, offset):
		if ((offset + len(buf)) > (5 * 1024 * 1024 * 1024)):
			return -errno.EFBIG

		self.file.seek(offset)
		self.file.write(buf)
		self.file.flush()
		size = self.node.stat.st_size
		self.node.stat.st_size += (len(buf) - (size - offset))
		self.node.setDirty(True)
		return len(buf)

	def release(self, flags):
		self.file.close()
		self.node.close(self.myFS)

	def flush(self):
		self.file.flush()
		return

	def fsync(self, isfsyncfile):
		# Not much to really do here
		os.fsync(self.fd)
		return

	def fgetattr(self):
		uid = os.getuid()
		gid = os.getgid()
		if (self.node.stat.st_uid != -1):
			uid = self.node.stat.st_uid
		if (self.node.stat.st_gid != -1):
			gid = self.node.stat.st_gid
		rostat = fs45gROStat(self.node.stat, uid, gid)
		return rostat

	def ftruncate(self, len):
		self.file.truncate(len)
		self.node.stat.st_size = len
		return

