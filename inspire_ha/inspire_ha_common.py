import logging
import time
from datetime import datetime

""" Common module for Inspire Home Automation API
See https://www.inspirehomeautomation.co.uk/client/api_help.php"""

""" Depends on a 'connection' dict which has entries to be set up during connection = 'api_key', 'key', 'session' and 'get_payload'
note the 'get_payload' value is a function reference to _get_payload(connection, get_or_post, ivars) to be implemented in calling module
'connection' dict also has optional configuration entries - 'cache_secs', 'api_url', 'device_name'"""
                                                               
API_URL = "https://www.inspirehomeautomation.co.uk/client/api1_4/api.php"
CACHE_SECS = 60 # min interval between API information requests
FUNCTIONS = {
    'off': '1',
    'program 1': '2',
    'program1': '2',
    'program_1': '2',
    '1': '2',
    'program 2': '3',
    'program2': '3',
    'program_2': '3',
    '2': '3',
    'both': '4',
    'on': '5',
    'boost': '6',
    }
FUNCTIONS_LIST = ( 'Off', 'Program_1', 'Program_2', 'Both', 'On', 'Boost' )
PROFILES = {
    '1': 'Profile_One',
    '2': 'Profile_Two',
    '3': 'Profile_Three',
    '4': 'Profile_Four',
    }
PROFILE_TYPES = {
    '1': '7 Day',
    '2': '5/2',
    '3': '1 Day',
}
ADVANCE = {
    'Off': '1',
    'On': '2',
}
PROFILES_LIST = list(PROFILES.keys())
PROPERTIES = ( 'device_id', 'device_name', 'device_type', 'advance', 'temperature', 'function', 'switch', 'profiles', 'profile', 'set_points', 'set_point' )

try:
    task.executor()
except NameError:
    PYSCRIPT = False
except TypeError:
    PYSCRIPT = True
else: # default
    PYSCRIPT = False
    
if not PYSCRIPT:
    log = logging.getLogger(__name__)
    
class InspireAPIException(Exception):
    pass
    
def error_msg(source, status, extra=None):
    err_msg = 'Error in %s()' % source
    if isinstance(status, dict):
        err_msg = err_msg + ': code %s: message: %s' % (status['code'], status['message'])
    elif status:
        err_msg = err_msg + ': ' + str(status)
    if extra:
        err_msg += ' ' + str(extra)
    return err_msg
    
def _get_data(connection, action, extra_vars = {} ):
    ivars = {
        'action': action,
        }
    ivars.update(extra_vars)
    payload, status = connection['get_payload'](connection, 'get', ivars)
    if payload:
        return payload, None
    return None, error_msg(action, status, extra_vars) 
    
def get_devices(connection):
    if connection.get('devices'):
        return connection['devices']
    data, err_msg = _get_data(connection, 'get_devices')
    if err_msg:
        log.error(err_msg)
        return None
    if data and data.get('devices') and data['devices'].get('device'):
        dvc = data['devices']['device']
        if dvc:
            if not isinstance (dvc, list):
                dvc = [ dvc ]
            connection['devices'] = dvc
            return dvc
    log.error(error_msg('get_devices', 'Empty device list returned'))
    return None
    
def get_device(connection):
    if not connection.get('device'):
        dvcs = get_devices(connection)
        if not dvcs:
            return None
        if not connection.get('device_name') or len(dvcs) == 1:
            connection['device'] = dvcs[0]
        elif connection.get('device_name'):
            for d in dvcs:
                if d['name'] == connection['device_name']:
                    connection['device'] = d
                    break
            if not connection.get('device'):
                err_msg = error_msg('get_device', "No device name found to match '%s'" % connection['device_name'])
                raise InspireAPIException(err_msg)
    return connection['device'] if connection.get('device') else None
    
def get_device_info(connection):
    dvc = get_device(connection)
    if not dvc:
        return None
    extra_vars = { 'device_id': dvc['device_id'] } 
    data, err_msg = _get_data(connection, 'get_device_information', extra_vars)
    if err_msg:
        log.error(err_msg)
        return None
    if data and data.get('Device_Information'):
        connection['info'] = data['Device_Information']
        connection['info_time'] = time.time()
        return data['Device_Information']
    log.error(error_msg('get_device_info', 'Empty device information returned'))    
    return None  

def device_id(connection): 
    device = get_device(connection) 
    return device['device_id'] if device else None
    
def device_name(connection): 
    device = get_device(connection) 
    return device['name'] if device else None  
        
def device_type(connection): 
    device = get_device(connection) 
    return device['type'] if device else None  

def advance(connection): 
    info = get_information(connection) 
    return info['Program_Advance'] if info else None
             
def temperature(connection): 
    info = get_information(connection) 
    return info['Current_Temperature'] if info else None
    
def function(connection): 
    info = get_information(connection) 
    return info['Current_Function'] if info else None
    
def switch(connection): 
    info = get_information(connection) 
    return info['Switch_Status'] if info else None 

def profile(connection): 
    info = get_information(connection) 
    if not info:
        return None
    #print(json.dumps(info['Profiles'], indent=2))
    profile = info['Profiles']['Selected_Profile'] # = a single digit character
    profile_type = info['Profile_Type']['Profile_Type_' + profile]
    profile_name = info['Profiles']['Profile_Management']['Profile_' + profile]['Name']
    dt = datetime.now()
    weekday = dt.strftime('%A')
    hourmin = dt.strftime('%H:%M')
    if profile_type == '1 Day':
        profile_section = 'Every_Day'
    elif profile_type == '7 Day':
        profile_section = weekday
    elif weekday in [ 'Saturday', 'Sunday' ]:
        profile_section = 'Weekend' 
    else:
        profile_section = 'Weekdays'
    switch_temp = None
    switch_end_time = None
    switch_start_time = None
    seg_list = info['Profiles'][PROFILES[profile]][profile_section]['Segment']
    for i, s in enumerate(seg_list):
        if s['Switch_Time'] >= hourmin:
            switch_temp = seg_list[i-1]['Switch_Temperature']
            switch_start_time = seg_list[i-1]['Switch_Time']
            switch_end_time = s['Switch_Time']
            break
    if switch_temp is None:
        switch_temp = seg_list[-1]['Switch_Temperature']
        switch_start_time = seg_list[-1]['Switch_Time']
        switch_end_time = seg_list[0]['Switch_Time']
    return {
        'index': profile,
        'name': profile_name,
        'type': profile_type,
        'section': profile_section,
        'current_day': weekday,
        'current_time': hourmin,
        'segment_temperature': switch_temp,
        'segment_start': switch_start_time,
        'segment_end': switch_end_time,
    }
    
def profiles(connection): 
    info = get_information(connection) 
    if not info:
        return None
    selected = info['Profiles']['Selected_Profile'] # = a single digit character
    profiles = []
    for p in PROFILES_LIST:
        prf = {}
        prf['name'] = info['Profiles']['Profile_Management']['Profile_' + p]['Name']
        prf['active'] = info['Profiles']['Profile_Management']['Profile_' + p]['Active']
        prf['type'] = info['Profile_Type']['Profile_Type_' + p]
        prf['selected'] = 'Yes' if p == selected else 'No'
        profiles.append(prf)
    return profiles
    
def set_point(connection, function = None):   
    info = get_information(connection)
    if not info:
        return None
    if function is None:
        function = info['Current_Function']
    function = function.lower()
    if function == 'on':
        return info['Set_Temperatures']['On_Temperature']
    elif function == 'boost':
        return info['Set_Temperatures']['Boost_Temperature']
    elif function == 'off':
        return info['Frost_Temperature']
    else:
        return info['Set_Temperatures']['Profile_Temperature']
        
def set_points(connection):   
    info = get_information(connection)
    if not info:
        return None
    return {
        'on': info['Set_Temperatures']['On_Temperature'],
        'boost': info['Set_Temperatures']['Boost_Temperature'],
        'off': info['Frost_Temperature'],
        'profile': info['Set_Temperatures']['Profile_Temperature'],
        }

def get_information(connection):
    cache_secs = connection['cache_secs'] if connection.get('cache_secs') else CACHE_SECS
    if connection.get('info') and connection.get('info_time'):
        if (time.time() - connection['info_time']) <= cache_secs:
            return connection['info']
    info = get_device_info(connection)
    return info if info else None
    
def _send_msg(connection, message, msg_vars = {}):
    device = get_device(connection)
    if not device:
        return error_msg('_send_msg', 'No device found')
    ivars = {
        'action': 'send_message', 
        'device_id': connection['device']['device_id'],
        'message': 'set_' + message,
    }
    ivars.update(msg_vars)
    payload, status = connection['get_payload'](connection, 'post', ivars)
    if isinstance(status, dict) and status['code'] == '14': # message sent
        return 'OK'
    return error_msg('_send_msg', status) 
        
def set_device_set_point(connection, set_point): 
    info = get_information(connection)
    if not info:
        return None
    function = info['Current_Function'].lower()
    if function == 'off':
        return error_msg('set_device_set_point', "Cannot adjust set point when Off")
    elif function == 'boost':
        return error_msg('set_device_set_point', "Cannot adjust set point when in Boost mode")
        # does not work returns code 9 invalid message
        #result = _send_msg(connection, 'set_boost_temp', { 'value': str(set_point) })
    else:
        result = _send_msg(connection, 'set_point', { 'value_temp': str(set_point) })
    connection.pop('info', None) # clear cached device information
    connection.pop('info_time', None)
    return result
        
def set_device_function(connection, function):
    strfunc = str(function)
    if not strfunc.isdigit():
        strfunc = FUNCTIONS.get(strfunc.lower())
        if not strfunc:
            return error_msg('set_device_function', "Invalid function value '%s'" % str(function))
    elif strfunc not in list(FUNCTIONS.values()):
        return error_msg('set_device_function', "Invalid function value '%s'" % strfunc)
    result = _send_msg(connection, 'function', { 'value': strfunc })
    connection.pop('info', None) # clear cached device information
    connection.pop('info_time', None)
    return result
    
def set_device_profile(connection, profile):
    strprof = str(profile)
    if strprof not in PROFILES_LIST:
        return error_msg('set_device_profile', "Invalid profile value '%s'" % strprof)
    result = _send_msg(connection, 'set_active_profile', { 'value': strprof })
    connection.pop('info', None) # clear cached device information
    connection.pop('info_time', None)
    return result
    
def set_device_advance(connection, advance):
    stradv = str(advance)
    if not stradv.isdigit():
        stradv = ADVANCE.get(stradv.lower())
        if not stradv:
            return error_msg('set_device_advance', "Invalid advance value '%s'" % str(advance))
    elif stradv not in list(ADVANCE.values()):
        return error_msg('set_device_advance', "Invalid advance value '%s'" % stradv)
    result = _send_msg(connection, 'set_advance', { 'value': stradv })
    connection.pop('info', None) # clear cached device information
    connection.pop('info_time', None)
    return result

def print_properties(connection):
    for p in PROPERTIES:
        name = p.replace('_', ' ').capitalize() + ':'
        print(name, globals()[p](connection))
    
def close(connection):
    if connection.get('session') is not None:
        connection['session'].close()
    connection.pop('get_payload', None)
    connection.pop('session', None)
    connection.pop('key', None)
    connection.pop('devices', None)
    connection.pop('device', None)
    connection.pop('info', None)
    connection.pop('info_time', None)

