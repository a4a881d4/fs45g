import sys
import fs45g

fs = fs45g.fs45g( sys.argv[1], sys.argv[2] )
obj = fs.prepareDir('',0,0,'664')
fs.prepareDirInDir('home', 0, 0, '664', obj) 
fs.persistenceDirRecursion(obj)




