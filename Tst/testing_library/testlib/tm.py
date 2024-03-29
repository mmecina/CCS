#!/usr/bin/env python3
"""
Telemetry
=========

Which function to fetch TM packets are available? All functions which fetch TM packets should check if it is a TM and
not a TC!
  > Functions which do not WAIT:
    get TM with specific parameters: st, sst, apid, event_id, procedure_id
    within a time interval in the [past, now*]
  > Function which do WAIT for a specific TM packet (TM maybe is received in the future)
    get TM with specific parameters: st, sst, apid, event_id, procedure_id
    time intervals: [past, future], [now*, future]
    There must always be a maximum waiting time to prevent the program to stuck
    This function will be called by await_hk, await_event,...
    e.g.: await_event: calls function which fetches TMs (no waiting) -> calls function to validate condition ->
  > functions which do collect TMs for a duration (really necessary? why not just wait till the duration is over and
    call the function which do not wait?
    get TM with specific parameters: st, sst, apid, event_id, procedure_id
    time intervals: [past, future], [now*, future]
*: now is the CUC timestamp of the last TM packet in the pool. Kind of the packet does not matter.

conclusion:
  * There should be just one and only one function which is doing the database access!
    The return of this function should be unpacked and decoded TM packets with header, data tuple
  * The functions which are waiting, should make database calls repetitive database calls, till the condition
    is fulfilled. Important is that the frequency of making sessions is not high.

housekeeping:
* get the last of a kind
* get the next of a kind (await housekeeping)
* get all of a kind for time interval

* get hk-entries of the last of a kind
* get hk-entries of the next of a kind (await housekeeping)
* get hk-entries of all of a kind for time interval

events:
* get last event of a kind
* get next event of a kind (await event)
* get all events of a kind for time interval
* get event data entry

acknowledgements:
  * get the acknowledgement TM packets for a specific TC or TCs
  * if the TCs were sent some seconds ago, the acknowledgement TMs maybe not created yet because actions of IASW may
    take some time
  * if the TC fails the failure code should be logged in a readable form (ToDo)

Functions in detail:
--------------------
"""

import logging
import sys
import time

import confignator
sys.path.append(confignator.get_option('paths', 'ccs'))
import ccs_function_lib as cfl

from database import tm_db

# from . import idb
# from . import tools
import tools
import idb

# create a logger
logger = logging.getLogger(__name__)


def filter_chain(query, pool_name, is_tm=True, st=None, sst=None, apid=None, seq=None, t_from=None, t_to=None, dest_id=None, not_apid=None):
    """
    Add filter to a database query for telemetry/telecommand packets.l
    :param query: 
    :param pool_name: str
    :param is_tm: bool
        If this argument is True the query asks only for telemetry packets (TM).
        If this argument is False the query asks only for telecommand packets (TC).
    :param st: int
        Service type of the packet
    :param sst: int
        Sub-Service type of the packet
    :param apid: int
        Application process ID of the packet
    :param seq: 
    :param t_from: 
    :param t_to: 
    :param dest_id: 
    :param not_apid: 
    :return: 
    """
    if is_tm is True:
        query = query.filter(tm_db.DbTelemetry.is_tm == 0)  # ToDo: why is this entry in the DB zero when it is a TM?
    else:
        query = query.filter(tm_db.DbTelemetry.is_tm == 1)  # query for TCs
    if pool_name is not None:
        query = query.join(
            tm_db.DbTelemetryPool,
            tm_db.DbTelemetry.pool_id == tm_db.DbTelemetryPool.iid
        ).filter(
            tm_db.DbTelemetryPool.pool_name == pool_name
        )
    if st is not None:
        query = query.filter(tm_db.DbTelemetry.stc == st)
    if sst is not None:
        query = query.filter(tm_db.DbTelemetry.sst == sst)
    if apid is not None:
        query = query.filter(tm_db.DbTelemetry.apid == apid)
    if seq is not None:
        query = query.filter(tm_db.DbTelemetry.seq == seq)
    if t_from is not None:
        # ToDo database has the CUC timestamp as string. Here the timestamps are floats.
        # Does this comparison operations work?
        t_from_string = str(t_from) + 'U'  # the timestamps in the database are saved as string
        query = query.filter(tm_db.DbTelemetry.timestamp >= t_from)  # ToDo check if the change from > to >= breaks something!
        # ToDo: Funktion Cast verwenden um String auf Double zu casten
        # query = query.filter(tm_db.DbTelemetry.timestamp > t_from)  # <- comparison with float
    if t_to is not None:
        # ToDo database has the CUC timestamp as string. Here the timestamps are floats.
        # Does this comparison operations work?
        t_to_string = str(t_to) + 'U'  # the timestamps in the database are saved as string
        query = query.filter(tm_db.DbTelemetry.timestamp <= t_to) # ToDo: Funktion Cast verwenden um String auf Double zu casten
        # query = query.filter(tm_db.DbTelemetry.timestamp <= end)  # <- comparison with float
    if dest_id is not None:
        query = query.filter(tm_db.DbTelemetry.destID == dest_id)
    if not_apid is not None:
        query = query.filter(tm_db.DbTelemetry.apid != not_apid)
    return query


def highest_cuc_timestamp(tm_list):
    """
    Get the TM packet with the highest CUC timestamp of the packet list

    :param list tm_list: List of TM packets
    :return: The TM packet with the highest CUC timestamp (this is the one with the smallest difference to now).
    :rtype: PUS packet || None
    """
    highest = None
    timestamp = None
    if isinstance(tm_list, list) and len(tm_list) > 0:
        cuc = 0
        for i in range(len(tm_list)):
            try:
                tstamp = cfl.get_cuctime(tm_list[i])
            except Exception as unknown_error:
                logger.exception(unknown_error)
                continue
            if tstamp > cuc:
                cuc = tstamp
                highest = tm_list[i]
                timestamp = tstamp
    return highest, timestamp


def lowest_cuc_timestamp(pool_name, tm_list):
    """
    Get the TM packet with the lowest CUC timestamp of the packet list

    :param (str) pool_name: name of the packet pool in the database
    :param (list) tm_list: List of TM packets

    :return: TM packet with the lowest CUC timestamp (this is the one with the largest difference to now)
    :rtype: PUS packet || None
    """
    lowest = None
    if isinstance(tm_list, list) and len(tm_list) > 0:
        cuc = cfl.get_last_pckt_time(pool_name=pool_name, string=False)
        for i in range(len(tm_list)):
            try:
                tstamp = cfl.get_cuctime(tm_list[i])
            except Exception as unknown_error:
                logger.exception(unknown_error)
                continue
            if tstamp < cuc:
                cuc = tstamp
                lowest = tm_list[i]
    return lowest


def time_tc_accepted(pool_name, tc_identifier):
    """
    Get the CUC timestamp of the command acceptance acknowledgement TM packet (or acceptance failure)

    :param str pool_name: name of the packet pool in the database
    :param tuple tc_identifier: TC identifier is a tuple which consists out of apid, ssc, CUC-timestamp

    :return: CUC timestamp of the TM(1,1) or TM(1,2) of the telecommand
    :rtype: CUC-timestamp || None
    """
    cuc = None
    # get the acknowledgement packets
    suc, acknow = await_tc_acknow(pool_name=pool_name, tc_identifier=tc_identifier, tm_st=1)
    # filter for accepted TM(1,1) or acceptance failure TM(1,2)
    if len(acknow) > 0:
        for i in range(len(acknow)):
            subservicetype = acknow[i][0][11]
            if subservicetype == 1 or subservicetype == 2:
                # get the cuc timestamp of the acknowledgement packet
                cuc = cfl.get_cuctime(acknow[i])
                break
    else:
        logger.warning('time_tc_accepted: no acknowledgement TM found for TM {}'.format(tc_identifier))
    return cuc


def set_time_interval(pool_name, t_from, t_to, duration):
    """
    Calculate the time interval for given values t_from, t_to and duration.
    The time interval is used to for database queries.
    There are three cases:

    * If no duration is provided the t_to returned unchanged.
    * If t_to and a duration are provided, the value of t_to is stronger. The duration probably was set as a default
      value in a other function.
    * If only a duration and no t_to is provided the upper boundary = lower boundary + duration
    
    :param str pool_name: name of the packet pool in the database
    :param float t_from: CUC timestamp, lower boundary for the time interval. If t_from is None the current CUC timestamp is retrieved from the database by packets.get_last_pckt_time()
    :param float t_to: CUC timestamp, upper boundary for the time interval.
    :param int duration: duration in seconds

    :return: CUC timestamps of t_from and the calculated t_to
    :rtype: float, float
    """
    assert isinstance(t_from, float) or t_from is None
    assert isinstance(t_to, float) or t_to is None
    assert isinstance(duration, float) or isinstance(duration, int) or duration is None

    t_to_new = None

    # set the lower interval boundary, if no t_from is given, the current time will be used
    if t_from is None:
        # CUC timestamp of the last tm packet is used as "now"
        last_packet_time = cfl.get_last_pckt_time(pool_name=pool_name, string=False)
        if last_packet_time:
            t_from = last_packet_time
        else:
            logger.error('set_time_interval: Could not retrieve the timestamp of the last telemetry packet.')
            return False, None

    # calculate the t_to value
    if t_from is not None:
        if t_to is None and duration is None:  # got none of both
            logger.critical('set_time_interval: neither t_to nor duration was provided')
        elif t_to is not None and duration is not None:  # got both
            # t_to is stronger than duration, because duration may was set as default value
            t_to_new = t_to
        elif t_to is None and duration is not None:  # got only duration
            t_to_new = t_from + duration
        elif t_to is not None and duration is None:  # got only t_to
            t_to_new = t_to

    # check if calculating the interval boundaries was successful
    if t_from is None or t_to_new is None:
        raise Exception('set_time_interval: could not calculate t_from and/or t_to')
    # give out a warning if t_from is larger than t_to
    if t_from > t_to_new:
        logger.critical('set_time_interval: t_from is larger than t_to!')

    return t_from, t_to_new


def set_query_interval(t_from, t_to):
    """
    Set the frequency for doing database queries.
    If the time frame gets larger the frequency of the queries gets lower.
    
    :param float t_from: lower boundary for the CUC timestamp
    :param float t_to: upget_last_pckt_timeper boundary for the CUC timestampcheck

    :return: the interval in seconds for the database queries to be done
    :rtype: float
    """
    assert isinstance(t_from, float)
    assert isinstance(t_to, float)
    interval = 0.5

    diff = t_to - t_from
    if 5.0 < diff <= 20.0:
        interval = 1.0
    if 20.0 < diff <= 60.0:
        interval = 2.5
    if 60.0 < diff:
        interval = 5.0

    return interval


def decode_single_tm_packet(packet):
    """
    Decodes a single TM packet. The packet has to be of the type bytes.
    If the packet is a TC the returned tuple consists out of (header, None)
    If the packet is a TM the returned tuple consists out of (header, data)
    For the case that the data field can not be read the tuple (header, None) is returned

    :param bytes packet: TM packet in byte-string format

    :return: tuple or None
    :rtype: the decoded packet || None
    """
    assert isinstance(packet, bytes)

    result = None
    header = cfl.Tmread(packet)
    if header is not None:
        # the packet is a TC
        if header[0].PKT_TYPE == 1:
            result = header, None
        # the packet is a TM
        elif header[0].PKT_TYPE == 0:
            data = cfl.Tmdata(packet)
            if data != (None, None):  # data field could be decoded
                result = header, data
            else:  # data field could not be decoded
                result = header, None
    else:
        logger.error('decode_tm: could not read the header of the packet {}'.format(packet))

    return result


def decode_tm(tm_packets):
    """
    Check if a TM packet or a list of TM packets are still bytes.
    If so, they are decoded, otherwise just pass the packets. If a failure occurs while unpacking return None

    :param list tm_packets: <list> of <bytes>: TM packet or a list of TM packets in byte format or as tm_db.DbTelemetry row

    :return: list decoded TM packets (a TM packet is a tuple (header, data))
    :rtype: list
    """
    decoded = []

    # distinguish if tm_packets is a single TM packet or a list of packets
    if isinstance(tm_packets, list):
        time_per_packet = None
        if len(tm_packets) > 100:
            logger.warning('decode_tm: list has {} packets, this may be very slow to decode'.format(len(tm_packets)))
        for j in range(len(tm_packets)):
            t_start = time.time()
            if isinstance(tm_packets[j], bytes):
                decoded.append(decode_single_tm_packet(packet=tm_packets[j]))
            elif isinstance(tm_packets[j], tuple):
                decoded.append(tm_packets[j])
            elif isinstance(tm_packets[j], tm_db.DbTelemetry):
                row = tm_packets[j].raw
                decoded.append(decode_single_tm_packet(packet=row))
            else:
                logger.debug('decode_tm: data format for the TM packet is not known! Type of the packet is {}'
                          .format(type(tm_packets[j])))
            t_end = time.time()
            if len(tm_packets) > 100:
                time_per_packet = t_end - t_start
                logger.warning('decode_tm: it took {}s to decode one packet'.format(time_per_packet))

    else:
        if isinstance(tm_packets, bytes):
            decoded.append(decode_single_tm_packet(packet=tm_packets))
        elif isinstance(tm_packets, tuple):
            decoded.append(tm_packets)
        elif isinstance(tm_packets, tm_db.DbTelemetry):
            row = tm_packets.raw
            decoded.append(decode_single_tm_packet(packet=row))
        else:
            logger.debug('decode_tm: data format for the TM packet is not known! Type of the packet is {}'
                      .format(type(tm_packets)))

    return decoded


def get_tm_data_entries(tm_packet, data_entry_names):
    """
    For one TM packet the specified entries are extracted and returned.

    :param PUS-packet tm_packet: TM packet which holds the desired parameter entries
    :param string-or-list data_entry_names: string or list of strings: this are the names/identifiers of the data entries

    :return: key-value pairs of the data entries (as dict) or a empty dict
    :rtype: dict
    """
    values = {}
    keys = data_entry_names
    # if the TM packets are not decoded already, do it now
    packet = decode_tm(tm_packets=tm_packet)

    # extract the required entries from the telemetry packet/packets
    if len(packet) == 1:
        if isinstance(keys, str):  # make a single string to an array with one entry
            keys = [keys]
        if isinstance(keys, dict):  # extract the keys if it is a dictionary
            name_list = []
            for key in keys:
                name_list.append(key)
            keys = name_list
        if isinstance(keys, list):
            entries = {}
            if packet[0][1] is not None and packet[0][1][0] is not None:
                for i, para in enumerate(keys):
                    entry = list(filter(lambda tup: tup[2] == para, packet[0][1][0]))
                    if len(entry) > 0:
                        entries[entry[0][2]] = entry[0][0]
                    else:
                        logger.debug('get_tm_data_entries: Entry with the key "{}" was not found.'.format(para))
            else:
                logger.debug('get_tm_data_entries: TM packet has no data. Packet: {}'.format(packet[0]))
            if len(entries) > 0:
                values = entries
    if len(packet) == 0:
        logger.debug('get_tm_data_entries(): there is no TM packet. Probably the decoding of the packet failed.')
    if len(packet) > 1:
        logger.debug('get_tm_data_entries(): more than one TM packet was provided. Expecting a single packet.')
    return values


# For every TM packet of the list the specified entries are extracted and returned.
#   @param event_tms: <list> or single TM packet (expecting a event TM packet)
#   @param data_entry_names: <string> or <list of strings>: this are the names/identifiers of the data entry
#   @return: <list> of <dict>: key-value pairs of the data entries (as dict) or a empty array
def get_tm_list_data_entries(tm_packets, data_entry_names):
    result = []
    # if the TM packets are not decoded already, do it now
    event_packets = decode_tm(tm_packets=tm_packets)

    # extract the required entries from the telemetry packet/packets
    if event_packets is not None:
        if isinstance(event_packets, list) and len(event_packets) > 0:
            for j in range(len(event_packets)):
                result.append(get_tm_data_entries(tm_packet=event_packets[j], data_entry_names=data_entry_names))
    return result


# checks if for the provided TM packet the required entry exists and if the value is as expected
#   @param packet: TM packet
#   @param entry_name: <str> name of the entry (the 3rd value of the tuple)
#   @param entry_value: value the entry (the 1st value of the tuple)
#   @return: <boolean>: True if entry exists and has the correct value
def has_entry(packet, entry_name, entry_value):
    item = get_tm_data_entries(tm_packet=packet, data_entry_names=entry_name)
    if item is not None:
        if entry_name in item and item[entry_name] == entry_value:
            return True


# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++


def fetch_packets(pool_name, is_tm=True, st=None, sst=None, apid=None, ssc=None, t_from=None, t_to=None,
                  dest_id=None, not_apid=None, decode=True, silent=False):
    # ToDo: remove the agrument silent, as this functionality is covert by using log level INFO
    # (DEBUG still logs more information)
    """ Makes a single database query for packets from the pool for a fixed time interval.
    By using arguments, specific packets can be retrieved.

    :param pool_name: str
        The name of the pool in the database
    :param is_tm: bool
        In the pool are TM (telemetry packets) and TC (telecommand packets). You can query for TMs or TCs.
    :param st: int
        Service type of the packet
    :param sst: int
        Sub service type of the packet
    :param apid: int or str
        Application process id of the packet. Can be a integer or a hexagonal number string.
    :param ssc: int
        Source sequence counter of the packet
    :param t_from: float
        Querying for packets which have a CUC timestamp higher or equal than t_from
    :param t_to: float
        Querying for packets which have a CUC timestamp lower or equal than t_to
    :param dest_id: int
        Destination ID of the packet.
    :param not_apid: int or str
        If a the packets should not have this APID. Can be a integer or a hexagonal number string.
    :param decode: bool
        By default de packets are decoded. Set this parameter to false, if the packets are required as byte strings

    :return: list
        A list with the found packets is returned.
        If no packets with the parameters can be found a empty list is returned.
    """
    assert isinstance(is_tm, bool)
    assert isinstance(st, int) or st is None
    assert isinstance(sst, int) or sst is None
    assert (isinstance(apid, int) or isinstance(apid, str) or apid is None)
    assert isinstance(ssc, int) or ssc is None
    assert isinstance(t_from, float) or t_from is None
    assert isinstance(t_to, float) or t_to is None
    assert isinstance(dest_id, int) or dest_id is None
    assert (isinstance(not_apid, int) or isinstance(not_apid, str) or not_apid is None)
    assert isinstance(decode, bool)

    data = []

    # if apid is a hexagonal value, convert it to a integer
    if apid is not None:
        apid = tools.convert_apid_to_int(apid=apid)

    # make database query
    session = cfl.scoped_session_storage()
    query = session.query(tm_db.DbTelemetry)
    query = filter_chain(query,
                         pool_name=pool_name,
                         is_tm=is_tm,
                         st=st,
                         sst=sst,
                         apid=apid,
                         seq=ssc,
                         t_from=t_from,
                         t_to=t_to,
                         dest_id=dest_id,
                         not_apid=not_apid)
    data = query.all()
    session.close()
    logger.debug('fetch_packets: returned {} packets; is_tm:{}, st:{}, sst:{}, apid:{}, ssc:{}, t_from:{}, t_to:{},'
              ' dest_id:{}, not_apid:{}, decode:{}'
              .format(len(data), is_tm, st, sst, apid, ssc, t_from, t_to, dest_id, not_apid, decode))

    # get the raw data out of the query result
    for i in range(len(data)):
        data[i] = data[i].raw

    # decode the data
    if len(data) > 0 and decode is True:
        data = decode_tm(tm_packets=data)

    return data


def await_tm(pool_name, st, sst=None, apid=None, ssc=None, t_from=None, t_to=None, dest_id=None, not_apid=None, decode=True, duration=5, check_int=None):
    """ Waiting for a specific TM packet, if it is received the packet is returned immediately.
    The database queries are done in regular intervals.
    
    :param pool_name: str
        name of the pool in the database
    :param st: int
        Service type of the packet
    :param sst: int
        Sub service type of the packet
    :param apid: int or str
        Application process id of the packet. Can be a integer or a hexagonal number string.
    :param ssc: int
        Source sequence counter of the packet
    :param t_from: float
        Querying for packets which have a CUC timestamp higher or equal than t_from
    :param t_to: float
        Querying for packets which have a CUC timestamp lower or equal than t_to
    :param dest_id: int
        Destination ID of the packet.
    :param not_apid: int or str
        If a the packets should not have this APID. Can be a integer or a hexagonal number string.
    :param decode: bool
        By default de packets are decoded. Set this parameter to false, if the packets are required as byte strings
    :param duration: int
        Seconds how long the function waits and do database queries in regular intervals
    :param check_int: float
        Frequency for executing database queries. If it is not provided, it will be set depending on the value of duration
    :return: list
        List of TM packets or []
    """
    # always a empty array should be returned in order to prevent code-breaking bugs
    result = []

    # set time interval for the desired packets
    t_from, t_to = set_time_interval(pool_name=pool_name, t_from=t_from, t_to=t_to, duration=duration)

    # set the interval of fetching packets from the pool
    if check_int is None:
        check_int = set_query_interval(t_from=t_from, t_to=t_to)

    # repeat the database call till the TM packet was received or t_to is reached
    condition = True
    while condition is True:
        # get packets from the database
        packets = fetch_packets(pool_name=pool_name,
                                is_tm=True,
                                st=st,
                                sst=sst,
                                apid=apid,
                                ssc=ssc,
                                t_from=t_from,
                                t_to=t_to,
                                dest_id=dest_id,
                                not_apid=not_apid,
                                decode=decode,
                                silent=True)
        # check condition
        if len(packets) > 0 or cfl.get_last_pckt_time(pool_name=pool_name, string=False) > t_to:
            condition = False
            result = packets
        else:
            logger.debug('await_tm: waiting for {}s and then doing the query again'.format(check_int))
            time.sleep(check_int)

    return result


def get_tm(pool_name, st=None, sst=None, apid=None, ssc=None, duration=5, t_from=None, t_to=None,
           check_interval=0.2, decode=True):
    # ToDo: remove the argument check_interval
    """
    Get telemetry packets from the database for a specific time interval. Selection of the packets can be done via
    parameters.
    Time intervals: ]t_from, t_from+duration[ or ]now, now+duration[. "now" means the CUC timestamp of the last tm packet.

    :param pool_name: str
        Name of the pool for TM and TC packets in the database.
    :param st: int
        Service Type of the TM packets.
    :param sst: int
        Sub-Service Type of the TM packets.
    :param apid: int
        Application Process ID of the TM packets.
    :param duration: float
        Duration of the time interval where packets are taken. Unit is seconds.
    :param t_from: float
        CUC timestamp. Packets with a timestamp higher as this parameter are returned.
    :param t_to: float
        CUC timestamp. Packets with a timestamp lower as this parameter are returned.
    :param check_interval: float
        If the database query does not return results, the next loop of the while function waits. Unit is seconds.
    :param decode: bool
        If True the TM packets get decoded
    :return: <list>
        of decoded telemetry packets or []
    """


    # set the time interval
    t_from, t_to = set_time_interval(pool_name=pool_name, t_from=t_from, t_to=t_to, duration=duration)

    # for the case that t_to is in future, wait
    current_cuc = cfl.get_last_pckt_time(pool_name=pool_name, string=False)

    if t_to > current_cuc:
        difference = t_to - current_cuc
        time.sleep(difference)

    # get packets
    tm_packets = fetch_packets(pool_name=pool_name,
                               st=st,
                               sst=sst,
                               apid=apid,
                               ssc=ssc,
                               t_from=t_from,
                               t_to=t_to,
                               decode=decode)

    # return the results and log parameters if no data was returned
    if len(tm_packets) < 1:
        message = 'The database query returned no telemetry packets for '
        if st is not None:
            message += 'st={} '.format(st)
        if sst is not None:
            message += 'sst={} '.format(sst)
        if apid is not None:
            message += 'apid={} '.format(apid)
        message += 'within the time interval ]{}, {}]'.format(t_from, t_to)
        logger.debug(message)

    return tm_packets


# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++


def get_hk_tm(pool_name, hk_name, t_from=None, t_to=None, duration=5):
    """
    Fetches housekeeping reports TM(3,25) from the database and filter them by the housekeeping name (SID).

    :param pool_name: str
        Name of the pool for TM/TC packets in the database
    :param hk_name: str
        Name of the housekeeping. For example: 'IFSW_HK', 'IBSW_DG'
    :param t_from: float
        CUC timestamp. Packets with a timestamp higher as this parameter are returned.
    :param t_to:
        CUC timestamp. Packets with a timestamp lower as this parameter are returned.
    :param duration: float or int
        Duration of the time interval where packets are taken. Unit is seconds.
    :return: list
        List of the housekeeping TM packets or an empty list.
    """
    hk_list = []

    # set the time interval for the database query
    t_from, t_to = set_time_interval(pool_name=pool_name, t_from=t_from, t_to=t_to, duration=duration)

    # get the TM packets from the database
    data = get_tm(pool_name=pool_name, st=3, sst=25, t_from=t_from, t_to=t_to, duration=duration)

    for packet in data:
        if has_entry(packet=packet, entry_name='Sid', entry_value=hk_name):
            hk_list.append(packet)

    return hk_list


def await_hk_tm(pool_name, sid=None, t_from=None, duration=5):
    """ Get the next housekeeping TM packet with a specific SID. If there are more packets of the same kind. The one
    with the highest CUC timestamp is returned.

    :param pool_name: str
        Name of the TM/TC pool in the database
    :param sid: int or str
        SID of the desired housekeeping packet. If the SID is provided as integer, the corresponding name is taken from
        the database
    :param t_from: CUC
        Start timestamp of the query for packets
    :param duration: int or float
        Seconds to wait for the housekeeping packet. Upper boundary of the query time interval.

    :return: PUS packet || None
        Single housekeeping packet where the SID matches. If more than one HK packets are found the one with the highest
        CUC timestamp is returned.
    """
    result = None

    # if the sid is a integer, get the name string from the instrument database
    if isinstance(sid, int):
        sid = idb.convert_hk_sid(sid=sid)

    # get the housekeeping TM packets from the pool
    tm_list = await_tm(pool_name=pool_name, st=3, sst=25, t_from=t_from, duration=duration)

    # filter for the correct housekeeping kind (SID)
    housekeepings = []
    for packet in tm_list:
        packet_sid = get_tm_data_entries(tm_packet=packet, data_entry_names='Sid')
        if 'Sid' in packet_sid:
            if packet_sid['Sid'] == sid:
                housekeepings.append(packet)

    # get the TM packet with the highest CUC timestamp
    if len(housekeepings) > 0:
        logger.debug('await_hk_tm: found {} packets with SID {}'.format(len(housekeepings), sid))
        # ToDo: change to the lowest_cuc_timestamp (the first HK with this SID), because of waiting for the next HK TM?!
        youngest = highest_cuc_timestamp(tm_list=housekeepings)
        header = youngest[0]
        data = youngest[1]
        result = header, data
    else:
        logger.debug('await_hk_tm: no housekeeping packets with SID {} found'.format(sid))

    return result


def get_self_def_hk_tm(pool_name, sid, format_string, t_from=None, t_to=None):
    """
    Fetches TM(3,25) housekeeping packets for self defined housekeeping. In order to unpack the data field a
    format string is required. The packets from the pool are filtered, after unpacking, by the SID (which are the first
    two bytes in the data field).
    
    Parameters
    ----------
    :param pool_name: str
        pool name of the TM/TC packets pool
    :param sid: int
        the RDL list identifier
    :param format_string: str
        A string containing the information how to unpack the Bits() in the data field.
        This string should not consider the SID (which are the first 8 bits).
        Example: 'uint:16,uint:16' for two entries each 2 bytes long
    :param t_from: float
        CUC timestamp: from this timestamp on the packets are fetched
    :param t_to: float
        CUC timestamp: up to this timestamp the packets are fetched from the pool
    
    Returns
    -------
    :return: list
        a list of TM(3,25) packets or []. All packets have matching SIDs. 
    """
    assert isinstance(sid, int)
    assert isinstance(format_string, str)
    assert isinstance(t_from, float) or t_from is None
    assert isinstance(t_to, float) or t_to is None

    hk_list = []

    # get the TM packets from the database
    packets = get_tm(pool_name=pool_name, st=3, sst=25, t_from=t_from, t_to=t_to, decode=False)

    # filter TM packets with the correct Sid
    for packet in packets:
        # read the header
        header = cfl.Tmread(pckt=packet)
        # extract the SID from the Bits-Field (the first 8 bits are the SID)
        packet_sid = header[-2][0:8].unpack('uint:8')[0]
        if packet_sid == sid:
            # unpacking the rest of the Bits-Field
            try:
                packet_entries = header[-2][8:].unpack(format_string)
                logger.debug('Successfully unpacked the TM(3,25) with the SID {}'.format(packet_sid))
                hk_list.append((header, {'sid': packet_sid, 'entries': packet_entries}))
            except:
                logger.warning('get_self_def_hk_tm: Unpacking the data field failed.')

    # log if no packets were found
    if len(hk_list) == 0:
        logger.info('get_self_def_hk_tm: No TM(3,25) packets with SID {} found'.format(sid))

    return hk_list


def get_hk_entry(pool_name, hk_name, name=None, t_from=None, t_to=None, duration=5, silent=False):
    """
    Get a specific entry of the youngest housekeeping report from the TM/TC database by name.

    :param pool_name:
    :param hk_name:
    :param name:
    :param t_from:
    :param t_to:
    :param duration:
    :param silent:
    :return: <tuple> ((<tuple> hk entry), CUC timestamp, <str> housekeeping name) OR None
    """
    result = None

    # fetch the housekeeping entry
    if name is not None:
        # for the case that the names are provided as dict, create an array of entry names
        if isinstance(name, dict):
            new_names = []
            for key in name:
                new_names.append(key)
            name = new_names

        # get the TM packets from the database
        hk_list = get_hk_tm(pool_name=pool_name, hk_name=hk_name, t_from=t_from, t_to=t_to, duration=duration)

        if len(hk_list) > 0:
            # take the youngest housekeeping report
            hk_report = highest_cuc_timestamp(tm_list=hk_list)
            # get the requested housekeeping entry out of the TM packet
            entries = get_tm_data_entries(tm_packet=hk_report, data_entry_names=name)
            # pick out the results
            if len(entries) > 0:
                result = entries, cfl.get_cuctime(hk_report), hk_name
                # log the result
                if isinstance(entries, dict):
                    keys = entries.keys()
                    for key in keys:
                        if not silent:
                            logger.info('{} = {}'.format(key, entries[key]))
                else:
                    logger.debug('get_hk_entry: UNDER CONSTRUCTION: HERE IS SOMETHING TO IMPLEMENT')
            if len(entries) < 1:
                logger.debug('No entry with name(s) {} found in the housekeeping {} with '
                          'CUC timestamp {}'.format(name, hk_name, cfl.get_cuctime(hk_report)))
        else:
            logger.warning('The required {} housekeeping report/entry could not be found in the database.'.format(hk_name))

    return result


def await_hk_entries(pool_name, sid=None, name=None):  # 2 usages IASW39
    result = None
    hks = await_hk_tm(pool_name, sid=sid)

    # extract the required entries from the housekeeping
    if hks is not None:
        if isinstance(name, str):
            entry = list(filter(lambda tup: tup[2] == name, hks[1][0]))
            if len(entry) > 0:
                result = entry[0][0]
            else:
                logger.warning('Entry with the key "{}" could not be found in the housekeeping.'.format(name))
        if isinstance(name, list):
            entries = {}
            for i, para in enumerate(name):
                entry = list(filter(lambda tup: tup[2] == para, hks[1][0]))
                if len(entry) > 0:
                    entries[entry[0][2]] = entry[0][0]
                else:
                    logger.warning('Entry with the key "{}" could not be found in the housekeeping.'.format(para))
            if len(entries) > 0:
                result = entries

    return result


# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++


def get_st_and_sst(pool_name, apid, ssc, is_tm=False, t_from=None):
    """
    Get the ST and SST of a packet by using the APID and SSC of the packet.
    Does a database query with the APID and SSC for a TM or a TC.
    For TC the t_from will be ignored, since TC does not have a valid CUC timestamp
    :param pool_name: str
        name of the pool for TC/TMs in  the database
    :param apid: str or int
        Application process ID of the packet
    :param ssc: int
        Source Sequence Counter of the packet
    :param is_tm: bool
        If True the desired packet is a telemetry packet, else for a TC is queried
    :param t_from: float
        CUC timestamp from where the query starts
    :return: int, int
        ServicType, SubserviceType
        of the packet with the provided APID and SSC
    """
    assert isinstance(apid, str) or isinstance(apid, int)
    assert isinstance(ssc, int)
    assert isinstance(is_tm, bool)
    assert isinstance(t_from, float) or t_from is None

    tc_st = None
    tc_sst = None

    # make a database query for the packet in order to retrieve the ST and SST for logging
    if is_tm is False:  # for TC the timestamp is no valid CUC timestamp
        tc_list = fetch_packets(pool_name=pool_name, is_tm=is_tm, apid=apid, ssc=ssc)
    else:
        tc_list = fetch_packets(pool_name=pool_name, is_tm=is_tm, apid=apid, ssc=ssc, t_from=t_from)

    # if the packet was found read the header and extract the ST and SST
    if len(tc_list) == 1:
        if tc_list[0][0] is not None:
            header = tc_list[0][0][0]
            #tc_st = header[10]
            #tc_sst = header[11]
            tc_st = header.SERV_TYPE
            tc_sst = header.SERV_SUB_TYPE
    elif len(tc_list) < 1:
        logger.warning('get_st_and_sst: TC packet with apid {} and source sequence counter {} could not be found in the '
                    'database'.format(apid, ssc))
    elif len(tc_list) > 1:
        logger.error('get_st_and_sst: More than one TC packet with apid {} and source sequence counter {} were found in '
                  'the database'.format(apid, ssc))
    return tc_st, tc_sst


def extract_ssc_from_psc(psc):
    """
    The Source Sequence Counter (SSC) is embedded in the Packet Sequence Control (PSC).

    Background information: (see CHEOPS Instrument Application SW - TM/TC ICD document for further information)
    The PSC consists out of 16 bits, where the first 2 bits are the Segmentation Flags and the other 14 bits are
    the SSC.
    For a 'stand-alone' packet the Segmentation Flags are '11' and thus the PSC with a SSC of 1 will be:
    1100 0000 0000 0001

    :param psc: int
        Decimal notation of the PSC
    :return: int
        Source Sequence Counter (SSC) as integer
    """
    assert isinstance(psc, int)
    ssc = psc & 0x3fff

    return ssc


def extract_apid_from_packetid(packet_id):
    """
    The Application Process ID (APID) is embedded in the Packet ID.

    Background information: (see CHEOPS Instrument Application SW - TM/TC ICD document for further information)
    The Packet ID consists out of 16 bits, where
        * the first 3 bits are the Version number
        * 1 bit for the Packet Type
        * 1 bit for the Data Field Header Flag
        * 11 bit for the APID

    :param packet_id: int
        Decimal notation of the Packet ID
    :return: int
        APID in decimal notation
    """
    assert isinstance(packet_id, int)
    apid = packet_id & 0x7ff

    return apid


def confirm_pkt(pool_name, st, sst, apid=None, pi1_off=None, pi1_wid=None, pi1_val=None, wait=0):
    """
    Confirm reception of TM packet with service type st and sub-tpye sst after last TC.
    By using the pi1_* parameters, an additional constraint using a discriminant can be applied.

    :param pool_name:
    :param st:
    :param sst:
    :param apid:
    :param pi1_off: byte offset of discriminant parameter in the entire packet (i.e., incl. PUS header)
    :param pi1_wid: size of discriminant parameter in bytes
    :param pi1_val: discriminant value
    :param wait: seconds to wait before running the check
    :return:
    """

    time.sleep(wait)

    tc_data = get_data_of_last_tc(pool_name, apid=apid)

    if tc_data is None:
        return False, []

    t_tc_sent = tc_data[0]
    tc_idx = tc_data[1]
    tc_head_bytes = tc_data[2]

    tms = cfl.get_pool_rows(pool_name)
    tms = tms.filter(cfl.DbTelemetry.stc == st, cfl.DbTelemetry.sst == sst, cfl.DbTelemetry.idx > tc_idx).order_by(cfl.DbTelemetry.idx)

    if pi1_off and pi1_wid and pi1_val:
        tms = cfl.filter_by_discr(tms, pi1_off, pi1_wid, pi1_val)

    pkt = tms.first()

    if pkt is None:
        return False, []
    else:
        return True, pkt.raw


def verify_tc_ack(pool_name, ack_types=None, tc_apid=321):
    """
    Confirm acknowledgement of last TC packet.

    :param pool_name:
    :param ack_types: list of ACK types (i.e., service 1 sub-types) to check for
    :param tc_apid:
    :return:
    """

    if ack_types is None:
        remaining = [1, 7]
    else:
        remaining = list(ack_types)

    tc_data = get_data_of_last_tc(pool_name, apid=tc_apid)

    if tc_data is None:
        return False, []

    t_tc_sent = tc_data[0]
    tc_idx = tc_data[1]
    tc_head_bytes = tc_data[2]

    assert isinstance(pool_name, str)
    assert isinstance(tc_apid, (int, str))
    assert isinstance(t_tc_sent, (float, int))
    assert isinstance(tc_idx, int)
    assert isinstance(tc_head_bytes, (int, str, bytes))

    acks = cfl.get_pool_rows(pool_name)
    acks = acks.filter(cfl.DbTelemetry.stc == 1, cfl.DbTelemetry.idx > tc_idx).order_by(cfl.DbTelemetry.idx)

    ack_pkts = []
    result = False

    for ack in acks:
        if ack.data[:4] == tc_head_bytes:

            if ack.sst in [1, 3, 7]:
                logger.info('TM({},{}) @ {}'.format(ack.stc, ack.sst, ack.timestamp))
            elif ack.sst in [2, 4, 8]:
                if ack.sst == 2:
                    logger.info('TM({},{}) @ {} FAILURE: Acknowledge failure of acceptance check for a command.'
                                .format(ack.stc, ack.sst, ack.timestamp))
                    logger.debug('Data of the TM packet: {}'.format(ack.raw.hex()))
                if ack.sst == 4:
                    logger.info('TM({},{}) @ {} FAILURE: Acknowledge failure of start check for a command.'
                                .format(ack.stc, ack.sst, ack.timestamp))
                    logger.debug('Data of the TM packet: {}'.format(ack.raw.hex()))
                if ack.sst == 8:
                    logger.info(
                        'TM({},{}) @ {} FAILURE: Acknowledge failure of termination check for a command.'
                        .format(ack.stc, ack.sst, ack.timestamp))
                    logger.debug('Data of the TM packet: {}'.format(ack.raw.hex()))
            else:
                logger.info('No TM found with matching pattern {}'.format(tc_head_bytes))

            try:
                remaining.remove(ack.sst)
            except ValueError:
                pass

            ack_pkts.append(ack.raw)

    if not remaining:
        result = True

    if not ack_pkts:
        logger.info('No ACKs found with matching pattern {}'.format(tc_head_bytes.hex().upper()))

    return result, ack_pkts


def get_hk_val(pool_name, sid, par_id, apid=None):

    return cfl.get_hk_val(pool_name, sid, par_id, apid=apid)


def get_tc_acknow(pool_name="LIVE", tc_apid=321, tc_ssc=None, tm_st=1, tm_sst=None):
    """
    Check if for the TC acknowledgement packets can be found in the database.
    This function makes a single database query.
    :param pool_name: str
        Name of the TM pool in the database
    :param tc_apid: int or str
        Application process ID of the sent TC. Can be provided as integer or hexadecimal string
    :param tc_ssc: int
        Source sequence counter of the sent TC
    :return: (boolean, list)
        boolean:
            True if one or up to all acknowledgement packets TM(1,1), TM(1,3), TM(1,7) were found
            False if one or all of TM(1,2), TM(1,4), TM(1,8) were found
        list:
            List of the acknowledgement TM packets for the TC,
            [] if no acknowledgement TM packets could be found in the database
    """
    result = None

    tc_data = get_data_of_last_tc(pool_name)
    t_tc_sent = tc_data[0]
    tc_iid = tc_data[1]
    tc_bytes = tc_data[2]

    assert isinstance(pool_name, str)
    assert isinstance(tc_apid, (int, str))
    assert isinstance(t_tc_sent, (float, int))
    assert isinstance(tc_iid, int)
    assert isinstance(tc_bytes, (int, str))

    # if the tc_apid is provided as hexadecimal number, convert it to and integer
    tc_apid = tools.convert_apid_to_int(apid=tc_apid)

    # make database query
    packets = fetch_packets(pool_name=pool_name, st=tm_st, sst=tm_sst, t_from=t_tc_sent)
    # print(packets[1][0][0].CTIME + (packets[1][0][0].FTIME/1000000))
    # filter for TM packets with the correct APID and source sequence counter (SSC) in the data field
    ack_tms = []
    for i in range(len(packets)):
        if packets[i][1] is not None and packets[i][1][0] is not None:
            # get the data entries for APID and SSC
            #pac_apid = packets[i][0][3]  # TODO: not compatible anymore
            pac_apid = packets[i][0][0].APID
            first_tm_bytes = packets[i][0][1].hex()[0:4]

            if pac_apid == 961:  # for acknowledgements from SEM
                name_apid = 'PAR_CMD_APID'
                name_psc = 'PAR_CMD_SEQUENCE_COUNT'
            else:
                name_apid = 'TcPcktId'
                name_psc = 'TcPcktSeqCtrl'
            para = get_tm_data_entries(tm_packet=packets[i], data_entry_names=[name_apid, name_psc])
            if name_apid in para and name_psc in para:
                # extract the SSC from the PSC
                ssc = extract_ssc_from_psc(psc=para[name_psc])
                apid = extract_apid_from_packetid(packet_id=para[name_apid])
                if pac_apid == 961:  # acknowledgement packets from SEM have the PID in the field 'PAR_CMD_APID'
                    tc_pid = tools.extract_pid_from_apid(tc_apid)
                    if apid == tc_pid and ssc == tc_ssc:
                        ack_tms.append(packets[i])
                else:
                    if apid == tc_apid and ssc == tc_ssc:
                        ack_tms.append(packets[i])
        else:
            logger.debug('get_tc_acknow: could not read the data from the TM packet')

    # treat with the result from the database query
    if len(ack_tms) > 0:
        # get the ST and SST of the TC for logging purposes
        tc_st, tc_sst = get_st_and_sst(pool_name=pool_name,
                                       apid=tc_apid,
                                       ssc=tc_ssc,
                                       is_tm=False,
                                       t_from=t_tc_sent)
        logger.info('Received acknowledgement TM packets for TC({},{}) apid={} ssc={}:'
                 .format(tc_st, tc_sst, tc_apid, tc_ssc))

        # check if there was a failure, the result becomes False if a failure occurred
        for i in range(len(ack_tms)):
            head = ack_tms[i][0][0]
            data = ack_tms[i][1]
            if result is not False:
                if head.SERV_SUB_TYPE in [1, 3, 7] and (first_tm_bytes == tc_bytes):
                    logger.info('TM({},{}) @ {}'.format(head.SERV_TYPE, head.SERV_SUB_TYPE, cfl.get_cuctime(head)))
                    result = True
                    # print(head.SERV_TYPE, head.SERV_SUB_TYPE)
                elif head.SERV_SUB_TYPE in [2, 4, 8] and (first_tm_bytes == tc_bytes):
                    if head.SERV_SUB_TYPE == 2:
                        logger.info('TM({},{}) @ {} FAILURE: Acknowledge failure of acceptance check for a command.'
                                 .format(head.SERV_TYPE, head.SERV_SUB_TYPE, cfl.get_cuctime(head)))
                        logger.debug('Data of the TM packet: {}'.format(data))
                    if head.SERV_SUB_TYPE == 4:
                        logger.info('TM({},{}) @ {} FAILURE: Acknowledge failure of start check for a command.'
                                 .format(head.SERV_TYPE, head.SERV_SUB_TYPE, cfl.get_cuctime(head)))
                        logger.debug('Data of the TM packet: {}'.format(data))
                    if head.SERV_SUB_TYPE == 8:
                        logger.info(
                            'TM({},{}) @ {} FAILURE: Acknowledge failure of termination check for a command.'
                            .format(head.SERV_TYPE, head.SERV_SUB_TYPE, cfl.get_cuctime(head)))
                        logger.debug('Data of the TM packet: {}'.format(data))
                    result = False
                else:
                    logger.info('No TM found with matching pattern {}'.format(tc_bytes))

    return result, ack_tms




def get_tc_acknow_original(pool_name="LIVE", t_tc_sent=0, tc_apid=321, tc_ssc=1, tm_st=1, tm_sst=None):
    """
    Check if for the TC acknowledgement packets can be found in the database.
    This function makes a single database query.
    :param pool_name: str
        Name of the TM pool in the database
    :param t_tc_sent: float
        CUC timestamp from which search for telecommand should start
    :param tc_apid: int or str
        Application process ID of the sent TC. Can be provided as integer or hexadecimal string
    :param tc_ssc: int
        Source sequence counter of the sent TC
    :return: (boolean, list)
        boolean:
            True if one or up to all acknowledgement packets TM(1,1), TM(1,3), TM(1,7) were found
            False if one or all of TM(1,2), TM(1,4), TM(1,8) were found
        list:
            List of the acknowledgement TM packets for the TC,
            [] if no acknowledgement TM packets could be found in the database
    """
    result = None
    assert isinstance(pool_name, str)
    assert isinstance(tc_apid, (int, str))
    assert isinstance(t_tc_sent, (float, int))

    # if the tc_apid is provided as hexadecimal number, convert it to and integer
    tc_apid = tools.convert_apid_to_int(apid=tc_apid)

    # make database query
    packets = fetch_packets(pool_name=pool_name, st=tm_st, sst=tm_sst, t_from=t_tc_sent - 1)
    # print(packets[1][0][0].CTIME + (packets[1][0][0].FTIME/1000000))
    # filter for TM packets with the correct APID and source sequence counter (SSC) in the data field
    ack_tms = []
    for i in range(len(packets)):
        if packets[i][1] is not None and packets[i][1][0] is not None:
            # get the data entries for APID and SSC
            #pac_apid = packets[i][0][3]  # TODO: not compatible anymore
            pac_apid = packets[i][0][0].APID
            if pac_apid == 961:  # for acknowledgements from SEM
                name_apid = 'PAR_CMD_APID'
                name_psc = 'PAR_CMD_SEQUENCE_COUNT'
            else:
                name_apid = 'TcPcktId'
                name_psc = 'TcPcktSeqCtrl'
            para = get_tm_data_entries(tm_packet=packets[i], data_entry_names=[name_apid, name_psc])
            if name_apid in para and name_psc in para:
                # extract the SSC from the PSC
                ssc = extract_ssc_from_psc(psc=para[name_psc])
                apid = extract_apid_from_packetid(packet_id=para[name_apid])
                if pac_apid == 961:  # acknowledgement packets from SEM have the PID in the field 'PAR_CMD_APID'
                    tc_pid = tools.extract_pid_from_apid(tc_apid)
                    if apid == tc_pid and ssc == tc_ssc:
                        ack_tms.append(packets[i])
                else:
                    if apid == tc_apid and ssc == tc_ssc:
                        ack_tms.append(packets[i])
        else:
            logger.debug('get_tc_acknow: could not read the data from the TM packet')

    # treat with the result from the database query
    if len(ack_tms) > 0:
        # get the ST and SST of the TC for logging purposes
        tc_st, tc_sst = get_st_and_sst(pool_name=pool_name,
                                       apid=tc_apid,
                                       ssc=tc_ssc,
                                       is_tm=False,
                                       t_from=t_tc_sent)
        logger.info('Received acknowledgement TM packets for TC({},{}) apid={} ssc={}:'
                 .format(tc_st, tc_sst, tc_apid, tc_ssc))

        # check if there was a failure, the result becomes False if a failure occurred
        for i in range(len(ack_tms)):
            head = ack_tms[i][0][0]
            data = ack_tms[i][1]
            if result is not False:
                if head.SERV_SUB_TYPE in [1, 3, 7]:
                    logger.info('TM({},{}) @ {}'.format(head.SERV_TYPE, head.SERV_SUB_TYPE, cfl.get_cuctime(head)))
                    result = True
                    print(head.SERV_TYPE, head.SERV_SUB_TYPE)
                elif head.SERV_SUB_TYPE in [2, 4, 8]:
                    if head.SERV_SUB_TYPE == 2:
                        logger.info('TM({},{}) @ {} FAILURE: Acknowledge failure of acceptance check for a command.'
                                 .format(head.SERV_TYPE, head.SERV_SUB_TYPE, cfl.get_cuctime(head)))
                        logger.debug('Data of the TM packet: {}'.format(data))
                    if head.SERV_SUB_TYPE == 4:
                        logger.info('TM({},{}) @ {} FAILURE: Acknowledge failure of start check for a command.'
                                 .format(head.SERV_TYPE, head.SERV_SUB_TYPE, cfl.get_cuctime(head)))
                        logger.debug('Data of the TM packet: {}'.format(data))
                    if head.SERV_SUB_TYPE == 8:
                        logger.info(
                            'TM({},{}) @ {} FAILURE: Acknowledge failure of termination check for a command.'
                            .format(head.SERV_TYPE, head.SERV_SUB_TYPE, cfl.get_cuctime(head)))
                        logger.debug('Data of the TM packet: {}'.format(data))
                    result = False

    return result, ack_tms


def await_tc_acknow(tc_identifier, pool_name="LIVE", duration=10, tm_st=1, tm_sst=None):
    """ Waiting to receive the acknowledgement packet of a sent telecommand (TC) for a given duration.
    As soon as acknowledgement packets were found the function returns.
    
    :param pool_name: str
        Name of the pool in the database
    :param tc_identifier: tuple
        A tuple consisting out of (APID, SSC, CUC-timestamp) of the TC
    :param duration: int or float
        This is the time in second were the function repeatedly tries to find acknowledgment packets in the database
    :return: bool, list
        bool:
            None if no acknowledgement packets were found for the TC
            True if one or up to all acknowledgement packets TM(1,1), TM(1,3), TM(1,7) were found
            False if one or all of TM(1,2), TM(1,4), TM(1,8) were found
        list:
            list of the found acknowledgement packets
        
    """
    assert isinstance(pool_name, str)
    assert isinstance(tc_identifier, tuple)
    tc_apid = tc_identifier[0]
    tc_ssc = tc_identifier[1]
    t_tc_sent = tc_identifier[2]
    assert isinstance(tc_apid, int) or isinstance(tc_apid, str)
    assert isinstance(tc_ssc, int)
    assert isinstance(t_tc_sent, float)
    assert isinstance(duration, int) or isinstance(duration, float)

    result = None

    # do database queries till, the acknowledgement packets are found or the duration elapsed
    start_time = time.time()
    finished = False
    while True:
        # get the acknowledgement packets for the TC
        outcome, ack_list = get_tc_acknow(pool_name=pool_name,
                                          t_tc_sent=t_tc_sent,
                                          tc_apid=tc_apid,
                                          tc_ssc=tc_ssc,
                                          tm_st=tm_st,
                                          tm_sst=tm_sst)
        # if no acknowledgement packets were found, wait and do the next loop
        if outcome is None:
            time.sleep(1)
        # acknowledgement packets were found
        else:
            finished = True
            # if not all 3 TM(1,1), TM(1,3), TM(1,7) were received, wait 1s and query a last time
            if tm_sst is None and len(ack_list) < 3:
                time.sleep(1)
                outcome, ack_list = get_tc_acknow(pool_name=pool_name,
                                                  t_tc_sent=t_tc_sent,
                                                  tc_apid=tc_apid,
                                                  tc_ssc=tc_ssc,
                                                  tm_st=tm_st,
                                                  tm_sst=tm_sst)
            result = outcome
        # stop the loop if the duration is elapsed
        current_time = time.time()
        elapsed_time = current_time - start_time
        if elapsed_time > duration:
            finished = True
        # if finished, leave the while loop
        if finished is True:
            break

    # if no acknowledgement packets were received at all after the loop
    if result is None:
        # get the ST and SST of the TC for logging purposes
        tc_st, tc_sst = get_st_and_sst(pool_name=pool_name,
                                       apid=tc_apid,
                                       ssc=tc_ssc,
                                       is_tm=False,
                                       t_from=t_tc_sent)
        logger.warning('No acknowledgement TM packets for TC({},{}) apid={} ssc={}: found in the database'
                    .format(tc_st, tc_sst, tc_apid, tc_ssc))
    return result, ack_list


def get_5_1_tc_acknow(pool_name="LIVE", tm_name="name", parameter_1=5, parameter_2=3):
    """
        Check if for the TC acknowledgement packets can be found in the database.
        This function makes a single database query.
        :param pool_name: str
            Name of the TM pool in the database
        :param tm_name: string
            Description of TM as found in TM Table
        :param parameter_1: int
            Value of the second parameter of the TM
        :param parameter_2: int
            Value of the third parameter of the TM
        :return: (boolean)
            boolean:
                True if the 5_1 packet was found with the given parameters
                False if no such packet was found
        """

    assert isinstance(pool_name, str)
    assert isinstance(tm_name, str)
    assert isinstance(parameter_1, int)
    assert isinstance((parameter_2, int))


    time_of_packet = get_time_of_last_tc(pool_name)
    packets = fetch_packets(pool_name=pool_name, is_tm=True, st=5, sst=None, apid=321, ssc=None, t_from=time_of_packet,
                            t_to=time_of_packet+30 , dest_id=None, not_apid=None, decode=True, silent=False)

    if tm_name == "SASW Rep1_EVT_IASW_TR" and parameter_1 == 5 and parameter_2 == 3:
        assert packets[0][1][0][1][4][0] == parameter_1
        assert packets[0][1][0][2][4][0] == parameter_2
        return True

    elif tm_name == "SASW Rep1_EVT_FEE_TR":


        if parameter_1 == 3 and parameter_2 == 2:
            assert packets[1][1][0][1][4][0] == parameter_1
            assert packets[1][1][0][2][4][0] == parameter_2
            return True
        elif parameter_1 == 2 and parameter_2 == 7:
            assert packets[2][1][0][1][4][0] == parameter_1
            assert packets[2][1][0][2][4][0] == parameter_2
            return True
        elif parameter_1 == 7 and parameter_2 == 6:
            assert packets[3][1][0][1][4][0] == parameter_1
            assert packets[3][1][0][2][4][0] == parameter_2
            return True
        else:
            print("Packet does not exist. SASW Rep1_EVT_FEE_TR")
            return False

    else:
        print("Packet does not exist. ASW Rep1_EVT_IASW_TR")
        return False




    # return packets

    # print(packets[1][0][0].CTIME + (packets[1][0][0].FTIME/1000000))
    # filter for TM packets with the correct APID and source sequence counter (SSC) in the data field




def check_if_packet_is_received(ST=1,SST=7,pool_name="LIVE"):
    """
    Checks if a certain type of packet has been received
    :param ST: int
        The subtype of the packet that should be checked for
    :param SST: int
        The subsubtype of the packet that should be checked for
    :param pool_name: str
         Name of the TM pool in the database
    """

    assert isinstance(pool_name, str)
    assert isinstance(ST, int)
    assert isinstance(SST, int)


    raw_packet_list, data_packet_list = get_last_100_packets(pool_name=pool_name)
    # print(raw_packet_list)


    # ST 10 Stelle
    # SST 11 Stelle
    for i in range(len(raw_packet_list)):
        packet = cfl.get_header_parameters_detailed(raw_packet_list[i])

        # print(packet)

        current_packet_ST = packet[10][1]
        current_packet_SST = packet[11][1]



        try:
            current_timestamp = cfl.get_cuctime(raw_packet_list[i])
        except:
            current_timestamp = ""

        # print(current_packet_ST, current_packet_SST, current_timestamp)

        if current_packet_ST == ST and current_packet_SST == SST:
            print("Match")
            print(ST, SST, current_timestamp)
            return True
        else:
            continue

        # print(time)

        if current_packet_ST == ST and current_packet_SST == SST:
            print("Found it")





def get_sid_of_tm(packet):
    """
    Gets SID from raw packet data.
    :param packet: bytes
        Packet whose SID should be extracted
    """

    decoded_packet = packet.hex()
    header = decoded_packet[36:124]
    return int(header[3])




def get_frequency_of_hk(duration=60., frequency=20, SID=1, pool_name="LIVE"):
    """
           Check the time passing between TM packets during a given duration.
           This function makes a multiple database queries.
           :param pool_name: str
               Name of the TM pool in the database
           :param duration: float
               timeslot in which the incoming packages are checked for their cuc-timestamp
    """


    assert isinstance(duration, (float, int))
    assert isinstance(frequency, int)
    assert isinstance(SID, int)


    list_of_timestamps = []
    last_telemetry_packet = cfl.get_pool_rows(pool_name)[-1].raw
    timestamp = cfl.get_cuctime(last_telemetry_packet)
    # last_packet_sid = get_sid_of_tm(last_telemetry_packet)
    current_timestamp = 0.0
    end_time = timestamp + duration

    while current_timestamp <= end_time:

        current_telemetry_packet = cfl.get_pool_rows(pool_name)[-1].raw
        current_timestamp = cfl.get_cuctime(current_telemetry_packet)
        current_packet_sid = get_sid_of_tm((current_telemetry_packet))
        if current_timestamp not in list_of_timestamps and current_packet_sid == SID:
            list_of_timestamps.append(current_timestamp)
        else:
            continue

    list_of_differences = [j-i for i, j in zip(list_of_timestamps[:-1], list_of_timestamps[1:])]

    first_element = round(list_of_differences[0])
    chk = True

    for item in list_of_differences:
        if first_element != round(item):
            chk = False
            break

    if chk == True:
        # print(round(list_of_differences[0]))
        print(first_element)
        if first_element == frequency:
            print(True)
            return True
    else:
        print("Didn't work")
        return False





# get_frequency_of_hk()

def check_acknowledgement(pool_name, tc_identifier, duration=10):
    """
    Check that for a sent TC the acknowledgement packets were received (assuming the acknowledgement was enabled)
    Will return True when all tree acknowledgement TM packets (1,1), (1,3), (1,7) or (1,1), (1,3) or just (1,1) were
    received.

    :param pool_name: str
        Name of the telemetry pool
    :param tc_identifier: tuple or list
        (APID, SSC, CUC) or list of tuples of this kind
    :param duration: int
        Duration in seconds for how long the functions tries to get packets from the database
    :return: bool
        None if no acknowledgement packets were found for the TC
        True if one or up to all acknowledgement packets TM(1,1), TM(1,3), TM(1,7) were found
        False if one or all of TM(1,2), TM(1,4), TM(1,8) were found
    """
    outcome = None
    # check if there is a single or a list of TC for acknowledgements to check
    if isinstance(tc_identifier, tuple):
        outcome, acks = await_tc_acknow(pool_name=pool_name, tc_identifier=tc_identifier, duration=duration)

    if isinstance(tc_identifier, list):
        tc_res = []
        # do the check for all commands
        for telecommand in tc_identifier:
            outcome, acks = await_tc_acknow(pool_name=pool_name, tc_identifier=telecommand, duration=duration)
            tc_res.append(outcome)

        # check if the TC were successful (by acknowledgement TM packets)
        for item in tc_res:
            if item is True:
                outcome = True
            else:
                outcome = False
                break
    return outcome

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++


def condition_event_id(tmpackets, event_id, data_entries=None):
    """
    # checking the TM packets (list) if the event_id and, if given, the entries matches
    #   @param tmpackets: <list> of TM packets (events)
    # returns a list of TM packets
    :param tmpackets:
    :param event_id:
    :param data_entries:
    :return:
    """
    found_packets = []
    tmpackets = decode_tm(tm_packets=tmpackets)

    # compare the event identifier and if requested the data entries
    if len(tmpackets) > 0:
        for i in range(len(tmpackets)):
            tm_data = tmpackets[i][1]
            if tm_data is None:
                return found_packets
            if tm_data[0] is None:
                return found_packets
            if tm_data[0][0] is None:
                return found_packets
            if tm_data[0][0][0] is None:
                return found_packets
            event_identifier = tm_data[0][0][0]  # ToDo: Here the assumption is made that the eventId is the first entry!!!
            if event_identifier == event_id:
                if data_entries is not None:  # filter events which have the correct key and correct value
                    if isinstance(data_entries, dict):  # for a single entry
                        new_data_entries = []
                        new_data_entries.append(data_entries)
                        data_entries = new_data_entries
                    if isinstance(data_entries, list):  # for a array of entries
                        matches = False
                        # if one of the entries does not match the packet is rejected
                        for k in range(len(data_entries)):
                            if isinstance(data_entries[k], dict):
                                keys = data_entries[k].keys()
                                for key in keys:
                                    value = get_tm_data_entries(tm_packet=tmpackets[i], data_entry_names=key)
                                    if key in value:
                                        if value[key] == data_entries[k][key]:
                                            matches = True
                                        else:
                                            matches = False
                                            break
                            else:
                                logger.error('condition_event_id(): the provided list of TM packet data entries '
                                          'should be a dictionary key-value pairs. But unfortunately something '
                                          'else was given.')
                        if matches is True:
                            found_packets.append(tmpackets[i])
                else:  # no filtering for entries required, identifier match is enough
                    found_packets.append(tmpackets[i])
    return found_packets


def get_events(pool_name, severity, event_id, t_from=None, t_to=None, duration=None, entries=None):
    """
    For a given duration all events with suiting severity are collected.
    Filtering for events with specific entries can be done by providing them in the argument entries.
    The function makes a single database query. If upper time interval boundary is the future, the function waits
    before doing the database query.

    :param pool_name: str
        Name of the pool for TM packets in the database
    :param severity: int
        The severity of events is equal to the Sub-Service Type of TM packets
    :param event_id: str
        Event ID
    :param t_from: float
        CUC timestamp. Only events with a CUC higher or equal are taken into account
    :param t_to: float
        CUC timestamp. Only events with a CUC smaller or equal are taken into account
    :param duration: int or float
        Seconds of the time interval for TM packet timestamps
    :param entries: dict or list of dicts
        If the events should have specific entries the entries are provided as dicts
    :return: list
        List of event TM with the correct event ID and entries. Or a empty list.
    """
    # always a empty array should be returned in order to prevent code-breaking bugs
    result = []

    # set the time interval
    t_from, t_to = set_time_interval(pool_name=pool_name, t_from=t_from, t_to=t_to, duration=duration)

    # for the case that t_to is in future, wait
    current_cuc = cfl.get_last_pckt_time(pool_name=pool_name, string=False)
    if t_to > current_cuc:
        difference = t_to - current_cuc
        time.sleep(difference)

    # get packets
    tm_packets = fetch_packets(pool_name=pool_name, st=5, sst=severity, t_from=t_from, t_to=t_to)

    # check condition (if the event TM packets have been found)
    tm_list = condition_event_id(tmpackets=tm_packets, event_id=event_id, data_entries=entries)
    if len(tm_list) > 0:
        result = tm_list

    # logging and return of the result
    if len(result) > 0:
        desc = 'get_events: found {} events {} '.format(len(result), str(event_id))
        if entries is not None:
            desc += ' with key(s) '
            keys = entries.keys()
            for key in keys:
                desc += '{}={} '.format(key, entries[key])
        logger.debug(desc)
    else:
        logger.debug('get_events: no events {} found'.format(event_id))

    return result


def await_event(pool_name, severity, event_id, entries=None, duration=10, t_from=None, check_period=1, decode=True):
    """
    Wait for a event to happen. When it is received the function returns.
    Database queries are done periodically till the duration is elapsed or the event is received.

    :param str pool_name: Name of the TM pool in the database
    :param int severity: The severity of an event is equal with the Sub-Service Type of the TM packet
    :param str event_id: Event ID
    :param dict-or-list-of-dicts entries: Entries in the data field of the event TM packet which should be checked
    :param int-or-float duration: Seconds which will be waited. This time will be added to t_from
    :param float t_from: CUC timestamp of the start of the waiting for the event
    :param int-or-float check_period: Seconds between the database queries
    :param bool decode: If True the TM packets will be decoded, otherwise not

    :return: A list of the found event TM is returned. If none are found a empty list is returned.
    :rtype: list
    """
    # always a empty array should be returned in order to prevent code-breaking bugs
    result = []

    # set time interval for the desired packets
    t_from, t_to = set_time_interval(pool_name=pool_name, t_from=t_from, t_to=None, duration=duration)

    # set the interval of fetching packets from the pool
    if check_period is None:
        check_period = set_query_interval(t_from=t_from, t_to=t_to)

    st = 5
    sst = severity

    # repeat the database call till the TM packet was received or t_to is reached
    condition = True
    while condition is True:
        # get packets from the database
        packets = fetch_packets(pool_name=pool_name,
                                is_tm=True,
                                st=st,
                                sst=sst,
                                t_from=t_from,
                                t_to=t_to,
                                decode=decode,
                                silent=True)

        # check condition (if the event TM packets have been found)
        events = condition_event_id(tmpackets=packets, event_id=event_id, data_entries=entries)

        if len(events) > 0 or cfl.get_last_pckt_time(pool_name=pool_name, string=False) > t_to:
            condition = False
            result = events
        else:
            logger.debug('await_event: waiting for {}s and then doing the query again'.format(check_period))
            time.sleep(check_period)

    # logging and return of the result
    if len(result) > 0:
        desc = 'await_event: found {} event {} '.format(len(result), str(event_id))
        if entries is not None:
            desc += ' with key(s) '
            keys = entries.keys()
            for key in keys:
                desc += '{}={} '.format(key, entries[key])
        logger.info(desc)
    else:
        logger.info('await_event: no events {} found'.format(event_id))

    return result


def extract_status_data(tm_packet):
    """
    Extract status data from Service 21 DAT_CCD_Window packets. Science data blocks are ignored
    Not all parameters are decoded correctly: HK_STAT_DATA_ACQ_TYPE, HK_STAT_DATA_ACQ_SRC, HK_STAT_CCD_TIMING_SCRIP
    HK_STAT_DATA_ACQ_TIME

    :param tm_packet: PUS packet
        A TM(21,3)
    :return: dict
        Status data of a TM(21,3)
    """
    status_data = {}

    header = cfl.Tmread(tm_packet)
    # check if it is a TM(21,3)
    if header[10] == 21 and header[11] == 3:
        data_field = header[-2]
        # hardcoded information on the parameter data type tuples (name, datatype, bits)
        parameter_data_types = [
            ('HK_STAT_DATA_ACQ_ID', 'uint:32', 32),
            ('HK_STAT_DATA_ACQ_TYPE', 'uint:4', 4),
            ('HK_STAT_DATA_ACQ_SRC', 'uint:4', 4),
            ('HK_STAT_CCD_TIMING_SCRIP', 'uint:8', 8),
            ('HK_STAT_DATA_ACQ_TIME', 'bits:48', 48),
            ('HK_STAT_EXPOSURE_TIME',  'uint:32', 32),
            ('HK_STAT_TOTAL_PACKET_NUM', 'uint:16', 16),
            ('HK_STAT_CURRENT_PACKET_N', 'uint:16', 16),
            ('HK_VOLT_FEE_VOD', 'float:32', 32),
            ('HK_VOLT_FEE_VRD', 'float:32', 32),
            ('HK_VOLT_FEE_VOG', 'float:32', 32),
            ('HK_VOLT_FEE_VSS', 'float:32', 32),
            ('HK_TEMP_FEE_CCD', 'float:32', 32),
            ('HK_TEMP_FEE_ADC', 'float:32', 32),
            ('HK_TEMP_FEE_BIAS', 'float:32', 32),
            ('HK_STAT_PIX_DATA_OFFSET', 'uint:16', 16),
            ('HK_STAT_NUM_DATA_WORDS', 'uint:16', 16)
        ]
        # get format string and length of bits
        format_string = ''
        bit_length = 0
        for i in range(len(parameter_data_types)):
            # build the format string out of the list parameter_data_types
            if format_string != '':
                format_string += ','
            format_string += parameter_data_types[i][1]
            # calculate how many bits the parameter use
            bit_length += parameter_data_types[i][2]

        # crop the data field (just retrieve the interesting bits)
        data_field_crop = data_field[:bit_length]
        # unpack the bits using the format string
        status_data_values = data_field_crop.unpack(format_string)
        # construct a dictionary of parameter name and value

        for k in range(len(parameter_data_types)):
            # get the name of the parameter
            name = parameter_data_types[k][0]
            # get the value of the parameter
            value = status_data_values[k]
            # add a entry to the dictionary
            status_data[name] = value
    else:
        logger.debug('extract_status_data: provided TM packet is not a TM(21,3)')

    return status_data


def get_acquisition(pool_name, tm_21_3):
    """
    Get all packets with the same acquisition ID.
    Requirement: the packet of the acquisition with the lowest CUC timestamp
    For every acquisition type of the same ID, it is checked if all packets were found.

    :param pool_name: str
        Name of the pool for TM/TC packets in the database
    :param tm_21_3: PUS packet
        The TM(21,3) of the desired acquisition with the lowest CUC timestamp
    :return: list
        All packets of the acquisition (not decoded)
    """
    result = []
    transmission_finished = False

    t_first_received = cfl.get_cuctime(tml=tm_21_3)

    # get the acquisition ID
    current_acq_id = extract_status_data(tm_packet=tm_21_3)['HK_STAT_DATA_ACQ_ID']

    # get TM(21,3), not decoded and check if the acquisition ID are the correct ones
    t_to = t_first_received + 3
    logger.info(t_first_received)
    while not transmission_finished:
        data = get_tm(pool_name=pool_name, st=21, sst=3, t_from=t_first_received, t_to=t_to, decode=False)
        # filter data for ACQ_ID
        data_acq_id = []
        data_acq_types = []
        for pac in data:
            # check if the packets has the correct acquisition ID
            status_data = extract_status_data(tm_packet=pac)
            if status_data['HK_STAT_DATA_ACQ_ID'] == current_acq_id:
                data_acq_id.append(pac)
            # add the acquisition type to a list
            data_acq_types.append(status_data['HK_STAT_DATA_ACQ_TYPE'])

        # extract all acquisition types and check if all packets are there
        data_acq_types = set(data_acq_types)
        found_all_packets = []
        meta_data = []
        for type in data_acq_types:
            # extract all packets with the current type (acquisition type)
            curr_type_packets = []
            for item in data_acq_id:
                status_data = extract_status_data(tm_packet=item)
                if status_data['HK_STAT_DATA_ACQ_TYPE'] == type:
                    curr_type_packets.append(item)
            # check if all packets of this type are here
            total_num = extract_status_data(tm_packet=curr_type_packets[0])['HK_STAT_TOTAL_PACKET_NUM']
            if len(curr_type_packets) == total_num:
                found_all_packets.append(True)
            else:
                found_all_packets.append(False)
            meta_data.append({'acquisition_id': current_acq_id,
                              'acquisition_type': type,
                              'total_num': total_num,
                              'found_packets': len(curr_type_packets)})

        # if every acquisition type has all packets, all packets were received
        have_all_packets = None
        for value in found_all_packets:
            if value is True:
                have_all_packets = True
            else:
                have_all_packets = False
                break

        logger.debug('Current status of found acquisition packets:')
        for i in range(len(meta_data)):
            logger.debug(meta_data[i])
        if have_all_packets is True:
            transmission_finished = True
            result = data_acq_id
        else:
            # set the new t_to and do another query with extended time interval
            last = highest_cuc_timestamp(tm_list=data)
            t_to = cfl.get_cuctime(last) + 3
            logger.info(t_to)
            # after 5 min stop the loop, if not finished yet
            length_of_time = t_to - t_first_received
            if length_of_time > 300:
                logger.info('Aborted to query for all acquisition packets after 5 minutes.')
                break

        logger.info('Found acquisition packets:')
        for i in range(len(meta_data)):
            logger.info(meta_data[i])
    return result


def get_data_of_last_tc(pool_name="LIVE", apid=None):
    """
    Finds the newest Telecommand in database with the Telemetry just before.
    :param pool_name: str
        Name of the pool for TM/TC packets in the database
    :return: str
        timestamp of packet, IID of packet, First four bytes of packet data
    """

    tm_pool = cfl.get_pool_rows(pool_name)

    tcpkt = tm_pool.filter(cfl.DbTelemetry.is_tm == 1).order_by(cfl.DbTelemetry.idx.desc())

    if apid is not None:
        tcpkt = tcpkt.filter(cfl.DbTelemetry.apid == apid)

    tcpkt = tcpkt.first()

    if tcpkt is None:
        return

    tc_id = tcpkt.idx
    tc_bytes = tcpkt.raw[:4]  # fist 4 bytes of TC used for identification in ACK service

    tm_before_tc = tm_pool.filter(cfl.DbTelemetry.is_tm == 0, cfl.DbTelemetry.idx < tc_id).order_by(cfl.DbTelemetry.idx.desc()).first()

    timestamp = tm_before_tc.timestamp
    timestamp = float(timestamp[:-1])
    return timestamp, tc_id, tc_bytes


def verify_no_more_hk(wait_time=5, pool_name="LIVE"):
    """
    Function waits for a spcified time and the searches the data pool for HK telemetry.
    Returns True if there is no HK.
    Returns False if there is HK.
    :param wait_time: int
        timespan in which the program checks if a hk has appeard
    :param pool_name: str
        Name of the pool for TM/TC packets in the database
    :return: boolean
        True if there is no HK, False if there is a HK
    """
    assert isinstance(SID, int)
    assert isinstance(pool_name, str)

    hk_signature = "0001050000000000000000000000000000000000000000000000000000000000000000000000000000000112"
    time.sleep(wait_time)
    # TODO incorporate function to find last 100 packets
    list_of_packets = []
    for i in range (1,1000):
        current_telemetry_packet = cfl.get_pool_rows(pool_name)[-i]
        current_raw = current_telemetry_packet.raw
        current_data = current_telemetry_packet.data
        list_of_packets.append(current_data.hex())

        try:
            current_timestamp = cfl.get_cuctime(current_raw)
            print(current_timestamp)
        except:
            break

    if hk_signature in list_of_packets:
        return False
    else:
        return True


def get_tm_timestamp(packet, pool_name="LIVE"):
    """
    gets timestamp from packet irregardless of data type
    """
    pass


def get_last_100_packets(pool_name="Live"):

# TODO Fix function to work with any number of packets
    raw_packets = []
    data_packets = []
    data_pool = cfl.get_pool_rows(pool_name)



    for i in range(1, 101):
        try:
            current_packet = cfl.get_pool_rows(pool_name)[-i]
            current_raw = current_packet.raw
            current_data = current_packet.data
            raw_packets.append(current_raw)
            data_packets.append(current_data)
        except IndexError:
            break


    return raw_packets, data_packets







def get_dpu_mode(pool_name="LIVE"):
    """
    Get the data from the last entry in the database and check its DPU Mode.
    :param pool_name: str
        Name of the pool for TM/TC packets in the database
    :param dpu_mode: dict
        DPU Mode of the packet

    """

    data_packet = cfl.get_pool_rows(pool_name)[-1].raw
    dpu_mode = get_tm_data_entries(data_packet,"DpuMode")
    print(dpu_mode)

def get_packet_length(pool_name="LIVE"):
    """
    Get the data from the last entry in the database and check its length.
    :param pool_name: str
        Name of the pool for TM/TC packets in the database
    :param data_packet: bit
        data in the last entry in database
    :param packet_length: int
        Length of data_packet

    """

    data_packet = cfl.get_pool_rows(pool_name)[-1].raw
    packet_length = len(data_packet)
    print(packet_length)

def get_version_number(version_number="0x0112", pool_name="LIVE"):
    """
    Get the version number of the newest TM packet.
    :param version_number: str
        version number which should be verified
    :param pool_name: str
        Name of the pool for TM/TC packets in the database
    :param data_packet: bytes
        Data in Packet
    :param packet_version_number_dic: dic
        dictionary containing the version number
    :param packet_version_number: str
        version number converted into hex
    """

    assert isinstance(version_number, str)

    data_packet = cfl.get_pool_rows(pool_name)[-1].raw
    packet_version_number_dic = get_tm_data_entries(data_packet, "VersionNumber")
    # print(packet_version_number)
    packet_version_number = hex(packet_version_number_dic["VersionNumber"])
    if packet_version_number == version_number:
        print(True)
        return True
    else:
        print(False)
        return False


def await_tc_identifier(pool_name, tc_apid, tc_ssc):
    """
    Gather the data necessary to identify the newest telecommand and put it in tuple.
    :param pool_name: str
        Name of the pool for TM/TC packets in the database
    :param tc_apid: int or str
        APID of the TC
    :param tc_ssc: int
        Sequence number of TC
    :param last_tm_timestamp: float
        Timestamp of the latest TM in datapool
    :return: tc_identifier: tuple
        Tuple with data to identify TC

    """

    assert isinstance(pool_name, str)
    assert isinstance(tc_apid, int) or isinstance(tc_apid, str)
    assert isinstance(tc_ssc, int)

    last_tm_timestamp = cfl.get_pool_rows(pool_name)[-1].timestamp
    length_last_tm_timestamp = len(last_tm_timestamp)
    last_tm_timestamp = last_tm_timestamp[:length_last_tm_timestamp - 1]
    last_tm_timestamp = float(last_tm_timestamp)

    tc_identifier = (tc_apid, tc_ssc, last_tm_timestamp)

    return tc_identifier


def get_tc_identifier(pool_name="LIVE", tc_apid=321, tc_ssc=1, tc_time=0.):
    """
    Gather the data necessary to identify the newest telecommand and put it in tuple.
    :param pool_name: str
        Name of the pool for TM/TC packets in the database
    :param tc_apid: int or str
        APID of the TC
    :param tc_ssc: int
        Sequence number of TC
    :param tc_time: float or int
        Timestamp of the latest TM in datapool
    :return: tc_identifier: tuple
        Tuple with data to identify TC

    """
    assert isinstance(pool_name, str)
    assert isinstance(tc_apid, int) or isinstance(tc_apid, str)
    assert isinstance(tc_ssc, int)
    assert isinstance(tc_time, int) or isinstance(tc_time, float)

    tc_time = float(tc_time)

    tc_identifier = (tc_apid, tc_ssc, tc_time)

    return tc_identifier


def await_tc_ack(*args, **kwargs):

    return cfl.Verification.await_tc_ack(*args, **kwargs)


if __name__ == '__main__':
    sys.path.append('.')