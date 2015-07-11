import hashlib
import base64
import tempfile
import shutil
import os
from tools import flag2mode

class fs45gCache:
	def __init__(self, namespace, dir="/tmp", size=-1, preserve=False):
		self.dir = os.path.abspath(dir) + "/" + namespace
		self.size = size
		self.stored_size = 0
		self.lru_list = []
		self.preserve = preserve

		if (os.path.exists(self.dir) == False):
			os.mkdir(self.dir)

		# Now check the files for SHA256 correctness

	def shutdown(self):
		if self.preserve == False:
			for root, dirs, files in os.walk(self.dir, topdown=False):
				for name in files:
					os.remove(os.path.join(root, name))
				for name in dirs:
					os.rmdir(os.path.join(root, name))
			os.rmdir(self.dir)
	
	def hash(self,node):
		keyname = node.getKeyName()
		filename = self.dir + "/" + keyname
		sum = hashlib.sha256()
		fd = open(filename)
		end = False
		while end == False:
			buf = fd.read(4096)
			if (len(buf) == 0):
				end = True
			else:
				sum.update(buf)
		sha_sum = base64.urlsafe_b64encode(sum.digest())
		fd.close()
		return sha_sum

	# Verify that the node is in cache and up to date
	def validate(self, node):
		if self.isInCache(node) == False:
			return True 
		if self.hash(node) != node.sha_sum:
			return False
		return True
	
	# Make sure that all files in cache are up to date
	def syncTree(self, node):
		# Validate the children
		for i in node.children:
			self.syncTree(i)
		# Validate this tree
	 	if self.validate(node) == False:
			# Remove the file from cache
			self.removeFromCache(node)

	def addToCache(self, node, flags=(os.O_RDWR|os.O_CREAT)):
		keyname = node.getKeyName()
		fd = os.fdopen(os.open(self.dir + "/" + keyname, flags),flag2mode(flags))
		fd.close()
		self.lru_list.append(keyname)
		return 0 
	def fn(self,node):
		keyname = node.getKeyName()
		return self.dir + "/" + keyname

	def removeFromCache(self, node):
		keyname = node.getKeyName()
		filename = self.dir + "/" + keyname
		if os.path.exists(filename) == True:
			os.unlink(filename)
			self.lru_list.remove(keyname)

	def isInCache(self, node):
		if node.pending_delete == True:
			return False
		keyname = node.getKeyName()
		filename = self.dir + "/" + keyname
		return os.path.exists(filename)

	def openInCache(self, node, flags=(os.O_RDWR|os.O_CREAT)):
		keyname = node.getKeyName()
		filename = self.dir + "/" + keyname
		self.updateLRU(keyname)
		fd = os.open(filename, flags)
		return fd

	def statInCache(self, node):
		filename = self.dir + "/" + node.getKeyName() 
		return os.stat(filename)

	def updateLRU(self, keyname):
		try:
			self.lru_list.remove(keyname)
		except ValueError:
			pass
		self.lru_list.append(keyname)

	def getLRUName(self):
		return self.lru_list[0]

	def shadowInCache(self, node):
		#Make a shadow copy that dissappears on close
		#Must be called with the nodes iolock held
		keyname = node.getKeyName()
		filename = self.dir + "/" + keyname
		origfile = os.fdopen(os.open(filename,os.O_RDWR),flag2mode(os.O_RDWR))
		shadowfile = tempfile.TemporaryFile("w+b")
		shutil.copyfileobj(origfile,shadowfile)
		shadowfile.seek(0)
		origfile.seek(0)
		sum = hashlib.sha256()
		end = False
		while end == False:
			buf = origfile.read(4096)
			if (len(buf) == 0):
				end = True
			else:
				sum.update(buf)
		origfile.close()

		node.sha_sum = base64.urlsafe_b64encode(sum.digest())

		return shadowfile
		

