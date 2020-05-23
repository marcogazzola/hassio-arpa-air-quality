import appdaemon.plugins.hass.hassapi as hass
import requests
import json
import secrets
from datetime import datetime, timedelta
import threading

class arpa_air_quality_notify:
	configError = 1
	noDataFound = 2
	appNotFound = 3

class arpa_air_quality(hass.Hass):

	def initialize(self):
		self.log("########### ARPA AIR QUALITY INIT ###########", level = 'INFO')
		try:
			with open('{}/{}/region.json'.format(
				self.app_dir, self.get_arg(self.args, 'app_folder_name'))) as json_file:
				self.config = json.load(json_file)
				self.log("self.config {}".format(self.config), level = 'DEBUG')
				self.regionsConfig = self.config["regions"]
				self.log("self.regionsConfig {}".format(self.regionsConfig), level = 'DEBUG')
				self.timer_interval = int(self.config["refresh_rate"]) * 60
				self.log("self.timer_interval {}".format(self.timer_interval), level = 'DEBUG')
		except Exception as inst:
			self.regionsConfig = None
			self.notify_frontend("ERROR", 
				"Configurazione non presente.\nVerificare la presenza e il formato del file region.json",
				arpa_air_quality_notify.configError)
			self.log(inst, level = 'ERROR')
			return

		self.listen_event(self.arpa_air_quality_refresh, "arpa_air_quality_refresh")

		self.throttle_timer = self.run_every(self.throttle_fetch_data, datetime.now() + timedelta(seconds=20), self.timer_interval)

		self.log("########### ARPA AIR MONITOR END INIT ###########", level = 'INFO')

	def terminate(self):
		self.cancel_timer(self.throttle_timer)

	def throttle_fetch_data(self, kwargs):
		self.log("throttle_fetch_data {}".format(kwargs), level = 'DEBUG')
		self.fetch_data()

	def arpa_air_quality_refresh(self, event_name, data, kwargs):
		self.log("Event: {}".format(event_name), level = 'DEBUG')
		self.log("Event data: {}".format(data), level = 'DEBUG')
		if "regions" in data:
			event_refresh_regions = dict((k, self.regionsConfig[k]) for k in data["regions"] if k in self.regionsConfig)
			self.log("regions to refresh: {}".format(event_refresh_regions), level = 'INFO')
			if event_refresh_regions:
				#throttle function to ensure that we don't call check multiple times
				self.cancel_timer(self.throttle_timer)
				self.fetch_data(event_refresh_regions)
				self.throttle_timer = self.run_every(self.throttle_fetch_data, datetime.now() + timedelta(seconds=self.timer_interval), self.timer_interval)

	def fetch_data(self, regions = None):
		self.log("Fetch_data {}".format(regions), level = 'DEBUG')
		regions = self.regionsConfig if regions is None else regions

		if not regions:
			self.log("Attention! No regions configured", level = "WARNING")
			self.notify_frontend("WARNING", 
				"Non ci sono regioni configurate. Verificare il file regions.json",
				arpa_air_quality_notify.noDataFound)
			return

		for region in regions:
			try:
				if not regions.get(region).get('url'):
					continue
				regionApp = self.get_app(region)
				if regionApp is None:
					self.log("App {} not found in AppDaemon".format(region), level = "ERROR")
					self.notify_frontend("ERROR", 
						"L'applicazione {} non è presente in AppDaemon!".format(region),
						arpa_air_quality_notify.appNotFound)
					continue
				regionApp.createSensor = self.config.get('create_sensor')
				self.log("regionApp {}".format(regionApp), level = 'DEBUG')
				sensorAttributes = regionApp.getResult(regions.get(region).get('url'),
					regions.get(region).get('station_id'),
					regions.get(region).get('monitored_params'),
					self.config.get('unit_of_measurement'))
				self.set_state("sensor.arpa_air_station_{}".format(region), 
					state="{}".format(regionApp.region_friendly_name), 
					attributes = sensorAttributes)
			except Exception as inst:
				self.notify_frontend("ERROR", 
					"Errore generico durante l'aggiornamento della regione {} - {}.".format(region, inst),
					arpa_air_quality_notify.configError)
				self.log("ERROR 2: {}".format(inst), level = "ERROR")
				return

	def get_arg(self, args, key):
		if key in args:
			key = args[key]
		if type(key) is str and key.startswith("secret_"):
			if key in secrets.secret_dict:
				return secrets.secret_dict[key.replace("secret_", "")]
			else:
				raise KeyError("Could not find {} in secret_dict".format(key))
		else:
			return key

	def notify_frontend(self, level, message, notificationId = None):
		notificationId = notificationId if notificationId is not None else random.randint(100,1000)
		#pretty_timestamp = datetime.now().strftime('%d/%m/%Y %T')
		title = "Attenzione! " if level == "WARNING" else "Errore! "
		self.call_service('persistent_notification/create',
			title="[AppDaemon {}] {}".format(self.get_arg(self.args, 'app_name'), title),
			message=("{}".format(message)),
			notification_id = notificationId)
