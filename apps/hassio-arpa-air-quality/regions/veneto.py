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


class veneto(arpa_base_class):

	def initialize(self):
		self.log("***** {} *****".format(self.region.upper()), level = "INFO")
		self.log("{} {}".format(self.region, self.args), level = "DEBUG")

	def getResult(self, url, station_id, arpa_monitored_params, unit_of_measurement = None):
		x = self.retrive_data(url, station_id, arpa_monitored_params, unit_of_measurement)
		self.log("getResult: {}".format(x), level = "DEBUG")
		return x

	def retrive_data(self, url, station_id, arpa_monitored_params, unit_of_measurement = None):
		self.log("[url]: {}".format(url), level = 'DEBUG')
		self.log("[station_id]: {}".format(station_id), level = 'DEBUG')
		self.log("[arpa_monitored_params]: {}".format(arpa_monitored_params), level = 'DEBUG')
		self.log("[unit_of_measurement]: {}".format(unit_of_measurement), level = 'DEBUG')

		r = requests.get(url)
		self.log("[api result]: {}".format(r), level = 'DEBUG')

		attributes_monitor={"friendly_name": self.region_friendly_name}
		if r.text != "":
			stazioni_json = json.loads(r.text)['stazioni']
			arpa_station = next((x for x in stazioni_json if x["codseqst"].lower() == str(station_id).lower()), "")
			if arpa_station:
				if arpa_monitored_params is None or arpa_monitored_params == []:
					arpa_monitored_params = list(set().union(*(d.keys() for d in arpa_station["misurazioni"])))
					self.log("Nessun parametro di monitoraggio configurato. Verranno utilizzati tutti quelli disponibili", level = 'WARNING')
				attribute_max_date = None
				for monitor_name in arpa_monitored_params:
					attribute_value = None
					attribute_unit = None
					attribute_date = None
					monitor_name = monitor_name.upper()
					misurazioni = [{ k.upper(): v for k,v in x.items()} for x in arpa_station["misurazioni"]]
					arpa_station["misurazioni"] = misurazioni
					if monitor_name in (json.dumps(arpa_station["misurazioni"])):
						for monitor_obj in arpa_station["misurazioni"]:
							attribute_value = None
							attribute_unit = None
							attribute_date = None
							monitor_obj = monitor_obj.get(str(monitor_name))
							if monitor_obj and monitor_obj is not None:
								monitor_sorted_list = sorted(monitor_obj, key=lambda x: x["data"], reverse=True)
								if "mis" in monitor_sorted_list[0]:
									attribute_value = self.tryCastToFloat(monitor_sorted_list[0]["mis"])
									attribute_date = self.stringToDate(monitor_sorted_list[0]["data"], '%Y-%m-%d %H:%M:%S') #2020-05-15 18:10:01
									attribute_max_date = attribute_date if attribute_max_date is None else attribute_max_date
									attribute_max_date = attribute_date if attribute_date is not None and attribute_max_date is not None and attribute_date > attribute_max_date else attribute_max_date
									attributes_monitor[monitor_name] = attribute_value if attribute_value is not None else "N/D"
								if unit_of_measurement is not None:
									unit_obj = next((value for key, value in unit_of_measurement.items() if key.upper() == monitor_name.upper()), "")
									if unit_obj:
										attribute_unit = unit_obj
										if attribute_value is not None: attributes_monitor[monitor_name] = "{} {}".format(attribute_value, unit_obj)
								if self.createSensor:
									attribute_sensor={}
									if attribute_unit is not None:
										attribute_sensor["unit_of_measurement"] = attribute_unit
									attribute_sensor["data_rilevazione"] = attribute_date
									attribute_sensor["last_updated"] = datetime.now()
									attribute_sensor["station_id"] = station_id
									attribute_sensor["friendly_name"]= "Misurazione parametro {} della stazione {} nella regione {}".format(
										monitor_name,
										station_id,
										self.region
										)
									self.log("Sensor {} attributes: {}".format(monitor_name, attribute_sensor), level = 'DEBUG')
									self.set_state("sensor.arpa_air_station_{}_{}".format(self.region, monitor_name), 
										state=attribute_value if attribute_value is not None else "N/D", 
										attributes = attribute_sensor)							
				if attributes_monitor:
					attributes_monitor["data_rilevazione"] = attribute_max_date
					attributes_monitor["last_updated"] = datetime.now()
					self.log("Main Sensor attributes: {}".format(attributes_monitor), level = 'DEBUG')
					return attributes_monitor
				else:
					return None
			else:
				self.log("errore arpa station", level = 'ERROR')
				return json.loads({"friendly_name": self.region_friendly_name, "error":"Non sono stati trovati dati per la Stazione {}".format(station_id)})
		else:
			self.log("error during fetch data", level = 'ERROR')
			return json.loads({"friendly_name": self.region_friendly_name, "error":"error during fetch data"})
