import appdaemon.plugins.hass.hassapi as hass
import requests
import json
import secrets
from datetime import datetime, timedelta
import threading
from abc import ABCMeta, abstractmethod

class arpa_base_class(hass.Hass, metaclass=ABCMeta): 

	createSensor = False
	region = "veneto"
	region_friendly_name = "Stazione di monitoraggio Arpa regione {}".format(region.capitalize())

	@abstractmethod
	def getResult(self, url, station_id, arpa_monitored_params):
		pass

class veneto(arpa_base_class):

	def initialize(self):
		self.log("***** {} *****".format(self.region.upper()))
		self.log("{} {}".format(self.region, self.args))

	def getResult(self, url, station_id, arpa_monitored_params, unit_of_measurement = None):
		x = self.retrive_data(url, station_id, arpa_monitored_params, unit_of_measurement)
		self.log("getResult: {}".format(x))
		return x

	def retrive_data(self, url, station_id, arpa_monitored_params, unit_of_measurement = None):
		self.log("[url]: {}".format(url), level = 'INFO')
		self.log("[station_id]: {}".format(station_id), level = 'INFO')
		self.log("[arpa_monitored_params]: {}".format(arpa_monitored_params), level = 'INFO')
		self.log("[unit_of_measurement]: {}".format(unit_of_measurement), level = 'INFO')

		r = requests.get(url)
		self.log("[api result]: {}".format(r), level = 'INFO')

		attributes_monitor={"friendly_name": self.region_friendly_name}
		if r.text != "":
			stazioni_json = json.loads(r.text)['stazioni']
			arpa_station = next((x for x in stazioni_json if x["codseqst"] == str(station_id)), "")
			if arpa_station:
				self.log("arpa_monitored_params {}".format(arpa_monitored_params))
				if arpa_monitored_params is None or arpa_monitored_params == []:
					arpa_monitored_params = list(set().union(*(d.keys() for d in arpa_station["misurazioni"])))
					self.log("Use all monitored params")
				for monitor_name in arpa_monitored_params:
					self.log("1. monitor_name {}".format(monitor_name))
					self.log("1bis. arpa_station['misurazioni'] {}".format(arpa_station["misurazioni"]))
					if monitor_name in (json.dumps(arpa_station["misurazioni"])):
						self.log("2. monitor_name ok")
						for monitor_obj in arpa_station["misurazioni"]:
							monitor_obj = monitor_obj.get(str(monitor_name))
							if monitor_obj and monitor_obj is not None:
								newlist = sorted(monitor_obj, key=lambda x: x["data"], reverse=True)
								self.log("5. {}".format(newlist[0]))
								newlist[0]["data_it"] = datetime.strftime(datetime.strptime(newlist[0]["data"], '%Y-%m-%d %H:%M:%S'), '%d-%m-%Y %H:%M:%S')
								attribute_sensor={}
								if unit_of_measurement is not None:
									unit_obj = next((value for key, value in unit_of_measurement.items() if key == monitor_name), "")
									self.log("unit: {}".format(unit_obj))
									if unit_obj:
										newlist[0]["unit_of_measurement"] = unit_obj
										attribute_sensor["unit_of_measurement"] = unit_obj
								attributes_monitor[monitor_name] = newlist[0]
								if self.createSensor:
									attribute_sensor["last_updated"] = datetime.now()
									attribute_sensor["station_id"] = station_id
									attribute_sensor["friendly_name"]= "Misurazione parametro {} della stazione {} nella regione {}".format(
										monitor_name,
										station_id,
										self.region
										)
									self.log(attribute_sensor)
									self.set_state("sensor.arpa_air_station_{}_{}".format(self.region, monitor_name), 
										state=newlist[0]["mis"] if newlist[0]["mis"] is not None else "N/D", 
										attributes = attribute_sensor)							

								self.log("attrs: {}".format(attributes_monitor[monitor_name]))
				if attributes_monitor:
					attributes_monitor["last_updated"] = datetime.now()
					return attributes_monitor
				else:
					return None
			else:
				self.log("errore arpa station")
				return json.loads({"friendly_name": self.region_friendly_name, "error":"Non sono stati trovati dati per la Stazione {}".format(station_id)})
		else:
			return json.loads({"friendly_name": self.region_friendly_name, "error":"error during fetch data"})
