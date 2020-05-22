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
		self.log("########### ARPA AIR QUALITY INIT ###########")
		try:
			with open('{}/{}/region.json'.format(
				self.app_dir, self.get_arg(self.args, 'app_folder_name'))) as json_file:
				self.config = json.load(json_file)
				self.log("self.config {}".format(self.config))
				self.regionsConfig = self.config["regions"]
				self.log("self.regionsConfig {}".format(self.regionsConfig))
				self.timer_interval = int(self.config["refresh_rate"]) * 60 * 60
				self.log("self.timer_interval {}".format(self.timer_interval))
		except Exception as inst:
			self.regionsConfig = None
			self.notify_frontend("ERROR", 
				"Configurazione non presente.\nVerificare la presenza e il formato del file region.json",
				arpa_air_quality_notify.configError)
			self.log(inst)
			return

		self.listen_event(self.arpa_air_quality_refresh, "arpa_air_quality_refresh")

		self.throttle_timer = self.run_every(self.throttle_fetch_data, datetime.now() + timedelta(seconds=20), self.timer_interval)

		self.log("########### ARPA AIR MONITOR END INIT ###########")

	def terminate(self):
		self.cancel_timer(self.throttle_timer)

	def throttle_fetch_data(self, kwargs):
		self.log("throttle_fetch_data {}".format(kwargs), level = 'INFO')
		self.fetch_data()

	def arpa_air_quality_refresh(self, event_name, data, kwargs):
		self.log("Event: {}".format(event_name))
		self.log("Event data: {}".format(data))
		if "regioni" in data:
			event_refresh_regions = dict((k, self.regionsConfig[k]) for k in data["regioni"] if k in self.regionsConfig)
			self.log("1. {}".format(event_refresh_regions))
			self.log("2. {}".format(event_refresh_regions.items()))
			self.log("3. {}".format(list(event_refresh_regions)))
			if event_refresh_regions:
				#throttle function to ensure that we don't call check multiple times
				self.cancel_timer(self.throttle_timer)
				self.fetch_data(event_refresh_regions)
				self.throttle_timer = self.run_every(self.throttle_fetch_data, datetime.now() + timedelta(seconds=10), self.timer_interval)

	def fetch_data(self, regions = None):
		self.log("fetch_data.1 {}".format(regions))
		regions = self.regionsConfig if regions is None else regions
		self.log("fetch_data.2 {}".format(regions))

		if not regions:
			self.log("No regions configured", level = "WARNING")
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
				self.log("regionApp {}".format(regionApp))
				self.log("1.unit_of_measurement {}".format(self.config.get('unit_of_measurement')))
				sensorAttributes = regionApp.getResult(regions.get(region).get('url'),
					regions.get(region).get('station_id'),
					regions.get(region).get('monitored_params'),
					self.config.get('unit_of_measurement'))
				self.log("sensorAttributes {}".format(sensorAttributes))
				self.set_state("sensor.arpa_air_station_{}".format(region), 
					state="Stazione di monitoraggio Arpa regione {} Stazione {}".format(
						region.capitalize(), regions.get(region).get('station_id')), 
					attributes = sensorAttributes)
			except Exception as inst:
				self.notify_frontend("ERROR", 
					"Errore generico durante l'aggiornamento della regione {} - {}.".format(region, inst),
					arpa_air_quality_notify.configError)
				self.log("ERROR: {}".format(inst), level = "ERROR")
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
