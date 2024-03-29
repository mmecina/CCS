import io
import os
import importlib
import json
import struct
import threading
import subprocess
import time
import sys
import dbus
import dbus.service
from dbus.mainloop.glib import DBusGMainLoop
import DBus_Basic

import ccs_function_lib as cfl

from typing import NamedTuple
import confignator
import gi

import matplotlib
matplotlib.use('Gtk3Cairo')

gi.require_version('Gtk', '3.0')
gi.require_version('Notify', '0.7')
from gi.repository import Gtk, Gdk, GdkPixbuf, GLib, Notify, Pango  # NOQA

from event_storm_squasher import delayed

# from matplotlib.figure import Figure
# from matplotlib.backends.backend_gtk3cairo import FigureCanvasGTK3Cairo as FigureCanvas
# from matplotlib.backends.backend_gtk3agg import FigureCanvasGTK3Agg as FigureCanvas
# from matplotlib.backends.backend_gtk3 import NavigationToolbar2GTK3 as NavigationToolbar

# from sqlalchemy.sql.expression import func, distinct
from sqlalchemy.orm import load_only
from database.tm_db import DbTelemetryPool, DbTelemetry, RMapTelemetry, FEEDataTelemetry, scoped_session_maker

ActivePoolInfo = cfl.ActivePoolInfo

cfg = confignator.get_config(check_interpolation=False)

project = 'packet_config_{}'.format(cfg.get('ccs-database', 'project'))
packet_config = importlib.import_module(project)
TM_HEADER_LEN, TC_HEADER_LEN, PEC_LEN = [packet_config.TM_HEADER_LEN, packet_config.TC_HEADER_LEN, packet_config.PEC_LEN]

Telemetry = {'PUS': DbTelemetry, 'RMAP': RMapTelemetry, 'FEE': FEEDataTelemetry}


class TMPoolView(Gtk.Window):
    # (label, data column alignment)

    column_labels = {'PUS': [('#', 1), ('TM/TC', 1), ("APID", 1), ("SEQ", 1), ("len-7", 1), ("ST", 1), ("SST", 1),
                             ("Dest ID", 1), ("Time", 1), ("Data", 0)],
                     'RMAP': [('#', 1), ('TYPE', 1), ('R/W', 1), ('VERIFY', 1), ('REPLY', 1), ('INCR', 1),
                              ('KEY/STAT', 1), ('TA ID', 1), ('ADDRESS', 1), ('DATALEN', 1), ('RAW', 0)],
                     'FEE': [('#', 1), ('TYPE', 1), ('FRAME CNT', 1), ('SEQ', 1), ('RAW', 0)]}

    tm_columns = {'PUS': {'#': [DbTelemetry.idx, 0, None], 'TM/TC': [DbTelemetry.is_tm, 0, None],
                          "APID": [DbTelemetry.apid, 0, None], "SEQ": [DbTelemetry.seq, 0, None],
                          "len-7": [DbTelemetry.len_7, 0, None], "ST": [DbTelemetry.stc, 0, None],
                          "SST": [DbTelemetry.sst, 0, None], "Dest ID": [DbTelemetry.destID, 0, None],
                          "Time": [DbTelemetry.timestamp, 0, None], "Data": [DbTelemetry.data, 0, None]},
                  'RMAP': {'#': [RMapTelemetry.idx, 0, None], 'TYPE': [RMapTelemetry.cmd, 0, None],
                           'R/W': [RMapTelemetry.write, 0, None], "VERIFY": [RMapTelemetry.verify, 0, None],
                           "REPLY": [RMapTelemetry.reply, 0, None], 'INCR': [RMapTelemetry.increment, 0, None],
                           "KEY": [RMapTelemetry.keystat, 0, None], "TA ID": [RMapTelemetry.taid, 0, None],
                           "ADDRESS": [RMapTelemetry.addr, 0, None], "DATALEN": [RMapTelemetry.datalen, 0, None],
                           "RAW": [RMapTelemetry.raw, 0, None]},
                  'FEE': {'#': [FEEDataTelemetry.idx, 0, None], 'TYPE': [FEEDataTelemetry.type, 0, None],
                          "FRAME CNT": [FEEDataTelemetry.framecnt, 0, None],
                          "SEQ": [FEEDataTelemetry.seqcnt, 0, None],
                          "RAW": [FEEDataTelemetry.raw, 0, None]}}

    sort_order_dict = {0: Gtk.SortType.ASCENDING, 1: Gtk.SortType.ASCENDING, 2: Gtk.SortType.DESCENDING}
    filter_rules = {}
    rule_box = None
    tmtc = {0: 'TM', 1: 'TC'}
    w_r = {0: 'R', 1: 'W'}
    cmd_repl = {0: 'rep', 1: 'cmd'}
    sort_order = Gtk.SortType.ASCENDING
    pckt_queue = None
    queues = {}
    row_colour = ''
    colour_filters = {}
    # active_pool_info = None  # type: Union[None, ActivePoolInfo]
    decoding_type = 'PUS'
    live_signal = {True: '[REC]', False: None}
    currently_selected = set()
    shift_range = [1, 1]
    active_row = None
    selected_row = 1
    cursor_path = 0
    pool_refresh_rate = 1 / 10.
    last_decoded_row = None
    row_buffer_n = 100
    main_instance = None
    first_run = True
    only_scroll = False

    CELLPAD_MAGIC = float(cfg['ccs-misc']['viewer_cell_pad'])

    def __init__(self, cfg=cfg, pool_name=None, cfilters='default', standalone=False):
        Gtk.Window.__init__(self, title="Pool View", default_height=800, default_width=1100)

        self.refresh_treeview_active = False
        self.cnt = 0
        # self.active_pool_info = ActivePoolInfo(None, None, None, None)
        self.active_pool_info = ActivePoolInfo('', 0, '', False)
        self.set_border_width(2)
        self.set_resizable(True)
        self.set_default_size(1150, 1280)
        # self.set_position(Gtk.WindowPosition.CENTER)
        self.set_gravity(Gdk.Gravity.NORTH_WEST)

        Notify.init('PoolViewer')

        # self.cfg = confignator.get_config()
        self.cfg = cfg

        self.autoscroll = 1
        self.autoselect = 1

        self._selected_mon_par_set = None

        self.paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL, wide_handle=True, position=400)

        self.statusbar = Gtk.Statusbar()
        self.statusbar.set_halign(Gtk.Align.END)
        grid = Gtk.VBox()
        grid.pack_start(self.paned, 1, 1, 0)
        grid.pack_start(self.statusbar, 0, 0, 0)
        self.add(grid)

        self.grid = Gtk.Grid()
        self.grid.set_column_homogeneous(True)
        self.grid.set_row_homogeneous(False)
        self.paned.add2(self.grid)

        self.set_events(self.get_events() | Gdk.EventMask.SCROLL_MASK)

        self.treebox = self.create_treeview()

        self.grid.attach(self.treebox, 0, 3, 1, 12)

        self.create_pool_managebar()
        self.grid.attach(self.pool_managebar, 0, 0, 1, 1)

        self.filterbar = self.create_filterbar()
        self.grid.attach(self.filterbar, 0, 1, 1, 1)

        self._add_rulebox()

        dataview = self.create_tm_data_viewer()
        self.paned.add1(dataview)

        self.set_keybinds()
        self.key_held_pressed = False

        sets = self.get_settings()
        sets.set_property('gtk-error-bell', False)

        if self.cfg.has_section('ccs-pool_colour_filters') and (cfilters is not None):
            for cfilter in json.loads(self.cfg['ccs-pool_colour_filters'][cfilters]):
                self.add_colour_filter(cfilter)

        self.rgba_black = Gdk.RGBA()
        self.rgba_black.parse('black')

        self.session_factory_idb = scoped_session_maker('idb')
        self.session_factory_storage = scoped_session_maker('storage')

        # Set up the logging module
        self.logger = cfl.start_logging('Poolviewer')

        if pool_name is not None:
            self.set_pool(pool_name)

        self.stored_packet = []

        self.connect("delete-event", self.quit_func)
        self.show_all()

    def checking(self):
        self.adj.set_value(60)
        return

    def quit_func(self, *args):
        # Check if Poolmanager is running otherwise just close viewer
        if not cfl.is_open('poolmanager', cfl.communication['poolmanager']):
            self.close_terminal_connection()
            self.update_all_connections_quit()
            if Gtk.main_level():
                Gtk.main_quit()
            return False

        pmgr = cfl.dbus_connection('poolmanager', cfl.communication['poolmanager'])
        # Check if Gui and only close poolviewer if it is
        if cfl.Variables(pmgr, 'gui_running'):
            self.close_terminal_connection()
            self.update_all_connections_quit()
            if Gtk.main_level():
                Gtk.main_quit()
            return False

        # Ask if Poolmanager should be cloosed too
        ask = UnsavedBufferDialog(parent=self, msg='Response NO will keep the Poolmanager running in the Background')
        response = ask.run()

        if response == Gtk.ResponseType.NO:
            Notify.Notification.new('Poolmanager is still running without a GUI').show()

        elif response == Gtk.ResponseType.CANCEL:
            ask.destroy()
            return True

        else:
            self.close_terminal_connection()
            self.update_all_connections_quit()
            ask.destroy()
            pmgr.Functions('quit_func_pv', ignore_reply=True)
            Gtk.main_quit()
            return False

        self.close_terminal_connection()
        self.update_all_connections_quit()
        ask.destroy()
        Gtk.main_quit()
        return False

    def close_terminal_connection(self):
        # Try to tell terminal in the editor that the variable is not longer availabe
        for service in dbus.SessionBus().list_names():
            if service.startswith(self.cfg['ccs-dbus_names']['editor']):
                editor = cfl.dbus_connection(service[0:-1].split('.')[1], service[-1])
                if self.main_instance == editor.Variables('main_instance'):
                    nr = self.my_bus_name[-1]
                    if nr == str(1):
                        nr = ''
                    editor.Functions('_to_console_via_socket', 'del(pv'+str(nr)+')')
        return

    def update_all_connections_quit(self):
        """
        Tells all running applications that it is not longer availabe and suggests another main communicator if one is
        available
        :return:
        """
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

    def send_cfg(self):
        return self.cfg

    def set_pool_from_pmgr(self):
        try:
            poolmgr = cfl.dbus_connection('poolmanager', cfl.communication['poolmanager'])
            if not poolmgr:
                return

            pools = cfl.Functions(poolmgr, 'loaded_pools_export_func')

            if not pools:
                self.logger.warning('No loaded pools found, nothing to view.')
                return

            for pool in pools:
                if not pool[0].count('/'):
                    self.set_pool(pool[0])

        except Exception as err:
            self.logger.exception(err)

    def set_pool(self, pool_name, pmgr_pools=None, instance=None):
        if pool_name is None:
            return

        if not pmgr_pools:
            try:
                poolmgr = cfl.dbus_connection('poolmanager', cfl.communication['poolmanager'])
                if not poolmgr:
                    raise TypeError('No poolmanager instance found.')
                try:
                    self.Active_Pool_Info_append(cfl.Dictionaries(poolmgr, 'loaded_pools', pool_name))
                except (dbus.DBusException, KeyError):
                    raise ValueError('No loaded pool {} found.'.format(pool_name))

                cfl.Functions(poolmgr, 'loaded_pools_func', self.active_pool_info.pool_name, self.active_pool_info)
            except Exception as err:
                self.logger.warning(err)
                if '/' in pool_name:
                    pool_path = str(os.path.realpath(pool_name))
                    # pool_name = pool_name.split('/')[-1]
                else:
                    pool_path = pool_name
                # change_error
                attribute = [pool_path, int(round(time.time())), str(pool_name), False]
                self.Active_Pool_Info_append(attribute)
        else:
            for pool in pmgr_pools:
                if pool_name == pool[2]:
                    self.Active_Pool_Info_append(list(pool))
            # self.Active_Pool_Info_append(pmgr_pools[pool_name])

        self._set_pool_list_and_display(instance=instance)
        if self.active_pool_info.live:
            self.refresh_treeview(pool_name)
            # print('THIS STEP IS NOT NEEDED ANYMORE')
            # if self.pool is None:
            #     self.pool = pool
            #
            # thread = threading.Thread(target = self.update_packets)
            # thread.daemon = True
            # thread.start()

    # def set_queue(self, pool_name, pckt_queue):
    #
    #     self.queues.update({pool_name: pckt_queue})
    #
    #     model = self.pool_selector.get_model()
    #
    #     iter = model.append([pool_name])
    #
    #     if model.iter_n_children() == 1:
    #         self.pool_selector.set_active_iter(iter)
    #         self.pool_liststore.clear()
    #         self.pckt_queue = pckt_queue
    #         self.pool_name = pool_name

    # def update_packets_worker(self):

    #     pckt_queue = self.pckt_queue
    #     if pckt_queue is None or self.pool is None or pckt_queue.empty():
    #         return True

    #     print("Worker resumes...")
    #     unpack_pus = self.pool.unpack_pus
    #     getpq = pckt_queue.get
    #     appendls = self.pool_liststore.append
    #     cuctime = self.pool.cuc_time_str

    #     print("Worker resumes 2...")
    #     # self.treeview.set_model(None)
    #     self.treeview.set_model(self.pool_liststore)
    #     self.treeview.freeze_child_notify()
    #     pckt_count = 0
    #     while not pckt_queue.empty():
    #         (seq, pckt) = getpq()
    #         tm = unpack_pus(pckt)
    #         appendls([seq] + [self.tmtc[tm[1]]] + [tm[3]] + tm[5:7] + tm[10:13] + [cuctime(tm)] + [tm[-2]])
    #         pckt_count+=1
    #         if (pckt_count % 128) == 127:
    #             # self.treeview.set_model(self.pool_liststore)
    #             self.treeview.thaw_child_notify()
    #             print("Added:", pckt_count, "...")
    #             return True
    #
    #     self.treeview.thaw_child_notify()
    #     print("Completed - Added:", pckt_count, "\n")
    #     # self.change_cursor(self.scrolled_treelist.get_window(),'default')
    #     return True

    def change_communication(self, application, instance=1, check=True):
        # If it is checked that both run in the same project it is not necessary to do it again
        if check:
            conn = cfl.dbus_connection(application, instance)
            # Both are not in the same project do not change

            if not cfl.Variables(conn, 'main_instance') == self.main_instance:
                self.logger.warning('Application {} is not in the same project as {}: Can not communicate'.format(
                    self.my_bus_name, self.cfg['ccs-dbus_names'][application] + str(instance)))
                return

        cfl.communication[application] = int(instance)
        return

    def get_communication(self):
        return cfl.communication

    def connect_to_all(self, My_Bus_Name, Count):
        self.my_bus_name = My_Bus_Name
        #print(My_Bus_Name)
        # Look if other applications are running in the same project group
        our_con = []
        #Look for all connections starting with com, therefore only one loop over all connections is necessary
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
                    cfl.communication = conn.Functions('get_communication')
                    conn_com = conn.Functions('get_communication')
                    if conn_com[self.my_bus_name.split('.')[1]] == 0:
                        conn.Functions('change_communication', self.my_bus_name.split('.')[1], self.my_bus_name [-1], False)

        if not cfl.communication[self.my_bus_name.split('.')[1]]:
            cfl.communication[self.my_bus_name.split('.')[1]] = int(self.my_bus_name[-1])

        # Connect to the Terminal
        if Count == 1:
            for service in dbus.SessionBus().list_names():
                if service.startswith(self.cfg['ccs-dbus_names']['editor']):
                    editor = cfl.dbus_connection('editor', service[-1])
                    editor.Functions('_to_console_via_socket', "pv = dbus.SessionBus().get_object('" + str(My_Bus_Name)
                                     + "', '/MessageListener')")

        else:
            for service in dbus.SessionBus().list_names():
                if service.startswith(self.cfg['ccs-dbus_names']['editor']):
                    editor = cfl.dbus_connection('editor', service[-1])
                    editor.Functions('_to_console_via_socket', "pv" +str(Count)+ " = dbus.SessionBus().get_object('" +
                                     str(My_Bus_Name) + "', '/MessageListener')")

        # Check if pool from poolmanagers should be loaded, default is True
        if '--noload' not in sys.argv:
            self.set_pool_from_pmgr()

    def add_colour_filter(self, colour_filter):
        seq = len(self.colour_filters.keys())
        rgba = Gdk.RGBA()
        rgba.parse(colour_filter['colour'])
        colour_filter['colour'] = rgba
        self.colour_filters.update({seq: colour_filter})

    def update_colour_filter(self, index, colour_filter):
        self.colour_filters.update({index: colour_filter})

    def del_colour_filter(self, filter_index):
        self.colour_filters.pop(filter_index)

    def get_colour_filters(self):
        return self.colour_filters

    def text_colour(self, column, cell, tree_model, iter, data=None):

        # labels = list(map(list, zip(*self.column_labels)))[0]

        """ this is a bit stupid and inefficient, but it does the job """

        if column == self.treeview.get_column(0):
            labels = [x[0] for x in self.column_labels[self.decoding_type]]

            self.row_colour = self.rgba_black
            for filter in self.colour_filters:
                d = {}
                cf = self.colour_filters[filter].copy()
                cf.pop('colour')

                for key in cf.keys():
                    d.update({key: tree_model[iter][labels.index(key)]})

                if d == cf:
                    self.row_colour = self.colour_filters[filter]['colour']

        # cell.set_property('foreground', self.row_colour)

        cell.set_property('foreground-rgba', self.row_colour)

    def text_colour2(self, column, cell, tree_model, iter, data=None):
        if column == self.treeview.get_column(0):
            labels = [x[0] for x in self.column_labels[self.decoding_type]]

            d = {key: tree_model[iter][labels.index(key)] for key in labels[1:-2]}  # skip idx, time and data fields

            self.row_colour = self.rgba_black
            for f in self.colour_filters:
                cf = self.colour_filters[f].copy()
                colour = cf.pop('colour')

                if cf.items() <= d.items():
                    self.row_colour = colour
                    break
                else:
                    continue

        cell.set_property('foreground-rgba', self.row_colour)

    def create_treeview(self):

        self.pool_liststore = self.create_liststore()

        self.treeview = Gtk.TreeView()
        self.treeview.set_model(self.pool_liststore)
        self.treeview.set_rubber_banding(False)
        self.treeview.set_activate_on_single_click(True)
        # self.treeview.set_fixed_height_mode(True)

        self.create_treeview_columns()

        self.scrolled_treelist = Gtk.ScrolledWindow()
        self.scrolled_treelist.set_policy(Gtk.PolicyType.ALWAYS, Gtk.PolicyType.ALWAYS)
        self.scrolled_treelist.set_overlay_scrolling(False)
        self.scrolled_treelist.set_min_content_height(235)
        self.scrolled_treelist.set_vexpand(True)

        self.scrolled_treelist.add(self.treeview)
        self.scrolled_treelist.add_events(Gdk.EventMask.SMOOTH_SCROLL_MASK)
        self.scrolled_treelist.add_events(Gdk.EventMask.SCROLL_MASK)

        self.connect('configure-event', self.set_number_of_treeview_rows)
        # self.connect('check-resize', self.set_number_of_treeview_rows)
        self.connect('window-state-event', self.resize_treeview)

        self.treeview.connect('size-allocate', self.treeview_update)
        # self.treeview.connect('size-allocate', self.set_tm_data_view)
        self.treeview.connect('key-press-event', self.key_pressed)
        # self.treeview.connect('key-press-event', self.set_tm_data_view)
        # self.treeview.connect('key-press-event', self.set_currently_selected)
        self.treeview.connect('button-release-event', self.set_currently_selected)
        self.treeview.connect('button-press-event', self._set_current_row)

        # something like that
        # self.scrolled_treelist.connect('edge-reached', self.edge_reached)
        # self.scrolled_treelist.connect('edge-overshot', self.edge_reached)
        self.scrolled_treelist.connect('scroll-event', self.scroll_event)
        # self.scrolled_treelist.connect('scroll-event', self.reselect_rows)
        # self.scrolled_treelist.connect('button-release-event', self.scroll_event)
        self.scrolled_treelist.connect('scroll-child', self.scroll_child)
        # self.scrolled_treelist.get_vscrollbar().connect('value-changed', self.scroll_bar)
        self.scrolled_treelist.get_vscrollbar().set_visible(False)

        self.selection = self.treeview.get_selection()
        self.selection.set_mode(Gtk.SelectionMode.SINGLE)
        # self.selection.connect('changed', self.tree_selection_changed)
        self.selection.connect('changed', self.set_tm_data_view)
        # self.selection.connect('changed', self.unselect_bottom)

        scrollbar = Gtk.VScrollbar()
        self.adj = scrollbar.get_adjustment()
        # get size of tmpool

        if self.active_pool_info.pool_name not in (None, ''):
            self.adj.set_upper(self.count_current_pool_rows())
        height = self.treeview.get_allocated_height()
        column = self.treeview.get_column(0)
        cell_pad = column.get_cells()[0].get_padding()[1]
        cell = column.cell_get_size()[-1] + cell_pad * self.CELLPAD_MAGIC
        nlines = height // cell
        self.adj.set_page_size(nlines)
        scrollbar.connect('value_changed', self._on_scrollbar_changed, self.adj, False)
        scrollbar.connect('button-press-event', self.scroll_bar)
        # scrollbar.connect('value_changed', self.reselect_rows)


        # Set up Drag and Drop
        self.treeview.drag_source_set(Gdk.ModifierType.BUTTON1_MASK, [], Gdk.DragAction.COPY)
        self.treeview.drag_source_set_target_list(None)
        self.treeview.drag_source_add_text_targets()

        self.treeview.connect("drag-data-get", self.on_drag_data_get)

        hbox = Gtk.HBox()
        hbox.pack_start(self.scrolled_treelist, 1, 1, 0)
        hbox.pack_start(scrollbar, 0, 0, 0)

        return hbox

    def create_treeview_columns(self):
        for i, (column_title, align) in enumerate(self.column_labels[self.decoding_type]):
            render = Gtk.CellRendererText(xalign=align)
            if column_title in ('Data', 'RAW'):
                render.set_property('font', 'Monospace')

            column = Gtk.TreeViewColumn(column_title, render, text=i)
            column.set_cell_data_func(render, self.text_colour2)

            # column.set_sort_column_id(i)
            column.set_clickable(True)
            column.set_resizable(True)
            column.connect('clicked', self.column_clicked)
            self.treeview.append_column(column)

    def _set_current_row(self, widget=None, event=None):
        x, y = event.x, event.y
        path = widget.get_path_at_pos(x, y)
        if path is not None:
            self.active_row = widget.get_model()[path[0]][0]
            self.set_shift_range(self.active_row)
            self.autoselect = 0
            self.set_tm_data_view()

    def set_shift_range(self, row):
        self.shift_range[0] = self.shift_range[1]
        self.shift_range[1] = row

    # @delayed(10)
    def set_number_of_treeview_rows(self, widget=None, allocation=None):
        # alloc = widget.get_allocation()
        height = self.treeview.get_allocated_height()
        # height = self.treeview.get_visible_rect().height
        # cell = 25
        column = self.treeview.get_column(0)
        cell_pad = column.get_cells()[0].get_padding()[1]
        cell = column.cell_get_size()[-1] + cell_pad * self.CELLPAD_MAGIC
        nlines = height // cell
        self.adj.set_page_size(nlines - 1)
        # self._scroll_treeview()
        self.reselect_rows()

    def resize_treeview(self, widget, event):
        if Gdk.WindowState.MAXIMIZED == event.new_window_state:
            self.set_number_of_treeview_rows()

    # @delayed(10)
    def _on_scrollbar_changed(self, widget=None, adj=None, force=True):
        if self.autoscroll and not force:
            return
        if self.only_scroll:    # Stops second scroll event after scrollbar zeiger was reset,if scrolled by scroll wheel
            return
        self.offset = int(self.adj.get_value())
        self.limit = int(self.adj.get_page_size())

        self.feed_lines_to_view(self.fetch_lines_from_db(offset=self.offset, limit=self.limit, force_import=True))
        self.reselect_rows()

    def count_current_pool_rows(self, pool_info=None):
        if pool_info is not None:
            self.Active_Pool_Info_append(pool_info)

        if self.active_pool_info is None:
            return 0

        new_session = self.session_factory_storage
        rows = new_session.query(
            Telemetry[self.decoding_type]
        ).join(
            DbTelemetryPool,
            Telemetry[self.decoding_type].pool_id == DbTelemetryPool.iid
        ).filter(
            DbTelemetryPool.pool_name == self.active_pool_info.filename
        )
        if rows.first() is None:
            self.logger.warning('Could not find rows for pool {}'.format(self.active_pool_info.filename))
            cnt = 0
        else:
            cnt = rows.order_by(Telemetry[self.decoding_type].idx.desc()).first().idx
        new_session.close()
        return cnt

    def get_current_pool_rows(self, dbsession=None):
        if self.active_pool_info is None:
            return 0
        new_session = self.session_factory_storage
        rows = new_session.query(
            Telemetry[self.decoding_type]
        ).join(
            DbTelemetryPool,
            Telemetry[self.decoding_type].pool_id == DbTelemetryPool.iid
        ).filter(
            DbTelemetryPool.pool_name == self.active_pool_info.filename
        )
        new_session.close()
        return rows

    def on_drag_data_get(self, treeview, drag_context, selection_data, info, time, *args):
        treeselection = treeview.get_selection()
        model, my_iter = treeselection.get_selected()

        if model is not None and my_iter is not None:
            new_session = self.session_factory_storage
            row = new_session.query(
                Telemetry[self.decoding_type]
            ).join(
                DbTelemetryPool,
                Telemetry[self.decoding_type].pool_id == DbTelemetryPool.iid
            ).filter(
                DbTelemetryPool.pool_name == self.active_pool_info.filename
            ).filter(
                Telemetry[self.decoding_type].idx == model[my_iter][0]
            )
            selection_data.set_text(str(row.first().raw), -1)
            new_session.close()

    def fetch_lines_from_db(self, offset=0, limit=None, sort=None, order='asc', buffer=10, rows=None, scrolled=False,
                            force_import=False):
        """
        Reads the packages from the Database and shows it according to the position of the scrollbar
        @param offset: Index of first line - 1
        @param limit: How many packages should be displayed
        @param sort: If the packages are sorted in any way
        @param order: In which order the packages should be displayed
        @param buffer: How many packages should be loaded but are not shown
        @param rows: Show these rows if given
        @param scrolled: True if view is scrolled
        @param force_import: Import all rows again from the Database
        @return: -
        """

        if self.active_pool_info is None:
            return

        limit = self.adj.get_page_size() if not limit else limit  # Check if a limit is given

        if rows is None:
            # Combine the Storage Tables and filter only the packages for the given pool
            new_session = self.session_factory_storage
            rows = new_session.query(
                Telemetry[self.decoding_type]
            ).join(
                DbTelemetryPool,
                Telemetry[self.decoding_type].pool_id == DbTelemetryPool.iid
            ).filter(
                DbTelemetryPool.pool_name == self.active_pool_info.filename
            )
            new_session.close()

        sorted = False
        # Check if the rows should be shown in any specific order
        for col in self.tm_columns[self.decoding_type]:
            if self.tm_columns[self.decoding_type][col][1] == 1:
                rows = rows.order_by(self.tm_columns[self.decoding_type][col][0], Telemetry[self.decoding_type].idx)
                sorted = True
            elif self.tm_columns[self.decoding_type][col][1] == 2:
                rows = rows.order_by(self.tm_columns[self.decoding_type][col][0].desc(), Telemetry[self.decoding_type].idx.desc())
                sorted = True

        # Check if a filter has been applied
        if self.filter_rules_active:
            rows = self._filter_rows(rows)

        if sorted:
            rows = rows.options(load_only()).yield_per(1000).offset(offset).limit(limit)
        else:
            rows = rows.filter(Telemetry[self.decoding_type].idx > offset).limit(limit)
        return rows

    def _filter_rows(self, rows):

        def f_rule(x):
            if x[1] == '==':
                return x[0] == x[2]
            elif x[1] == '!=':
                return x[0] != x[2]
            elif x[1] == '<':
                return x[0] < x[2]
            elif x[1] == '>':
                return x[0] > x[2]

        # for fid in self.filter_rules:
        #     ff = self.filter_rules[fid]
        #     if ff[1] == '==':
        #         rows = rows.filter(ff[0] == ff[2])
        #     elif ff[1] == '!=':
        #         rows = rows.filter(ff[0] != ff[2])
        #     elif ff[1] == '<':
        #         rows = rows.filter(ff[0] < ff[2])
        #     elif ff[1] == '>':
        #         rows = rows.filter(ff[0] > ff[2])

        first = 1
        for fil in self.filter_rules.values():
            if first:
                rule = f_rule(fil)
                first = 0
            elif fil[3] == 'AND':
                rule = rule & f_rule(fil)
            elif fil[3] == 'OR':
                rule = rule | f_rule(fil)

        # filter_chain = [f_rule(self.filter_rules[ff]) for ff in self.filter_rules]
        if not first:
            rows = rows.filter(rule)

        return rows

    def feed_lines_to_view(self, rows):
        """
        Updates the shown packages from the buffer
        @param shown_diff: how many lines has been scrolled
        @return: -
        """

        self.pool_liststore.clear()

        # new_rows = [[tm.idx, self.tmtc[tm.is_tm], tm.apid, tm.seq, tm.len_7, tm.stc, tm.sst, tm.destID, str(tm.timestamp),
        #              tm.data.hex()] for tm in rows]

        # self.treeview.freeze_child_notify()

        for tm in rows:
            self.pool_liststore.append([tm.idx, self.tmtc[tm.is_tm], tm.apid, tm.seq, tm.len_7, tm.stc, tm.sst,
                                        tm.destID, str(tm.timestamp), tm.data.hex()])

        # self.treeview.thaw_child_notify()

    def format_loaded_rows(self, dbrows):
        '''
        This function converts every packet into a readable form
        @param dbrows: The rows from SQL query
        @return: rows in readable form
        '''

        tm_rows = []
        if self.decoding_type == 'PUS':
            for tm in dbrows:
                tm_row = [tm.idx, self.tmtc[tm.is_tm], tm.apid, tm.seq, tm.len_7, tm.stc, tm.sst, tm.destID,
                          str(tm.timestamp), tm.data.hex()]
                tm_rows.append(tm_row)
        elif self.decoding_type == 'RMAP':
            for tm in dbrows:
                tm_row = [tm.idx, self.cmd_repl[tm.cmd], self.w_r[tm.write], int(tm.verify), int(tm.reply),
                          int(tm.increment), '0x{:02X}'.format(tm.keystat), tm.taid, self._addr_fmt_hex_str(tm.addr),
                          tm.datalen, tm.raw.hex()]
                tm_rows.append(tm_row)
        elif self.decoding_type == 'FEE':
            for tm in dbrows:
                tm_row = [tm.idx, tm.type, tm.framecnt, tm.seqcnt, tm.raw.hex()]
                tm_rows.append(tm_row)
        else:
            self.logger.error('Unsupported packet format!')
        return tm_rows

    @staticmethod
    def _addr_fmt_hex_str(x):
        if x is not None:
            return '0x{:08X}'.format(x)
        else:
            return ''

    def tree_selection_changed(self, selection):
        mode = selection.get_mode()
        model, treepaths = selection.get_selected_rows()

        if len(treepaths) > 0:
            path = treepaths[-1]
        else:

            if mode != Gtk.SelectionMode.SINGLE:
                return

            model, treeiter = selection.get_selected()

            if treeiter is None:
                return

            path = model.get_path(treeiter)

        self.logger.debug('SEL', time.time(), path, self.autoscroll, self.autoselect)
        # I will probably be murdered in my sleep for doing this, but it works!
        entry = int(str(path))
        children = self.pool_liststore.iter_n_children() - 1

        if entry == children:
            self.autoselect = 1
        else:
            self.autoselect = 0
        self.set_tm_data_view()

    def column_clicked(self, widget):
        # widget.get_sort_column_id()
        self._toggle_sort_order(widget)
        self._scroll_treeview(force_db_import=True)

    def _toggle_sort_order(self, column):
        colname = column.get_title()
        newstate = self.tm_columns[self.decoding_type][colname][1] = (self.tm_columns[self.decoding_type][colname][1] + 1) % 3
        column.set_sort_indicator(newstate)
        column.set_sort_order(self.sort_order_dict[newstate])

    def get_last_item(self, model, parent=None):
        n = model.iter_n_children(parent)
        return n and model.iter_nth_child(parent, n - 1)

    def treeview_update(self, widget=None, event=None, data=None, row=1):
        if self.autoscroll:
            # adj = widget.get_vadjustment()
            # if self.sort_order == Gtk.SortType.DESCENDING:
            # adj.set_value(adj.get_upper() - adj.get_page_size())

            if self.autoselect:
                # selection = self.treeview.get_selection()
                # self.selection.set_mode(Gtk.SelectionMode.SINGLE)
                last = self.get_last_item(self.pool_liststore)
                if last != 0:
                    self.selection.select_iter(last)
                    row = self.pool_liststore[self.pool_liststore.get_path(last)][0]
                    if self.selected_row != row:
                        self.set_tm_data_view()
                        self.selected_row = row
                        # self.selection.set_mode(Gtk.SelectionMode.MULTIPLE)

    def edge_reached(self, widget, event, data=None):
        if event.value_name == 'GTK_POS_BOTTOM':
            self.autoscroll = 1
            self.autoselect = 1

    def scroll_bar(self, widget=None, event=None):
        # a little crude, but we want to catch scrollbar-drag events too
        self.autoscroll = 0

    def scroll_child(self, widget, event, data=None):
        self.logger.debug('Seems like I do not work')
        return

    def scroll_event(self, widget, event, data=None):
        # print(event.direction.value_name, event.delta_x, event.delta_y)
        self.only_scroll = True
        if event.direction.value_name == 'GDK_SCROLL_SMOOTH':
            scroll_lines = 3 * max(-1, event.delta_y)
            if scroll_lines < 0:
                self.autoscroll = 0
            elif scroll_lines > 6:
                self.autoscroll = 1
        # needed for remote desktop
        elif event.direction.value_name == 'GDK_SCROLL_UP':
            scroll_lines = -3
            self.autoscroll = 0
        elif event.direction.value_name == 'GDK_SCROLL_DOWN':
            scroll_lines = 3
        else:
            return

        self._scroll_treeview(scroll_lines)
        self.reselect_rows()
        # Only_scroll is necessary to not launch a second event after the scrollbar is reset to new value
        self.only_scroll = False
        # print(self.offset, self.limit)
        # disable autoscroll on scrollwheel up
        # if event.get_scroll_deltas()[2] == -1:
        #     self.autoscroll = 0

    def _scroll_treeview(self, scroll_lines=0, sort=None, order='asc', rows=None, force_db_import=False):
        upper_limit = self.adj.get_upper() - self.adj.get_page_size()
        self.offset = int(min(upper_limit, self.adj.get_value() + scroll_lines))
        self.offset = max(0, self.offset)
        self.limit = int(self.adj.get_page_size())
        self.feed_lines_to_view(
            self.fetch_lines_from_db(self.offset, self.limit, sort=sort, order=order, rows=rows))
        self.adj.set_value(self.offset)

    def key_pressed(self, widget=None, event=None):

        def unselect_rows(clear=False):
            # selection = widget.get_selection()
            # self.selection.disconnect_by_func(self.tree_selection_changed)
            if clear:
                self.currently_selected = set()
            else:
                model, paths = self.selection.get_selected_rows()
                self.currently_selected = {model[path][0] for path in paths}
            self.reselect_rows()
            # self.selection.connect('changed', self.tree_selection_changed)

        try:
            cursor_path = self.treeview.get_cursor()[0]
            in_row = cursor_path.get_indices()[0]
            # cursor_path.free()
            self.cursor_path = cursor_path
        except AttributeError:
            in_row = 1
            # cursor_path = self.cursor_path
            # in_row = cursor_path.get_indices()[0]

        # if in_row not in (0, self.limit - 1):
        #     return

        if event.keyval == Gdk.KEY_Up and in_row == 0:
            # cursor_path = self.treeview.get_cursor()[0]
            self._scroll_treeview(-1)
            self.treeview.set_cursor(cursor_path)
            self.autoscroll = False
            unselect_rows()
        elif event.keyval == Gdk.KEY_Up:
            self.autoselect = False
            self.autoscroll = False
        elif event.keyval == Gdk.KEY_Down and in_row == self.limit - 1:
            # cursor_path = self.treeview.get_cursor()[0]
            self._scroll_treeview(1)
            self.treeview.set_cursor(cursor_path)
            unselect_rows()
        elif event.keyval == Gdk.KEY_Home:
            self._scroll_treeview(-self.offset)
            # self.treeview.set_cursor(cursor_path)
            self.autoscroll = False
            unselect_rows()
        elif event.keyval == Gdk.KEY_End:
            # cursor_path = self.treeview.get_cursor()[0]
            # self._scroll_treeview(self.adj.get_upper() - self.offset - self.limit)
            # self.treeview.set_cursor(cursor_path)
            self.autoscroll = True
            self.autoselect = True
            self.scroll_to_bottom()
            unselect_rows(clear=True)
        elif event.keyval == Gdk.KEY_Page_Up:
            # cursor_path = self.treeview.get_cursor()[0]
            self._scroll_treeview(-self.limit)
            if cursor_path is not None:
                self.treeview.set_cursor(cursor_path)
            self.autoscroll = False
            unselect_rows()
        elif event.keyval == Gdk.KEY_Page_Down:
            # cursor_path = self.treeview.get_cursor()[0]
            self._scroll_treeview(self.limit)
            if cursor_path is not None:
                self.treeview.set_cursor(cursor_path)
            self.autoscroll = False
            unselect_rows()
            # else:
            #     print(event.keyval)
            # Gdk.KEY_Page_Up,Gdk.KEY_Page_Down,Gdk.KEY_Home,Gdk.KEY_End

    def set_currently_selected(self, widget=None, event=None):
        state = event.get_state()
        # print(state, state & Gdk.ModifierType.CONTROL_MASK == Gdk.ModifierType.CONTROL_MASK)
        # if state & Gdk.ModifierType.CONTROL_MASK == Gdk.ModifierType.CONTROL_MASK:
        #     # selection = widget.get_selection()
        #     # model, paths = selection.get_selected_rows()
        #     idx = self.shift_range[1]
        #     if idx in self.currently_selected:
        #         self.currently_selected.remove(idx)
        #     else:
        #         self.currently_selected.add(idx)
        #         # for path in paths:
        #         #    self.currently_selected.add(model[path][0])
        # elif state & Gdk.ModifierType.SHIFT_MASK == Gdk.ModifierType.SHIFT_MASK:
        #     # selection = widget.get_selection()
        #     # model, paths = selection.get_selected_rows()
        #     # for path in paths:
        #     #     self.currently_selected.add(model[path][0])
        #     if len(self.currently_selected) > 1:
        #         for idx in range(min(self.shift_range), max(self.shift_range) + 1):
        #             self.currently_selected.add(idx)
        #     else:
        #         self.currently_selected = set(range(min(self.shift_range), max(self.shift_range) + 1))
        # else:
        #     # selection = widget.get_selection()
        #     model, paths = self.selection.get_selected_rows()
        #     self.currently_selected = {model[path][0] for path in paths}
        model, paths = self.selection.get_selected_rows()
        self.currently_selected = {model[path][0] for path in paths}
        self.reselect_rows()

    def select_all_rows(self, widget=None, *args):
        nrows = self.count_current_pool_rows()
        self.currently_selected = set(range(1, nrows + 1))
        self.reselect_rows()

    def reselect_rows(self, widget=None, event=None):
        model = self.pool_liststore  # self.treeview.get_model()
        # self.treeview.get_selection().unselect_all()
        for row in model:
            if row[0] in self.currently_selected:
                try:
                    self.selection.select_path(model.get_path(model.get_iter(row[0] - self.offset - 1)))
                except ValueError:
                    self.logger.info('valerr')
                except TypeError:
                    self.logger.info('typerr')

    def unselect_bottom(self, widget=None):
        if widget.count_selected_rows() > 1:
            bottom_path = widget.get_selected_rows()[-1][-1]
            widget.unselect_path(bottom_path)

    def create_liststore(self):
        if self.decoding_type == 'PUS':
            return Gtk.ListStore('guint', str, 'guint', 'guint', 'guint', 'guint', 'guint', 'guint', str, str)
        elif self.decoding_type == 'RMAP':
            return Gtk.ListStore('guint', str, str, 'guint', 'guint', 'guint', str, 'guint', str, 'guint', str)
        elif self.decoding_type == 'FEE':
            return Gtk.ListStore('guint', 'guint', 'guint', 'guint', str)
        else:
            self.logger.error('Decoding Type is an unknown value')

    def set_keybinds(self):

        accel = Gtk.AccelGroup()
        accel.connect(Gdk.keyval_from_name('w'), Gdk.ModifierType.CONTROL_MASK,
                      0, self.quit_func)
        accel.connect(Gdk.keyval_from_name('q'), Gdk.ModifierType.CONTROL_MASK,
                      0, self.quit_func)
        # accel.connect(Gdk.keyval_from_name('a'), Gdk.ModifierType.CONTROL_MASK,
        #               0, self.select_all_rows)
        self.add_accel_group(accel)

    def create_pool_managebar(self):
        self.pool_managebar = Gtk.HBox()

        self.pool_selector = Gtk.ComboBoxText(tooltip_text='Pool path')
        pool_names = Gtk.ListStore(str, str, str, str)

        #        if self.pool != None:
        #            [self.pool_names.append([name]) for name in self.pool.datapool.keys()]

        self.pool_selector.set_model(pool_names)

        cell = self.pool_selector.get_cells()[0]
        cell.set_property('ellipsize', Pango.EllipsizeMode.MIDDLE)

        type_cell = Gtk.CellRendererText(foreground='gray', style=Pango.Style.ITALIC)
        self.pool_selector.pack_start(type_cell, 0)
        self.pool_selector.add_attribute(type_cell, 'text', 2)
        state_cell = Gtk.CellRendererText(foreground='red')
        self.pool_selector.pack_start(state_cell, 0)
        self.pool_selector.add_attribute(state_cell, 'text', 1)

        self.pool_selector.connect('changed', self.select_pool)

        icon_path = os.path.join(self.cfg.get('paths', 'ccs'), 'pixmap/func.png')
        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(icon_path, 32, 32)
        plot_butt = Gtk.Button(image=Gtk.Image.new_from_pixbuf(pixbuf), tooltip_text='Parameter Plotter')
        # plot_butt.connect('button-press-event', self.show_context_menu, self.context_menu())
        plot_butt.connect('clicked', self.plot_parameters)

        icon_path = os.path.join(self.cfg.get('paths', 'ccs'), 'pixmap/monitor.png')
        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(icon_path, 32, 32)
        self.mon_butt = Gtk.Button(image=Gtk.Image.new_from_pixbuf(pixbuf), tooltip_text='Parameter Monitor')
        self.mon_butt.connect('clicked', self.monitor_parameters)
        self.mon_butt.connect('button-press-event', self.show_context_menu, self.context_menu())

        dump_butt = Gtk.Button.new_from_icon_name('gtk-save', Gtk.IconSize.LARGE_TOOLBAR)
        dump_butt.set_tooltip_text('Save pool')
        dump_butt.connect('clicked', self.save_pool)
        load_butt = Gtk.Button.new_from_icon_name('gtk-open', Gtk.IconSize.LARGE_TOOLBAR)
        load_butt.set_tooltip_text('Load pool')
        load_butt.connect('clicked', self.load_pool)
        extract_butt = Gtk.Button.new_from_icon_name('gtk-paste', Gtk.IconSize.LARGE_TOOLBAR)
        extract_butt.set_tooltip_text('Extract packets')
        extract_butt.connect('clicked', self.collect_packet_data)

        # live buttons
        self.rec_butt = Gtk.Button(image=Gtk.Image.new_from_icon_name('gtk-media-record', Gtk.IconSize.LARGE_TOOLBAR),
                                   tooltip_text='Manage recording to LIVE pool')
        self.rec_butt.connect('clicked', self.start_recording)
        self.stop_butt = Gtk.Button(image=Gtk.Image.new_from_icon_name('gtk-media-stop', Gtk.IconSize.LARGE_TOOLBAR),
                                    tooltip_text='Stop recording to currently selected LIVE pool')
        self.stop_butt.set_sensitive(False)
        self.stop_butt.connect('clicked', self.stop_recording)

        clear_butt = Gtk.Button.new_from_icon_name('edit-clear', Gtk.IconSize.LARGE_TOOLBAR)
        clear_butt.set_tooltip_text('Clear current pool')
        clear_butt.connect('clicked', self.clear_pool)

        self.univie_box = self.create_univie_box()

        bigd = Gtk.Button.new_from_icon_name('gtk-justify-fill', Gtk.IconSize.LARGE_TOOLBAR)
        bigd.set_tooltip_text('Open Large Data Viewer')
        bigd.connect('clicked', self.show_bigdata)

        self.pool_managebar.pack_start(self.pool_selector, 1, 1, 0)
        self.pool_managebar.pack_start(plot_butt, 0, 0, 0)
        self.pool_managebar.pack_start(self.mon_butt, 0, 0, 0)
        self.pool_managebar.pack_end(self.univie_box, 0, 0, 0)
        self.pool_managebar.pack_end(clear_butt, 0, 0, 0)
        self.pool_managebar.pack_end(bigd, 0, 0, 0)
        self.pool_managebar.pack_end(self.stop_butt, 0, 0, 0)
        self.pool_managebar.pack_end(self.rec_butt, 0, 0, 0)
        self.pool_managebar.pack_end(extract_butt, 0, 0, 0)
        self.pool_managebar.pack_end(dump_butt, 0, 0, 0)
        self.pool_managebar.pack_end(load_butt, 0, 0, 0)

    def create_filterbar(self):
        filterbar = Gtk.HBox()

        box = Gtk.HBox()

        column_model = Gtk.ListStore(str)
        for name in self.tm_columns[self.decoding_type]:
            column_model.append([name])

        column_name = Gtk.ComboBoxText()
        column_name.set_model(column_model)
        column_name.set_tooltip_text('Select column')

        operator_model = Gtk.ListStore(str)
        for op in ['==', '!=', '<', '>']:
            operator_model.append([op])

        operator = Gtk.ComboBoxText()
        operator.set_model(operator_model)
        operator.set_active(0)
        operator.set_tooltip_text('Select relational operator')

        filter_value = Gtk.Entry()
        filter_value.set_placeholder_text('Filter value')
        filter_value.set_tooltip_text('Filter value')
        filter_value.set_width_chars(14)
        filter_value.connect('activate', self._add_to_rules, filter_value, column_name, operator, 'AND')

        path_ccs = self.cfg.get('paths', 'ccs')

        add_to_rule_button_and = Gtk.Button()
        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(os.path.join(path_ccs, 'pixmap/intersection_icon.svg'), 10, 10)
        add_to_rule_button_and.set_image(Gtk.Image.new_from_pixbuf(pixbuf))
        add_to_rule_button_and.set_tooltip_text('AND')
        add_to_rule_button_and.connect('clicked', self._add_to_rules, filter_value, column_name, operator, 'AND')

        add_to_rule_button_or = Gtk.Button()
        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(os.path.join(path_ccs, 'pixmap/union_icon.svg'), 10, 10)
        add_to_rule_button_or.set_image(Gtk.Image.new_from_pixbuf(pixbuf))
        add_to_rule_button_or.set_tooltip_text('OR')
        add_to_rule_button_or.connect('clicked', self._add_to_rules, filter_value, column_name, operator, 'OR')

        box.pack_start(column_name, 1, 1, 0)
        box.pack_start(operator, 1, 1, 0)
        box.pack_start(filter_value, 1, 1, 0)
        box.pack_start(add_to_rule_button_and, 1, 1, 0)
        box.pack_start(add_to_rule_button_or, 1, 1, 0)

        filterbar.pack_start(box, 0, 0, 0)

        # for col in self.column_labels:
        #     if col[0] == 'Data':
        #         continue
        #     filter = Gtk.Entry()
        #     filter.set_placeholder_text(col[0])
        #     filter.set_tooltip_text(col[0])
        #     filter.set_width_chars(5)
        #     filter.connect('activate', self._update_filters)
        #     filterbar.pack_start(filter, 0, 0, 0)

        # filterbar.pack_start(Gtk.Separator.new(Gtk.Orientation.VERTICAL), 1, 0, 0)

        goto_timestamp = Gtk.Entry()
        goto_timestamp.set_placeholder_text('GOTO timestamp')
        goto_timestamp.set_tooltip_text('GOTO timestamp')
        goto_timestamp.set_width_chars(14)
        goto_timestamp.connect('activate', self._goto_timestamp)
        filterbar.pack_end(goto_timestamp, 0, 0, 0)

        goto_idx = Gtk.Entry()
        goto_idx.set_placeholder_text('GOTO idx')
        goto_idx.set_tooltip_text('GOTO idx')
        goto_idx.set_width_chars(10)
        goto_idx.connect('activate', self._goto_idx)
        filterbar.pack_end(goto_idx, 0, 0, 0)

        return filterbar

    def _add_to_rules(self, widget=None, filter_value_box=None, column_name=None, operator=None, and_or=None):

        if and_or == 'AND':
            aosym = '\u2229'
        elif and_or == 'OR':
            aosym = '\u222A'

        column = column_name.get_active_text()
        value = filter_value_box.get_text()
        operator = operator.get_active_text()

        if not column or not value or not operator:
            return

        # if self.rule_box is None:
        #     self._add_rulebox()

        rule = Gtk.HBox()
        if len(self.rule_box) == 1:
            name = Gtk.Label('{}{}{}'.format(column, operator, value))
        else:
            name = Gtk.Label('{} {}{}{}'.format(aosym, column, operator, value))
        rule.pack_start(name, 1, 1, 0)
        close_butt = Gtk.Button()
        close_butt.set_image(Gtk.Image.new_from_icon_name(Gtk.STOCK_CLOSE, Gtk.IconSize.MENU))
        close_butt.set_relief(Gtk.ReliefStyle.NONE)
        close_butt.connect('clicked', self._remove_rule)
        rule.pack_end(close_butt, 0, 0, 0)
        self.filter_rules[hash(rule)] = (self.tm_columns[self.decoding_type][column][0], operator, value, and_or)

        self.rule_box.pack_start(rule, 0, 0, 0)
        self.show_all()

        self._scroll_treeview(force_db_import=True)

    def _add_rulebox(self):
        # if self.rule_box is not None:
        #     self.rule_box.remove()
        #     self.rule_box = None
        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.NEVER)
        rule_box = Gtk.HBox()
        rule_box.set_spacing(3)
        rule_box.pack_start(Gtk.Label(label='Filters: '), 0, 0, 0)
        scrolled_window.add(rule_box)

        #scrolled_window.add(resize_view_check_button)

        # remove_rule_button = Gtk.Button()
        # remove_rule_button.set_image(Gtk.Image.new_from_icon_name('list-remove', Gtk.IconSize.BUTTON))
        # remove_rule_button.connect('clicked', self._remove_rule)
        # rule_box.pack_end(remove_rule_button, 1, 1, 0)

        rule_active_button = Gtk.Switch()
        # rule_active_button.set_image(Gtk.Image.new_from_icon_name('list-remove', Gtk.IconSize.BUTTON))
        rule_active_button.set_tooltip_text('Toggle filter rules')
        rule_active_button.connect('state-set', self._toggle_rule)
        self.filter_rules_active = rule_active_button.get_active()

        self.filter_spinner = Gtk.Spinner()

        self.rule_box = rule_box

        box = Gtk.HBox()
        box.set_spacing(3)
        box.pack_start(scrolled_window, 1, 1, 5)
        box.pack_start(self.filter_spinner, 1, 1, 1)
        box.pack_end(rule_active_button, 0, 0, 0)
        self.grid.attach(box, 0, 2, 1, 1)
        #self.filter_spinner.start()
        # self.show_all()

    def _resize_scrollbar_toggled(self, widget):
        #self._on_scrollbar_changed()
        pass

    # def resize_scrollbar(self):
    #
    #     if self.first_run or self.resize_thread.is_alive():
    #         self.first_run = False
    #         self.resize_thread = threading.Thread(target=self.small_refresh_function)
    #         return
    #
    #     self.resize_thread = threading.Thread(target=self.scrollbar_size_worker)
    #     self.resize_thread.setDaemon(True)
    #     self.resize_thread.start()
    #
    # def scrollbar_size_worker(self):
    #     #print(1)
    #     new_session = self.session_factory_storage
    #     rows = new_session.query(
    #         Telemetry[self.decoding_type]
    #     ).join(
    #         DbTelemetryPool,
    #         Telemetry[self.decoding_type].pool_id == DbTelemetryPool.iid
    #     ).filter(
    #         DbTelemetryPool.pool_name == self.active_pool_info.filename
    #     )
    #     #new_session.close()
    #     cnt = rows.count()
    #     #print(cnt)
    #     rows = self._filter_rows(rows)
    #     cnt = rows.count()
    #     #count_q = que.statement.with_only_columns([func.count()]).order_by(None)
    #     #cnt = new_session.execute(count_q).scalar()
    #     #cnt = new_session.query(que).count()
    #     #print(2)
    #     #print(cnt)
    #     GLib.idle_add(self.adj.set_upper, cnt,)
    #     #print(3)
    #     new_session.close()

    def _toggle_rule(self, widget=None, data=None):
        self.filter_rules_active = widget.get_active()
        self._scroll_treeview(force_db_import=True)

    def _remove_rule(self, widget=None):
        rule = widget.get_parent()
        self.filter_rules.pop(hash(rule))
        rule.get_parent().remove(rule)
        self.show_all()

        self._scroll_treeview()

    def _update_filters(self, widget):
        value = widget.get_text()
        value = None if value == '' else value
        self.tm_columns[self.decoding_type][widget.get_placeholder_text()][2] = value
        self._scroll_treeview()

    def _goto_idx(self, widget):
        try:
            widget.set_sensitive(False)
            goto = int(widget.get_text()) - 1
        except ValueError:
            return
        finally:
            widget.set_sensitive(True)
        upper_limit = self.adj.get_upper() - self.adj.get_page_size()
        self.offset = abs(int(min(upper_limit, goto)))
        self.limit = int(self.adj.get_page_size())
        self.feed_lines_to_view(self.fetch_lines_from_db(self.offset, self.limit, sort=None, order='asc', force_import=True))

        self.autoscroll = False
        self.adj.set_value(self.offset)

    def _goto_timestamp(self, widget):
        if self.decoding_type != 'PUS':
            self.logger.info('No Timestamp in RMAP and FEE data')
            return

        try:
            goto = widget.get_text()
        except ValueError:
            return
        upper_limit = self.adj.get_upper() - self.adj.get_page_size()
        rows = self.get_current_pool_rows()
        try:
            widget.set_sensitive(False)
            idx = rows.filter(Telemetry[self.decoding_type].timestamp.like(goto + "%"))[0].idx - 1
        except IndexError:
            return
        finally:
            widget.set_sensitive(True)
        self.offset = abs(int(min(upper_limit, idx)))
        self.limit = int(self.adj.get_page_size())
        self.feed_lines_to_view(self.fetch_lines_from_db(self.offset, self.limit, sort=None, order='asc', force_import=True))
        self.autoscroll = False

        self.adj.set_value(self.offset)

    def context_menu(self):

        menu = Gtk.Menu()

        par_sets = cfg['ccs-monitor_parameter_sets']
        for parset in par_sets:
            item = Gtk.MenuItem(label=str(parset))
            item.connect('activate', self.mon_menu, parset)
            menu.append(item)

        return menu

    def show_context_menu(self, widget, event, menu):

        if event.button != 3:
            return

        menu.show_all()
        menu.popup_at_pointer()

    def mon_menu(self, widget=None, parset=None):

        if parset is not None:
            self._selected_mon_par_set = parset
            self.mon_butt.set_tooltip_text('Parameter Monitor [{}]'.format(parset))

    def check_structure_type(self):

        # If pool is changed but not created:
        model = self.pool_selector.get_model()
        if self.pool_selector.get_active_iter():
            current_selected_type = model.get_value(self.pool_selector.get_active_iter(), 2)  # Get the shown decoding type
            current_selected_pool = self.pool_selector.get_active_text()   # get the shown pool
        else:
            current_selected_type = False
            current_selected_pool = False
        if self.active_pool_info.pool_name == current_selected_pool:
            self.decoding_type = current_selected_type
            return
        '''   
        count = 0
        while count < len(model):
            value = model.get_value(model.get_iter(count), 0)  # Get the value
            if value.split(' - ')[0] == self.active_pool_info.pool_name:
                self.pool_selector.set_active_iter(model.get_iter(count))
                changed = True
                break
            count += 1
        # if no other poo'''

        # If pool is created
        # Check in the DB which datatype should be use
        new_session = self.session_factory_storage
        pool = new_session.query(
            DbTelemetryPool.protocol
        ).filter(
            DbTelemetryPool.pool_name == self.active_pool_info.filename
        )
        pool = pool.all()
        # new_session.commit()
        # time.sleep(0.5)  # with no wait query might return empty. WHY?
        # Still sometimes empty, if not pool abfrage should stopp this behaviour

        if not pool:
            self.decoding_type = 'PUS'
        elif pool[0][0] in ['PUS', 'PLMSIM']:  # If PUS decode PUS
            self.decoding_type = 'PUS'
        else:   # If a new pool is created always show RMAP
            self.decoding_type = 'RMAP'
        new_session.close()
        return

    # def get_pool_names(self, widget):
    #     if self.pool is None:
    #         return
    #
    #     self.pool_names = Gtk.ListStore(str)
    #     [self.pool_names.append([name]) for name in self.pool.datapool.keys()]
    #     self.pool_selector.set_model(self.pool_names)

    # This function fills the Active pool info variable with data form pus_datapool
    def Active_Pool_Info_append(self, pool_info=None):
        if pool_info is not None:
            self.active_pool_info = ActivePoolInfo(str(pool_info[0]), int(pool_info[1]),
                                                   str(pool_info[2]), bool(pool_info[3]))
        self.check_structure_type()
        self._set_pool_selector_tooltip()
        return self.active_pool_info

    def _set_pool_selector_tooltip(self):
        self.pool_selector.set_tooltip_text(self.active_pool_info.filename)

    def _check_pool_is_loaded(self, filename):
        model = self.pool_selector.get_model()
        for pool in model:
            if pool[3] == filename:
                self.logger.info('Pool {} already loaded'.format(filename))
                return pool
        return False

    def update_columns(self):
        columns = self.treeview.get_columns()
        for column in columns:
            self.treeview.remove_column(column)
        self.create_treeview_columns()

        self.pool_liststore = self.create_liststore()
        self.treeview.set_model(self.pool_liststore)

        # self.scrolled_treelist.add(self.treeview)

        self.show_all()

    def select_pool(self, selector, new_pool=None):

        active_info = selector.get_model()[selector.get_active_iter()]

        if new_pool is None:
            pool_name = active_info[3]
        else:
            pool_name = new_pool

        new_session = self.session_factory_storage()
        try:
            live = False
            dbpool = new_session.query(DbTelemetryPool).filter(DbTelemetryPool.pool_name == pool_name).first()

            if active_info[0] == active_info[3]:  # check if pool is loaded from a file
                live = True

            if dbpool is not None:
                self.Active_Pool_Info_append(pool_info=[pool_name, dbpool.modification_time, os.path.basename(pool_name), live])
            else:
                self.Active_Pool_Info_append(pool_info=None)

        except Exception as err:
            self.logger.warning(err)
            return
        finally:
            new_session.close()

        self.update_columns()
        # self._set_pool_list_and_display()

        if not self.active_pool_info.live:
            self.stop_butt.set_sensitive(False)
        else:
            self.stop_butt.set_sensitive(True)
            self.refresh_treeview(pool_name)
        self.adj.set_upper(self.count_current_pool_rows())
        self.adj.set_value(0)
        self._on_scrollbar_changed(adj=self.adj)

        # queue = self.queues[pool_name]
        #
        # if queue is not None:
        #     self.pool_liststore.clear()
        #     self.pckt_queue = queue
        #     self.pool_name = pool_name
        #     if self.pool is not None:
        #         self.model_unset = True
        #         self.pool.reset_queue_seq(pool_name, queue)
        #         # self.change_cursor(self.scrolled_treelist.get_window(),'progress')

    def clear_pool(self, widget):

        # don't clear static pools
        if self.active_pool_info.filename.count('/'):
            return

        pool_name = self.get_active_pool_name()

        if pool_name is None:
            return

        widget.set_sensitive(False)
        poolmgr = cfl.get_module_handle('poolmanager', timeout=2)

        if not poolmgr:
            widget.set_sensitive(True)
            return

        poolmgr.Functions('_clear_pool', pool_name)
        # self.active_pool_info = poolmgr.Dictionaries('loaded_pools', pool_name)
        self.Active_Pool_Info_append(poolmgr.Dictionaries('loaded_pools', pool_name))
        self.offset = 0

        self.autoscroll = True
        self.autoselect = True

        self.adj.set_upper(self.count_current_pool_rows())
        self._on_scrollbar_changed()
        widget.set_sensitive(True)

    def create_univie_box(self):
        """
        Creates the Univie Button which can be found in every application, Used to Start all parts of the CCS and
        manage communication
        :return:
        """
        univie_box = Gtk.HBox()
        univie_button = Gtk.ToolButton()
        # button_run_nextline.set_icon_name("media-playback-start-symbolic")
        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(
            self.cfg.get('paths', 'ccs') + '/pixmap/Icon_Space_blau_en.png', 48, 48)
        icon = Gtk.Image.new_from_pixbuf(pixbuf)
        univie_button.set_icon_widget(icon)
        univie_button.set_tooltip_text('Applications and About')
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
            vbox.pack_start(start_button, False, True, 0)

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
        vbox.pack_start(about_button, False, True, 10)

        self.popover.add(vbox)
        self.popover.set_position(Gtk.PositionType.BOTTOM)
        self.popover.set_relative_to(univie_button)

        return univie_box

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

    def _on_select_about_dialog(self, action):
        cfl.about_dialog(self)
        return

    def get_active_pool_name(self):
        return self.pool_selector.get_active_text()

    def update_pool_view(self, pool_name, pmgr_load_pool=None, instance=1):
        """
        Used to change the view to given pool, or create a new entry if it does not exist
        Mostly used by Poolmanger GUI 'Display' Button
        :param pool_name: Name of the pool to change to or to create
        :return:
        """
        # If Active (Shown) Pool is the one dont do anything
        if pool_name == self.get_active_pool_name():
            return
        changed = False
        #self.select_pool(False, new_pool=pool_name)
        model = self.pool_selector.get_model()
        # It will check all entries in the Pool selector and change to the one if possible
        count = 0
        while count < len(model):
            value = model.get_value(model.get_iter(count), 0)  # Get the value
            if value == pool_name:  # If the wanted connection is found change to it
                self.pool_selector.set_active_iter(model.get_iter(count))
                changed = True
                break
            count += 1
        # if no other pool could be found create a new one
        if not changed:
            if not pmgr_load_pool:
                self.set_pool(pool_name, instance=instance)
            else:
                self.set_pool(pool_name, pmgr_load_pool, instance=instance)

        # Instance has to be used only here, explanation is found in pus_datapool where this function is called
        if instance:
            poolmgr = cfl.dbus_connection('poolmanager', instance)
            cfl.Functions(poolmgr, 'loaded_pools_func', self.active_pool_info.pool_name, self.active_pool_info)
        return

    def create_tm_data_viewer(self):
        box = Gtk.VBox()

        self.decoder_box = Gtk.VBox()
        decoder_bar = self.create_decoder_bar()
        self.decoder_box.pack_start(decoder_bar, 1, 1, 1)
        box.pack_start(self.decoder_box, 0, 0, 0)

        self.rawswitch = Gtk.CheckButton.new_with_label('Decode Source Data')
        self.rawswitch.connect('toggled', self.set_tm_data_view, None, True)
        self.rawswitch.connect('toggled', self._update_user_tm_decoders)
        switchbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        switchbox.pack_start(self.rawswitch, 0, 0, 0)

        self.calibrated_switch = Gtk.CheckButton.new_with_label('Calibrated')
        self.calibrated_switch.set_sensitive(False)
        self.calibrated_switch.connect('toggled', self.set_tm_data_view, None, True)
        self.rawswitch.connect('toggled', self._enable_calibrated_switch)

        switchbox.pack_start(self.calibrated_switch, 0, 0, 0)

        ctrlbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        ctrlbox.pack_start(switchbox, 0, 0, 0)

        self.hexview = Gtk.Label()
        self.hexview.set_selectable(True)
        ctrlbox.pack_end(self.hexview, 1, 1, 0)

        box.pack_start(ctrlbox, 0, 0, 3)

        scrolled_header_view = Gtk.ScrolledWindow()
        scrolled_header_view.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.NEVER)
        # self.tm_data_viewer.set_hexpand(True)
        self.tm_header_view = Gtk.TextView(editable=False, cursor_visible=False)
        scrolled_header_view.add(self.tm_header_view)
        box.pack_start(scrolled_header_view, 0, 0, 0)

        scrolled_tm_view = Gtk.ScrolledWindow()
        self.tm_data_view = self.create_tm_data_viewer_list(decode=False, create=True)
        data_selection = self.tm_data_view.get_selection()
        data_selection.connect('changed', self.set_hexview)
        scrolled_tm_view.add(self.tm_data_view)
        box.pack_start(scrolled_tm_view, 1, 1, 0)

        return box

    def _enable_calibrated_switch(self, *args):
        if self.rawswitch.get_active():
            self.calibrated_switch.set_sensitive(True)
            self.calibrated_switch.set_active(True)
        else:
            self.calibrated_switch.set_sensitive(False)
            self.calibrated_switch.set_active(False)

    def create_tm_data_viewer_list(self, decode=False, create=False):
        tm_data_model = Gtk.ListStore(str, str, str, str)
        if create:
            listview = Gtk.TreeView()
            listview.set_model(tm_data_model)

            # Set up Drag and Drop
            listview.drag_source_set(Gdk.ModifierType.BUTTON1_MASK, [], Gdk.DragAction.COPY)
            listview.drag_source_set_target_list(None)
            listview.drag_source_add_text_targets()

            listview.connect("drag-data-get", self.on_drag_tmdata_get)

        else:
            listview = self.tm_data_view
            for c in listview.get_columns():
                listview.remove_column(c)
            listview.set_model(tm_data_model)

        if decode:
            for i, column_title in enumerate(['Parameter', 'Value', 'Unit']):
                render = Gtk.CellRendererText()
                column = Gtk.TreeViewColumn(column_title, render, text=i)
                # column.set_cell_data_func(render, self.text_colour2)

                column.set_sort_column_id(i)
                column.set_clickable(True)
                column.set_resizable(True)
                # column.connect('clicked', self.column_clicked)
                listview.append_column(column)

            render = Gtk.CellRendererText()
            column = Gtk.TreeViewColumn('tooltip', render, text=3)
            column.set_visible(False)
            listview.append_column(column)
            listview.set_tooltip_column(3)

        else:
            for i, column_title in enumerate(['BYTEPOS', 'HEX', 'DEC', 'ASCII']):
                render = Gtk.CellRendererText()
                column = Gtk.TreeViewColumn(column_title, render, text=i)
                # column.set_cell_data_func(render, self.text_colour2)
                column.set_resizable(True)
                listview.append_column(column)

        if create:
            return listview

    def on_drag_tmdata_get(self, treeview, drag_context, selection_data, info, time, *args):
        treeselection = treeview.get_selection()
        model, my_iter = treeselection.get_selected()
        selection_data.set_text('{} = {}'.format(*model[my_iter][:2]), -1)

    def create_decoder_bar(self):
        box = Gtk.VBox()

        box1 = Gtk.HBox()
        package_button = Gtk.Button(label='Create TM Structure')
        package_button.set_image(Gtk.Image.new_from_icon_name('list-add', Gtk.IconSize.MENU))
        package_button.set_tooltip_text('Create user defined TM packet structure')
        package_button.set_always_show_image(True)

        parameter_button = Gtk.Button(label='Create Parameter')
        parameter_button.set_image(Gtk.Image.new_from_icon_name('list-add', Gtk.IconSize.MENU))
        parameter_button.set_tooltip_text('Create user defined parameter')
        parameter_button.set_always_show_image(True)

        decode_udef_check = Gtk.CheckButton.new_with_label('UDEF')
        decode_udef_check.set_tooltip_text('Force decoding with custom packet structures')

        package_button.connect('clicked', self.add_new_user_package)
        parameter_button.connect('clicked', self.add_decode_parameter)
        decode_udef_check.connect('toggled', self.set_decoding_order)

        box1.pack_start(package_button, 0, 0, 0)
        box1.pack_start(parameter_button, 0, 0, 0)
        box1.pack_start(decode_udef_check, 0, 0, 2)

        box2 = Gtk.HBox()

        decoder_name = Gtk.ComboBoxText.new_with_entry()
        decoder_name.set_tooltip_text('Label')
        decoder_name_entry = decoder_name.get_child()
        decoder_name_entry.set_placeholder_text('Label')
        decoder_name_entry.set_width_chars(10)

        decoder_name.set_model(self.create_decoder_model())

        bytepos = Gtk.Entry()
        bytepos.set_placeholder_text('Offset')  # +{}'.format(TM_HEADER_LEN))
        bytepos.set_tooltip_text('Offset')  # +{}'.format(TM_HEADER_LEN))
        bytepos.set_width_chars(7)

        bytelength = Gtk.Entry()
        bytelength.set_placeholder_text('Length')
        bytelength.set_tooltip_text('Length')
        bytelength.set_width_chars(7)

        add_button = Gtk.Button(label=' Decoder')
        add_button.set_image(Gtk.Image.new_from_icon_name('list-add', Gtk.IconSize.MENU))
        add_button.set_tooltip_text('Add byte decoder')
        add_button.set_always_show_image(True)

        decoder_name.connect('changed', self.fill_decoder_mask, bytepos, bytelength)
        add_button.connect('clicked', self.add_decoder, decoder_name, bytepos, bytelength)

        box2.pack_start(decoder_name, 0, 1, 0)
        box2.pack_start(bytepos, 0, 0, 0)
        box2.pack_start(bytelength, 0, 0, 0)
        box2.pack_start(add_button, 0, 0, 0)

        box.pack_start(box1, 0, 0, 0)
        box.pack_start(box2, 0, 0, 0)

        self.decoder_dict = {}
        self.UDEF = False

        return box

    def add_decode_parameter(self, widget):
        cfl.add_decode_parameter(parentwin=self)

    def add_new_user_package(self, widget):
        cfl.add_tm_decoder(parentwin=self)

    def set_decoding_order(self, widget):

        if widget.get_active():
            self.UDEF = True
        else:
            self.UDEF = False

        self.set_tm_data_view()

    def create_decoder_model(self):
        model = Gtk.ListStore(str)

        # if self.cfg.has_section('user_decoders'):
        #    for decoder in self.cfg['user_decoders'].keys():
        #        model.append([decoder])

        for decoder in self.cfg['ccs-user_decoders'].keys():
            len = self.cfg['ccs-user_decoders'][decoder]
            if 'bytelen' in len:
                model.append([decoder])

        return model

    def fill_decoder_mask(self, widget, bytepos=None, bytelen=None):
        decoder = widget.get_active_text()

        # if not self.cfg.has_option('user_decoders',decoder):
        #    return

        if self.cfg.has_option('ccs-user_decoders', decoder):
            data = json.loads(self.cfg['ccs-user_decoders'][decoder])

            bytepos.set_text(str(data['bytepos']))
            bytelen.set_text(str(data['bytelen']))

    def add_decoder(self, widget, decoder_name, byteoffset, bytelength):
        try:
            label, bytepos, bytelen = decoder_name.get_active_text(), int(byteoffset.get_text()), int(bytelength.get_text())
        except Exception as err:
            self.logger.info(err)
            return

        if label in (None, ''):
            return

        self.decoder_dict[label] = {'bytepos': bytepos, 'bytelen': bytelen}
        try:
            self.cfg.save_option_to_file('ccs-user_decoders', label, json.dumps(self.decoder_dict[label]))
        except AttributeError:
            self.logger.info('Could not save decoder to cfg')

        decoder_name.set_model(self.create_decoder_model())

        box = Gtk.HBox()

        name = Gtk.Label(label=decoder_name.get_active_text())
        name.set_tooltip_text('bytes {}-{}'.format(bytepos, bytepos + bytelen - 1))
        hexa = Gtk.Label()
        uint = Gtk.Label()
        bina = Gtk.Label()

        box.pack_start(name, 1, 1, 0)

        close_butt = Gtk.Button()
        close_butt.set_image(Gtk.Image.new_from_icon_name(Gtk.STOCK_CLOSE, Gtk.IconSize.MENU))
        close_butt.set_relief(Gtk.ReliefStyle.NONE)

        box.pack_end(close_butt, 0, 0, 0)
        box.pack_end(bina, 1, 0, 1)
        box.pack_end(uint, 1, 0, 1)
        box.pack_end(hexa, 1, 0, 1)

        decoder_box = widget.get_parent().get_parent()
        decoder_box.pack_start(box, 0, 0, 1)

        close_butt.connect('clicked', self.remove_decoder, box, decoder_box)
        self.show_all()

        return box

    def remove_decoder(self, widget, decoder, decoder_box):
        decoder_box.remove(decoder)
        self.show_all()

    def set_decoder_view(self, tm):
        decoders = self.decoder_box.get_children()[0].get_children()[2:]

        for decoder in decoders:
            try:
                name, hexa, uint, bina, _ = decoder.get_children()
                bytepos = self.decoder_dict[name.get_label()]['bytepos']
                bytelen = self.decoder_dict[name.get_label()]['bytelen']
                byts = tm[bytepos:bytepos + bytelen]
                hexa.set_label(byts.hex().upper())
                uint.set_label(str(int.from_bytes(byts, 'big')))
                bina.set_label(bin(int.from_bytes(byts, 'big'))[2:])
            except Exception as err:
                self.logger.info(err)
                hexa.set_label('###')
                uint.set_label('###')
                bina.set_label('###')

    def set_hexview(self, widget=None, data=None):
        if self.rawswitch.get_active():
            model, treepath = widget.get_selected_rows()
            if treepath:
                value = model[treepath[0]][3]
                self.hexview.set_text(value)

    def _update_user_tm_decoders(self, widget):
        if widget.get_active():
            importlib.reload(cfl)

    @delayed(10)
    def set_tm_data_view(self, selection=None, event=None, change_columns=False, floatfmt='.7G'):
        if not self.active_pool_info:
            self.logger.warning('No active pool')
            return

        if self.decoding_type != 'PUS' and self.rawswitch.get_active():
            self.logger.info('Cannot decode parameters for RMAP or FEE data packets')
            buf = Gtk.TextBuffer(text='Parameter view not available for non-PUS packets')
            self.tm_header_view.set_buffer(buf)
            self.tm_data_view.get_model().clear()
            return

        if change_columns:
            self.tm_data_view.freeze_child_notify()
            self.create_tm_data_viewer_list(decode=self.rawswitch.get_active(), create=False)
            self.tm_data_view.thaw_child_notify()
        # print(time.time(), self.autoselect)
        # self.adj.set_upper(self.count_current_pool_rows())
        # textview = self.tm_data_viewer.get_child()
        datamodel = self.tm_data_view.get_model()

        if not isinstance(selection, Gtk.TreeSelection):
            toggle = True
            selection = self.treeview.get_selection()
        else:
            toggle = False

        # nrows = selection.count_selected_rows()
        nrows = len(self.currently_selected)
        if nrows > 1:
            self.tm_header_view.set_buffer(Gtk.TextBuffer(text='{} packets selected'.format(nrows)))
            datamodel.clear()
            return

        if selection is None:
            return

        model, treepath = selection.get_selected_rows()

        if len(treepath) == 0:
            return
        else:
            rowidx = model[treepath][0]

        if rowidx == self.last_decoded_row and not toggle:
            return
        else:
            self.last_decoded_row = rowidx

        tm_index = model[treepath[0]][0]
        new_session = self.session_factory_storage
        raw = new_session.query(
            Telemetry[self.decoding_type].raw
        ).join(
            DbTelemetryPool,
            DbTelemetryPool.iid == Telemetry[self.decoding_type].pool_id
        ).filter(
            DbTelemetryPool.pool_name == self.active_pool_info.filename,
            Telemetry[self.decoding_type].idx == tm_index
        ).first()
        if not raw:
            new_session.close()
            return
        tm = raw[0]
        new_session.close()
        self.set_decoder_view(tm)

        if self.rawswitch.get_active():
            self.tm_header_view.set_monospace(False)
            datamodel.clear()
            nocalibration = not self.calibrated_switch.get_active()
            try:
                if self.UDEF:
                    data = cfl.Tmformatted(tm, textmode=False, udef=True, nocal=nocalibration, floatfmt=floatfmt)
                    buf = Gtk.TextBuffer(text=cfl.Tm_header_formatted(tm) + '\n{}\n'.format(data[1]))
                    self._feed_tm_data_view_model(datamodel, data[0])
                else:
                    data = cfl.Tmformatted(tm, textmode=False, nocal=nocalibration, floatfmt=floatfmt)
                    buf = Gtk.TextBuffer(text=cfl.Tm_header_formatted(tm) + '\n{}\n'.format(data[1]))
                    self._feed_tm_data_view_model(datamodel, data[0])

            except Exception as error:
                buf = Gtk.TextBuffer(text='Error in decoding packet data:\n{}\n'.format(error))

        else:
            self.tm_header_view.set_monospace(False)

            if self.decoding_type != 'PUS':
                tmio = io.BytesIO(tm)
                headers, _, _ = cfl.extract_spw(tmio)
                header = headers[0].raw
                headlen = len(header)
                head = cfl.spw_header_formatted(headers[0])
            else:
                head = cfl.Tm_header_formatted(tm, detailed=True)
                headlen = TC_HEADER_LEN if (tm[0] >> 4 & 1) else TM_HEADER_LEN

            tmsource = tm[headlen:]
            byteview = [[str(n + headlen), '{:02X}'.format(i), str(i), ascii(chr(i)).strip("'")] for n, i in enumerate(tmsource[:])]
            self._feed_tm_data_view_model(datamodel, byteview)
            buf = Gtk.TextBuffer(text=head + '\n')

        self.tm_header_view.set_buffer(buf)

    def _feed_tm_data_view_model(self, model, data):
        try:
            if not isinstance(data[0], list):
                data = [data]
        except IndexError:
            model.clear()
            return
        self.tm_data_view.freeze_child_notify()
        model.clear()
        for row in data:
            if row:
                model.append(row)
        self.tm_data_view.thaw_child_notify()

    def save_pool(self, widget):
        dialog = SavePoolDialog(parent=self, decoding_type=self.decoding_type)

        response = dialog.run()

        if response == Gtk.ResponseType.OK:
            filename = dialog.get_filename()

            modes = dialog.formatbox.get_children()
            if modes[0].get_active():
                mode = 'binary'
            elif modes[1].get_active():
                mode = 'hex'
            elif modes[2].get_active():
                mode = 'text'

            merge = dialog.merge_tables.get_active()

            if dialog.selectiononly.get_active():
                # selection = self.treeview.get_selection()
                # model, paths = selection.get_selected_rows()
                # indices = [model[path][0] for path in paths]
                indices = self.currently_selected
                # tmlist = self.ccs.get_packet_selection(indices, self.get_active_pool_name())
                tmlist = self.get_packets_from_indices(indices=indices, filtered=dialog.save_filtered.get_active())
            else:
                # tmlist = self.pool.datapool[self.get_active_pool_name()]['pckts'].values()
                indices = None
                tmlist = self.get_packets_from_indices(filtered=dialog.save_filtered.get_active(), merged_tables=merge)

            crc = dialog.crccheck.get_active()
            cfl.Tmdump(filename, tmlist, mode=mode, st_filter=None, check_crc=crc)
            self.logger.info(
                '{} packets from {} saved as {} in {} mode (CRC {})'.format(len(list(tmlist)),
                                                                            self.get_active_pool_name(),
                                                                            filename,
                                                                            mode.upper(), crc))
            if dialog.store_in_db.get_active():
                self.save_pool_in_db(filename, int(os.path.getmtime(filename)), indices)
        dialog.destroy()

    def save_pool_in_db(self, filename, timestamp, indices=None):
        # this function only works for PUS packets at the moment
        if self.decoding_type != 'PUS':
            self.logger.error('Save to DB not supported for {} protocol.'.format(self.decoding_type))
            return

        new_session = self.session_factory_storage
        self.logger.info('Deleting any existing DB entries associated with {}'.format(filename))
        new_session.execute(
           'DELETE tm FROM tm INNER JOIN tm_pool ON tm.pool_id=tm_pool.iid WHERE tm_pool.pool_name="{}"'.format(
               filename))
        new_session.execute('DELETE tm_pool FROM tm_pool WHERE tm_pool.pool_name="{}"'.format(filename))
        new_session.commit()
        self.logger.debug('...deleted')

        self.logger.info('Storing current pool {} in DB for {}'.format(self.active_pool_info.pool_name, filename))

        newPoolRow = DbTelemetryPool(pool_name=filename, protocol='PUS', modification_time=timestamp)

        new_session.add(newPoolRow)
        new_session.flush()
        rows = new_session.query(
            Telemetry[self.decoding_type]
        ).join(
            DbTelemetryPool,
            DbTelemetryPool.iid == Telemetry[self.decoding_type].pool_id
        ).filter(
            DbTelemetryPool.pool_name == self.active_pool_info.filename)
        if indices is not None:
            rows = rows.filter(Telemetry[self.decoding_type].idx.in_(indices))
        for idx, row in enumerate(rows, 1):
            new_session.add(Telemetry[self.decoding_type](pool_id=newPoolRow.iid,
                                                          idx=idx,
                                                          is_tm=row.is_tm,
                                                          apid=row.apid,
                                                          seq=row.seq,
                                                          len_7=row.len_7,
                                                          stc=row.stc,
                                                          sst=row.sst,
                                                          destID=row.destID,
                                                          timestamp=row.timestamp,
                                                          data=row.data,
                                                          raw=row.raw))

        # new_session.flush()
        new_session.commit()
        new_session.close()

    '''
    # Poolmgr can call the LoadInfo Window via dbus, needed for the load_pool function
    def LoadInfo(self):
        loadinfo = LoadInfo(parent=self)
        return loadinfo
    '''
    def load_saved_pool(self, filename=None, protocol='PUS'):
        if filename is not None:
            self.load_pool(widget=None, filename=filename, protocol=protocol)
        else:
            self.logger.error('Please give a Filename')
            return 'Please give a Filename'
        return

    # Whole function is now done in Poolmgr
    # def load_pool2(self, widget=None, filename=None, brute=False, force_db_import=False, protocol='PUS'):
    #     if cfl.is_open('poolmanager', cfl.communication['poolmanager']):
    #         poolmgr = cfl.dbus_connection('poolmanager', cfl.communication['poolmanager'])
    #     else:
    #         cfl.start_pmgr(gui=False)
    #         #path_pm = os.path.join(confignator.get_option('paths', 'ccs'), 'pus_datapool.py')
    #         #subprocess.Popen(['python3', path_pm, '--nogui'])
    #         self.logger.info('Poolmanager was started in the background')
    #
    #         # Here we have a little bit of a tricky situation since when we start the Poolmanager it wants to tell the
    #         # Manager to which number it can talk to but it can only do this when PoolViewer is not busy...
    #         # Therefore it is first found out which number the new Poolmanager will get and it will be called by that
    #         our_con = []
    #         # Look for all connections starting with com.poolmanager.communication,
    #         # therefore only one loop over all connections is necessary
    #         for service in dbus.SessionBus().list_names():
    #             if service.startswith(self.cfg['ccs-dbus_names']['poolmanager']):
    #                 our_con.append(service)
    #
    #         new_pmgr_nbr = 0
    #         if len(our_con) != 0:   # If an active PoolManager is found they have to belong to another prject
    #             for k in range(1, 10):  # Loop over all possible numbers
    #                 for j in our_con:   # Check every number with every PoolManager
    #                     if str(k) == str(j[-1]):    # If the number is not found set variable found to True
    #                         found = True
    #                     else:   # If number is found set variable found to False
    #                         found = False
    #                         break
    #
    #                 if found:   # If number could not be found save the number and try connecting
    #                     new_pmgr_nbr = k
    #                     break
    #
    #         else:
    #             new_pmgr_nbr = 1
    #
    #         if new_pmgr_nbr == 0:
    #             self.logger.warning('The maximum amount of Poolviewers has been reached')
    #             return
    #
    #         # Wait a maximum of 10 seconds to connect to the poolmanager
    #         i = 0
    #         while i < 100:
    #             if cfl.is_open('poolmanager', new_pmgr_nbr):
    #                 poolmgr = cfl.dbus_connection('poolmanager', new_pmgr_nbr)
    #                 break
    #             else:
    #                 i += 1
    #                 time.sleep(0.1)
    #
    #     if filename is not None and filename:
    #         pool_name = filename.split('/')[-1]
    #         try:
    #             new_pool = cfl.Functions(poolmgr, 'load_pool_poolviewer', pool_name, filename, brute, force_db_import,
    #                                          self.count_current_pool_rows(), self.my_bus_name[-1], protocol)
    #
    #         except:
    #             self.logger.warning('Pool could not be loaded, File: ' + str(filename) + 'does probably not exist')
    #             # print('Pool could not be loaded, File' +str(filename)+ 'does probably not exist')
    #             return
    #     else:
    #         dialog = Gtk.FileChooserDialog(title="Load File to pool", parent=self, action=Gtk.FileChooserAction.OPEN)
    #         dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK)
    #
    #         area = dialog.get_content_area()
    #         hbox, force_button, brute_extract, type_buttons = self.pool_loader_dialog_buttons()
    #
    #         area.add(hbox)
    #         area.show_all()
    #
    #         dialog.set_transient_for(self)
    #
    #         response = dialog.run()
    #
    #         if response == Gtk.ResponseType.OK:
    #             filename = dialog.get_filename()
    #             pool_name = filename.split('/')[-1]
    #             isbrute = brute_extract.get_active()
    #             force_db_import = force_button.get_active()
    #             for button in type_buttons:
    #                 if button.get_active():
    #                     package_type = button.get_label()
    #         else:
    #             dialog.destroy()
    #             return
    #
    #         if package_type:
    #             if package_type not in ['PUS', 'PLMSIM']:
    #                 package_type == 'SPW'
    #
    #         # package_type defines which type was selected by the user, if any was selected
    #         new_pool = cfl.Functions(poolmgr, 'load_pool_poolviewer', pool_name, filename, isbrute, force_db_import,
    #                                  self.count_current_pool_rows(), self.my_bus_name[-1], package_type)
    #
    #         dialog.destroy()
    #
    #     if new_pool:
    #         self._set_pool_list_and_display(new_pool)

    def load_pool(self, widget=None, filename=None, brute=False, force_db_import=False, protocol='PUS', no_duplicates=True):

        if filename is None:
            dialog = Gtk.FileChooserDialog(title="Load File to pool", parent=self, action=Gtk.FileChooserAction.OPEN)
            dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK)

            area = dialog.get_content_area()
            hbox, force_button, brute_extract, type_buttons = self.pool_loader_dialog_buttons()

            area.add(hbox)
            area.show_all()

            dialog.set_transient_for(self)

            response = dialog.run()

            if response == Gtk.ResponseType.OK:
                filename = dialog.get_filename()
                brute = brute_extract.get_active()
                force_db_import = force_button.get_active()
                for button in type_buttons:
                    if button.get_active():
                        protocol = button.get_label()
            else:
                dialog.destroy()
                return

            if protocol:
                if protocol not in ['PUS', 'PLMSIM']:
                    protocol = 'SPW'

            dialog.destroy()

        if no_duplicates and (not force_db_import):
            loadeditem = self._check_pool_is_loaded(filename)
            if loadeditem:
                self.pool_selector.set_active_iter(loadeditem.iter)
                return

        new_pool, loader_thread = cfl.DbTools.sql_insert_binary_dump(filename, brute=brute, force_db_import=force_db_import,
                                                                     protocol=protocol, pecmode='warn', parent=self)

        self._set_pool_list_and_display(new_pool)

        if loader_thread is not None:
            checkloader_thread = threading.Thread(target=self._db_loading_checker, args=[new_pool, loader_thread])
            checkloader_thread.daemon = True
            checkloader_thread.start()

    def _db_loading_checker(self, pool_info, thread):

        try:
            model = self.pool_selector.get_model()
            for pool in model:
                if pool[3] == pool_info.filename:
                    pool[1] = '[LOAD]'

            while thread.is_alive():
                time.sleep(1)

            model = self.pool_selector.get_model()

            for pool in model:
                if pool[3] == pool_info.filename:
                    pool[1] = None
                    break

            # check via filename if loaded pool is currently viewed
            if model[self.pool_selector.get_active_iter()][3] == pool_info.filename:
                # self.select_pool(self.pool_selector, pool_info.filename)
                self.adj.set_upper(self.count_current_pool_rows(pool_info=pool_info))
                self.adj.set_value(0)
                self._on_scrollbar_changed(adj=self.adj)

        except Exception as err:
            self.logger.error(err)
            model = self.pool_selector.get_model()
            for pool in model:
                if pool[3] == pool_info.filename:
                    pool[1] = 'ERR'

    def pool_loader_dialog_buttons(self):
        '''
        Small Function to set up the buttons for the Pool Loading Window
        @return: A Gtk.HBox
        '''
        hbox = Gtk.HBox()
        hbox.set_border_width(10)
        brute_extract = Gtk.CheckButton.new_with_label('Search valid packets')
        brute_extract.set_tooltip_text('Keep searching for valid packets if invalid ones are encountered')
        force_button = Gtk.CheckButton.new_with_label('Force DB Import')
        force_button.set_tooltip_text(
            'Do a fresh import of the packets in the dump, even if they are already in the DB')


        hbox.pack_end(brute_extract, 0, 0, 0)
        hbox.pack_end(force_button, 0, 0, 0)

        import_pool_win_buttons = []
        i = 1
        # for packet_type in self.column_labels:
        for packet_type in ['PUS', 'SPW']:
            if i == 1:
                button1 = Gtk.RadioButton(label=str(packet_type))
                button1.set_tooltip_text("Imported file has {} protocol".format(packet_type))
                button1.set_sensitive(True)
                import_pool_win_buttons.append(button1)
                hbox.pack_end(button1, 0, 0, 0)
            else:
                button = Gtk.RadioButton.new_from_widget(button1)
                button.set_label(str(packet_type))
                button.set_sensitive(True)
                button.set_tooltip_text("Imported file has {} protocol".format(packet_type))
                import_pool_win_buttons.append(button)
                hbox.pack_end(button, 0, 0, 0)
            i += 1

        # force_button.connect("toggled", self._on_force_button_changed, import_pool_win_buttons)
        # hbox.pack_end(force_button, 0, 0, 0)
        return hbox, force_button, brute_extract, import_pool_win_buttons

    def _on_force_button_changed(self, widget, buttons):
        if widget.get_active():
            for button in buttons:
                button.set_sensitive(True)
        else:
            for button in buttons:
                button.set_sensitive(False)


    # Glib.idle_add only does only do something when there is time, sometimes this is blocked until the main loop does
    # another iteration, this nonesense function start this and lets Glib.idle add do the funciton
    # Also used to set up the thread variable in resize scrollbar
    def small_refresh_function(self):
        return

    # Only to use Glib idle add and ignore_reply keyword at the same time
    def _set_list_and_display_Glib_idle_add(self, active_pool_info_mgr=None, instance=None):
        if active_pool_info_mgr is not None:
            GLib.idle_add(self._set_pool_list_and_display(active_pool_info_mgr, instance))
        else:
            GLib.idle_add(self._set_pool_list_and_display(instance=instance))
        return

    def _set_pool_list_and_display(self, pool_info=None, instance=None):

        if pool_info is not None:
            self.Active_Pool_Info_append(pool_info)

        self.update_columns()

        self.adj.set_upper(self.count_current_pool_rows())
        self.offset = 0
        self.limit = self.adj.get_page_size()
        self._on_scrollbar_changed(adj=self.adj, force=True)
        # Check the decoding type to show a pool
        if self.decoding_type == 'PUS':
            model = self.pool_selector.get_model()
            iter = model.append([self.active_pool_info.pool_name, self.live_signal[self.active_pool_info.live], self.decoding_type, self.active_pool_info.filename])
            self.pool_selector.set_active_iter(iter)
        else:
            # If not PUS open all other possible types but show RMAP
            for packet_type in Telemetry:
                if packet_type == 'RMAP':
                    model = self.pool_selector.get_model()
                    iter = model.append([self.active_pool_info.pool_name, self.live_signal[self.active_pool_info.live], packet_type, self.active_pool_info.filename])
                    self.pool_selector.set_active_iter(iter)   # Always show the RMAP pool when created
                else:
                    model = self.pool_selector.get_model()
                    iter = model.append([self.active_pool_info.pool_name, self.live_signal[self.active_pool_info.live], packet_type, self.active_pool_info.filename])

        if self.active_pool_info.live:
            self.stop_butt.set_sensitive(True)
        else:
            self.stop_butt.set_sensitive(False)

        refresh_rate = 1  # in Hz

        GLib.timeout_add(1000 / refresh_rate, self.show_data_rate, refresh_rate, instance, priority=GLib.PRIORITY_DEFAULT)
        return True

    def collect_packet_data(self, widget):
        # selection = self.treeview.get_selection()
        # model, paths = selection.get_selected_rows()
        if not self.active_pool_info:
            self.logger.error('No pool to extract packets from')
            return
            ###############
            # If this is ever changed to all packet standards and not only PUS, be aware that further down the database is asced of ST and SST... only possible for PUS
            ###############

        indices = self.currently_selected

        dialog = ExtractionDialog(parent=self, pkttype=self.decoding_type)
        response = dialog.run()

        if response == Gtk.ResponseType.OK:
            try:
                st, sst = dialog.st.get_text(), dialog.sst.get_text()
                onlysource = dialog.sourcebox.get_active()

                new_session = self.session_factory_storage
                rows = new_session.query(
                    Telemetry[self.decoding_type]
                ).join(
                    DbTelemetryPool,
                    Telemetry[self.decoding_type].pool_id == DbTelemetryPool.iid
                ).filter(
                    DbTelemetryPool.pool_name == self.active_pool_info.filename
                ).filter(
                    Telemetry[self.decoding_type].idx.in_(indices)
                )
            except AttributeError as error:
                self.logger.error(error)
                dialog.destroy()
                return

            if st != '':
                rows = rows.filter(DbTelemetry.stc == int(st))
            if sst != '':
                rows = rows.filter(DbTelemetry.sst == int(sst))

            packets = [row.raw for row in rows]
            new_session.close()
            if onlysource:
                packetdata = [tm[TM_HEADER_LEN:-PEC_LEN] for tm in packets]
            else:
                packetdata = packets
            self.selected_packet(packetdata)
        dialog.destroy()

    def selected_packet(self, packet=None):
        if packet is not None:
            self.stored_packet = packet
            return packet
        else:
            return str(self.stored_packet)

    def get_packets_from_indices(self, indices=None, filtered=False, merged_tables=False):

        if indices is None:
            indices = []

        new_session = self.session_factory_storage

        if not merged_tables:
            rows = new_session.query(
                Telemetry[self.decoding_type]
            ).join(
                DbTelemetryPool,
                Telemetry[self.decoding_type].pool_id == DbTelemetryPool.iid
            ).filter(
                DbTelemetryPool.pool_name == self.active_pool_info.filename
            )

            if len(indices) != 0:
                rows = rows.filter(
                    Telemetry[self.decoding_type].idx.in_(indices)
                )

            if filtered and self.filter_rules_active:
                rows = self._filter_rows(rows)

            ret = [row.raw for row in rows]

        else:
            ret = self.get_raw_from_merged_tables(self.active_pool_info.filename)

        new_session.close()
        return ret

    def get_raw_from_merged_tables(self, pool_name, filtered=False):
        # db = self.session_factory_storage
        # q1 = db.query(RMapTelemetry.idx,RMapTelemetry.raw).join(DbTelemetryPool,RMapTelemetry.pool_id==DbTelemetryPool.iid).filter(DbTelemetryPool.pool_name==pool_name)
        # q2 = db.query(FEEDataTelemetry.idx,FEEDataTelemetry.raw).join(DbTelemetryPool,FEEDataTelemetry.pool_id==DbTelemetryPool.iid).filter(DbTelemetryPool.pool_name==pool_name)
        # rows = q1.union_all(q2).order_by(FEEDataTelemetry.idx)

        # if filtered and self.filter_rules_active:
        #     rows = self._filter_rows(rows)
        # return (p.raw for p in q.yield_per(1000))

        que = 'SELECT idx,raw FROM rmap_tm LEFT JOIN tm_pool ON pool_id=tm_pool.iid WHERE pool_name="{}"\
        UNION SELECT idx,raw FROM feedata_tm LEFT JOIN tm_pool ON pool_id=tm_pool.iid WHERE pool_name="{}"\
        ORDER BY idx'.format(pool_name, pool_name)

        # alternative fetch with stream
        # conn = self.session_factory_storage.connection()
        # res = conn.execution_options(stream_results=True).execute(que)
        # self.session_factory_storage.close()

        res = self.session_factory_storage.execute(que)
        return [row[1] for row in res]

    def plot_parameters(self, widget=None, parameters=None, start_live=False):

        if not self.active_pool_info.filename:
            self.logger.warning('No pool selected')
            return

        cfl.start_plotter(self.active_pool_info.filename)

    def monitor_parameters(self, widget=None, **kwargs):

        if not self.active_pool_info.filename:
            self.logger.warning('No pool selected')
            return

        cfl.start_monitor(self.active_pool_info.filename, parameter_set=self._selected_mon_par_set)

    def start_recording(self, widget=None):
        if cfl.is_open('poolmanager', cfl.communication['poolmanager']):
            poolmgr = cfl.dbus_connection('poolmanager', cfl.communication['poolmanager'])
        else:
            path_pm = os.path.join(self.cfg.get('paths', 'ccs'), 'pus_datapool.py')
            subprocess.Popen(['python3', path_pm])
            return

        if poolmgr.Variables('gui_running'):
            poolmgr.Functions('raise_window')
            return

        # Ignore_reply is no problem here since only the gui is started
        poolmgr.Functions('start_gui', ignore_reply = True)
        return

    def stop_recording(self, widget=None, pool_name=None):
        if not self.active_pool_info.live:
            return False

        if cfl.is_open('poolmanager', cfl.communication['poolmanager']):
            poolmgr = cfl.dbus_connection('poolmanager', cfl.communication['poolmanager'])
        else:
            poolmgr = None

        if pool_name is None:
            pool_name = self.active_pool_info.pool_name

        # Not necessary done in Poolmanager
        # Dictionarie in Dictionaries are not very well supported over dbus connection
        # Get dictonary connections, key pool_name, key 'recording' set to False, True to change
        # poolmgr.Dictionaries('connections', pool_name, 'recording', False, True)

        if self.active_pool_info.pool_name == pool_name:
            self.active_pool_info = ActivePoolInfo(pool_name, self.active_pool_info.modification_time, pool_name, False)
            if poolmgr:
                poolmgr.Functions('loaded_pools_func', pool_name, self.active_pool_info)

        else:
            # Check if the pool name does exist
            try:
                pinfo = poolmgr.Dictionaries('loaded_pools', pool_name)
            except (dbus.DBusException, KeyError):
                self.logger.error("Can't stop recording: pool name not in loaded pools")
                return

            pinfo_modification_time = int(pinfo[2])
            #poolmgr.Functions('loaded_pools_func', pool_name, ActivePoolInfo(pool_name, pinfo_modification_time, pool_name, False), ignore_reply=True)
            if poolmgr:
                poolmgr.Functions('loaded_pools_func', pool_name,
                                  ActivePoolInfo(pool_name, pinfo_modification_time, pool_name, False))


        # Update the Poolmanager GUI
        #poolmgr.Functions('disconnect', pool_name, ignore_reply = True)
        if poolmgr:
            poolmgr.Functions('disconnect', pool_name)

        itr = self.pool_selector.get_active_iter()
        mod = self.pool_selector.get_model()
        if mod is not None:
            mod[itr][1] = self.live_signal[self.active_pool_info.live]
            self.stop_butt.set_sensitive(False)

        return

    def stop_recording_info(self, pool_name=None):
        """
        Connection is closed by the Poolmanager, Informes the Pool Viewer to stop updating or
        Poolmanager is closed and therefore all Pools become static pools
        Functions is normally called by the poolmanager when it is closing or disconnecting any connections
        """

        # if no pool name was specified, Change all connections to static
        if not pool_name:
            mod = self.pool_selector.get_model()
            self.active_pool_info = ActivePoolInfo(self.active_pool_info.filename,
                                                   self.active_pool_info.modification_time,
                                                   self.active_pool_info.pool_name, False)
            #self.active_pool_info.live = False
            for row in mod:
                mod[row.iter][1] = self.live_signal[self.active_pool_info.live]
                self.stop_butt.set_sensitive(False)

        # If active pool is live change it to static
        elif self.active_pool_info.pool_name == pool_name:
            self.active_pool_info = ActivePoolInfo(self.active_pool_info.filename, self.active_pool_info.modification_time, self.active_pool_info.pool_name, False)

            iter = self.pool_selector.get_active_iter()
            mod = self.pool_selector.get_model()
            if mod is not None:
                mod[iter][1] = self.live_signal[self.active_pool_info.live]
                self.stop_butt.set_sensitive(False)

        # Specific Pool is no longer LIVe
        else:
            mod = self.pool_selector.get_model()
            for row in mod:
                if mod[row.iter][0] == pool_name:
                    mod[row.iter][1] = self.live_signal[self.active_pool_info.live]
                    self.stop_butt.set_sensitive(False)

        return

    def refresh_treeview(self, pool_name):
        if self.refresh_treeview_active:
            return

        self.refresh_treeview_active = True
        self.n_pool_rows = 0
        GLib.timeout_add(self.pool_refresh_rate * 1000, self.refresh_treeview_worker2, pool_name)  # priority=GLib.PRIORITY_HIGH)

    # def refresh_treeview_worker(self, pool_name):
    #     poolmgr = cfl.dbus_connection('poolmanager', cfl.communication ['poolmanager'])
    #     # while not self.pool.recordingThread.stopRecording:
    #     # Get value of dict connections, with key self.active... and key recording, True to get
    #     pool_connection_recording = cfl.Dictionaries(poolmgr, 'connections', self.active_pool_info.pool_name, 'recording', True)
    #     type = self.decoding_type
    #     #while self.pool.connections[self.active_pool_info.pool_name]['recording']:
    #     while pool_connection_recording:
    #         GLib.idle_add(self.scroll_to_bottom)
    #         time.sleep(self.pool_refresh_rate)
    #         if pool_name != self.active_pool_info.pool_name or type != self.decoding_type:
    #             dbsession.close()
    #             return
    #     self.stop_recording()

    def refresh_treeview_worker2(self, pool_name):
        if pool_name != self.active_pool_info.pool_name:
            self.refresh_treeview_active = False
            return False

        if self.active_pool_info.live:
            rows = self.get_current_pool_rows()
            if rows.first() is None:
                cnt = 0
            else:
                cnt = rows.order_by(Telemetry[self.decoding_type].idx.desc()).first().idx
            if cnt != self.n_pool_rows:
                self.scroll_to_bottom(n_pool_rows=cnt, rows=rows)
                self.n_pool_rows = cnt
                return True
            else:
                return True
        else:
            self.refresh_treeview_active = False
            return False

    def dbtest(self, pool_name, sleep=0.1):
        dbcon = self.session_factory_storage
        while self.testing:
            rows = dbcon.query(
                Telemetry[self.decoding_type]
            ).join(
                DbTelemetryPool,
                Telemetry[self.decoding_type].pool_id == DbTelemetryPool.iid
            ).filter(
                DbTelemetryPool.pool_name == pool_name
            )
            # cnt = rows.count()
            cnt = rows.order_by(Telemetry[self.decoding_type].idx.desc()).first().idx
            # print(cnt)
            rows = rows.filter(Telemetry[self.decoding_type].idx > (cnt - 100)).offset(100 - 25).limit(25).all()
            # rr=[row for row in rows]
            self.logger.info('fetched', rows[-1].idx, cnt, 'at', time.time())
            dbcon.close()
            time.sleep(sleep)
        self.logger.warning('TEST ABORTED')

    def starttest(self, pool_name, sleep=0.1):
        t = threading.Thread(target=self.dbtest, args=[pool_name, sleep])
        t.daemon = True
        t.start()

    def scroll_to_bottom(self, n_pool_rows=None, rows=None):
        if self.active_pool_info.live:
            if n_pool_rows is None:
                cnt = self.count_current_pool_rows()
            else:
                cnt = n_pool_rows
            self.adj.set_upper(cnt)
            if self.autoscroll:
                self._scroll_treeview(self.adj.get_upper(), rows=rows)
                self.reselect_rows()
        else:
            self._scroll_treeview(self.adj.get_upper(), rows=rows)

    def change_cursor(self, window, name='default'):
        window.set_cursor(Gdk.Cursor.new_from_name(Gdk.Display.get_default(), name))

    def show_data_rate(self, refresh_rate=1, instance=1):

        if not self.active_pool_info.live:
            return False

        if not instance:
            instance = 1
        try:
            pmgr = cfl.dbus_connection('poolmanager', instance)
            trashbytes, tc_data_rate, data_rate, tc_rx_bytes = pmgr.Functions('calc_data_rate', self.active_pool_info.filename, refresh_rate)
            self.statusbar.push(0, 'Trash: {:d} B | TC: {:7.3f} KiB/s | TM: {:7.3f} KiB/s'.format(
                trashbytes, tc_data_rate/1024, data_rate/1024))
            self.statusbar.set_tooltip_text('TCRX: {:d} B | TC: {:7.3f} kbps | TM: {:7.3f} kbps'.format(tc_rx_bytes, tc_data_rate/1000*8, data_rate/1000*8))
        except Exception as err:
            self.logger.debug(err)

        return True

    def show_bigdata(self, *args):
        self.bigd = BigDataViewer(self)


class ExtractionDialog(Gtk.MessageDialog):
    def __init__(self, parent=None, pkttype='PUS'):
        super(ExtractionDialog, self).__init__(title="Extract packets", parent=parent, flags=0)

        self.add_buttons(Gtk.STOCK_OK, Gtk.ResponseType.OK, Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)
        self.set_transient_for(parent)

        box = self.get_content_area()
        self.set_markup('Select Service Type and Subtype to be extracted (PUS)')

        hbox = Gtk.HBox()

        self.st = Gtk.Entry()
        self.sst = Gtk.Entry()
        self.st.set_placeholder_text('Service Type')
        self.sst.set_placeholder_text('Service Subtype')

        hbox.pack_start(self.st, 0, 0, 0)
        hbox.pack_start(self.sst, 0, 0, 0)
        hbox.set_homogeneous(True)

        self.sourcebox = Gtk.CheckButton.new_with_label('Source data only')

        box.pack_end(self.sourcebox, 0, 0, 0)
        box.pack_end(hbox, 0, 0, 5)

        if pkttype != 'PUS':
            self.st.set_sensitive(False)
            self.sst.set_sensitive(False)
            self.sourcebox.set_sensitive(False)

        self.show_all()


class SavePoolDialog(Gtk.FileChooserDialog):
    def __init__(self, parent=None, decoding_type='PUS'):
        super(SavePoolDialog, self).__init__(title="Save packets", parent=parent, action=Gtk.FileChooserAction.SAVE)
        self.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_SAVE, Gtk.ResponseType.OK)

        # self.set_transient_for(parent)

        area = self.get_content_area()

        hbox = Gtk.HBox()
        hbox.set_border_width(10)

        self.formatbox = Gtk.HBox()

        binbut = Gtk.RadioButton.new_with_label_from_widget(None, 'binary')
        hexbut = Gtk.RadioButton.new_with_label_from_widget(binbut, 'hex')
        csvbut = Gtk.RadioButton.new_with_label_from_widget(binbut, 'csv (decoded)')

        self.formatbox.pack_start(binbut, 0, 0, 3)
        self.formatbox.pack_start(hexbut, 0, 0, 3)
        self.formatbox.pack_start(csvbut, 0, 0, 3)

        self.selectiononly = Gtk.CheckButton.new_with_label('Save only selected packets')
        self.crccheck = Gtk.CheckButton.new_with_label('CRC')
        self.crccheck.set_tooltip_text('Save only packets that pass CRC')
        self.store_in_db = Gtk.CheckButton.new_with_label('Store in DB')
        self.store_in_db.set_tooltip_text('Permanently store pool in DB - THIS MAY TAKE A WHILE FOR LARGE DATASETS!')
        if decoding_type != 'PUS':
            self.store_in_db.set_sensitive(False)
        self.save_filtered = Gtk.CheckButton.new_with_label('Apply packet filter')
        self.save_filtered.set_tooltip_text('Save only packets according to the currently active poolview filter')
        self.merge_tables = Gtk.CheckButton.new_with_label('Merge tables')
        self.merge_tables.set_tooltip_text('Merge and save all packet types from the same pool/connection')

        hbox.pack_start(self.formatbox, 0, 0, 0)
        hbox.pack_start(self.selectiononly, 0, 0, 0)
        hbox.pack_start(self.crccheck, 0, 0, 0)
        hbox.pack_start(self.store_in_db, 0, 0, 0)
        hbox.pack_start(self.save_filtered, 0, 0, 0)
        hbox.pack_start(self.merge_tables, 0, 0, 0)

        hbox.set_homogeneous(True)

        area.add(hbox)  # ,0,0,10)

        self.show_all()


# TODO
class LoadPoolDialog(Gtk.FileChooserDialog):
    def __init__(self, parent=None):
        super(LoadPoolDialog, self).__init__(title="Save packets", parent=parent, action=Gtk.FileChooserAction.SAVE,
                                             buttons=(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                                                      Gtk.STOCK_SAVE, Gtk.ResponseType.OK))

        dialog = Gtk.FileChooserDialog(title="Load File to pool", parent=self, action=Gtk.FileChooserAction.OPEN)
        dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK)

        area = dialog.get_content_area()
        hbox, force_button, brute_extract, type_buttons = self.pool_loader_dialog_buttons()

        area.add(hbox)
        area.show_all()

        self.show_all()


'''
class LoadInfo(Gtk.Window):
    def __init__(self, parent=None, title=None):
        Gtk.Window.__init__(self)

        if title is None:
            self.set_title('Loading data to pool...')
        else:
            self.set_title(title)

        grid = Gtk.VBox()
        logo = Gtk.Image.new_from_file('pixmap/cheops-logo-with-additional3.png')

        self.spinner = Gtk.Spinner()
        self.spinner.set_size_request(32, 32)
        self.log = Gtk.Label()
        self.ok_button = Gtk.Button.new_with_label('OK')
        self.ok_button.connect('clicked', self.destroy_window, self)

        grid.pack_start(logo, 1, 1, 0)
        grid.pack_start(self.spinner, 1, 1, 0)
        grid.pack_start(self.log, 1, 1, 0)
        grid.pack_start(self.ok_button, 1, 1, 0)
        grid.set_spacing(2)

        self.add(grid)

        self.show_all()

    def destroy_window(self, widget, window):
        window.destroy()
'''


class RecordingDialog(Gtk.MessageDialog):
    def __init__(self, parent=None):
        Gtk.Dialog.__init__(self, "Record to pool", parent, 0,
                            buttons=(Gtk.STOCK_OK, Gtk.ResponseType.OK, Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL))

        # self.set_transient_for(parent)
        ok_butt = self.get_action_area().get_children()[0]
        ok_butt.set_always_show_image(True)
        ok_butt.set_image(Gtk.Image.new_from_icon_name('gtk-media-record', Gtk.IconSize.BUTTON))
        ok_butt.set_label('Connect')
        ok_butt.set_sensitive(True)

        box = self.get_content_area()
        self.set_markup('Start recording from socket:')

        vbox = Gtk.VBox()
        vbox.set_spacing(2)

        self.host = Gtk.Entry(text="127.0.0.1")
        self.host.connect('changed', self.check_entry, ok_butt)
        self.port = Gtk.Entry(text="5570")
        self.port.connect('changed', self.check_entry, ok_butt)
        self.pool_name = Gtk.Entry(text="LIVE")
        self.pool_name.connect('changed', self.check_entry, ok_butt)
        self.host.set_placeholder_text('Host')
        self.port.set_placeholder_text('Port')
        self.pool_name.set_placeholder_text('Pool name')

        vbox.pack_start(self.host, 0, 0, 0)
        vbox.pack_start(self.port, 0, 0, 0)
        vbox.pack_start(self.pool_name, 0, 0, 0)
        vbox.set_homogeneous(True)

        box.pack_end(vbox, 0, 0, 0)
        self.set_focus(self.get_action_area().get_children()[1])
        self.show_all()

    def check_entry(self, widget, button):
        fields = self.get_content_area().get_children()[1].get_children()
        if not all([len(field.get_text()) for field in fields]):
            button.set_sensitive(False)
            return
        try:
            int(self.port.get_text())
            button.set_sensitive(True)
        except ValueError:
            button.set_sensitive(False)


class BigDataViewer(Gtk.Window):
    def __init__(self, pv):
        super(BigDataViewer, self).__init__()
        self.pv = pv
        self.interval = 0.05
        self.connect('delete-event', self.stop_thread)

        self.hscale = 1
        self.maxhscale = 8
        self.minhscale = 0.125

        self.init_ui()
        self.start_cycle()

    def init_ui(self):
        self.darea = Gtk.DrawingArea()
        self.darea.connect("draw", self.on_draw)
        self.darea.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        self.darea.add_events(Gdk.EventMask.SCROLL_MASK)
        self.darea.connect("button-press-event", self.on_button_press)
        self.darea.connect("scroll-event", self.set_hscale)
        self.add(self.darea)

        self.set_title("Big Data")
        self.resize(500, 800)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.show_all()

    def on_draw(self, widget, cr):
        poolmgr = cfl.dbus_connection('poolmanager', cfl.communication['poolmanager'])

        if not poolmgr:
            return

        check = poolmgr.Functions('_return_colour_list', 'try')
        if check is False:
            return

        n = int(self.darea.get_allocated_height() / self.hscale)
        w = self.darea.get_allocated_width()
        length = poolmgr.Functions('_return_colour_list', 'length')
        for i in range(min(n, length)):
        #for i in range(min(n, len(self.pv.pool.colour_list))):
            #rgb, pcktlen = self.pv.pool.colour_list[-i - 1]
            rgb, pcktlen = poolmgr.Functions('_return_colour_list', i)
            cr.rectangle(0, self.hscale * (n - i), (pcktlen + 7) / 1024 * w, self.hscale)
            cr.set_source_rgb(*rgb)
            cr.fill()

        # cr.translate(220, 180)
        # cr.scale(1, 0.7)
        # cr.fill()

    def on_button_press(self, w, e):

        if e.type == Gdk.EventType.BUTTON_PRESS and e.button == 1:
            self.start_cycle()
            # self.palette = [np.random.random(3) for i in range(1000)]
            # self.darea.queue_draw()

        if e.type == Gdk.EventType.BUTTON_PRESS and e.button == 3:
            self.darea.queue_draw()
            self.cycle_on = False

    def start_cycle(self):
        self.cycle_on = True
        if 'BigDataViewer' in [x.name for x in threading.enumerate()]:
            # self.interval /= 2.
            return
        t = threading.Thread(target=self.cycle_worker)
        t.setName('BigDataViewer')
        t.setDaemon(True)
        t.start()

    def cycle_worker(self):
        while self.cycle_on:
            GLib.idle_add(self.darea.queue_draw)
            time.sleep(self.interval)

    def stop_thread(self, widget=None, data=None):
        self.cycle_on = False

    def set_hscale(self, widget, event):
        if event.direction.value_name == 'GDK_SCROLL_SMOOTH':
            scale = 2 ** (-event.delta_y)
        # needed for remote desktop
        elif event.direction.value_name == 'GDK_SCROLL_UP':
            scale = 2
        elif event.direction.value_name == 'GDK_SCROLL_DOWN':
            scale = 0.5
        else:
            return
        self.hscale = max(min(self.hscale * scale, self.maxhscale), self.minhscale)


class UnsavedBufferDialog(Gtk.MessageDialog):
    def __init__(self, parent=None, msg=None):
        Gtk.MessageDialog.__init__(self, title="Close Poolmanager?", parent=parent, flags=0,
                                   buttons=(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                                   Gtk.STOCK_NO, Gtk.ResponseType.NO,
                                    Gtk.STOCK_YES, Gtk.ResponseType.YES,))
        head, message = self.get_message_area().get_children()
        if msg is None:
            head.set_text('Response NO will keep the Poolmanager running in the Background')
        else:
            head.set_text(msg)

        self.show_all()


def run(pool_name):
    bus_name = cfg.get('ccs-dbus_names', 'poolviewer')

    DBusGMainLoop(set_as_default=True)

    pv = TMPoolView()

    DBus_Basic.MessageListener(pv, bus_name, *sys.argv)

    if pool_name is not None:
        pv.set_pool(pool_name)
    Gtk.main()


if __name__ == "__main__":

    poolname = None
    if len(sys.argv) > 1:
        for arg in sys.argv[1:]:
            if not arg.startswith('-'):
                poolname = arg

    run(pool_name=poolname)


