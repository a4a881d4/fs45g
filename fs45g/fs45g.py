import tools
import os
import time
import json


class fs45g:
	def __init__(self,root,cashe):
		self.root = root
		self.cashe = root

	def makefile(self,hashkey,rc):
		if rc == 'meta':
			path = self.root
		else:
			path = self.cashe
		path += '/' + hashkey[:2]
		
		if not os.path.isdir(path):
			os.mkdir(path)

		filename = path + '/' + hashkey
		
		return filename
	
	def _createMeta( self, path, UID, GID, mode ):
		my = dict()
		my['path']=path
		my['UID']=UID
		my['GID']=GID
		my['mode']=tools.fmode(mode)
		my['ctime']=time.time()
		my['mtime']=time.time()
		my['atime']=time.time()	
		return my

	def prepareDir( self, path, UID, GID, mode ):
		mydir = self._createMeta( path, UID, GID, mode )
		fns = path.split('/')
		if fns:
			mydir['name'] = fns[-1]
		else:
			mydir['name'] = ''
		mydir['namehash'] = tools.hashpath(path)
		mydir['type'] = 'dir'
		mydir['files'] = []
		return mydir

	def persistenceDir( self, mydir ):
		path = self.makefile( mydir['namehash'], 'meta' )
		f = open(path,'w')
		f.write(json.dumps(mydir['files'],indent=2))
		f.close()
		mydir['type'] = 'dirinmeta'
		mydir['files'] = []

	def prepareFileInDir( self, fn, UID, GID, mode, mydir ):
		myfile = self._createMeta( mydir['path']+'/'+fn, UID, GID, mode )
		myfile['name'] = fn
		myfile['namehash'] = tools.hashpath(myfile['path'])
		myfile['type'] = 'file'
		mydir['files'].append(myfile)

	def prepareDirInDir( self, fn, UID, GID, mode, mydir ):
		myfile = self._createMeta( mydir['path']+'/'+fn, UID, GID, mode )
		myfile['name'] = fn
		myfile['namehash'] = tools.hashpath(myfile['path'])
		myfile['type'] = 'dir'
		myfile['files'] = []
		mydir['files'].append(myfile)

	def loadDirByPathRecursion( self, path ):
		metapath = self.makefile( tools.hashpath(path), 'meta' )
		with open(filepath) as meta_file:    
			mydir_files = json.load(meta_file)
			for f in mydir_files:
				if f['type'] == 'dirinmeta':
					f['files'] = self.loadDirByPath(f['path'])
					f['type'] = 'dir'
			return mydir_files
		return []

	def persistenceDirRecursion( self, mydir ):
		for f in mydir['files']:
			if f['type'] == 'dir':
				self.persistenceDirRecursion( f )
				f['type'] = 'dirinmeta'
				f['files'] = []
		path = self.makefile( mydir['namehash'], 'meta' )
		f = open(path,'w')
		f.write(json.dumps(mydir['files'],indent=2))
		f.close()
		



