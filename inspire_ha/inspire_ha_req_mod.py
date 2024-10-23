import requests
import xmltodict
import yaml

import inspire_ha_common as common

""" Client module for Inspire Home Automation API
See https://www.inspirehomeautomation.co.uk/client/api_help.php
                                                                
Note works on Home Assistant pyscript ie requests are wrapped with task.executor
See https://hacs-pyscript.readthedocs.io/en/latest/index.html"""
    
def _external_request(connection, get_or_post, ivars = {}):
    api_url = connection['api_url'] if connection.get('api_url') else common.API_URL
    if get_or_post.lower() == 'get':
        if common.PYSCRIPT:
            return task.executor(connection['session'].get, api_url, params = ivars)
        else:
            return connection['session'].get( api_url, params = ivars)
    elif get_or_post.lower() == 'post':
        if common.PYSCRIPT:
            return task.executor(connection['session'].post, api_url, data = ivars)
        else:
            return connection['session'].post( api_url, data = ivars)
    raise InspireAPIException("_external_request() requires 'get' or 'post'")
    
def _get_payload(connection, get_or_post, ivars = {}):
    if not connection.get('api_key') or not connection.get('key') or connection.get('session') is None: 
        common.close(connection)
        connect(connection)
    rvars = {
        'apikey': connection['api_key'],
        'key': connection['key'],
        }
    rvars.update(ivars)
    try:
        response = _external_request(connection, get_or_post, rvars)
        response.raise_for_status()
        payload = xmltodict.parse(response.text)
        if not payload or not payload.get('xml'):
            return None, None
        if not payload['xml'].get('status'):
            return payload['xml'], None
        elif payload['xml']['status']:
            return None, payload['xml']['status']
    except requests.RequestException as e:
        return None, e
    return None, None

def connect(connection): # note has to work - exception if it does not
    if not connection.get('api_key') or not connection.get('user_name') or not connection.get('password'): 
        raise common.InspireAPIException("connect() requires 'user_name', 'password' and 'api_key'")
    ivars = {
        'action': 'connect', 
        'apikey': connection['api_key'],
        'username': connection['user_name'],
        'password': connection['password'],
        }
    if connection.get('session') is None:
        connection['session'] = requests.Session()
    response = _external_request(connection, 'post', ivars)
    response.raise_for_status()
    payload = xmltodict.parse(response.text)
    if payload and payload.get('xml'):
        if payload['xml'].get('key'):
            connection['key'] = payload['xml']['key']
            connection['get_payload'] = _get_payload
            return connection
        elif payload['xml'].get('status'):
            raise common.InspireAPIException(common.error_msg('connect', payload['xml']['status']))
    raise common.InspireAPIException(common.error_msg('connect', 'Returned invalid payload: %s' % response.text))

    
if __name__ == "__main__":

    import argparse
    
    parser = argparse.ArgumentParser(description='Status and/or actions for an Inspire Home Automation thermostat',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("-n", "--noprops", help="no thermostat properties are printed out", action='store_true')
    parser.add_argument("-s", "--setpoint", help="change set point for thermostat", type=float)
    parser.add_argument("-f", "--function", help="change function of thermostat", choices=common.FUNCTIONS_LIST)
    #parser.add_argument("-p", "--profile", help="change profile of thermostat", choices=common.PROFILES_LIST)
    args = parser.parse_args()

    with open('secrets.yaml', 'r') as file:
        secrets = yaml.safe_load(file)
    with open('main.yaml', 'r') as file:
        config = yaml.safe_load(file)
    config = config if config else {}
    config.update(secrets)
        
    connection = connect(config)
    
    if not args.noprops:
        common.print_properties(connection)
        
    if args.function:
        result = common.set_device_function(connection, args.function)
        print("Setting function ...", result)
        print('New function:', common.function(connection))
        
    #if args.profile:
    #    result = common.set_device_profile(connection, args.profile)
    #    print("Setting profile ...", result)
    #    print('New profile:', common.profile(connection))
    
    if args.setpoint:
        result = common.set_device_set_point(connection, args.setpoint)
        print("Setting set point ...", result)
        print('New set points:', common.set_points(connection))
        
    common.close(connection)
    
        
  