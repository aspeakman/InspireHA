import inspire_ha_req_mod as inspire_ha
import inspire_ha_common as common

ENTITY_UNAVAILABLE = ( None, 'unavailable', 'unknown', 'none' )
PRESET_MODES = ( 'away', 'comfort', 'eco', 'home', 'sleep', 'activity' )

iha_config = pyscript.app_config['inspire_ha']
config = {
    'api_key': iha_config['api_key'],
    'user_name': iha_config['user_name'],
    'password':iha_config['password'],
    'device_name': iha_config.get('device_name'),
    'api_url': iha_config.get('api_url'),
    'cache_secs': iha_config.get('cache_secs'),
    }
target_sensor = pyscript.app_config['target_sensor']
heater = pyscript.app_config['heater']
setpoint_sensor = pyscript.app_config.get('setpoint_sensor')
generic_thermostat = pyscript.app_config['generic_thermostat']
manual_only = False if pyscript.app_config.get('manual_only') is False else True
if pyscript.app_config.get('poll_cron_mins'):
    poll_cron_mins = pyscript.app_config['poll_cron_mins'].replace(' ', '')
else:
    poll_cron_mins = '*/5'

SENSOR_ATTS = {
    'state_class': 'measurement',
    'unit_of_measurement': '°C',
    'device_class': 'temperature',
}

connection = inspire_ha.connect(config) # establish connection session

therm_attrs = None
device = common.get_device(connection) 
if device is None:
    log.error("Cannot connect to inspire thermostat API using: %s" % str(connection))
    #raise common.InspireAPIException("Cannot connect to inspire thermostat API using: %s" % str(connection))
else:
    delays = 10
    for i in range(delays):
        therm_attrs = state.getattr('climate.' + generic_thermostat) 
        if therm_attrs is None or not therm_attrs.get('friendly_name'):
            log.debug("Attempt %d to get attributes from climate.%s" % (i+1, generic_thermostat))
            task.sleep(10)
        else:
            break
        if i >= delays - 1:
            log.error("%d attempts to get attributes from climate.%s" % (delays, generic_thermostat))
            #raise common.InspireAPIException("%d attempts to get attributes from climate.%s" % (delays, generic_thermostat))
            therm_attrs = None
    if therm_attrs is not None:
        friendly_name = therm_attrs['friendly_name']
        previous_mode = 'none' # previous mode = preset mode or 'none'
        stored_target_temp = None # last manual set_point before entering preset mode
        stored_function = None # last heating function before entering preset mode

        temperature_attributes = { 
            'friendly_name': friendly_name + ' Temperature',
            }
        switch_attributes = { 
            'friendly_name': friendly_name + ' Switch',
            }
        set_point_attributes = { 
            'friendly_name': friendly_name + ' Set Point',
        }
        temperature_attributes.update(SENSOR_ATTS)
        set_point_attributes.update(SENSOR_ATTS)
        
        log.info("Controlling %s via inspire_ha_thermostat" % friendly_name)
    else:
        log.error("Cannot connect to generic thermostat climate.%s" % generic_thermostat)

""" Terminology
'remote' aka external is the physical thermostat controlled via the Inspire HA API
'set_point' is the set point of the 'remote' device
'local' aka internal is the generic_thermostat entity within the Home Assistant system
'target_temp' is the set point of the 'local' entity
"""

def entity_set(entity_name, value, attrs=None, domain='sensor'): 
    # returns None (no action possible), False (value already set), True (set changed value))
    if value is None:
        return None
    entity_name = entity_name if entity_name.startswith(domain + '.') else domain + '.' + entity_name
    try:
        result = state.get(entity_name)
        if result in ENTITY_UNAVAILABLE:
            return None
        elif result == value:
            return False
    except NameError:
        pass # at start up the entity will not exist so just proceed to set it
    state.set(entity_name, value, attrs)
    return True

def update_from_remote(): # transfer 3 settings from remote API to local sensors

    changed = False
    temperature = common.temperature(connection)
    if temperature:
        res = entity_set(target_sensor, temperature, attrs=temperature_attributes)
        changed = True if res is True else changed
    switch = common.switch(connection)
    if switch:
        res = entity_set(heater, switch.lower(), attrs=switch_attributes, domain='switch')
        changed = True if res is True else changed
    set_point = common.set_point(connection) # external set_point string
    if set_point and setpoint_sensor:
        res = entity_set(setpoint_sensor, set_point, attrs=set_point_attributes)
        changed = True if res is True else changed
    if changed:
        log.info('Local %s updated: temp. %s, setpoint %s, heating %s)' % (friendly_name, temperature, set_point, switch.lower()))
    return temperature, switch, set_point
    
def target_temp_to_remote(target_temp, prefix_msg = None): # sync local target with remote setpoint

    set_point = common.set_point(connection) # external set_point string
    if not set_point:
        return
    
    if target_temp != set_point: 
        status = common.set_device_set_point(connection, target_temp)
        prefix_msg = 'Remote ' if prefix_msg is None else prefix_msg + ': '
        log.info('%s%s changed set point (old %s new %s) %s' % (prefix_msg, device['name'], set_point, target_temp, status))
    else:
        prefix_msg = 'Remote ' if prefix_msg is None else prefix_msg + ': '
        log.debug('%s%s unchanged set point (%s = %s)' % (prefix_msg, device['name'], set_point, target_temp))

    task.sleep(5)
    update_from_remote()

@time_trigger("cron(" + poll_cron_mins + " * * * *)") # poll remote for setpoint, temperature and switch state
def poll_thermostat():
    if device is None or therm_attrs is None:
        return
    log.debug('Polling remote device %s' %  device['name'])
    
    temperature, switch, set_point = update_from_remote() # updates sensors
    
    # if necessary update local target_temp from remote set_point 
    if set_point: 
        attrs = state.getattr('climate.' + generic_thermostat) 
        # NB the 'temperature' attribute here is not the sensed temperature but the local target_temp
        target_temp = '%g' % attrs['temperature'] if attrs.get('temperature') else None # %g no trailing zero
        preset_mode = attrs['preset_mode'] if attrs.get('preset_mode') else 'none' 
        if preset_mode == 'none' and target_temp and target_temp != set_point: 
            climate.set_temperature(entity_id = 'climate.' + generic_thermostat, temperature = float(set_point))
            #NB triggers event below if different
        
@state_trigger('climate.' + generic_thermostat + '.temperature', state_hold = 1) # transfer changed target_temp from local climate entity to remote set_point
def target_temp_changed(**kwargs):
    if device is None or therm_attrs is None:
        return
    log.debug('Target temp of local %s changed' % friendly_name)
    
    attrs = state.getattr('climate.' + generic_thermostat) 
    name = attrs.get('friendly_name', '*')
    value = kwargs.get('value', '')
    old_value = kwargs.get('old_value' '')
    if value != 'heat' or old_value != 'heat': # signature when generic thermostat is reloaded or stopped
        log.debug('target_temp_changed() of %s cut short at start up' % name)
        return
    
    function = common.function(connection)
    # if manual_only is true, only update the remote set_point if the remote thermostat is in On/Manual mode
    # if manual_only is false, update the remote set_point if the remote thermostat is in Program or On/Manual
    if not function or (manual_only and function != 'On') or \
            (not manual_only and function in ['Off', 'Boost'] ): 
        return
        
    attrs = state.getattr('climate.' + generic_thermostat)
    target_temp = '%g' % attrs['temperature'] if attrs.get('temperature') else None # %g no trailing zero
    # NB the 'temperature' attribute here is not the sensed temperature but the local target_temp
    if not target_temp: 
        return
        
    target_temp_to_remote(target_temp)

@state_trigger('climate.' + generic_thermostat + '.preset_mode') # store/restore target_temp if preset mode changes
def restore_target_temp(**kwargs):
    if device is None or therm_attrs is None:
        return
    log.debug('(Re)storing target temp. for %s' % friendly_name)
    global previous_mode
    global stored_target_temp
    global stored_function
    
    attrs = state.getattr('climate.' + generic_thermostat) 
    name = attrs.get('friendly_name', '*')
    value = kwargs.get('value', '')
    old_value = kwargs.get('old_value' '')
    if value != 'heat' or old_value != 'heat': # signature when generic thermostat is reloaded or stopped
        log.debug('restore_target_temp() of %s cut short at start up' % name)
        return
    
    function = common.function(connection)
    # if manual_only is true, only update the remote set_point if the remote thermostat is in On/Manual mode
    # if manual_only is false, update the remote set_point if the remote thermostat is in Program or On/Manual
    if not function or (manual_only and function != 'On') or \
            (not manual_only and function in ['Off', 'Boost'] ): 
        return
        
    attrs = state.getattr('climate.' + generic_thermostat)
    preset_mode = attrs['preset_mode'].lower() if attrs.get('preset_mode') else 'none' 
    if preset_mode in PRESET_MODES and previous_mode == 'none':
        if function == 'On':
            stored_target_temp = common.set_point(connection) # last manual target before entering preset mode
        else:
            stored_target_temp = None
            common.set_device_function(connection, 'On')
        stored_function = function
        previous_mode = preset_mode
        return
    elif preset_mode != 'none':
        previous_mode = preset_mode
        return
        
    # returning from any preset mode to 'none' mode
    if function == 'On':
        if stored_function == 'On': # no change to function
            target_temp = stored_target_temp # previously set manual target_temp
            msg = "Restored manual temp."
        elif stored_function is not None:
            common.set_device_function(connection, stored_function)
            profile = common.profile(connection)
            target_temp = profile.get('segment_temperature') # time appropriate profile temp. target
            msg = "Restored profile temp."
        target_temp_to_remote(target_temp, msg)
    stored_target_temp = None
    stored_function = None
    previous_mode = 'none'
       


