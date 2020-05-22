import appdaemon.plugins.hass.hassapi as hass
import requests
import json
import secrets
from datetime import datetime, timedelta
import threading
from abc import ABCMeta, abstractmethod

class arpa_base_class(hass.Hass, metaclass=ABCMeta): 

	createSensor = False
	region = "toscana"
	region_friendly_name = "Stazione di monitoraggio Arpa regione {}".format(region.capitalize())

	@abstractmethod
	def getResult(self, url, station_id, arpa_monitored_params):
		pass

class toscana(arpa_base_class):

	#region_friendly_name = "Stazione di monitoraggio Arpa regione Toscana"

	def initialize(self):
		self.log("***** {} *****".format(self.region.upper()))
		self.log("{} {}".format(self.region, self.args))

	def getResult(self, url, station_id, arpa_monitored_params, unit_of_measurement = None):
		x = self.retrive_data(url, station_id, arpa_monitored_params, unit_of_measurement)
		self.log("getResult: {}".format(x))
		return x

	def retrive_data(self, url, station_id, arpa_monitored_params, unit_of_measurement = None):
		url = "{}{}{}".format(
			url,
			("/" if not url.endswith("/") else ""),
			station_id)
		self.log("[url]: {}".format(url), level = 'INFO')
		self.log("[station_id]: {}".format(station_id), level = 'INFO')
		self.log("[arpa_monitored_params]: {}".format(arpa_monitored_params), level = 'INFO')
		self.log("[unit_of_measurement]: {}".format(unit_of_measurement), level = 'INFO')

		r = requests.get(url)
		self.log("[api result]: {}".format(r), level = 'INFO')

		attributes_monitor={"friendly_name": self.region_friendly_name}

		if r.text != "":
			arpa_station = json.loads(r.text)
			if arpa_station:
				last_obj = sorted(arpa_station, key=lambda x: self.stringToDate(x["STR_DATA_OSSERVAZIONE"]), reverse=True)
				last_obj = last_obj[0]
				if arpa_monitored_params is None or arpa_monitored_params == []:
					arpa_monitored_params = list(set().union(*(d.keys() for d in arpa_station)))
					self.log("Use all monitored params")
					arpa_monitored_params.remove('NOME_STAZIONE')
					arpa_monitored_params.remove('STR_DATA_OSSERVAZIONE')
				for monitor_name in arpa_monitored_params:
					monitor_name = monitor_name.upper()
					self.log("1. monitor_name {}".format(monitor_name))
					if monitor_name.lower() in [i.lower() for i in last_obj]:
						attributes_monitor[monitor_name] = {}
						lookup = dict((k, v) for k, v in last_obj.items())
						attributes_monitor[monitor_name]["value"] = lookup.get(monitor_name.upper())#last_obj[monitor_name]
						attribute_sensor={}
						self.log("pre DataOsservazione")
						DataOsservazione = self.stringToDate(last_obj["STR_DATA_OSSERVAZIONE"]) if "STR_DATA_OSSERVAZIONE" in last_obj else None
						self.log("DataOsservazione {}".format(DataOsservazione))
						if DataOsservazione:
							attributes_monitor[monitor_name]["data_it"] = datetime.strftime(DataOsservazione, '%d-%m-%Y %H:%M:%S')
							attribute_sensor["data_it"] = datetime.strftime(DataOsservazione, '%d-%m-%Y %H:%M:%S')
						if unit_of_measurement is not None:
							unit_obj = next((value for key, value in unit_of_measurement.items() if key.lower() == monitor_name.lower()), "")
							self.log("unit: {}".format(unit_obj))
							if unit_obj:
								attributes_monitor[monitor_name]["unit_of_measurement"] = unit_obj
								attribute_sensor["unit_of_measurement"] = unit_obj
						self.log("attrs: {}".format(attributes_monitor[monitor_name]))
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
								state=attributes_monitor[monitor_name]["value"] if attributes_monitor[monitor_name]["value"] is not None else "N/D", 
								attributes = attribute_sensor)							
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

	def stringToDate (self, stringDate):
		dateObj = datetime.strptime(stringDate, '%d-%m-%Y %H')
		return dateObj
