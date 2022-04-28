# HAL-TS-Bridge
*Because **T**ime**S**eries databases are cool*

Collects data from the HAL MQTT network and posts to a local InfluxDB 1.8.x server.

## Description
The HAL-TS-Bridge name says everything.  It serves as a bridge between the HAL internal MQTT network and the time series database.  All topics are subscribed to at bridge bootup using the MQTT wildcard `/#`.

## Getting Started
This section is provided as a quick startup guide.  Please remember that these readmes are likely to go out of date between arbitrarily infrequent documentation updates.
### Dependencies 
#### Software
* Python 3
	* dataclasses_json
	* paho mqtt
	* InfluxDB 1.8.x

### Installing 
* clone from github
* configure by changing items in `ts_br_config.json`
* copy the included systemd service definition `hal-ts-bridge.service` to the systemd service store `/lib/systemd/system`
* enable the systemd service `systemctl enable hal-ts-bridge.service`

### Configuration
The included `ts_br_config.json` or `ts_br_config.json.example` is included for your reference.

The parameter `loglevel` can be set to your preferred verbosity: `CRITICAL`, `ERROR`, `WARNING`, `INFO`, and `DEBUG`.  If an incorrect level string is entered, it should default to `WARNING`.

### Execution
Systemd should execute the bridge automatically and provide restarts should it fail or the MQTT server disappear.

The included `hal-ts-bridge.py` is able to execute the bridge on its own if systemd execution is not preferred.

## Help
If you encounter a bug that you can not resolve, please submit a github bug report on `MAGLaboratory/hal-ts-bridge`.

## Authors
* @blu006

## Version History
No version numbers are used.  And the first "stable-ish" hash isn't provided yet.

## License 
Public domain

## Acknowledgements 
* @kyang014
* Proxmox
* InfluxDB
* Authors of the supporting libraries
* Readers like you, thank you.
