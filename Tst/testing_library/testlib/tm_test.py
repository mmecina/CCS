import tm
import ccs_function_lib as cfl
import confignator
import matplotlib
matplotlib.use('Gtk3Cairo')
import confignator
import sys
sys.path.append(confignator.get_option('paths', 'ccs'))

from confignator import config
check_cfg = config.get_config(file_path=confignator.get_option('config-files', 'ccs'))

import inspect



telemetry = cfl.get_pool_rows("PLM")
telemetry_packet_1_1 = cfl.get_pool_rows("PLM")[0].iid
telemetry_packet_1 = cfl.get_pool_rows("PLM")[0].raw
telemetry_packet_2 = cfl.get_pool_rows("PLM")[1].raw


""" 
To test PI1VALUE on 5_3     1, 3, 4
"""

packet_1 = telemetry[1]
packet_2 = telemetry[3]
packet_3 = telemetry[4]
packet_4 = telemetry[5]

print(packet_1.iid, packet_1.raw.hex())
print(packet_2.iid, packet_2.raw.hex())
print(packet_3.iid, packet_3.raw.hex())

# print(tm.decode_single_tm_packet(packet_4.raw)[1])

decoded_packet = tm.decode_single_tm_packet(packet_4.raw)

print(decoded_packet)

print(decoded_packet[1])
print(type(decoded_packet[1][1]))
print(decoded_packet[1][1])
string_packet = str(decoded_packet[1][1])
string_packet = string_packet[2:25]
print("string: ", string_packet)
# new_packet = decoded_packet[1][1](1-25)
# print(new_packet)
print(type(decoded_packet[1][0][0][4][0]))

wanted_data = string_packet, decoded_packet[1][0][0][4][0]

print(wanted_data)



# dictionary_of_tms = cfl.get_tm_id()

# tm_list = list(dictionary_of_tms.keys())

# print(tm_list)

# print(telemetry_packet_1)

# print(cfl.Tmdata(telemetry_packet_3_1))

# print(telemetry_packet_3_1.raw)
# print(telemetry_packet_3_1.timestamp)

# print(tm.get_data_of_last_tc("PLM"))
# print(telemetry_packet_3_1.iid)

# test_packet = database.tm_db.DBTelemetry()
# print(test_packet)


# print(telemetry_packet_3.stc)
# print(cfl.get_cuc_now())

list_of_tm_packets = [telemetry_packet_1, telemetry_packet_2]

# package_id = telemetry_packet_3.iid
# print(package_id)
# package_time = cfl.get_cuctime(telemetry_packet_3)
# print(package_time)


# packet_list = tm.fetch_packets("PLM", is_tm=True, st=5, sst=None, apid=321, ssc=None, t_from=5224., t_to=5240.,
#                   dest_id=None, not_apid=None, decode=True, silent=False)



# print(tm.get_tc_acknow(pool_name="PLM", tc_apid=321, tc_ssc=1, tm_st=1, tm_sst=None))

# print(packet_list[0])
# print(packet_list[0][0][0])
# print(packet_list[0][1][0][0])   # EvtId
# print(packet_list[0][1][0][1])   # SrcIaswSt
# print(packet_list[0][1][0][2])   # DestIaswSt

# print(packet_list[1])
# print(packet_list[1][1][0][0])
# print(packet_list[1][1][0][1])
# print(str(packet_list[1][1][0][1][0]) + " " + str(packet_list[1][1][0][1][4][0]))
# print(packet_list[1][1][0][2])



# print(tm.get_tm_data_entries(telemetry_packet_3, "SrcIaswSt"))
# print(tm.get_tm_data_entries(packet_list[0][0][0], "SrcIaswSt"))


# important tm.check_if_packet_is_received(pool_name="PLM")
# tm.get_last_100_packets("PLM")




# header = cfl.Tmread(telemetry_packet_1)







# print(get_time_of_last_tc(pool_name="PLM"))


# decode_list = tm.decode_single_tm_packet(telemetry_packet_3)[1][0]









"""
test_1 = cfl.get_header_parameters_detailed(telemetry_packet_1)
test_2 = cfl.get_header_parameters_detailed(telemetry_packet_2)


print(test_1)
print(test_2)
"""

# y = tm.get_tc_acknow(pool_name='PLM', t_tc_sent=60.0, tc_apid=321, tc_ssc=9, tm_st=3, tm_sst=1)
# print(y)
"""
x = tm.get_5_1_tc_acknow(pool_name='PLM', t_tc_sent=get_time_of_last_tc("PLM"), tc_apid=321, tc_ssc=1, tm_st=5, tm_sst=None)
print(x[0])
print(x[0][0][0])
print(x[0][0][1].hex())
print(x[1][0][1].hex())
print(x[2][0][1].hex())
print(x[3][0][1].hex())
"""

# print(cfl.Tmdata(x[0][0][1]))
# read = cfl.Tmread(x[0][0][1])
# print(read)
# for i in x:
    # print(i[0][1].hex())
    # print(i)
    # print(tm.get_tm_data_entries(i, "EvtId"))
    # tm.decode_single_tm_packet(i)

# get_list_from_d b = tm.fetch_packets(pool_name="PLM", is_tm=True, st=None, sst=None, apid=None, ssc=None, t_from=0., t_to=1401.,
#                  dest_id=None, not_apid=None, decode=False, silent=False)


# test = tm.get_tc_acknow(pool_name="PLM", t_tc_sent=1980., tc_apid=321, tc_ssc=1, tm_st=1, tm_sst=1)
# test = tm.get_5_1_tc_acknow(pool_name='PLM', t_tc_sent=0., tc_apid=321, tc_ssc=0, tm_st=5, tm_sst=1)

# print(test)
# print(test[0])
# print(test[1][0][0][0].CTIME + (test[1][0][0][0].FTIME/1000000))


# print(tm.get_tc_acknow.__globals__["get_tc_acknow"])

# print(inspect.signature(tm.get_tc_acknow))



# identified_tc = tm.get_tc_identifier(pool_name="PLM",tc_apid=321,tc_ssc=1, tc_time=100)



# acknowledgement = tm.await_tc_acknow(pool_name="PLM", tc_identifier=identified_tc, duration=10, tm_st=1, tm_sst=7)


# print(acknowledgement[1][0][0][0].CTIME + (acknowledgement[1][0][0][0].FTIME/1000000))







"""
# fetch funktion, demonstration von .CTIME und FTIME

test = tm.fetch_packets(pool_name="PLM", is_tm=True, st=3, sst=25, apid=321, ssc=None, t_from=0.00, t_to=21.0,
                  dest_id=None, not_apid=None, decode=True, silent=False)


# print(test)
# print(test[0][0][1])
# print("Test: ", test[0][0][1])
header = test[0][0][0]
# print(header.CTIME)
# print(header.FTIME)

print(header.CTIME + (header.FTIME/1000000))

test_liste = []

for i in test:
    test_liste.append(i[0][0])

print(len(test_liste))
print(test_liste)

"""




