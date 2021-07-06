#!/usr/bin/env python3

import sys
import editor
import gi
import DBus_Basic
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib
from dbus.mainloop.glib import DBusGMainLoop

import ccs_function_lib as cfl
import confignator

cfg = confignator.get_config()


def run():
    global cfg

    win = editor.CcsEditor()
    # cfl.start_editor()

    if cfg.has_option('init', 'init_script'):
        init_script = cfg.get('init', 'init_script')
        if init_script != '':
            init_cmd = 'exec(open("{}","r").read())\n'.format(init_script)
            # win.ipython_view.text_buffer.insert_at_cursor(init_cmd, len(init_cmd))
            # win.ipython_view._processLine()
            win.ipython_view.feed_child(init_cmd, len(init_cmd))

    given_cfg = None
    for i in sys.argv:
        if i.endswith('.cfg'):
            given_cfg = i
    if given_cfg:
        cfg = confignator.get_config(file_path=given_cfg)
    else:
        cfg = confignator.get_config(file_path=confignator.get_option('config-files', 'ccs'))
    # pv = TMPoolView(cfg)
    DBusGMainLoop(set_as_default=True)
    if len(sys.argv) > 1:
        for fname in sys.argv[1:]:
            if not fname.startswith('-'):
                win.open_file(fname)
    else:
        win.open_file('getting_started.py')

    Bus_Name = cfg.get('ccs-dbus_names', 'editor')

    DBus_Basic.MessageListener(win, Bus_Name, *sys.argv)


if __name__ == "__main__":

    if '--quickstart' not in sys.argv:
        cfl.ProjectDialog()
        Gtk.main()
    else:
        sys.argv.remove('--quickstart')

    run()
    Gtk.main()
