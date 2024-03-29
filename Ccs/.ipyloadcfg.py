# import pickle
# import struct
import sys
import io
import os
# import gi
import dbus
import dbus.service
import logging
import ccs_function_lib as cfl

sys.path.append(cfl.cfg.get('paths', 'ccs'))

# gi.require_version('Gtk', '3.0')

# import confignator
# cfg = confignator.get_config(check_interpolation=False)

logging.getLogger().setLevel(logging.WARNING)

dbus_type = dbus.SessionBus()


def kwargs(arguments=None):

    if arguments is None:
        arguments = {}

    return dbus.Dictionary({'kwargs': dbus.Dictionary(arguments, signature='sv')})
