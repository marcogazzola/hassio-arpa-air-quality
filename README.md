# hassio-arpa-air-quality
Get air information from Arpa (https://www.arpa.veneto.it/)
# <span style="font-family: 'Segoe UI Emoji'">🌬</span> Arpa Veneto Air quality

[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg?style=for-the-badge)](https://github.com/custom-components/hacs)

Collect information about Air quality information provided by Arpa Veneto throught sensor

## Sensor
Automatically will be created sensor **sensor.arpa_air_station**

<img src="example-sensor.png" width="400px">

## Configuration

Just add these key to your secrets.yaml file:
- arpa_url_json
- arpa_station_id
- arpa_refresh_rate
- arpa_monitored_params

| Parameter                       | Description                              | Type     | Example                                     |
| ------------------------------- | ---------------------------------------- | ------   | ------------------------------------------- |
| [`arpa_url_json`](#)            | Url of Json data                         | `string` | http://213.217.132.81/aria-json/exported/aria/data.json      |
| [`arpa_station_id`](#)          | Station ID to fetch data.                | `integer`| 500021975         |
| [`arpa_refresh_rate`](#)        | Refresh rate in hour. Default 6 hours    | `integer`| 6                 |
| [`arpa_monitored_params`](#)    | List of params to monitor                | `list`   | - ozono</br>- pm10 
|


> ```yaml
> # Example secrets.yaml entry
> arpa_url_json: http://213.217.132.81/aria-json/exported/aria/data.json
> arpa_station_id: 500021975
> arpa_refresh_rate: 6
> arpa_monitored_params:
>   - ozono
>   - pm10
> ```
