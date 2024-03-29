import gi

gi.require_version('Gtk', '3.0')
gi.require_version('GtkSource', '3.0')
gi.require_version('Vte', '2.91')

from gi.repository import Gtk, Gdk, GdkPixbuf, GtkSource, Pango, GLib, Vte, GObject
import time
import numpy as np
import glob
import sys
import socket
import threading
import pickle
import confignator
import os

import dbus
import dbus.service
from dbus.mainloop.glib import DBusGMainLoop
import DBus_Basic

import ccs_function_lib as cfl

sys.path.append(os.path.join(confignator.get_option("paths", "Tst"), "testing_library/testlib"))

cfg = confignator.get_config()

pixmap_folder = cfg.get('ccs-paths', 'pixmap')
action_folder = cfg.get('ccs-paths', 'actions')

VERIFY_EXEC_NO_BP = True


def group_scripts(fname, scrptdict):
    """
    arrange scripts hierarchically

    :param fname:
    :param scrptdict:
    :return:
    """
    p, b = os.path.split(fname)
    if not p:
        if p in scrptdict:
            scrptdict[p].append(fname)
        else:
            scrptdict[p] = [fname]
        return scrptdict
    else:
        pre, *post = p.strip(os.path.sep).split(os.path.sep)
        post = os.path.join(*post, b)
        if pre not in scrptdict:
            scrptdict[pre] = {}
        return group_scripts(post, scrptdict[pre])


def mk_xml(k, xmldict, name, lvl):
    """
    generate UI XML snippet

    :param k:
    :param xmldict:
    :param name:
    :param lvl:
    :return:
    """
    if k == '':
        lis = xmldict[k]
        lis.sort(key=lambda x: (x == '', x.lower()))
        name = name.replace(os.path.sep, '|')
        pfx = lvl * _idt + "<menuitem action='{}' />"
        for x in lis:
            _stxt.append(pfx.format(name + x[:-3]))
            # _smitems.append(name + x[:-3])
    else:
        _stxt.append((lvl) * _idt + "<menu action='ScriptsMenu{}'>".format(name))
        _scr_groups.append(("ScriptsMenu" + name, k))
        sl = list(xmldict[k].keys())
        sl.sort(key=lambda x: (x == '', x.lower()))
        for j in sl:
            mk_xml(j, xmldict[k], name+'|'+j, lvl+1)
        _stxt.append(lvl * _idt + "</menu>")


# generate scripts menu from directory content
scrpath = os.path.join(cfg.get('paths', 'ccs'), "scripts")
scripts = glob.glob(os.path.join(scrpath, "**/*.py"), recursive=True)
scripts = [os.path.relpath(x, scrpath) for x in scripts]

_idt = '  '
_sdata = {}
_stxt = []
_scr_groups = []
for fn in scripts:
    group_scripts(fn, _sdata)

_sl = list(_sdata.keys())
_sl.sort(key=lambda x: (x == '', x.lower()))
for sd in _sl:
    mk_xml(sd, _sdata, sd, 0)
    
script_actions = '\n        '.join(_stxt)

LOG_UPDT_PER = 2000  # ms

UI_INFO = """
<ui>
  <menubar name='MenuBar'>
    <menu action='FileMenu'>
      <menuitem action='FileNew' />
      <separator />
      <menuitem action='FileOpen' />
      <menuitem action='FileSave' />
      <menuitem action='FileSaveAs' />
      <separator />
      <menuitem action='FileQuit' />
    </menu>
    <menu action='EditMenu'>
      <menuitem action='EditUndo' />
      <menuitem action='EditRedo' />
      <separator />
      <menuitem action='EditCut' />
      <menuitem action='EditCopy' />
      <menuitem action='EditPaste' />
      <separator />
      <menuitem action='EditFind' />
      <menuitem action='EditComment' />
      <menuitem action='EditAddBp' />
      <separator />
      <menuitem action='EditPreferences' />
      <menuitem action='EditStyle' />
    </menu>
    <menu action='ModulesMenu'>
      <menuitem action='Poolviewer' />
      <menuitem action='Poolmanager' />
      <menuitem action='Plotter' />
      <menuitem action='Monitor' />
      <menuitem action='TST' />
    </menu>
    <menu action='ToolsMenu'>
      <menuitem action='ActionButtons' />
      <menuitem action='ReconnectSQL' />
      <menuitem action='RestartTerminal' />
      <menuitem action='ClearLog' />
    </menu>
    <menu action='ScriptsMenu'>
        {}    
    </menu>
    <menu action='HelpMenu'>
      <menuitem action='AboutDialog' />
    </menu>
  </menubar>
</ui>
""".format(script_actions)

VTE_VERSION = "{}.{}.{}".format(Vte.MAJOR_VERSION, Vte.MINOR_VERSION, Vte.MICRO_VERSION)


# class SearchDialog(Gtk.Dialog):
#     def __init__(self, parent):
#         Gtk.Dialog.__init__(self, "Search", parent,
#                             Gtk.DialogFlags.MODAL, buttons=(Gtk.STOCK_FIND, Gtk.ResponseType.OK,
#                                                             Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL))
#
#         box = self.get_content_area()
#         box.set_spacing(5)
#         box.set_homogeneous(True)
#
#         label = Gtk.Label("Insert text you want to search for:")
#         box.add(label)
#
#         self.entry = Gtk.Entry()
#         box.add(self.entry)
#
#         self.show_all()


class IPythonTerminal(Vte.Terminal):

    ccs_path = cfg.get('paths', 'ccs')
    ipyloadcfg_path = os.path.join(ccs_path, '.ipyloadcfg.py')
    ipycfg_path = os.path.join(ccs_path, '.ipycfg.py')

    term = ["/usr/bin/env", "ipython3", "--gui=gtk3", "-i", ipyloadcfg_path, "--config", ipycfg_path]

    def __init__(self, scrollback_lines, *args, **kwds):
        super(IPythonTerminal, self).__init__(*args, **kwds)
        self.spawn_async(
            Vte.PtyFlags.DEFAULT,  # Pty Flags
            None,  # Working DIR
            self.term,  # Command/BIN (argv)
            None,  # Environmental Variables (envv)
            GLib.SpawnFlags.DEFAULT,  # Spawn Flags
            None, None,  # Child Setup
            -1,  # Timeout (-1 for indefinitely)
            None,  # Cancellable
            None,  # Callback
            None)  # User Data

    def feed_child_compat(self, msg, msglen=None):
        """
        Wrapper function for feed_child to handle VTE version inconsistencies
        :param msglen:
        :param msg:
        """
        if VTE_VERSION < '0.52.3':
            if msglen is not None:
                return self.feed_child(msg, msglen)
            else:
                return self.feed_child(msg, len(msg))
        else:
            msg_enc = msg.encode('utf-8') if msg is not None else msg
            return self.feed_child(msg_enc)


class CcsEditor(Gtk.Window):

    def __init__(self, given_cfg=None):
        super(CcsEditor, self).__init__(title="CCS Editor")

        # self.set_default_size(1366, 768)  # laptop full screen
        self.set_default_size(1010, 1080)
        # self.set_default_size(1920, 1080) # samsung full screen

        self.cfg = confignator.get_config()
        self.cfg.source = self.cfg.get('config-files', 'ccs')

        # Set up the logger
        self.logger = cfl.start_logging('Editor')
        self.logdir = self.cfg.get('ccs-paths', 'log-file-dir')

        if given_cfg:
            self.logger.warning('{} is ignored! Change the configuration in ccs_main_config.cfg instead!'.format(given_cfg))

        self.paned = Gtk.Paned(orientation=Gtk.Orientation.VERTICAL)
        self.paned.set_wide_handle(True)
        self.add(self.paned)

        self.grid = Gtk.Grid()
        self.grid.connect('key-release-event', self._kill_search)
        self.paned.add1(self.grid)

        menubar = self.create_menus()
        self.grid.attach(menubar, 0, 0, 3, 1)

        toolbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        toolbar = self.create_toolbar()
        toolbox.pack_start(toolbar, 1, 1, 0)
        self.univie_box = self.create_univie_box()
        toolbox.pack_end(self.univie_box, 0, 0, 0)
        self.grid.attach(toolbox, 0, 1, 3, 1)

        self.search_context = None
        self.editor_notebook = Gtk.Notebook()
        self.editor_notebook.set_scrollable(True)
        self.editor_notebook.connect('switch-page', self._set_search_context)

        self.searchbar = self.create_searchbar()
        self.grid.attach(self.searchbar, 0, 2, 3, 1)

        self.sourcemarks = {}
        self.create_mark_attributes()

        self.grid.attach(self.editor_notebook, 0, 3, 3, 1)

        if self.cfg.has_option('ccs-editor', 'color_scheme'):
            self._update_style_schemes(self.cfg.get('ccs-editor', 'color_scheme'))
        else:
            self.style_scheme = None

        self.clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)

        # self.connect('size-allocate', self.paned_check_resize)
        self.paned.set_position(self.get_default_size()[1] * 0.7)

        self.set_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        self.nb = Gtk.Notebook(tab_pos=Gtk.PositionType.RIGHT)

        self.logwin, self.logwintext, self.logbuffer = self.create_log_window()

        self.ipython_view = IPythonTerminal(scrollback_lines=int(self.cfg.get('ccs-editor', 'scrollback_lines')))
        self.feed_ready = True

        self.nb.append_page(self.ipython_view, tab_label=Gtk.Label(label='Console', angle=270))
        self.nb.append_page(self.logwin, tab_label=Gtk.Label(label='Log', angle=270))
        self.paned.add2(self.nb)

        self.log_file = None
        self.log_file_text = None  # save the shown text from the log file tab
        # Update the log-file view window every LOG_UPDT_PER milliseconds
        GLib.timeout_add(LOG_UPDT_PER, self.switch_notebook_page, self.logwin, self.logwintext, self.logbuffer)

        self.ipython_view.connect("size-allocate", self.console_autoscroll, self.ipython_view)

        self.ed_host, self.ed_port = self.cfg.get('ccs-misc', 'editor_host'), int(self.cfg.get('ccs-misc', 'editor_ul_port'))
        try:
            self.setup_editor_socket(self.ed_host, self.ed_port)
        except OSError:
            self.ed_port = np.random.randint(4243, 4342)
            self.setup_editor_socket(self.ed_host, self.ed_port)
            GLib.idle_add(self.process_line_idle, 'print("Standard editor cmd port {} occupied, using {}")'.format(
                int(self.cfg.get('ccs-misc', 'editor_ul_port')), self.ed_port))

        self.connect("delete-event", self.quit_func)
        # self.connect("delete-event", self.tcpserver_shutdown)
        self.connect('key-press-event', self.key_pressed)

        # self._apply_css(cssfile='style.css')
        self.show_all()

    def _apply_css(self, cssfile=None, data=None):
        style_provider = Gtk.CssProvider()
        if data is not None:
            style_provider.load_from_data(data)
        if cssfile is not None:
            style_provider.load_from_path(cssfile)
        Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(),
                                                 style_provider,
                                                 Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    def timeout(self, sec):
        print(self.cfg['ccs-database']['commit_interval'])
        print('PAUSE')
        time.sleep(sec)
        return

    def change_communication(self, application, instance=1, check=True):
        '''
        Changes the main communication of the editor
        @param application: Which application is changed
        @param instance: The instance to which it is changed to
        @param check: Should be checked if they are in same project or not
        @return: -
        '''
        # If it is checked that both run in the same project it is not necessary to do it again
        if check:
            conn = cfl.dbus_connection(application, instance)
            # Both are not in the same project do not change

            if not conn.Variables('main_instance') == self.main_instance:
                # print('Both are not running in the same project, no change possible')
                self.logger.warning('Application {} is not in the same project as {}: Can not communicate'.format(
                    self.my_bus_name, self.cfg['ccs-dbus_names'][application] + str(instance)))
                return

        # Change for terminal
        if int(instance) != int(cfl.communication[application]):
            self._to_console_via_socket("cfl.communication['"+str(application)+"'] = " + str(int(instance)))

        # Local change
        cfl.communication[application] = int(instance)

        return

    def get_communication(self):
        return cfl.communication

    def checking(self):
        self.logger.debug('Hello')

    def connect_to_all(self, My_Bus_Name, Count):
        """
        Function changes the cfl.communication variable (Which app instance to talk to), when the app is started, called
        by DBus_Basic
        @param My_Bus_Name: D-Bus name of the started app
        @param Count: Instance of the app
        @return: -
        """

        # This function exists in every app, but is different here, be careful!

        self.my_bus_name = My_Bus_Name
        # Look if other applications are running in the same project group
        our_con = []
        # Look for all connections starting with com, therefore only one loop over all connections is necessary
        for service in dbus.SessionBus().list_names():
            if service.startswith('com'):
                our_con.append(service)

        # Check if a com connection has the same name as given in cfg file
        for app in our_con:
            if app.split('.')[1] in self.cfg['ccs-dbus_names']:
                # If name is the name of the program skip
                if app == self.my_bus_name:
                    continue

                # Otherwise save the main connections in cfl.communication
                conn_name = app.split('.')[1]

                conn = cfl.dbus_connection(conn_name, app[-1])
                if conn.Variables('main_instance') == self.main_instance:
                    # cfl.communication = conn.Functions('get_communication')
                    new_com = conn.Functions('get_communication')
                    cfl.communication[conn_name] = int(new_com[conn_name])
                    conn_com = conn.Functions('get_communication')
                    if conn_com[self.my_bus_name.split('.')[1]] == 0:
                        conn.Functions('change_communication', self.my_bus_name.split('.')[1], self.my_bus_name[-1], False)
                        # conn.Functions('change_communication', self.my_bus_name.split('.')[1], app[-1], False)

        if not cfl.communication[self.my_bus_name.split('.')[1]]:
            cfl.communication[self.my_bus_name.split('.')[1]] = int(self.my_bus_name[-1])

        self._to_console_via_socket("cfl.communication = " + str(cfl.communication))

        # Connect to the Terminal if another editor exists
        if Count == 1:
            self._to_console_via_socket(
                "editor = dbus.SessionBus().get_object('" + str(My_Bus_Name) + "', '/MessageListener')")

        else:
            for service in dbus.SessionBus().list_names():
                if service.startswith(self.cfg['ccs-dbus_names']['editor']):
                    if service == self.my_bus_name:
                        self._to_console_via_socket("editor" + str(Count) + " = dbus.SessionBus().get_object('" +
                                                    str(My_Bus_Name) + "', '/MessageListener')")
                    else:
                        editor = cfl.dbus_connection('editor', service[-1])
                        editor.Functions('_to_console_via_socket', "editor" + str(Count) +
                                         " = dbus.SessionBus().get_object('" + str(My_Bus_Name) +
                                         "', '/MessageListener')")

        # Connect to all running applications for terminal
        our_con = []
        # Search for all applications
        for service in dbus.SessionBus().list_names():
            if service.startswith('com'):
                our_con.append(service)

        for service in our_con:
            # Connect to all Poolmanagers
            if service.startswith(self.cfg['ccs-dbus_names']['poolmanager']):
                con = cfl.dbus_connection('poolmanager', service[-1])
                if con.Variables('main_instance') == self.main_instance:
                    if service[-1] == str(1):
                        self._to_console_via_socket("pmgr = dbus.SessionBus().get_object('" +
                                                    str(service) + "', '/MessageListener')")
                    else:
                        self._to_console_via_socket("pmgr" + str(service[-1]) + " = dbus.SessionBus().get_object('" +
                                                    str(service) + "', '/MessageListener')")
            # Connect to all Poolviewers
            if service.startswith(self.cfg['ccs-dbus_names']['poolviewer']):
                con = cfl.dbus_connection('poolviewer', service[-1])
                if con.Variables('main_instance') == self.main_instance:
                    if service[-1] == str(1):
                        self._to_console_via_socket("pv = dbus.SessionBus().get_object('" +
                                                    str(service) + "', '/MessageListener')")
                    else:
                        self._to_console_via_socket("pv" + str(service[-1]) + " = dbus.SessionBus().get_object('" +
                                                    str(service) + "', '/MessageListener')")
            # Connect to all Plotters
            if service.startswith(self.cfg['ccs-dbus_names']['plotter']):
                con = cfl.dbus_connection('plotter', service[-1])
                if con.Variables('main_instance') == self.main_instance:
                    if service[-1] == str(1):
                        self._to_console_via_socket("paramplot = dbus.SessionBus().get_object('" +
                                                    str(service) + "', '/MessageListener')")
                    else:
                        self._to_console_via_socket("paramplot" + str(service[-1]) + " = dbus.SessionBus().get_object('"
                                                    + str(service) + "', '/MessageListener')")
            # Connect to all Monitors
            if service.startswith(self.cfg['ccs-dbus_names']['monitor']):
                con = cfl.dbus_connection('monitor', service[-1])
                if con.Variables('main_instance') == self.main_instance:
                    if service[-1] == str(1):
                        self._to_console_via_socket("monitor = dbus.SessionBus().get_object('" +
                                                    str(service) + "', '/MessageListener')")
                    else:
                        self._to_console_via_socket("monitor" + str(service[-1]) + " = dbus.SessionBus().get_object('" +
                                                    str(service) + "', '/MessageListener')")
            # Connect to all remaining editors
            if service.startswith(self.cfg['ccs-dbus_names']['editor']):
                if not service == My_Bus_Name:
                    con = cfl.dbus_connection('editor', service[-1])
                    if con.Variables('main_instance') == self.main_instance:
                        if service[-1] == str(1):
                            self._to_console_via_socket("editor = dbus.SessionBus().get_object('" +
                                                        str(service) + "', '/MessageListener')")
                        else:
                            self._to_console_via_socket("editor" + str(service[-1]) +
                                                        " = dbus.SessionBus().get_object('" + str(service) +
                                                        "', '/MessageListener')")

    def restart_terminal(self):

        # Kill the IPython Console
        self.ipython_view.destroy()
        self.ipython_view = None

        # Ćlose the socket connection
        self.is_editor_socket_active = False

        # Just send some unncessary command to get the terminal worker out of his loop, and that it closes the thread and the socket connection
        self._to_console_via_socket('"Restart Terminal"')

        # Open a new IPython Terminal and connect it to a new socket
        self.ipython_view = IPythonTerminal(scrollback_lines=int(self.cfg.get('ccs-editor', 'scrollback_lines')))
        self.nb.insert_page(self.ipython_view, tab_label=Gtk.Label('Console', angle=270), position=0)

        self.ipython_view.connect("size-allocate", self.console_autoscroll, self.ipython_view)

        self.ed_host, self.ed_port = self.cfg.get('ccs-misc', 'editor_host'), int(self.cfg.get('ccs-misc', 'editor_ul_port'))  # Get standard port

        # Connect to standard port if possible otherwise use a random alternative
        try:
            self.setup_editor_socket(self.ed_host, self.ed_port)
        except OSError:
            self.ed_port = np.random.randint(4243, 4342)
            self.setup_editor_socket(self.ed_host, self.ed_port)
            GLib.idle_add(self.process_line_idle, 'print("Standard editor cmd port {} occupied, using {}")'.format(
                int(self.cfg.get('ccs-misc', 'editor_ul_port')), self.ed_port))

        self.show_all() # Show the changes
        self.connect_to_all(self.my_bus_name, 1)  # Connect to editor

        self.nb.set_current_page(0) # Switch to Terminal tab

        self.logger.info('Terminal was restarted')
        return

    def tcpserver_shutdown(self, widget=None, event=None):
        self.tcpserver.shutdown()

    def key_pressed(self, widget=None, event=None):
        if event.state & Gdk.ModifierType.CONTROL_MASK == Gdk.ModifierType.CONTROL_MASK:
            print(event.keyval, event.hardware_keycode)
            if event.keyval == 101:
                self.on_button_nextline()
            elif event.keyval == 114:
                self.on_button_sameline()

    def _share_variables(self, **kwargs):
        """Store variables in file to share them with IPython shell"""
        # data = {}
        # for arg in args:
        #     raw = pickle.dumps(arg)
        #     rawlen = struct.pack('>H', len(raw))
        #     data.append(rawlen+raw)
        # stream = b''.join(data)
        with open('.sharedvariables.bin', 'wb') as fdesc:
            try:
                pickle.dump(kwargs, fdesc)
            except:
                self.logger.warning('Failed to create a file for the shared variables for iPython console')
            finally:
                fdesc.close()

    def ipy_commit(self, term, text, b):
        print(text, [ord(x) for x in text])
        if ord(text[0]) == 27:
        # if text[1:] in ('[13;1R', '[15;1R'):
            self.feed_ready = True

    def quit_func(self, widget=None, data=None):
        if self._check_unsaved_buffers():
            self.is_editor_socket_active = False

            for service in dbus.SessionBus().list_names():
                if service.startswith(self.cfg['ccs-dbus_names']['editor']):
                    if service != self.my_bus_name:
                        editor = cfl.dbus_connection(service[0:-1].split('.')[1], service[-1])
                        if self.main_instance == editor.Variables('main_instance'):
                            nr = self.my_bus_name[-1]
                            if nr == str(1):
                                nr = ''
                            editor.Functions('_to_console_via_socket', 'del(editor' + str(nr) + ')')

            self.update_all_connections_quit()
            Gtk.main_quit()
            return False
        else:
            return True

    def update_all_connections_quit(self):
        '''
        Tells all running applications that it is not longer availabe and suggests another main communicatior if one is
        available
        :return:
        '''
        our_con = [] # All connections to running applications without communicions form the same applications as this
        my_con = [] # All connections to same applications as this
        for service in dbus.SessionBus().list_names():
            if service.split('.')[1] in self.cfg['ccs-dbus_names']:   # Check if connection belongs to CCS
                if service == self.my_bus_name:     #If own allplication do nothing
                    continue
                conn = cfl.dbus_connection(service.split('.')[1], service[-1])
                if conn.Variables('main_instance') == self.main_instance:   #Check if running in same project
                    if service.startswith(self.my_bus_name[:-1]):   #Check if it is same application type
                        my_con.append(service)
                    else:
                        our_con.append(service)

        instance = my_con[0][-1] if my_con else 0   # Select new main application if possible, is randomly selected
        our_con = our_con + my_con  # Add the instances of same application to change the main communication as well
        for service in our_con:     # Change the main communication for all applications+
            conn = cfl.dbus_connection(service.split('.')[1], service[-1])
            comm = conn.Functions('get_communication')
            # Check if this application is the main applications otherwise do nothing
            if str(comm[self.my_bus_name.split('.')[1]]) == self.my_bus_name[-1]:
                conn.Functions('change_communication', self.my_bus_name.split('.')[1], instance, False)
        return

    def paned_check_resize(self, widget, data=None):
        """ Resize python panel to be 70% of window hight on a size-allocate event,
        e.g. when the window is first drawn or resized by the user.
        This allows us to easily set up the initial height but also allows
        to resize the pane while the window size remains unchanged
        """
        height = self.paned.get_allocation().height
        self.paned.set_position(height * 0.7)

    def console_autoscroll(self, widget, allocation, data):
        adj = data.get_vadjustment()
        adj.set_value(adj.get_upper() - adj.get_page_size())

    def setup_editor_socket(self, host, port):
        self.is_editor_socket_active = True
        self.sock_csl = socket.socket()
        self.sock_csl.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock_csl.bind((host, port))
        self.sock_csl.listen()
        self.sock_thread = threading.Thread(target=self.console_sock_worker, args=[self.sock_csl])
        self.sock_thread.daemon = True
        self.sock_thread.start()

    def console_sock_worker(self, sock_csl):
        while self.is_editor_socket_active:
            self.console_sock, addr = sock_csl.accept()
            line = self.console_sock.recv(2**16).decode()
            GLib.idle_add(self.process_line_idle, line)
            self.console_sock.sendall(b'ACK ' + line.encode()[:60])
            self.console_sock.close()
        sock_csl.close()

    def process_line_idle(self, line):
        if not line.endswith('\n'):
            line += '\n'
        if line.count('\n') > 2:
            self.ipython_view.feed_child_compat('%cpaste\n')
            time.sleep(0.2)  # wait for interpreter to return before feeding new code
            self.ipython_view.feed_child_compat(line)
            self.ipython_view.feed_child_compat('--\n')
        else:
            self.ipython_view.feed_child_compat(line)

    def create_mark_attributes(self):
        self.mark_play = GtkSource.MarkAttributes()
        pixmap_path = os.path.join(pixmap_folder, 'media-playback-start-symbolic_uvie.svg')
        icon = GdkPixbuf.Pixbuf.new_from_file(pixmap_path)
        self.mark_play.set_pixbuf(icon)
        # self.mark_play.set_icon_name("media-playback-start-symbolic")

        self.mark_break = GtkSource.MarkAttributes()
        pixmap_path = os.path.join(pixmap_folder, 'process-stop-symbolic_uvie.svg')
        icon = GdkPixbuf.Pixbuf.new_from_file(pixmap_path)
        self.mark_break.set_pixbuf(icon)
        # self.mark_break.set_icon_name("process-stop-symbolic")

        # self.tag_found = self.textbuffer.create_tag("found", background="yellow", foreground = "black")

    def create_menus(self):
        action_group = Gtk.ActionGroup(name="action_group")
        self.create_file_menu(action_group)
        self.create_edit_menu(action_group)
        # self.create_pool_menu(action_group)
        self.create_modules_menu(action_group)
        self.create_tools_menu(action_group)
        self.create_scripts_menu(action_group)
        self.create_help_menu(action_group)

        uimanager = Gtk.UIManager()
        uimanager.add_ui_from_string(UI_INFO)
        accelgroup = uimanager.get_accel_group()
        self.add_accel_group(accelgroup)

        uimanager.insert_action_group(action_group)
        menubar = uimanager.get_widget("/MenuBar")

        return menubar

    def create_file_menu(self, action_group):
        action = Gtk.Action(name="FileMenu", label="_File", tooltip=None, stock_id=None)
        action_group.add_action(action)

        action = Gtk.Action(name="FileNew", label="_New", tooltip=None, stock_id=Gtk.STOCK_NEW)
        action.connect("activate", self._on_menu_file_new)
        action_group.add_action_with_accel(action, "<control>N")

        action = Gtk.Action(name="FileOpen", label="_Open", tooltip=None, stock_id=Gtk.STOCK_OPEN)
        action.connect("activate", self.on_menu_file_open)
        action_group.add_action_with_accel(action, "<control>O")

        action = Gtk.Action(name="FileSave", label="_Save", tooltip=None, stock_id=Gtk.STOCK_SAVE)
        action.connect("activate", self.on_menu_file_save)
        action_group.add_action_with_accel(action, "<control>S")

        action = Gtk.Action(name="FileSaveAs", label="_Save As", tooltip=None, stock_id=Gtk.STOCK_SAVE_AS)
        action.connect("activate", self.on_menu_file_saveas)
        action_group.add_action_with_accel(action, "<control><shift>S")
        action_group.add_action(action)

        action = Gtk.Action(name="FileQuit", label="_Quit", tooltip=None, stock_id=Gtk.STOCK_QUIT)
        action.connect("activate", self.on_menu_file_quit)
        action_group.add_action_with_accel(action, "<control>Q")

    def create_edit_menu(self, action_group):
        action = Gtk.Action(name="EditMenu", label="_Edit", tooltip=None, stock_id=None)
        action_group.add_action(action)

        action = Gtk.Action(name="EditUndo", label="_Undo", tooltip=None, stock_id=Gtk.STOCK_UNDO)
        action.connect("activate", self._on_undo)
        action_group.add_action_with_accel(action, "<control>Z")

        action = Gtk.Action(name="EditRedo", label="Red_o", tooltip=None, stock_id=Gtk.STOCK_REDO)
        action.connect("activate", self._on_redo)
        action_group.add_action_with_accel(action, "<control>Y")

        action = Gtk.Action(name="EditCut", label="Cu_t", tooltip=None, stock_id=Gtk.STOCK_CUT)
        action.connect("activate", self._on_cut)
        action_group.add_action_with_accel(action, "<control>X")

        action = Gtk.Action(name="EditCopy", label="_Copy", tooltip=None, stock_id=Gtk.STOCK_COPY)
        action.connect("activate", self._on_copy)
        action_group.add_action_with_accel(action, "<control>C")

        action = Gtk.Action(name="EditPaste", label="_Paste", tooltip=None, stock_id=Gtk.STOCK_PASTE)
        action.connect("activate", self._on_paste)
        action_group.add_action_with_accel(action, "<control>V")

        action = Gtk.Action(name="EditFind", label="_Find", tooltip=None, stock_id=Gtk.STOCK_FIND)
        action.connect("activate", self.on_search_clicked)
        action_group.add_action_with_accel(action, "<control>F")

        action = Gtk.Action(name="EditComment", label="Comment Lines", tooltip=None)
        action.connect("activate", self._on_comment_lines)
        action_group.add_action_with_accel(action, "<control>T")

        action = Gtk.Action(name="EditAddBp", label="Add Breakpoint", tooltip=None)
        action.connect("activate", self._on_add_breakpoint)
        action_group.add_action_with_accel(action, "<control>B")

        action = Gtk.Action(name="EditPreferences", label="Preferences", tooltip=None, stock_id=Gtk.STOCK_PREFERENCES)
        action.connect("activate", cfl.start_config_editor)
        action_group.add_action(action)

        action = Gtk.Action(name="EditStyle", label="Set Editor Style", tooltip=None)
        action.connect("activate", self._on_set_style)
        action_group.add_action(action)

    def create_modules_menu(self, action_group):
        action = Gtk.Action(name="ModulesMenu", label="_Modules", tooltip=None, stock_id=None)
        action_group.add_action(action)

        action = Gtk.Action(name="Poolviewer", label="_Poolviewer", tooltip=None, stock_id=None)
        action.connect("activate", self._on_start_poolviewer)
        action_group.add_action(action)

        action = Gtk.Action(name="Poolmanager", label="_Poolmanager", tooltip=None, stock_id=None)
        action.connect("activate", self._on_start_poolmanager)
        action_group.add_action(action)

        action = Gtk.Action(name="Plotter", label="_Plotter", tooltip=None, stock_id=None)
        action.connect("activate", self._on_start_plotter)
        action_group.add_action(action)

        action = Gtk.Action(name="Monitor", label="_Monitor", tooltip=None, stock_id=None)
        action.connect("activate", self._on_start_monitor)
        action_group.add_action(action)

        action = Gtk.Action(name="TST", label="_Test Specification Tool", tooltip=None, stock_id=None)
        action.connect("activate", self._on_start_tst)
        action_group.add_action(action)

    def create_tools_menu(self, action_group):
        action = Gtk.Action(name="ToolsMenu", label="_Tools", tooltip=None, stock_id=None)
        action_group.add_action(action)

        action = Gtk.Action(name="ActionButtons", label="_Action Buttons Window", tooltip=None, stock_id=None)
        action.connect("activate", self._on_show_action_window)
        action_group.add_action(action)

        action = Gtk.Action(name="ReconnectSQL", label="_Reconnect SQL",
                            tooltip="Reconnect, in case 'SQL server has gone away'", stock_id=None)
        action.connect("activate", self._on_reconnect_sql)
        action_group.add_action(action)

        action = Gtk.Action(name="RestartTerminal", label="_Restart Terminal", tooltip=None, stock_id=None)
        action.connect("activate", self._on_restart_terminal)
        action_group.add_action(action)

        action = Gtk.Action(name="ClearLog", label="_Clear Log", tooltip=None, stock_id=None)
        action.connect("activate", self._on_clear_log)
        action_group.add_action(action)

    def create_scripts_menu(self, action_group):
        action = Gtk.Action(name="ScriptsMenu", label="_Scripts", tooltip=None, stock_id=None)
        action_group.add_action(action)

        for grp in _scr_groups:
            action = Gtk.Action(name=grp[0], label="_{}".format(grp[1]), tooltip=None, stock_id=None)
            action_group.add_action(action)

        for script in scripts:
            handle = script.replace(os.path.sep, '|')[:-3]
            name = os.path.basename(script)
            action = Gtk.Action(name=handle, label="_{}".format(name.replace('_', '__')), tooltip=None, stock_id=None)
            action.connect("activate", self._on_open_script, os.path.join(scrpath, script))
            action_group.add_action(action)

    def create_help_menu(self, action_group):
        action = Gtk.Action(name="HelpMenu", label="_Help", tooltip=None, stock_id=None)
        action_group.add_action(action)

        action = Gtk.Action(name="AboutDialog", label="_About", tooltip=None, stock_id=Gtk.STOCK_ABOUT)
        action.connect("activate", self._on_select_about_dialog)
        action_group.add_action(action)

    def _on_undo(self, action):
        buf = self._get_active_view().get_buffer()
        if buf.can_undo():
            buf.undo()

    def _on_redo(self, action):
        buf = self._get_active_view().get_buffer()
        if buf.can_redo():
            buf.redo()

    def _on_cut(self, action):
        buf = self._get_active_view().get_buffer()
        buf.cut_clipboard(self.clipboard, True)

    def _on_copy(self, action):
        buf = self._get_active_view().get_buffer()
        buf.copy_clipboard(self.clipboard)

    def _on_paste(self, action):
        buf = self._get_active_view().get_buffer()
        buf.paste_clipboard(self.clipboard, None, True)

    def _on_menu_file_new(self, widget=None, filename=None):
        self.notebook_open_tab()

    def _on_comment_lines(self, widget=None):
        view = self._get_active_view()
        textbuffer = view.get_buffer()

        hs = textbuffer.get_has_selection()

        if hs:
            x, y = textbuffer.get_selection_bounds()

            # remember selected part for re-selection at the end
            ix = x.get_offset()
            iyl, iyo = y.get_line(), y.get_line_offset()

            x.set_line_offset(0)
            tt = x.get_text(y)
            lnlist = tt.split('\n')
            if all([ln.startswith('#') for ln in lnlist]):
                newbuf = []
                for ln in lnlist:
                    newbuf.append(ln[1:])
                tr = '\n'.join(newbuf)
                ix -= 1
                iyo -= 1
            else:
                tr = '#' + tt.replace('\n', '\n#')
                ix += 1
                iyo += 1

        else:
            x = textbuffer.get_iter_at_mark(textbuffer.get_insert())
            x.set_line_offset(0)
            y = x.copy()
            y.forward_to_line_end()
            tt = x.get_text(y)

            if tt.startswith('#'):
                tr = tt[1:]
            else:
                tr = '#' + tt

        textbuffer.delete(x, y)
        textbuffer.insert(x, tr, len(tr))

        if hs:
            x = textbuffer.get_iter_at_offset(ix)
            y = textbuffer.get_iter_at_line_offset(iyl, iyo)
            textbuffer.select_range(x, y)

    def _on_add_breakpoint(self, widget=None):
        view = self._get_active_view()
        textbuffer = view.get_buffer()

        x = textbuffer.get_iter_at_mark(textbuffer.get_insert())
        x.set_line_offset(0)
        y = x.copy()
        y.forward_to_line_end()
        tt = x.get_text(y)

        bpcode = '#! CCS.BREAKPOINT'
        if not tt.startswith('\n'):
            bpcode += '\n'

        linenr = x.get_line()
        textbuffer.insert(x, bpcode, len(bpcode))
        textbuffer.create_source_mark(str(linenr), 'break', textbuffer.get_iter_at_line(linenr))

    def _on_start_poolviewer(self, action):
        cfl.start_pv()

    def _on_start_poolmanager(self, action):
        cfl.start_pmgr()

    def _on_start_plotter(self, action):
        cfl.start_plotter()

    def _on_start_monitor(self, action):
        cfl.start_monitor()

    def _on_start_tst(self, action):
        cfl.start_tst()

    def _on_open_poolmanager_gui(self, action):
        cfl.start_pmgr()

    def _on_show_action_window(self, action):
        if hasattr(self, 'action_button_window'):
            if self.action_button_window.get_property('visible'):
                self.action_button_window.present()
                return
        self.action_button_window = ActionWindow(self)

    def _on_reconnect_sql(self, action):
        self._to_console('cfl.scoped_session_idb.close()')

    def _on_restart_terminal(self, action):
        self.restart_terminal()

    def _on_open_script(self, action, filename):
        if os.path.isfile(filename):
            self.open_file(filename)
            self.logger.debug('Opened script ' + filename)
        else:
            self.logger.error('Could not open script {}'.format(filename))

    def _on_select_about_dialog(self, action):
        cfl.about_dialog(self)

    def _get_active_view(self):
        nbpage = self.editor_notebook.get_current_page()
        scrolled_window = self.editor_notebook.get_nth_page(nbpage)

        if scrolled_window is None:
            return

        view = scrolled_window.get_child()
        return view

    def notebook_open_tab(self, filename=None):

        label = Gtk.Label()

        if filename is None:
            label.set_text('*New')
        else:
            label.set_text(filename.split('/')[-1])
            label.set_tooltip_text(filename)

        img = Gtk.Image.new_from_icon_name('window-close-symbolic', Gtk.IconSize.MENU)

        button = Gtk.Button()
        button.set_image(img)
        button.set_relief(Gtk.ReliefStyle.NONE)

        hbox = Gtk.HBox()
        hbox.pack_start(label, False, False, 0)
        hbox.pack_start(button, False, False, 0)

        sourceview = self.create_textview(filename)
        self.editor_notebook.append_page(sourceview, hbox)
        self.editor_notebook.set_tab_reorderable(sourceview, True)

        button.connect("clicked", self._notebook_close_tab, sourceview)

        page_num = self.editor_notebook.get_current_page()
        nb_page = self.editor_notebook.get_nth_page(page_num)
        buf = nb_page.get_child().get_buffer()
        if filename is None:
            buf.connect('changed', self._notebook_buffer_modified, None, label)

        hbox.show_all()
        self.editor_notebook.show_all()
        self.editor_notebook.set_current_page(-1)

        view = self._get_active_view()
        begin = buf.get_iter_at_line(0)
        self._set_play_mark(view, begin)

        return sourceview

    def _notebook_close_tab(self, widget, data=None):
        page_num = self.editor_notebook.page_num(data)
        label = self.editor_notebook.get_tab_label(data).get_children()[0]
        label.page_num = page_num
        label_text = label.get_text()
        if label_text[0] == '*':
            ask = UnsavedBufferDialog(parent=self)
            response = ask.run()
            if response == Gtk.ResponseType.YES:
                self.on_menu_file_save(label=label)
            elif response == Gtk.ResponseType.CANCEL:
                ask.destroy()
                return

            ask.destroy()
        self.editor_notebook.remove_page(page_num)

        if page_num in self.sourcemarks:
            self.sourcemarks.pop(page_num)

    """ mark buffer as modified and disconnect this signal """

    def _notebook_buffer_modified(self, widget, unused, label):
        text = label.get_text()
        if text[0] != '*':
            label.set_text('*' + label.get_text())
        widget.disconnect_by_func(self._notebook_buffer_modified)

    def _check_unsaved_buffers(self):
        for page in self.editor_notebook:
            label = self.editor_notebook.get_tab_label(page).get_children()[0]
            save_as = False
            if label.get_text()[0] == '*':
                ask = UnsavedBufferDialog(parent=self, msg='Unsaved changes in {}. Save?'.format(label.get_text()[1:]))
                response = ask.run()

                if response == Gtk.ResponseType.YES:
                    buf = page.get_child().get_buffer()
                    text = buf.get_text(*buf.get_bounds(), True)
                    if label.get_tooltip_text():
                        with open(label.get_tooltip_text(), 'w') as fdesc:
                            fdesc.write(text)
                    else:
                        save_as = True
                elif response == Gtk.ResponseType.CANCEL:
                    ask.destroy()
                    return False

                ask.destroy()
                if save_as:
                    self.on_menu_file_saveas(label=label)

        return True

    """ save the buffer and reconnect the "changed" signal signal """

    def _notebook_save_helper(self, filename, label=None):
        if label is None or (not hasattr(label, 'page_num')):
            page_num = self.editor_notebook.get_current_page()
        else:
            page_num = label.page_num
        nb_page = self.editor_notebook.get_nth_page(page_num)

        buf = nb_page.get_child().get_buffer()
        start, end = buf.get_bounds()
        text = buf.get_text(start, end, True)

        if label is None:
            label = self._notebookt_current_get_label()
        label.set_text(label.get_text().strip('*'))
        buf.connect('changed', self._notebook_buffer_modified, None, label)

        with open(filename, 'w') as fdesc:
            fdesc.write(text)
            fdesc.close()

    """
    It would be nicer to extract the child by type rather than explicitly by its
    position, but this will do just fine for now. Also, encoding the full path
    in the label tooltip is a rather cheap trick...
    """

    def _notebookt_current_get_label(self):
        page_num = self.editor_notebook.get_current_page()
        nb_page = self.editor_notebook.get_nth_page(page_num)
        nb_label = self.editor_notebook.get_tab_label(nb_page)

        return nb_label.get_children()[0]

    def on_menu_file_save(self, widget=None, label=None):
        if label is None:
            label = self._notebookt_current_get_label()
        filename = label.get_tooltip_text()

        if filename is None:
            self.on_menu_file_saveas(label=None)
            return

        self._notebook_save_helper(filename, label=label)

    def on_menu_file_saveas(self, widget=None, label=None):
        dialog = Gtk.FileChooserDialog(title="Save file as", parent=None,
                                       action=Gtk.FileChooserAction.SAVE)
        dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                           Gtk.STOCK_SAVE, Gtk.ResponseType.OK)

        self.add_file_dialog_filters(dialog)

        dialog.set_transient_for(self)

        response = dialog.run()

        if response == Gtk.ResponseType.OK:
            filename = dialog.get_filename()
            self._notebook_save_helper(filename, label=label)
            if label is None:
                label = self._notebookt_current_get_label()
                label.set_text(filename.split('/')[-1])
                label.set_tooltip_text(filename)

        dialog.destroy()

    def on_menu_file_open(self, widget=None):
        dialog = Gtk.FileChooserDialog(title="Open", parent=None, action=Gtk.FileChooserAction.OPEN, select_multiple=True)
        dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK)
        self.add_file_dialog_filters(dialog)

        dialog.set_transient_for(self)

        response = dialog.run()

        if response == Gtk.ResponseType.OK:
            filenames = dialog.get_filenames()
            for filename in filenames:
                if os.path.isfile(filename):
                    self.open_file(filename)
                    self.logger.debug('Opened file: ' + filename)

        dialog.destroy()

    def add_file_dialog_filters(self, dialog):
        filter_py = Gtk.FileFilter()
        filter_py.set_name("Python Files")
        filter_py.add_mime_type("text/x-python")
        dialog.add_filter(filter_py)

        filter_any = Gtk.FileFilter()
        filter_any.set_name("All Files")
        filter_any.add_pattern("*")
        dialog.add_filter(filter_any)

    def on_menu_file_quit(self, widget):
        self.quit_func()
        # Gtk.main_quit()

    def create_toolbar(self):
        toolbar = Gtk.Toolbar()

        button_run_nextline = Gtk.ToolButton()
        # button_run_nextline.set_icon_name("media-playback-start-symbolic")

        pixmap_path = os.path.join(pixmap_folder, 'media-playback-start-symbolic_uvie.svg')
        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(pixmap_path, 24, 24)
        icon = Gtk.Image.new_from_pixbuf(pixbuf)
        button_run_nextline.set_icon_widget(icon)
        button_run_nextline.set_tooltip_text('Run Line')
        button_run_nextline.connect("clicked", self.on_button_nextline)
        toolbar.add(button_run_nextline)
        self.button_run_nextline = button_run_nextline

        button_run_sameline = Gtk.ToolButton()
        # button_run_nextline.set_icon_name("media-playback-start-symbolic")
        pixmap_path = os.path.join(pixmap_folder, 'media-playback-start-symbolic-down_uvie.svg')
        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(pixmap_path, 24, 24)
        icon = Gtk.Image.new_from_pixbuf(pixbuf)
        button_run_sameline.set_icon_widget(icon)
        button_run_sameline.set_tooltip_text('Run Line (remain in line)')
        button_run_sameline.connect("clicked", self.on_button_sameline)
        toolbar.add(button_run_sameline)

        button_run_all = Gtk.ToolButton()
        # button_run_all.set_icon_name("media-seek-forward-symbolic")
        pixmap_path = os.path.join(pixmap_folder, 'media-skip-forward-symbolic_uvie.svg')
        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(pixmap_path, 24, 24)
        icon = Gtk.Image.new_from_pixbuf(pixbuf)
        button_run_all.set_icon_widget(icon)
        button_run_all.set_tooltip_text('Run All')
        button_run_all.connect("clicked", self.on_button_run_block)
        toolbar.add(button_run_all)

        button_run_all_nobreak = Gtk.ToolButton()
        # button_run_all.set_icon_name("media-seek-forward-symbolic")
        pixmap_path = os.path.join(pixmap_folder, 'media-seek-forward-symbolic_uvie.svg')
        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(pixmap_path, 24, 24)
        icon = Gtk.Image.new_from_pixbuf(pixbuf)
        button_run_all_nobreak.set_icon_widget(icon)
        button_run_all_nobreak.set_tooltip_text('Run All (ignore breakmarks)')
        button_run_all_nobreak.connect("clicked", self.on_button_run_all_nobreak)
        toolbar.add(button_run_all_nobreak)

        toolbar.add(Gtk.SeparatorToolItem())

        button_search = Gtk.ToolButton()
        button_search.set_icon_name("system-search-symbolic")
        button_search.connect("clicked", self.on_search_clicked)
        toolbar.add(button_search)

        toolbar.add(Gtk.SeparatorToolItem())

        targets = Gtk.TargetList.new([])
        targets.add_text_targets(0)

        self.create_action_buttons(toolbar, targets)

        # button_reload_config = Gtk.ToolButton()
        # button_reload_config.set_icon_name("stock_refresh")
        # button_reload_config.set_tooltip_text('Reload action configuration file')
        # button_reload_config.connect("clicked", self.reload_config)
        # toolbar.add(button_reload_config)

        return toolbar

    def create_action_buttons(self, toolbar, targets, nbutt=10):
        for n in range(nbutt):
            button_action = Gtk.ToolButton()

            # button_img_path = os.path.join(pixmap_folder, self.cfg.get('ccs-actions', 'action{}_img'.format(n + 1)))
            # try:
            #     pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(button_img_path, 36, 36)
            # except:
            #     self.logger.warning('Could not load image {}'.format(button_img_path))
            #     pixmap_path = os.path.join(pixmap_folder, 'action.png')
            #     pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(pixmap_path, 36, 36)
            # icon = Gtk.Image.new_from_pixbuf(pixbuf)
            icon = self._get_toolbutton_icon(self.cfg.get('ccs-actions', 'action{}_img'.format(n + 1)))
            button_action.set_icon_widget(icon)
            button_action.set_name('action{}'.format(n + 1))
            button_action.set_tooltip_text(os.path.join(action_folder, self.cfg.get('ccs-actions', 'action{}'.format(n + 1))))
            button_action.connect("clicked", self.on_button_action)
            button_action.connect('button-press-event', self.show_action_context)
            button_action.drag_dest_set(Gtk.DestDefaults.ALL, [], Gdk.DragAction.COPY)
            button_action.connect("drag-data-received", self.on_drag_data_received)
            toolbar.add(button_action)
            button_action.drag_dest_set_target_list(targets)

    def on_drag_data_received(self, widget, drag_context, x, y, data, info, time):
        text = data.get_text()

        filename = os.path.join(action_folder, widget.get_name() + '.py')
        with open(filename, 'w') as fdesc:
            fdesc.write(text)

        self.cfg.save_option_to_file('ccs-actions', widget.get_name(), widget.get_name() + '.py')

        widget.set_tooltip_text(filename)

    def action_context_menu(self, action_button):
        action = action_button.get_name()
        menu = Gtk.Menu()

        item = Gtk.MenuItem(label='Open action script file')
        item.connect('activate', self.show_action_script, action)
        menu.append(item)
        item1 = Gtk.MenuItem(label='Set action script file')
        item1.connect('activate', self._set_action_button_script, action_button)
        menu.append(item1)
        item2 = Gtk.MenuItem(label='Set button icon')
        item2.connect('activate', self._set_action_button_icon, action_button)
        menu.append(item2)
        return menu

    def show_action_context(self, widget, event):
        if event.button != 3:
            return
        menu = self.action_context_menu(widget)
        menu.show_all()
        menu.popup(None, None, None, None, 3, event.time)

    def show_action_script(self, widget=None, action=None):
        if action is None:
            return
        self.open_file(os.path.join(action_folder, self.cfg.get('ccs-actions', action)))

    def _set_action_button_script(self, widget, action):
        if action is None:
            return

        dialog = Gtk.FileChooserDialog('Select action script')
        dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OK, Gtk.ResponseType.OK)
        self.add_file_dialog_filters(dialog)
        resp = dialog.run()

        if resp == Gtk.ResponseType.OK:
            fname = dialog.get_filename()
            action.set_tooltip_text(fname)
            if os.path.dirname(fname) == action_folder:
                fname = os.path.basename(fname)

            self.cfg.save_option_to_file('ccs-actions', action.get_name(), fname)

        dialog.destroy()

    def _set_action_button_icon(self, widget, action):
        if action is None:
            return

        dialog = Gtk.FileChooserDialog(title='Select action icon')
        dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OK, Gtk.ResponseType.OK)
        resp = dialog.run()
        if resp == Gtk.ResponseType.OK:
            fname = dialog.get_filename()
            if os.path.dirname(fname) == pixmap_folder:
                fname = os.path.basename(fname)
            icon = self._get_toolbutton_icon(fname)
            action.set_icon_widget(icon)
            action.show_all()
            self.cfg.save_option_to_file('ccs-actions', action.get_name() + '_img', fname)

        dialog.destroy()

    def _get_toolbutton_icon(self, icon_path):
        button_img_path = os.path.join(pixmap_folder, icon_path)

        try:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(button_img_path, 36, 36)
        except Exception as err:
            self.logger.debug(err)
            self.logger.warning('Could not load image {}'.format(button_img_path))
            pixmap_path = os.path.join(pixmap_folder, 'action.png')
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(pixmap_path, 36, 36)

        icon = Gtk.Image.new_from_pixbuf(pixbuf)

        return icon

    def open_file(self, filename):

        try:
            with open(filename, 'r') as fdesc:
                data = fdesc.read()

                sourceview = self.notebook_open_tab(filename=filename).get_child()
                buf = sourceview.get_buffer()
                buf.set_text(data)
                label = self._notebookt_current_get_label()
                label.set_text(label.get_text().strip('*'))
                buf.connect('changed', self._notebook_buffer_modified, None, label)

                self._parse_editor_commands(buf)
                view = self._get_active_view()
                begin = buf.get_iter_at_line(0)
                self._set_play_mark(view, begin)
        except FileNotFoundError as err:
            self.logger.error(str(err))

    def _parse_editor_commands(self, buffer):
        lines = buffer.get_text(*buffer.get_bounds(), True).split('\n')
        for i, line in enumerate(lines):
            # create breakpoints
            if line.strip().startswith('#! CCS.BREAKPOINT'):
                buffer.create_source_mark(str(i), 'break', buffer.get_iter_at_line(i))

    def _set_play_mark(self, view, iter):

        textbuffer = iter.get_buffer()

        # nbpage = self.editor_notebook.page_num(view.get_parent())

        if textbuffer in self.sourcemarks:
            mark = self.sourcemarks[textbuffer]
            textbuffer.delete_mark(mark)

        mark = textbuffer.create_source_mark("play", "play", iter)
        self.sourcemarks.update({textbuffer: mark})

    def _toggle_break_mark(self, view, iter):

        textbuffer = view.get_buffer()

        mark_list = textbuffer.get_source_marks_at_iter(iter, "break");

        if not len(mark_list):
            mark = textbuffer.create_source_mark(str(iter.get_line()), "break", iter)
        else:
            textbuffer.remove_source_marks(iter, iter, "break")

    def line_mark_activated(self, view, iter, event=None, data=None):

        if event is None:
            return

        button = event.get_button()[1]

        if button == 1:
            self._set_play_mark(view, iter)

        if button == 3:
            self._toggle_break_mark(view, iter)

    def create_searchbar(self):
        searchbar = Gtk.SearchBar.new()
        searchbar.set_search_mode(False)
        searchbar.set_show_close_button(True)
        self.searchentry = Gtk.SearchEntry(width_chars=40)

        # self.searchentry.connect('search-changed', self.search_and_mark)
        self.searchentry.connect('search-changed', self._on_search_changed)
        self.searchentry.connect('activate', self._on_search_next2)
        # self.searchentry.connect('next-match', self._on_search_next)
        self.searchentry.connect('next-match', self._on_search_next2)
        # self.searchentry.connect('previous-match', self._on_search_previous)
        self.searchentry.connect('previous-match', self._on_search_prev2)

        self._init_search_settings()

        next = Gtk.Button.new_from_icon_name('go-down-symbolic', Gtk.IconSize.BUTTON)
        next.connect('clicked', self._on_search_next2)
        prev = Gtk.Button.new_from_icon_name('go-up-symbolic', Gtk.IconSize.BUTTON)
        prev.connect('clicked', self._on_search_prev2)

        csens = Gtk.CheckButton.new_with_label('match case')
        csens.connect('toggled', self._set_case_sensitive)

        hbox = Gtk.HBox()
        searchbar.add(hbox)
        hbox.pack_start(self.searchentry, 1, 1, 4)
        hbox.pack_start(prev, 0, 0, 0)
        hbox.pack_start(next, 0, 0, 0)
        hbox.pack_start(csens, 0, 0, 6)

        return searchbar

    def _set_case_sensitive(self, widget):
        self.search_settings.set_case_sensitive(widget.get_active())

    def _on_search_changed(self, widget):
        self.findtext(start_offset=0)

    def _on_search_next2(self, widget):
        self.findtext()

    def _on_search_prev2(self, *args):
        self.findtext(start_offset=0, back=True)

    def _init_search_settings(self):
        self.search_settings = GtkSource.SearchSettings()
        self.search_settings.set_case_sensitive(False)
        self.search_settings.set_wrap_around(True)
        self.searchentry.bind_property('text', self.search_settings, 'search-text')

    def _set_search_context(self, notebook, nbchild, nbpage, *args):
        self.current_view = nbchild.get_child()
        self.current_buffer = self.current_view.get_buffer()
        self.search_context = GtkSource.SearchContext.new(self.current_buffer, self.search_settings)

    def findtext(self, start_offset=1, back=False):
        buf = self.current_buffer
        insert = buf.get_iter_at_mark(buf.get_insert())
        insert.forward_chars(start_offset)

        if not back:
            match, start_iter, end_iter, wrapped = self.search_context.forward2(insert)
        else:
            match, start_iter, end_iter, wrapped = self.search_context.backward2(insert)

        if match:
            buf.place_cursor(start_iter)
            buf.move_mark(buf.get_selection_bound(), end_iter)
            self.current_view.scroll_to_mark(buf.get_insert(), 0.25, True, 0.5, 0.5)
            return True
        else:
            buf.place_cursor(buf.get_iter_at_mark(buf.get_insert()))

    def _kill_search(self, widget, evt, *args):
        if evt.keyval == Gdk.KEY_Escape:
            self.searchentry.delete_text(0, -1)
            self.searchbar.set_search_mode(False)

    def create_textview(self, filename=None):
        scrolledwindow = Gtk.ScrolledWindow()
        scrolledwindow.set_hexpand(True)
        scrolledwindow.set_vexpand(True)

        textview = GtkSource.View()
        textview.set_buffer(GtkSource.Buffer())

        textview.set_wrap_mode(Gtk.WrapMode.WORD)

        textview.set_properties(insert_spaces_instead_of_tabs=True)
        textview.set_properties(show_line_numbers=True)
        textview.set_properties(auto_indent=True)
        # textview.set_properties(highlight_current_line = True)
        textview.set_properties(monospace=True)
        textview.set_properties(tab_width=4)
        textview.set_show_line_marks(True)
        textview.connect('line-mark-activated', self.line_mark_activated)

        # draw whitespace characters
        # if GtkSource version is < 3.24
        if not hasattr(textview, 'get_space_drawer'):
            textview.set_draw_spaces(GtkSource.DrawSpacesFlags.SPACE | GtkSource.DrawSpacesFlags.TAB |
                                     GtkSource.DrawSpacesFlags.LEADING | GtkSource.DrawSpacesFlags.TRAILING)
        # if GtkSource version is >= 3.24
        else:
            drawer = textview.get_space_drawer()
            drawer.set_types_for_locations(GtkSource.SpaceLocationFlags.INSIDE_TEXT, GtkSource.SpaceTypeFlags.NONE)
            drawer.set_types_for_locations(GtkSource.SpaceLocationFlags.TRAILING, GtkSource.SpaceTypeFlags.ALL ^
                                           GtkSource.SpaceTypeFlags.NEWLINE)
            drawer.set_enable_matrix(True)

        self._apply_css(data='grid textview {{font-size :{}pt}}'.format(self.cfg['ccs-editor']['font_size']).encode())

        textview.set_mark_attributes("play", self.mark_play, 1)
        textview.set_mark_attributes("break", self.mark_break, 2)

        textbuffer = textview.get_buffer()
        lang_manager = GtkSource.LanguageManager()
        language = lang_manager.get_language('python3')

        textbuffer.set_language(language)

        if self.style_scheme is not None:
            textbuffer.set_style_scheme(self.style_scheme)

        scrolledwindow.add(textview)

        return scrolledwindow

    def create_univie_box(self):
        """
        Creates the Univie Button which can be found in every application, Used to Start all parts of the CCS and
        manage communication
        :return:
        """
        univie_box = Gtk.Toolbar()
        univie_button = Gtk.ToolButton()
        # button_run_nextline.set_icon_name("media-playback-start-symbolic")
        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(os.path.join(pixmap_folder, 'Icon_Space_blau_en.png'), 48, 48)
        icon = Gtk.Image.new_from_pixbuf(pixbuf)
        univie_button.set_icon_widget(icon)
        univie_button.set_tooltip_text('Application Drawer')
        univie_button.connect("clicked", self.on_univie_button)
        univie_box.add(univie_button)

        # Popover creates the popup menu over the button and lets one use multiple buttons for the same one
        self.popover = Gtk.Popover()
        # Add the different Starting Options
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5, margin=4)
        for name in self.cfg['ccs-dbus_names']:
            if name in ['plotter', 'monitor']:
                continue
            start_button = Gtk.Button.new_with_label("Start " + name.capitalize())
            start_button.connect("clicked", cfl.on_open_univie_clicked)
            vbox.pack_start(start_button, True, True, 0)

        # Add the TST option
        conn_button = Gtk.Button.new_with_label('Test Specification Tool')
        conn_button.connect("clicked", cfl.start_tst)
        vbox.pack_start(conn_button, True, True, 0)

        # Add the manage connections option
        conn_button = Gtk.Button.new_with_label('Communication')
        conn_button.connect("clicked", self.on_communication_dialog)
        vbox.pack_start(conn_button, True, True, 0)

        # Add the configuration manager option
        conn_button = Gtk.Button.new_with_label('Preferences')
        conn_button.connect("clicked", cfl.start_config_editor)
        vbox.pack_start(conn_button, True, True, 0)

        # Add the option to see the Credits
        about_button = Gtk.Button.new_with_label('About')
        about_button.connect("clicked", self._on_select_about_dialog)
        vbox.pack_start(about_button, True, True, 10)

        # Add the close modules button
        kill_button = Gtk.Button.new_with_label('Close modules')
        kill_button.connect("clicked", self._close_modules_cmd)
        vbox.pack_start(kill_button, True, True, 0)

        self.popover.add(vbox)
        self.popover.set_position(Gtk.PositionType.BOTTOM)
        self.popover.set_relative_to(univie_button)

        return univie_box

    def _close_modules_cmd(self, *args):
        dialog = Gtk.MessageDialog()
        dialog.add_buttons(Gtk.STOCK_NO, Gtk.ResponseType.NO, Gtk.STOCK_YES, Gtk.ResponseType.YES,)
        dialog.set_markup('<b>Close all modules?</b>')
        response = dialog.run()
        if response == Gtk.ResponseType.YES:
            dialog.destroy()
        else:
            dialog.destroy()
            return

        self._to_console('cfl._close_modules()')

    def on_univie_button(self, action):
        """
        Adds the Popover menu to the UNIVIE Button
        :param action: Simply the button
        :return:
        """
        self.popover.show_all()
        self.popover.popup()

    def on_communication_dialog(self, button):
        cfl.change_communication_func(main_instance=self.main_instance, parentwin=self)
        # self._to_console("cfl.communication = " + str(cfl.communication))

    def on_button_nextline(self, widget=None, data=None):
        self.button_run_nextline.set_sensitive(False)

        view = self._get_active_view()
        textbuffer = view.get_buffer()

        if textbuffer in self.sourcemarks:
            mark = self.sourcemarks[textbuffer]
            iter = textbuffer.get_iter_at_mark(mark)
        else:
            iter = textbuffer.get_start_iter()  # init

        begin = textbuffer.get_iter_at_line(iter.get_line())
        end = begin.copy()
        end.forward_chars(begin.get_chars_in_line())

        """ dump line into console """

        line = textbuffer.get_text(begin, end, True)
        # self.ipython_view.text_buffer.insert_at_cursor(line, len(line))

        # while Gtk.events_pending():
        #     Gtk.main_iteration()

        # self.ipython_view._processLine()
        self._to_console(line)

        self.button_run_nextline.set_sensitive(True)
        self._set_play_mark(view, end)

        return iter

    def on_button_sameline(self, widget=None, data=None):

        view = self._get_active_view()
        textbuffer = view.get_buffer()

        if textbuffer in self.sourcemarks:
            mark = self.sourcemarks[textbuffer]
            iter = textbuffer.get_iter_at_mark(mark)
        else:
            iter = textbuffer.get_start_iter()  # init

        begin = textbuffer.get_iter_at_line(iter.get_line())
        end = begin.copy()
        end.forward_chars(begin.get_chars_in_line())

        """ dump line into console """
        line = textbuffer.get_text(begin, end, True)
        self._to_console(line)

        return iter

    def on_button_run_block(self, widget):

        view = self._get_active_view()
        textbuffer = view.get_buffer()

        if textbuffer in self.sourcemarks:
            mark = self.sourcemarks[textbuffer]
            start = textbuffer.get_iter_at_mark(mark)
        else:
            start = textbuffer.get_start_iter()
            self._set_play_mark(view, start)
            mark = self.sourcemarks[textbuffer]

        # bp = textbuffer.forward_iter_to_source_mark(stop, "break")
        bp = mark.next()  # only works if no category is given!?

        if bp is not None:
            stop = textbuffer.get_iter_at_mark(bp)
        else:
            stop = textbuffer.get_end_iter()

        """ dump line into console """
        line = textbuffer.get_text(start, stop, True)
        self._to_console(line)

        self._set_play_mark(view, stop)

    def on_button_run_all_nobreak(self, widget):

        if VERIFY_EXEC_NO_BP:
            confirm_run_all = Gtk.MessageDialog(title='Confirm execution')
            confirm_run_all.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OK, Gtk.ResponseType.OK)
            confirm_run_all.set_markup('\nExecute ignoring breakpoints?')
            confirm = confirm_run_all.run()

            if confirm != Gtk.ResponseType.OK:
                confirm_run_all.destroy()
                return

            confirm_run_all.destroy()

        view = self._get_active_view()
        textbuffer = view.get_buffer()

        if textbuffer in self.sourcemarks:
            mark = self.sourcemarks[textbuffer]
            iter = textbuffer.get_iter_at_mark(mark)
        else:
            iter = textbuffer.get_start_iter()  # init

        start = textbuffer.get_iter_at_line(iter.get_line())
        end = textbuffer.get_end_iter()

        """ dump line into console """
        line = textbuffer.get_text(start, end, True)
        self._to_console(line)

        self._set_play_mark(view, end)

    def _to_console_via_socket(self, buf):
        '''
        This function sends data to the IPython Terminal, It uses a socket connection for this, in some cases more
        useful than the built in function of Vte.Terminal which can be found in function "_to_console"
        @param buf:
        @return:
        '''

        editor_sock = socket.socket()
        editor_sock.connect((self.ed_host, self.ed_port))
        editor_sock.send(buf.encode())
        ack = editor_sock.recv(1024)
        editor_sock.close()
        return ack

    def _to_console(self, buf, execute=True, editor_read=False, protect_input=False):
        '''
        This function sends data to the IPython Terminal, Gtk.VteTerminal has a built in function to do this
        @param buf: String that should be sent
        @return: acknowledgment from the IPython Terminal
        '''
        if protect_input:
            shown_length = 10   # This is the length execution line in the terminal has if no code was given

            last_row_pos = self.ipython_view.get_cursor_position()  # Get the last row
            # Get the text that is written in the last row
            terminal_text = self.ipython_view.get_text_range(last_row_pos[1], 0, last_row_pos[1] + 1, -1, None)[0]
            entry_length = len(terminal_text)

            # Check if code is entered into the terminal which was not executed yet
            if len(terminal_text) > shown_length:
                saved_text = terminal_text[8:-2]
            else:
                saved_text = ''

            # If code was entered delete it, otherwise the new command would be added at the end
            while entry_length > shown_length:
                self.ipython_view.feed_child_compat('\b', len('\b'))
                shown_length += 1
        else:
            saved_text = None

        if not buf.endswith('\n'):
            buf += '\n'

        if buf.count('\n') > 2:
            self.ipython_view.feed_child_compat('%cpaste -q\n')
            time.sleep(0.2)
            self.ipython_view.feed_child_compat(buf)
            ack = self.ipython_view.feed_child_compat('--\n')
        else:
            ack = self.ipython_view.feed_child_compat(buf)

        # Write the previously deleted code back to the terminal
        if saved_text:
            self.ipython_view.feed_child_compat(saved_text, len(saved_text))

        return ack

    def on_search_clicked(self, widget):
        self.searchbar.set_search_mode(not self.searchbar.get_search_mode())
        if self.searchbar.get_search_mode():
            self.searchbar.get_child().get_child().get_children()[1].get_children()[0].get_children()[0].grab_focus()

    # def search_and_mark(self, widget=None, start=None, direction='next'):
    #     searchtext = self.searchentry.get_text()
    #     view = self._get_active_view()
    #     textbuffer = view.get_buffer()
    #     if start is None:
    #         start, end = textbuffer.get_bounds()
    #     else:
    #         start = textbuffer.get_iter_at_mark(start)
    #         end = textbuffer.get_end_iter()
    #     # tag_found = textbuffer.create_tag(background='limegreen')#, foreground='black')
    #
    #     if direction == 'next':
    #         found = start.forward_search(searchtext, 0)
    #     else:
    #         found = start.backward_search(searchtext, 0)
    #
    #     if found:
    #         start, end = found
    #         textbuffer.select_range(start, end)
    #         if direction == 'next':
    #             last_search_pos = textbuffer.create_mark('last_search_pos', end, False)
    #         else:
    #             last_search_pos = textbuffer.create_mark('last_search_pos', start, False)
    #         # textbuffer.apply_tag(tag_found, match_start, match_end)
    #         # view.scroll_to_iter(match_start,0.,False,0,0)
    #         view.scroll_mark_onscreen(last_search_pos)

    # def _on_search_next(self, widget, *args):
    #     view = self._get_active_view()
    #     textbuffer = view.get_buffer()
    #     last_search_pos = textbuffer.get_mark('last_search_pos')
    #     self.search_and_mark(start=last_search_pos, direction='next')

    # def _on_search_previous(self, widget, *args):
    #     view = self._get_active_view()
    #     textbuffer = view.get_buffer()
    #     last_search_pos = textbuffer.get_mark('last_search_pos')
    #     self.search_and_mark(start=last_search_pos, direction='prev')

    def on_button_action(self, widget):
        action_name = widget.get_name()

        if not (self.cfg.has_option('ccs-actions', action_name) and self.cfg.get('ccs-actions', action_name) != ''):
            self.logger.warning(action_name + ': not defined!')
            return

        action = os.path.join(action_folder, self.cfg.get('ccs-actions', action_name))
        if not os.path.isfile(action):
            self.logger.warning('File {} not found.'.format(action))
            return

        cmd = 'exec(open("{}","r").read())'.format(action)
        self.logger.debug('{} button pressed'.format(action))
        try:
            # self.ipython_view.text_buffer.insert_at_cursor(cmd, len(cmd))
            # self.ipython_view._processLine()
            self._to_console_via_socket(cmd)
            # exec(open(action,'r').read())
        except Exception as err:
            self.logger.error(str(err))

        return action

    # def reload_config(self, widget):
    #     # cfg_path = cfg.get('paths', 'ccs') + '/' + self.cfg.source
    #     self.cfg = confignator.get_config()
    #
    #     action_buttons = self.grid.get_children()[2].get_children()[7:17]
    #     for button in action_buttons:
    #         action_name = self.cfg.get('ccs-actions', button.get_name())
    #         action_img = self.cfg.get('ccs-actions', button.get_name() + '_img')
    #         button.set_tooltip_text(action_name)
    #         try:
    #             pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(action_img, 36, 36)
    #         except:
    #             pixmap_path = os.path.join(pixmap_folder, 'action.png')
    #             pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(pixmap_path, 36, 36)
    #         button.set_icon_widget(Gtk.Image.new_from_pixbuf(pixbuf))
    #     self.show_all()
    #     return

    def create_log_window(self):
        logwin = Gtk.ScrolledWindow()

        bff = Gtk.TextBuffer()
        view = Gtk.TextView(buffer=bff, cursor_visible=0, editable=0)
        logwin.add(view)

        return logwin, view, bff

    def switch_notebook_page(self, logwin, view, buffer):

        filelist = glob.glob(os.path.join(self.logdir, '*.log'))
        filelist.sort(reverse=True)
        if not filelist:
            self.logger.warning('No log files to track!')
            return True
        self.log_file = filelist[0]
        with open(self.log_file, 'r') as fd:
            file = fd.read()
        if self.log_file_text is None:
            logwin.remove(logwin.get_child())
            buffer.set_text('CCS Applications Log ({}):\n'.format(os.path.basename(self.log_file)))
            end = buffer.get_end_iter()
            buffer.insert(end, '\n')
            end = buffer.get_end_iter()
            buffer.insert(end, file)
            logwin.add(view)
        else:
            new_text = file[len(self.log_file_text):]
            if new_text:
                end = buffer.get_end_iter()
                buffer.insert(end, new_text)

        self.log_file_text = file
        return True

    def _on_clear_log(self, *args):
        try:
            with open(self.log_file, 'w') as fd:
                fd.write('{}.000: Log truncated\n'.format(time.strftime('%Y-%m-%d %H:%M:%S')))
            self.log_file_text = None
            self.switch_notebook_page(self.logwin, self.logwintext, self.logbuffer)
        except Exception as err:
            self.logger.error(err)

    def _on_set_style(self, widget):
        dialog = StyleChooserDialog(scheme=self.style_scheme)

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            style = dialog.styleschemechooser.get_style_scheme().get_id()
            style_manager = GtkSource.StyleSchemeManager.get_default()
            scheme = style_manager.get_scheme(style)
            self._update_style_schemes(scheme)
            self.cfg.save_option_to_file('ccs-editor', 'color_scheme', style)

        dialog.destroy()

    def _update_style_schemes(self, scheme):
        if isinstance(scheme, str):
            style_manager = GtkSource.StyleSchemeManager.get_default()
            scheme = style_manager.get_scheme(scheme)

        self.style_scheme = scheme
        for tab in self.editor_notebook:
            buf = tab.get_child().get_buffer()
            buf.set_style_scheme(scheme)


class UnsavedBufferDialog(Gtk.MessageDialog):
    def __init__(self, parent=None, msg=None):
        Gtk.MessageDialog.__init__(self, title="Unsaved changes", parent=parent, flags=0)

        self.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_YES, Gtk.ResponseType.YES,
                                   Gtk.STOCK_NO, Gtk.ResponseType.NO,)
        head, message = self.get_message_area().get_children()
        if msg is None:
            head.set_text('There are unsaved changes. Save?')
        else:
            head.set_text(msg)

        self.show_all()


class ActionWindow(Gtk.Window):
    def __init__(self, editor, nbuttons=20, ncolumns=2):
        super(ActionWindow, self).__init__(title='Action Toolbar')

        self.editor = editor
        self.logger = editor.logger
        grid = Gtk.Grid()
        buttons = {}
        pixmap_path = os.path.join(pixmap_folder, 'action.png')
        pixbuf_default = GdkPixbuf.Pixbuf.new_from_file_at_size(pixmap_path, 36, 36)

        for i in range(nbuttons):
            button = Gtk.ToolButton()
            if self.editor.cfg.has_option('ccs-actions', 'action{}'.format(i + 1)) and \
                    self.editor.cfg.get('ccs-actions', 'action{}'.format(i + 1)) != '':
                button.set_tooltip_text(os.path.join(action_folder, self.editor.cfg.get('ccs-actions', 'action{}'.format(i + 1))))
            else:
                button.set_tooltip_text('no action')
            try:
                button_img_path = os.path.join(pixmap_folder, self.editor.cfg.get('ccs-actions', 'action{}_img'.format(i + 1)))
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(button_img_path, 36, 36)
            except:
                pixbuf = pixbuf_default
            icon = Gtk.Image.new_from_pixbuf(pixbuf)
            button.set_icon_widget(icon)
            button.set_name('action{}'.format(i + 1))
            button.connect("clicked", editor.on_button_action)
            buttons['button{}'.format(i + 1)] = button
            grid.attach(button, i % ncolumns, i//2, 1, 1)

        self.add(grid)
        self.show_all()


class StyleChooserDialog(Gtk.Dialog):

    def __init__(self, scheme=None):
        super(StyleChooserDialog, self).__init__(title='Choose Style', use_header_bar=True)

        self.styleschemechooser = GtkSource.StyleSchemeChooserWidget()

        if scheme is not None:
            self.styleschemechooser.set_style_scheme(scheme)

        self.get_content_area().add(self.styleschemechooser)

        self.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OK, Gtk.ResponseType.OK)

        self.show_all()


if __name__ == "__main__":

    DBusGMainLoop(set_as_default=True)
    ed = CcsEditor()
    if len(sys.argv) > 1:
        for fname in sys.argv[1:]:
            if not fname.startswith('-'):
                ed.open_file(fname)
    else:
        ed.notebook_open_tab()

    Bus_Name = cfg.get('ccs-dbus_names', 'editor')
    DBus_Basic.MessageListener(ed, Bus_Name, *sys.argv)

    Gtk.main()
