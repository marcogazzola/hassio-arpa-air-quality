import appdaemon.plugins.hass.hassapi as hass

class ArpaBaseClass(hass.Hass):

	@abstractmethod
	def getResult(self, url, station_id, arpa_monitored_params):
		pass

class Pippo:
	pass

def Pluto(args, key):
	return key