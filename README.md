# InspireHA

Includes a Python package **inspire_ha** which has modules for controlling an
[Inspire Home Automation](https://www.inspirehomeautomation.co.uk/) thermostat
using their [API](https://www.inspirehomeautomation.co.uk/client/api_help.php). 

The project also includes **inspire_ha_thermostat** a [Pyscript](https://hacs-pyscript.readthedocs.io/en/latest/) Home Assistant app 
which synchronises your Inspire device with a [Generic Thermostat](https://www.home-assistant.io/integrations/generic_thermostat/) 
climate integration (for details see below).


## Pre-requisites

You will need to create a `secrets.yaml` - replace xxxx in the following example - for `api_key`
 [see](https://www.inspirehomeautomation.co.uk/client/api.php).:
```
user_name: "xxxx"
password: "xxxx"
api_key: "xxxx"
```

----------

# _inspire_ha_ python package 

## Configuration

Put your `secrets.yaml` in the _inspire_ha_ folder then edit `main.yaml` to suit - an example as follows:

```
cache_secs: 120 # secs to store data (default 60) before refreshing information from inspire API
#api_url: 'https://www.inspirehomeautomation.co.uk/client/api1_4/api.php' # default
#device_name: 'My Thermostat' # if set this must match the Unit Name as specified in Setup on the inspire web site, otherwise it uses the first device available
```

## Actions
Use the `inspire_req_mod.py` module. You should save your `secrets.yaml` in the same folder.

To get help:

> python inspire_req_mod.py -h

To get thermostat status information:

> python inspire_req_mod.py

To set thermostat set point to 15.5C:

> python inspire_req_mod.py -s 15.5

To set thermostat function to 'Boost':

> python inspire_req_mod.py -f boost

----------

# _inspire_ha_thermostat_ Home Assistant pyscript app 

## Description

The app synchronises the temperature and set point of your Inspire thermostat with a generic thermostat entity on 
Home Assistant (HA). If you change the target temperature on the HA generic thermostat then the current set point 
of your Inspire thermostat will change (as long as it is not in Boost or Off (frost protection) mode).

Similarly changes on your Inspire thermostat (scheduled or manual) will be mirrored on the HA generic thermostat.
If the Inspire is in Manual/On mode, then the Home Assistant app will effectively control the thermostat. However 
if it is in Program mode the generic thermostat will also change according to the Inspire timetabled program.

If your generic thermostat has any preset mode temperatures configured (eg Away, Eco, Sleep), then setting the 
generic thermostat to that mode will impose this target. When the preset mode is removed (preset None) 
the original set point will be restored (Inspire Manual/On mode) or the restored set point will be from the appropriate program 
segment (Inspire Program mode).

## Installation
First set up a [Generic Thermostat](https://www.home-assistant.io/integrations/generic_thermostat/) on Home Assistant
(see below) using 

Note down the ids of the generic thermostat and its underlying 'heater' and 'target_sensor' entities for 
substitution in the `config.yaml` below.

Next install [Pyscript](https://hacs-pyscript.readthedocs.io/en/latest/).
Then copy `inspire_ha_thermostat.py` to the pyscript _apps_ folder
and copy `inspire_ha_common.py` and `inspire_ha_req_mod.py` to the pyscript _modules_ folder. 

## Configuration
Configuration of the generic thermostat is via the HA `configuration.yaml` - an example as follows:
```
climate:
  - platform: generic_thermostat
    unique_id: hall_thermostat
    name: Hall Thermostat
    heater: switch.inspire_switch # use an arbitrary name in the 'switch' domain
    target_sensor: sensor.inspire_temperature # use an arbitrary name in the 'sensor' domain
    min_temp: 5
    max_temp: 25
    ac_mode: false
    initial_hvac_mode: "heat"
    target_temp: 12 # this set point is used when HA is restarted
    away_temp: 10 # this set point is used when in Away mode
```
Configuration is via the pyscript `config.yaml` - an example as follows:
```
allow_all_imports: true
hass_is_global: false
apps:
  inspire_ha_thermostat:
    # the following 3 settings are required
    generic_thermostat: 'hall_thermostat' # unique_id of controlling generic thermostat climate platform on home assistant
    heater: 'inspire_switch' # entity id of 'heater' state object in switch domain (use switch.entity_id in configuration of generic thermostat)
    target_sensor: 'inspire_temperature' # entity id of 'target_sensor' state object in sensor domain (use sensor.entity_id in configuration of generic thermostat)
    # the following 3 settings are all optional
    setpoint_sensor: 'inspire_setpoint' # entity id of a state object in sensor domain to reflect set point of inspire remote device (it will be created for you)
    manual_only: false # default true = only transfer settings from generic thermostat if remote thermostat is in Manual/On mode (not following a program)
    poll_cron_mins: '3,8,13,18,23,28,33,38,43,48,53,58' # cron minutes past the hour for polling the remote thermostat - default '*/5' 
    inspire_ha:
      api_key: !secret inspire_ha_api_key
      user_name: !secret inspire_ha_user_name
      password: !secret inspire_ha_password
      #device_name: # if set this must match the Unit Name as specified in Setup on the inspire web site, otherwise it uses the first device available
      #cache_secs: 60 # default secs to store data before refreshing information from inspire API
      #api_url: 'https://www.inspirehomeautomation.co.uk/client/api1_4/api.php' # default
```
You will need to add the following lines to the pyscript `secrets.yaml` replacing xxxx (see Pre-requisites above):
```
inspire_ha_user_name: "xxxx"
inspire_ha_password: "xxxx"
inspire_ha_api_key: "xxxx"
```

## Actions

Look in the logs for entries tagged _inspire_ha_. 

