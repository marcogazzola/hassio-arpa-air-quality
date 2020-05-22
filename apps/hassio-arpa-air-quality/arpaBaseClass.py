import appdaemon.plugins.hass.hassapi as hass

class arpa_base_class(hass.Hass):

	@abstractmethod
	def getResult(self, url, station_id, arpa_monitored_params):
		pass
