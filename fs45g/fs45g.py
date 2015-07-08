import tools
import os
import time
import json


class fs45g:
	def __init__(self,root,cashe):
		self.root = root
		self.cashe = root

	def makefile(self,hashkey,rc):
		if rc == 'root':
			path = self.root
		else:
			path = self.cashe
		path += '/' + hashkey[:2]
		
		if not os.path.isdir(path):
			os.mkdir(path)

		filename = path + '/' + hashkey
		
		return filename

	def prepareDir( self, path, UID, GID, mode ):
		mydir = dict()
		mydir['path']=path
		mydir['UID']=UID
		mydir['GID']=GID
		mydir['mode']=tools.fmode(mode)
		mydir['ctime']=time.time()
		mydir['mtime']=time.time()
		mydir['atime']=time.time()
		mydir['files']={}
		return tools.hashpath(path),mydir

	def persistenceDir( self, hashkey, obj ):
		path = self.makefile( hashkey, 'root' )
		f = open(path,'w')
		f.write(json.dumps(obj,indent=2))
		f.close()

