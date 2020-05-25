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
	region_friendly_name = "Stazione Arpa regione {}".format(region.capitalize())

	@abstractmethod
	def getResult(self, url, station_id, arpa_monitored_params):
		pass

	def tryCastToFloat(self, item):
		try:
			return float(item) if item is not None else None
		except ValueError:
			return item

	def stringToDate (self, stringDate, dateFormat = '%d-%m-%Y %H'):
		dateObj = datetime.strptime(stringDate, dateFormat)
		return dateObj


class toscana(arpa_base_class):

	#region_friendly_name = "Stazione di monitoraggio Arpa regione Toscana"

	def initialize(self):
		self.log("***** {} *****".format(self.region.upper()), level = "INFO")
		self.log("{} {}".format(self.region, self.args), level = "DEBUG")

	def getResult(self, url, station_id, arpa_monitored_params, unit_of_measurement = None):
		x = self.retrive_data(url, station_id, arpa_monitored_params, unit_of_measurement)
		self.log("getResult: {}".format(x), level = "DEBUG")
		return x

	def retrive_data(self, url, station_id, arpa_monitored_params, unit_of_measurement = None):
		url = "{}{}{}".format(
			url,
			("/" if not url.endswith("/") else ""),
			station_id)
		self.log("[url]: {}".format(url), level = 'DEBUG')
		self.log("[station_id]: {}".format(station_id), level = 'DEBUG')
		self.log("[arpa_monitored_params]: {}".format(arpa_monitored_params), level = 'DEBUG')
		self.log("[unit_of_measurement]: {}".format(unit_of_measurement), level = 'DEBUG')

		r = requests.get(url)
		self.log("[api result]: {}".format(r), level = 'DEBUG')

		attributes_monitor={"friendly_name": self.region_friendly_name}

		if r.text != "":
			arpa_station = json.loads(r.text)
			if arpa_station:
				last_obj = sorted(arpa_station, key=lambda x: self.stringToDate(x["STR_DATA_OSSERVAZIONE"], '%d-%m-%Y %H'), reverse=True)
				last_obj = last_obj[0]
				if arpa_monitored_params is None or arpa_monitored_params == []:
					arpa_monitored_params = list(set().union(*(d.keys() for d in arpa_station)))
					self.log("Nessun parametro di monitoraggio configurato. Verranno utilizzati tutti quelli disponibili", level = 'WARNING')
					arpa_monitored_params.remove('NOME_STAZIONE')
					arpa_monitored_params.remove('STR_DATA_OSSERVAZIONE')
				for monitor_name in arpa_monitored_params:
					monitor_name = monitor_name.upper()
					if monitor_name.lower() in [i.lower() for i in last_obj]:
						attributes_monitor[monitor_name] = {}
						lookup = dict((k, v) for k, v in last_obj.items())
						# attributes_monitor[monitor_name] = self.tryCastToFloat(lookup.get(monitor_name.upper()))
						attributes_monitor[monitor_name] = (
							str(self.tryCastToFloat(lookup.get(monitor_name.upper()))) 
							if lookup.get(monitor_name.upper()) is not None else "N/D"
						)
						attribute_sensor={}
						DataOsservazione = self.stringToDate(last_obj["STR_DATA_OSSERVAZIONE"], '%d-%m-%Y %H') if "STR_DATA_OSSERVAZIONE" in last_obj else None
						if DataOsservazione:
							# attributes_monitor[monitor_name]["data_it"] = datetime.strftime(DataOsservazione, '%d-%m-%Y %H:%M:%S')
							attribute_sensor["data_it"] = datetime.strftime(DataOsservazione, '%d-%m-%Y %H:%M:%S')
						if unit_of_measurement is not None:
							unit_obj = next((value for key, value in unit_of_measurement.items() if key.lower() == monitor_name.lower()), "")
							if unit_obj:
								# attributes_monitor[monitor_name]["unit_of_measurement"] = unit_obj
								if lookup.get(monitor_name.upper()) is not None: attributes_monitor[monitor_name] = "{} {}".format(attributes_monitor[monitor_name], unit_obj)
								if lookup.get(monitor_name.upper()) is not None: attribute_sensor["unit_of_measurement"] = unit_obj
						if self.createSensor:
							attribute_sensor["last_updated"] = datetime.now()
							attribute_sensor["station_id"] = station_id
							attribute_sensor["friendly_name"]= "{} stazione {} regione {}".format(
								monitor_name,
								station_id,
								self.region
								)
							self.log("Sensor {} attributes: {}".format(monitor_name, attribute_sensor), level = 'DEBUG')
							self.set_state("sensor.arpa_air_station_{}_{}".format(self.region, monitor_name), 
								# state=attributes_monitor[monitor_name]["value"] if attributes_monitor[monitor_name]["value"] is not None else "N/D", 
								state=attributes_monitor[monitor_name] if attributes_monitor[monitor_name] is not None else "N/D", 
								attributes = attribute_sensor)							
				if attributes_monitor:
					attributes_monitor["last_updated"] = datetime.now()
					self.log("Main Sensor attributes: {}".format(attributes_monitor), level = 'DEBUG')
					return attributes_monitor
				else:
					return {"friendly_name": self.region_friendly_name, "Error": "Generic error"}
			else:
				self.log("errore arpa station", level = 'ERROR')
				return {"friendly_name": self.region_friendly_name, "error":"Non sono stati trovati dati per la Stazione {}".format(station_id)}
		else:
			self.log("error during fetch data", level = 'ERROR')
			return {"friendly_name": self.region_friendly_name, "error":"error during fetch data"}

