from keylayoutelement import KeyLayoutElement

class MetaData:
	def __init__(self):
		self.version = 2 
		self.size_unlimited = True
		self.root = KeyLayoutElement('/') 
		self.root.runtimeSetup()

	def findNode(self, name):
		if name == "/":
			return self.root
		tokens = name.split("/")
		return self.root.pathWalk(tokens)

	def cloneForSave(self):
		clone = MetaData()
		clone.root = None
		clone.version = self.version
		clone.size_unlimited = self.size_unlimited
		clone.root = self.root.cloneSubtree() 
		return clone


