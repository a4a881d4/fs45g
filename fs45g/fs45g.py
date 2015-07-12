import tools
import os
import time
import fuse
import pickle
import syslog
import getopt
import sys
import errno
import stat
import shutil
import json

from fuse import Fuse
from keylayoutelement import KeyLayoutElement
from fs45gcache import fs45gCache
from fs45gstat import fs45gStat,fs45gROStat
from fs45gfile import fs45gFile
from metadata import MetaData

class fs45g(Fuse):
	def __init__(self, *args, **kw):
		Fuse.__init__(self, *args, **kw)
		self.writeback_time = 0.1
		self.lazy_fsdata=True
		self.cachedir="/tmp"
		self.persistence = "persistence"
		self.root = "root"

	def setup(self):
		preserve = False
		fsname = tools.hashpath('')
		fsname = self.root + '/' +fsname		
		fp = open(fsname, "rb")
		self.FSData = pickle.load(fp)
		fp.close()
		self.FSData.root.runtimeSetup()

		self.cache = fs45gCache('root',self.cachedir,-1,preserve)
		self.cache.syncTree(self.FSData.root)

		return True

	def updateFsData(self):
		fsdata_copy = self.FSData.cloneForSave()
		fsname = tools.hashpath('')
		fsname = self.root + '/' +fsname		
		fp = open(fsname,"w+b")
		pickle.dump(fsdata_copy,fp,-1)
		fp.close()
	
	def getattr(self, path):
		findnode = self.FSData.findNode(path)		
		if findnode == None:
			return -errno.ENOENT
		uid = findnode.stat.st_uid
		gid = findnode.stat.st_gid
		
		if (uid == -1):
			uid = os.getuid()
		if (gid == -1):
			gid = os.getgid()

		return fs45gROStat(findnode.stat, uid, gid) 

	def readdir(self, path, offset):
		dirNode = self.FSData.findNode(path)
		dirNames = [ '.', '..']
		for node in dirNode.children:
			dirNames.append(node.name)
		for i in dirNames:
			yield fuse.Direntry(i)
		
	def chmod ( self, path, mode ):
		node = self.FSData.findNode(path)
		if node == None:
			return -errno.ENOENT

		node.iolock.acquire()
		node.stat.st_mode = node.stat.st_mode & ~(0777)
		node.stat.st_mode = node.stat.st_mode | mode
		node.iolock.release()
		return 0

	def chown ( self, path, uid, gid ):
		node = self.FSData.findNode(path)
		if node == None:
			return -errno.ENOENT
		node.iolock.acquire()
		node.stat.st_uid = uid
		node.stat.st_gid = gid
		node.iolock.release()

	def link ( self, targetPath, linkPath ):
		nodetok = linkpath.split('/')
		lname = nodetok[len(nodetok)-1]
		nodetok.remove(lname)
		dir = ""
		for i in nodetok:
			if i != '':
				dir = dir + "/" + i
		if dir == "":
			dir = "/"
	
		dirnode = self.FSData.findNode(dir)
		if dirnode == None:
			return -errno.ENOENT

		tnode = self.FSData.findNode(targetPath)
		if tnode == None:
			return -errno.ENOENT

		lnode = KeyLayoutElement(lname)
		lnode.runtimeSetup()
		ndnode.stat.st_mode = S_IFLNK | 0777
		lnode.target_path = targetPath
		dirnode.addChild(lnode)
		return 0

	def mkdir ( self, path, mode ):
		nodetok = path.split('/')
		newdir = nodetok[len(nodetok)-1]
		nodetok.remove(newdir)
		dir = ""
		for i in nodetok:
			if i != '':
				dir = dir + "/" + i

		if dir == "":
			dir = "/"
	
		dirnode = self.FSData.findNode(dir)
		if dirnode == None:
			return -errno.ENOENT

		ndnode = KeyLayoutElement(newdir)
		ndnode.runtimeSetup()
		ndnode.stat.st_mode = stat.S_IFDIR | mode
		dirnode.addChild(ndnode)
		return 0

	def mknod ( self, path, mode, dev ):
		node = self.FSData.findNode(path)
		if node != None:
			return -errno.EEXIST
		nodetok = path.split('/')
		dir=""
		filename = nodetok[len(nodetok)-1]
		nodetok.remove(filename)
		for i in nodetok:
			if i != '':
				dir = dir + "/" + i
		if dir == "":
			dir = "/"

		dirnode = self.FSData.findNode(dir)
		file = KeyLayoutElement(filename)
		file.runtimeSetup()
		file.stat.st_mode = mode
		dirnode.addChild(file)
		node = self.FSData.findNode(path)
		fd = file.open(self) 
		fd.close()
		return 0

	def readlink ( self, path ):
		node = self.FSData.findNode(path)
		if node == None:
			return -errno.ENOENT
		return node.target_path

	def rename ( self, oldPath, newPath ):
		oldnode = self.FSData.findNode(oldPath)
		if oldnode == None:
			return -errno.ENOENT
		newnode = self.FSData.findNode(newPath)
		if newnode != None:
			return -errno.EEXIST

		newntok = newPath.split('/')
		newname = newntok[len(newntok)-1]
		newntok.remove(newname)
		dir = ""
		for i in newntok:
			if i != '':
				dir = dir + "/" + i
		if dir == "":
			dir = "/"

		newdirnode = self.FSData.findNode(dir)
		if newdirnode == None:
			return -errno.ENOENT
	
		newnode = KeyLayoutElement(newname)
		newnode.runtimeSetup()
		newnode.stat = oldnode.stat

		newdirnode.addChild(newnode)

		newfile = newnode.open(self, os.O_RDWR|os.O_CREAT)
		oldfile = oldnode.open(self, os.O_RDWR)

		newnode.iolock.acquire()
		oldnode.iolock.acquire()

		shutil.copyfileobj(oldfile,newfile)
	
		newnode.dirty = True

		newnode.iolock.release()
		oldnode.iolock.release()

		newnode.close(self)
		oldnode.close(self)

		oldnode.delete(self)

		return 0	

	def rmdir ( self, path ):
		node = self.FSData.findNode(path)
		if node == None:
			return -errno.ENOENT
		if ((node.stat.st_mode & stat.S_IFDIR) != stat.S_IFDIR):
			return -errno.ENOTDIR
		node.parent.removeChild(node,self)
		return 0 

	def access (self, path, mode):
		mask = 0007
		node = self.FSData.findNode(path)
		if node == None:
			return -errno.ENOENT
		if node.stat.st_uid == -1:
			uid = -1
		else:
			uid = os.getuid()

		if node.stat.st_gid == -1:
			gid = -1
		else:
			gid = os.getgid()

		if node.stat.st_uid == uid:
			return 0 
		if node.stat.st_guid == gid:
			return 0 

		return -errno.EACCESS 

		
	def getxattr(self, path, name, size):
		node = self.FSData.findNode(path)
		if node == None:
			return -errno.ENOENT

		try:
			attr = node.xattrs[name]
		except KeyError:
			return -errno.ENODATA
		if size == 0:
			return len(attr)
		return attr

	def setxattr(self, path, name, value):
		node = self.FSData.findNode(path)
		if node == None:
			return -errno.ENOENT

		node.xattrs[name] = value

	def statfs ( self ):
		st = fuse.StatVfs()
		st.f_bsize = 1024 
		st.f_frsize = 0x7fffffff
		st.f_blocks = 0x7fffffff
		st.f_bfree =  0x7fffffff
		st.f_bavail = 0x7fffffff
		st.f_files =  0x7fffffff
		st.f_ffree =  0x7fffffff
		st.f_namelen = 255 
		return st 
		
	def symlink ( self, targetPath, linkPath ):
		nodetok = linkPath.split('/')
		lname = nodetok[len(nodetok)-1]
		nodetok.remove(lname)
		dir = ""
		for i in nodetok:
			if i != '':
				dir = dir + "/" + i

		if dir == "":
			dir = "/"
	
		dirnode = self.FSData.findNode(dir)
		if dirnode == None:
			return -errno.ENOENT

		lnode = KeyLayoutElement(lname)
		lnode.runtimeSetup()
		lnode.stat.st_mode = stat.S_IFLNK | 0777
		lnode.target_path = targetPath
		dirnode.addChild(lnode)

	def unlink ( self, path ):
		node = self.FSData.findNode(path)
		if node == None:
			return -errno.ENOENT
		node.delete(self)
		return 0

	def utime(self, path, times):
		return 0

	def utimens(self, path, ts_acc, ts_mod):
		return 0

	def main(self, *a, **kw):
		self.file_class = fs45gFile
		fs45gFile.myFS = self
		return Fuse.main(self, *a, **kw)

	def shutdown(self):
		syslog.syslog(syslog.LOG_INFO, "Exiting, Cleaning up FS")

		syslog.syslog(syslog.LOG_INFO, "Verifying writeback")
		self.FSData.root.writebackAll(self)

		self.cache.shutdown()

		if self.lazy_fsdata == True:
			syslog.syslog(syslog.LOG_INFO, "Updating the Filesystem Metadata")
			self.updateFsData()	
	
def fs45gEmpty( root="root" ):
	fuse.fuse_python_api=(0, 2)
	fs = fs45g()
	fs.root = root
	fs.FSData = MetaData()
	fs.updateFsData()
		
def fs45gcheck( root='root', persistence='persistence' ):
	fuse.fuse_python_api=(0, 2)
	fs = fs45g()
	fs.root = root
	fs.persistence = persistence
	if fs.setup() == False:
		syslog.closelog()
		sys.exit(1)
	sums = fs.FSData.root.sha_sums()
	list = os.listdir(fs.persistence)
	deletelist=[]
	for dirs in list:
		path = fs.persistence + '/' + dirs
		files = os.listdir(path)
		for fn in files:
			fpath = path+'/'+fn
			if fn[:2]!=dirs:
				deletelist.append(fpath)
				print 'error dir: '+fpath
			elif tools.hashfile(fpath) != fn:
				deletelist.append(fpath)
				print 'error sha: ' + fpath
			elif not fn in sums:
				deletelist.append(fpath)
				print 'error in fs: ' + fpath
	for fpath in deletelist:
		os.unlink(fpath)


def fs45gDumpHash( root='root' ):
	fuse.fuse_python_api=(0, 2)
	fs = fs45g()
	fs.root = root
	if fs.setup() == False:
		syslog.closelog()
		sys.exit(1)
	print fs.FSData.root.sha_sums()

def fs45gDump( root='root' ):
	fuse.fuse_python_api=(0, 2)
	fs = fs45g()
	fs.root = root
	if fs.setup() == False:
		syslog.closelog()
		sys.exit(1)
	print json.dumps(fs.FSData.root.dump2dir(),indent=2)

def fs45g_cleanup(filesystem):
	filesystem.shutdown()
		
def main():
	fuse.fuse_python_api=(0, 2)
	fs = fs45g()
	try:
		opts, args = getopt.getopt(sys.argv[1:], "r:p:")
	except getopt.GetoptError:
		fs_usage()
		return 1
	for o, a in opts:
		if o == "-r":
			fs.root = a
		if o == "-p":
			fs.persistence = a
	syslog.openlog(ident="fs45g", facility=syslog.LOG_USER)
	fs.parse(values=fs,errex=1)
	fs.flags = 0
	fs.multithreaded = True 
	if fs.setup() == False:
		syslog.closelog()
		sys.exit(1)
	fs.main()	
	fs45g_cleanup(fs)
	syslog.closelog()

def fs_usage():
	print "./fs45g -C -hc <root> <persistence> <mountpoint>"
	print "-C enter command mode"
	print "-h This help menu"
	
def handle_command_mode():
	try:
		opts, args = getopt.getopt(sys.argv[2:], "hcHt:")
	except getopt.GetoptError:
		fs_usage()
		return 1
	for o, a in opts:
		if o == "-h":
			fs_usage()
			return 0
		if o == "-c":
			fs45gEmpty(sys.argv[3])
			return 0
		if o == "-H":
			fs45gDumpHash(sys.argv[3])
			return 0
		if o == "-t":
			if a == 'check':
				fs45gcheck(sys.argv[4],sys.argv[5])
			if a == 'create':
				fs45gEmpty(sys.argv[4])
			if a == 'dump':
				fs45gDump(sys.argv[4])
			return 0
	fs_usage()
	return 0


if __name__ == '__main__':
	if len(sys.argv) == 1 or sys.argv[1] == "-h":
		fs_usage()
		sys.exit(0)
	if sys.argv[1] == "-C":
		rc = handle_command_mode()
		sys.exit(rc)
	else:
		main()


