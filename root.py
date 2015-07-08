import sys
import fs45g

fs = fs45g.fs45g( sys.argv[1], sys.argv[2] )
key,obj = fs.prepareDir('/',0,0,'664')
fs.persistenceDir(key,obj)




