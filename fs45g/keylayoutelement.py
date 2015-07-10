import fs45gstat
import stat
import shutil
import time
import thread
import tools
import os

class KeyLayoutElement:
	def __init__(self,name):
		self.name = name
		self.stat = fs45gstat.fs45gStat()
		# by default make a directory that is mode 755
		self.stat.st_mode = stat.S_IFDIR | 0755
		self.stat.st_nlink = 1 
		
		# UID/GID should probably be set as the owner of the mount
		self.stat.st_uid = -1 
		self.stat.st_gid = -1 
		# By default this shoul be zero
		self.stat.st_size = 0 
		self.stat.st_blksize = 0
		self.stat.st_blocks =0 
		# We can worry about these later

		self.stat.st_atime = 0
		self.stat.st_mtime = 0
		self.stat.st_ctime = 0

		self.dirty = False

		self.children = [] 
		self.parent = None
		self.iolock = None
		self.openref = 0
		self.sha1_sum = '' 
		self.target_path = None 
		self.pending_delete = False
		self.xattrs = {} 

	def runtimeSetup(self):
		for i in self.children:
			i.runtimeSetup()
		self.iolock = thread.allocate_lock()

	def runtimeShutdown(self):
		for i in self.children:
			i.runtimeShutdown()
		self.iolock = None

	# Make a clone of this node for the purpose of saving as a pickle
	def cloneSubtree(self, parent=None):
		clone = KeyLayoutElement(self.name)

		clone.stat.st_mode = self.stat.st_mode 
		clone.stat.st_nlink = self.stat.st_nlink 
		
		# UID/GID should probably be set as the owner of the mount
		clone.stat.st_uid = self.stat.st_uid 
		clone.stat.st_gid = self.stat.st_gid 
		# By default this shoul be zero
		clone.stat.st_size = self.stat.st_size 
		clone.stat.st_blksize = self.stat.st_blksize
		clone.stat.st_blocks = self.stat.st_blocks
		# We can worry about these later

		clone.stat.st_atime = self.stat.st_atime 
		clone.stat.st_mtime = self.stat.st_mtime
		clone.stat.st_ctime = self.stat.st_ctime 

		# Need to repoint the parent to the passed in parent
		clone.parent = parent 

		clone.sha1_sum = self.sha1_sum

		for i in self.children:
			child = i.cloneSubtree(clone)
			clone.children.append(child)

		return clone
		
	
	def setDirty(self, isdirty):
		self.iolock.acquire()
		self.dirty = isdirty
		self.iolock.release()

	def addChild(self, child):
		self.iolock.acquire()
		self.children.append(child)
		child.parent = self
		self.iolock.release()

	def removeNode(self, filesystem, recurse=True):
		if self.parent != None:
			self.parent.removeChild(self,recurse)

	def removeChild(self, child, filesystem, recurse=True):
		self.iolock.acquire()
		self.children.remove(child)
		child.parent = None
		self.iolock.release()
		if (recurse == True):
			for i in child.children:
				child.removeChild(i, filesystem, recurse)

	def writeTo(self, filesystem):
		if filesystem.writeback_time != '-1':
			time.sleep(filesystem.writeback_time)
		
		self.iolock.acquire()
		if self.pending_delete == True:
			self.dirty = False
			self.iolock.release()
			return
		if self.openref > 0:
			self.iolock.release()
			return
		if self.stat.st_size == 0:
			self.iolock.release()
			return

		if filesystem.cache.validate(self):
			fn = tools.makefilename( self.sha_sum, filesystem.persistence )		
			if not os.path.isfile(fn):
				shutil.copy(filesystem.cache.fn(self),fn)			
			self.node.dirty = False
			self.node.iolock.release()
		return
		
	def readFrom(self, filesystem):
		fn = tools.makefilename( self.sha_sum, filesystem.persistence )
		if os.path.isfile(fn):
			self.iolock.acquire()
			shutil.copy(fn,filesystem.cache.fn(self))
			self.iolock.release()
		else:
			syslog.syslog(syslog.LOG_WARNING, "sha_sum = "+self.sha_sum+"not in persistence")

	def writebackAll(self, filesystem):
		for i in self.children:
			i.writebackAll(filesystem)
		if self.dirty == True:
			self.writeTo(filesystem)

	def isOnPersistence(self, filesystem):
		fn = tools.makefilename( self.sha_sum, filesystem.persistence )
		return os.path.isfile(fn)
		
	def open(self, filesystem, flags):
		if filesystem.cache.isInCache(self) == False:
			if self.isOnPersistence(filesystem) == False:
				print self.getKeyName(), " Is Not on persistence"
				filesystem.cache.addToCache(self)
			else:
				self.readFrom(filesystem)
				
		#File in cache, open it up
		self.iolock.acquire()
		self.openref = self.openref+1
		self.iolock.release()
		return os.fdopen(filesystem.cache.openInCache(self,flags),tools.flag2mode(flags))

	def close(self, filesystem):
		self.iolock.acquire()
		if self.openref == 0:
			print "WARNING: UNBALANCE REF COUNT!"
		self.openref = self.openref-1
		if self.openref == 0:
			# We should try to start a write thread
			if self.dirty == True:
				self.iolock.release()
				if filesystem.writeback_time != '-1':
					self.writeTo(filesystem)
				return
		self.iolock.release()
		return

	def pathWalk(self, namelist):
		#name should be fully qualfied from the node pointed
		#to by self
		name = namelist[0]
		if len(namelist) == 1:
			#We might be the node you're looking for
			if self.name == name:
				if self.pending_delete == True:
					return None
				return self
			else:
				return None
		else:
			#iterate over the children
			for kid in self.children:
				rc = kid.pathWalk(namelist[1:])
				if rc != None:
					return rc
		return None

	def getParentKeyString(self):
		if self.parent == None:
			# WE return . here because we delimit key names with a
			# '.' instead of a '/'
			return "root"
		parentkeystring = self.parent.getParentKeyString()
		return parentkeystring + "." + self.name

	def getKeyName(self):
		#walk our parent path and return the string that makes up our
		#key name
		keystring = self.getParentKeyString() 
		return keystring

	def makeUploadCopy(self, filesystem):
		# We make a temporary copy of the file for uploading
		fd = filesystem.cache.shadowInCache(self)
		return fd

