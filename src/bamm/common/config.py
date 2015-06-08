'''
Created on May 21, 2015

@author: Button
'''

import os
# import sys
import logging

runconfig = 'resources/run.config'
_is_logging_initialized = False

TARGETDIR = 'target'
GRAPHICS_SOURCEDIR = 'source'
EXTRA_GRAPHICS_SOURCEDIR = 'extra_source'
OUTPUTDIR = 'output'
GRAPHICS_OUTPUTDIR = 'save'
TEMPLATEFILE = 'templates'
ASCII_FILE = 'ascii'
GRAPHICS_OVERWRITE_LIST = 'graphics_overwrite'
GRAPHICS_IGNORE_LIST = 'graphics_ignore'
DEBUG = 'verbose'
USERSLOG = 'logfile'
MODDERSLOG = 'modders_log'

IS_DIR = 'dir'
IS_FILE = 'file'
IS_REGEX_LIST = 'list'
IS_BOOL = 'bool'


properties = {
              TARGETDIR: [IS_DIR],
              GRAPHICS_SOURCEDIR: [IS_DIR],
              OUTPUTDIR: [IS_DIR],
              GRAPHICS_OUTPUTDIR: [IS_DIR],
              TEMPLATEFILE: [IS_FILE],
              ASCII_FILE: [IS_FILE],
              GRAPHICS_OVERWRITE_LIST: [IS_REGEX_LIST],
              GRAPHICS_IGNORE_LIST: [IS_REGEX_LIST],
              DEBUG: [IS_BOOL],
              USERSLOG: [IS_FILE],
              MODDERSLOG: [IS_FILE],
              EXTRA_GRAPHICS_SOURCEDIR: [IS_DIR]
              }

userlog = logging.getLogger(USERSLOG)
modderslog = logging.getLogger(MODDERSLOG)


# TODO Allow file to be passed in, or possibly even a dict?
def load_run_config():
    """Load config information from the default file.

    Also initializes loggers if they haven't been already.
    """
    print("Loading run configuration...")
    global runconfig
    runconfig_file = open(runconfig, 'r')
    global properties
    for line in runconfig_file:
        uncommented = line.strip().split('#')[0]
        props = uncommented.strip().split('=')
        if len(props) == 0 or (len(props) == 1 and len(props[0]) == 0):
            continue
        elif len(props) != 2:
            print('Line "', line, '" in ', runconfig,
                  ' is improperly configured. Please format properties thus: \
                  "propertyname=value" (without quotes).')
        elif not _property_has_format_error(props[0], props[1]):
            set_property(props[0], props[1])
        else:
            print ('Line "', line, '" in', runconfig,
                   'is improperly configured. Please format properties thus: \
                   "propertyname=value" (without quotes).')

    runconfig_file.close()

    initialize_logging()
    userlog.info("**********")
    modderslog.info("**********")
    userlog.info("Run configuration loaded.")
    userlog.debug("Properties:")
    for propname in properties.keys():
        userlog.debug("Property %s:", propname)
        for item in properties[propname]:
            userlog.debug("\t%s", item)


# TODO implement parameters with defaults (and update docstring)
def initialize_logging():
    """Initialize loggers config.userlog and config.modderslog

    Will not double-initialize.
    """
    global _is_logging_initialized

    if _is_logging_initialized:
        return
    else:
        _is_logging_initialized = True

    # Logging
    fmt = logging.Formatter('%(message)s')

    userhandler = logging.FileHandler(properties[USERSLOG][1])
    userhandler.setFormatter(fmt)
    userlog.addHandler(userhandler)

    if properties[DEBUG][1]:
        userlog.setLevel(logging.DEBUG)
    else:
        userlog.setLevel(logging.INFO)

    modderhandler = logging.FileHandler(properties[MODDERSLOG][1])
    modderhandler.setFormatter(fmt)
    modderslog.addHandler(modderhandler)
    modderslog.setLevel(logging.INFO)


def _property_has_format_error(propkey, value):
    """Returns True if the property is formatted incorrectly.

    * propkey is the "name" of the property, and is expected to be one of the
    CONFIG.X module variables declared up above.
    * value is the value you wish to check for compatibility with the property
    in question.

    Returns True if:

    * The property key is not recognized
    * The property's type is IS_BOOL and the value is not 'True' or 'False
    * The property's type is IS_DIR and the value is an existing
    (non-directory) file
    * The property's type is IS_FILE and the value is an existing directory.

    Otherwise, returns False.
    """
    return (propkey not in properties.keys() or
            (properties[propkey][0] == IS_DIR and
                os.path.exists(value) and not os.path.isdir(value)) or
            (properties[propkey][0] == IS_FILE and os.path.exists(value) and
                not os.path.isfile(value)) or
            (properties[propkey][0] == IS_BOOL and
                value not in ('True', 'False')))


def set_property(prop_id, value):
    """ Sets property prop_id to value. """
    global properties
    if prop_id not in properties.keys():
        pass
    elif not _property_has_format_error(prop_id, value):
        properties[prop_id] = properties[prop_id][:1]
        if properties[prop_id][0] == IS_REGEX_LIST:
            properties[prop_id].extend(value.split(','))
        elif properties[prop_id][0] == IS_BOOL:
            if value == 'True':
                properties[prop_id].append(True)
            elif value == 'False':
                properties[prop_id].append(False)
        else:
            properties[prop_id].append(value)
