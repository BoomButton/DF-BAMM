'''
Created on May 21, 2015

@author: Button
'''

import os

runconfig = 'resources/run.config'

TARGETDIR = 'target'
GRAPHICS_SOURCEDIR = 'source'
OUTPUTDIR = 'output'
GRAPHICS_OUTPUTDIR = 'save'
TEMPLATEFILE = 'templates'
ASCII_FILE = 'ascii'
GRAPHICS_OVERWRITE_LIST = 'graphics_overwrite'
GRAPHICS_IGNORE_LIST = 'graphics_ignore'
DEBUG = 'verbose'

IS_DIR = 'dir'
IS_FILE = 'file'
IS_REGEX_LIST = 'list'
IS_BOOL = 'bool'

properties = {
              TARGETDIR:[IS_DIR],
              GRAPHICS_SOURCEDIR:[IS_DIR],
              OUTPUTDIR:[IS_DIR],
              GRAPHICS_OUTPUTDIR:[IS_DIR],
              TEMPLATEFILE:[IS_FILE],
              ASCII_FILE:[IS_FILE],
              GRAPHICS_OVERWRITE_LIST:[IS_REGEX_LIST],
              GRAPHICS_IGNORE_LIST:[IS_REGEX_LIST],
              DEBUG:[IS_BOOL]
              }

def load_run_config():
    print("Loading run configuration...")
    global runconfig
    runconfig_file = open(runconfig,'r')
    global properties
    for line in runconfig_file:
        uncommented = line.strip().split('#')[0]
        props = uncommented.strip().split('=')
        if len(props) == 0 or (len(props) == 1 and len(props[0]) == 0):
            continue
        elif len(props) != 2:
            print('Line "',line,'" in ',runconfig,' is improperly configured. Please format properties thus: "propertyname=value" (without quotes).')
        elif not _property_has_format_error(props[0],props[1]):
            if properties[props[0]][0] == IS_REGEX_LIST:
                properties[props[0]].extend(props[1].split(','))
            elif properties[props[0]][0] == IS_BOOL:
                if props[1] == 'True':
                    properties[props[0]].append(True)
                elif props[1] == 'False':
                    properties[props[0]].append(False)
            else:
                properties[props[0]].append(props[1])
        else:
            print ('Line "',line,'" in',runconfig,'is improperly configured. Please format properties thus: "propertyname=value" (without quotes).')

    runconfig_file.close()
    print("Run configuration loaded.")
    
def _property_has_format_error(propkey, value):
    return (propkey not in properties.keys() or 
        (properties[propkey][0] == IS_DIR and not os.path.isdir(value)) or 
        (properties[propkey][0] == IS_FILE and not os.path.isfile(value)) or
        (properties[propkey][0] == IS_BOOL and value not in ('True','False')))
    
def set_property(prop_id, value):
    global properties
    if prop_id not in properties.keys():
        pass
    else:
        pass