import appdaemon.plugins.hass.hassapi as hass
import requests
import json
import secrets
from datetime import datetime, timedelta
import threading


class arpa_air_quality(hass.Hass):

	def initialize(self):

		self.log("########### ARPA AIR QUALITY INIT ###########")

		#self.throttle_timer = None

		self.arpa_url = self.get_arg(self.args, 'arpa_url_json')
		self.arpa_url = self.get_state(self.arpa_url)
		self.log("[arpa_url]: {}".format(self.arpa_url), level = 'INFO')
		self.arpa_station_id = self.get_arg(self.args, 'arpa_station_id')
		self.arpa_station_id = self.get_state(self.arpa_station_id)
		self.log("[arpa_station_id]: {}".format(self.arpa_station_id), level = 'INFO')
		self.arpa_monitored_params = self.get_arg(self.args, 'arpa_monitored_params')
		self.arpa_monitored_params = self.arpa_monitored_params

		self.log("[arpa_monitored_params]: {}".format(self.arpa_monitored_params), level = 'INFO')
		self.arpa_refresh_rate = self.get_arg(self.args, 'arpa_refresh_rate')
		self.arpa_refresh_rate = self.get_state(self.arpa_refresh_rate)
		self.log("[arpa_refresh_rate]: {}".format(self.arpa_refresh_rate), level = 'INFO')
		self.timer_interval = int(self.arpa_refresh_rate) * 60 * 60
		self.log("[timer_interval]: {}".format(self.timer_interval), level = 'INFO')

		# create a sensor to track check result
		self.set_state("sensor.arpa_air_station", state="Stazione {}".format(self.arpa_station_id), attributes = {"friendly_name": "Stazione di monitoraggio Arpa"})
		
		self.listen_event(self.arpa_air_quality_refresh, "arpa_air_quality_refresh")

		self.throttle_timer = self.run_every(self.throttle_retrive_data, datetime.now() + timedelta(seconds=20), self.timer_interval)

		self.log("########### ARPA AIR MONITOR END INIT ###########")

	def throttle_retrive_data(self, kwargs):
		self.log("throttle_retrive_data {}".format(kwargs), level = 'INFO')
		self.retrive_data(self.arpa_url, self.arpa_station_id, self.arpa_monitored_params)

	def retrive_data(self, url, station_id, arpa_monitored_params):
		self.log("[url]: {}".format(url), level = 'INFO')
		self.log("[station_id]: {}".format(station_id), level = 'INFO')
		self.log("[arpa_monitored_params]: {}".format(arpa_monitored_params), level = 'INFO')

		self.set_state("sensor.arpa_air_station", state="Stazione {}".format(station_id), attributes = {"friendly_name": "Stazione di monitoraggio Arpa"})

		# make the request
		r = requests.get(url)
		self.log("[api result]: {}".format(r), level = 'INFO')
		# evaluate result

		stazioni_json = json.loads(r.text)['stazioni']
		attributes_monitor={"friendly_name": "Stazione di monitoraggio Arpa"}
		if r.text != "":
			arpa_station = next((x for x in stazioni_json if x["codseqst"] == str(station_id)), "")
			if arpa_station:
				self.log(arpa_station)
				self.log(arpa_station["misurazioni"])
				if arpa_monitored_params is None or arpa_monitored_params == []:
					arpa_monitored_params = list(set().union(*(d.keys() for d in arpa_station["misurazioni"])))
				for monitor_name in arpa_monitored_params:
					if monitor_name in (json.dumps(arpa_station["misurazioni"])):
						for monitor_obj in arpa_station["misurazioni"]:
							self.log("monitor_name {}".format(monitor_name), level = 'INFO')
							self.log("old monitor_obj {}".format(monitor_obj))
							monitor_obj = monitor_obj.get(str(monitor_name))
							self.log("new monitor_obj {}".format(monitor_obj))
							if monitor_obj and monitor_obj is not None:
								newlist = sorted(monitor_obj, key=lambda x: x["data"], reverse=True)
								self.log(newlist[0])
								newlist[0]["data_it"] = datetime.strftime(datetime.strptime(newlist[0]["data"], '%Y-%m-%d %H:%M:%S'), '%d-%m-%Y %H:%M:%S')
								attributes_monitor[monitor_name] = newlist[0]
							else:
								self.set_state("sensor.arpa_air_station", state="Stazione {}".format(station_id), attributes = {"friendly_name": "Stazione di monitoraggio Arpa"})
				if attributes_monitor:
					self.set_state("sensor.arpa_air_station", state="Stazione {}".format(station_id), attributes = attributes_monitor)
			else:
				self.set_state("sensor.arpa_air_station", state="Stazione {}".format(station_id), attributes = {"friendly_name": "Stazione di monitoraggio Arpa", "error":"Non sono stati trovati dati per la Stazione {}".format(station_id)})
		else:
			self.set_state("sensor.arpa_air_station", state="Stazione {}".format(station_id), attributes = {"friendly_name": "Stazione di monitoraggio Arpa", "error":"error during fetch data"})

	def arpa_air_quality_refresh(self, event_name, data, kwargs):
		self.log("Event: {}".format(event_name))
		self.log("Event data: {}".format(data))
		#throttle function to ensure that we don't call check multiple times
		self.log("arpa_air_quality_refresh: {}".format(kwargs))
		self.cancel_timer(self.throttle_timer)
		self.retrive_data(
				data["arpa_url"] if "arpa_url" in data else self.arpa_url,
				data["arpa_station_id"] if "arpa_station_id" in data else self.arpa_station_id,
				data["arpa_monitored_params"] if "arpa_monitored_params" in data else self.arpa_monitored_params				
				)
		self.throttle_timer = self.run_every(self.throttle_retrive_data, datetime.now() + timedelta(seconds=10), self.timer_interval)

	def listToDict(self, lst):
		op = {lst[i]: lst[i + 1] for i in range(0, len(lst), 2)}
		return op

	def get_arg(self, args, key):
		self.log(args)
		self.log(key)
		if key in args:
			key = args[key]
		if type(key) is str and key.startswith("secret_"):
			if key in secrets.secret_dict:
				self.log("res: {}".format(secrets.secret_dict[key.replace("secret_", "")]))
				return secrets.secret_dict[key.replace("secret_", "")]
			else:
				raise KeyError("Could not find {} in secret_dict".format(key))

		else:
			self.log("res2: {}".format(key))
			return key

	def function(json_object, name, value):
			return [obj for obj in json_object if obj["{}"].format(name)==value]
