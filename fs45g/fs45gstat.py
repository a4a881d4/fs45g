import fuse

class fs45gStat(fuse.Stat):
	def __init__(self):
		self.st_mode = 0
		self.st_ino = 0
		self.st_dev = 0
		self.st_nlink = 0
		self.st_uid = 0
		self.st_gid = 0
		self.st_size = 0
		self.st_atime = 0
		self.st_mtime = 0
		self.st_ctime = 0

class fs45gROStat(fs45gStat):
	def __init__(self, clone, uid, gid):
		super(fs45gStat,self).__setattr__('st_mode',clone.st_mode) 
		super(fs45gStat,self).__setattr__('st_ino',clone.st_mode)
		super(fs45gStat,self).__setattr__('st_dev',clone.st_dev) 
		super(fs45gStat,self).__setattr__('st_nlink',clone.st_nlink)
		super(fs45gStat,self).__setattr__('st_uid',uid) 
		super(fs45gStat,self).__setattr__('st_gid',gid)
		super(fs45gStat,self).__setattr__('st_size',clone.st_size)
		super(fs45gStat,self).__setattr__('st_atime',clone.st_atime) 
		super(fs45gStat,self).__setattr__('st_mtime',clone.st_mtime)
		super(fs45gStat,self).__setattr__('st_ctime',clone.st_ctime)

	def __setattr__(self, *args):
		raise TypeError("can't modify immutable instance")
	__delattr__ = __setattr__

