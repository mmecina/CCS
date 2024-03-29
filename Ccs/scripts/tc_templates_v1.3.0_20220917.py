# TC templates generated from schema mib_smile_sxi_3_3 (VDF:1.3)
# Date: 2022-09-19

# TC(3,1): SASW CreHkCmd [KSC50052]
# Create a Housekeeping Parameter Report Structure
SidNoCal = None  # KSP50190
Period = None  # KSP50173
NParam = None  # KSP50171
ParamId = None  # KSP50172
cfl.Tcsend_DB('SASW CreHkCmd', SidNoCal, Period, NParam, ParamId, pool_name='LIVE')

#! CCS.BREAKPOINT

# TC(3,3): SASW DelHkCmd [KSC50053]
# Delete a Housekeeping or Diagnostic Parameter Report Structure
SidNoCal = None  # KSP50190
cfl.Tcsend_DB('SASW DelHkCmd', SidNoCal, pool_name='LIVE')

#! CCS.BREAKPOINT

# TC(3,5): SASW EnbHkCmd [KSC50054]
# Enable Periodic Generation of a Housekeeping Parameter Report St
SidNoCal = None  # KSP50190
cfl.Tcsend_DB('SASW EnbHkCmd', SidNoCal, pool_name='LIVE')

#! CCS.BREAKPOINT

# TC(3,6): SASW DisHkCmd [KSC50055]
# Disable Periodic Generation of a Housekeeping Parameter Report S
SidNoCal = None  # KSP50190
cfl.Tcsend_DB('SASW DisHkCmd', SidNoCal, pool_name='LIVE')

#! CCS.BREAKPOINT

# TC(3,9): SASW RepStructHkCmd [KSC50056]
# Report Housekeeping Parameter Report Structure
SidNoCal = None  # KSP50190
cfl.Tcsend_DB('SASW RepStructHkCmd', SidNoCal, pool_name='LIVE')

#! CCS.BREAKPOINT

# TC(3,128): SASW ReqHkRepCmd [KSC50060]
# Request a Housekeeping Report
SidNoCal = None  # KSP50190
cfl.Tcsend_DB('SASW ReqHkRepCmd', SidNoCal, pool_name='LIVE')

#! CCS.BREAKPOINT

# TC(3,131): SASW ModHkPeriodCmd [KSC50061]
# Modify the Period of Housekeeping Parameter Report Structures
SidNoCal = None  # KSP50190
Period = None  # KSP50173
cfl.Tcsend_DB('SASW ModHkPeriodCmd', SidNoCal, Period, pool_name='LIVE')

#! CCS.BREAKPOINT

# TC(5,5): SASW EnbCmd [KSC50137]
# Enable Generation of Event Identifiers
NEvtId = None  # KSP50048
EvtId = None  # KSP50043
cfl.Tcsend_DB('SASW EnbCmd', NEvtId, EvtId, pool_name='LIVE')

#! CCS.BREAKPOINT

# TC(5,6): SASW DisCmd [KSC50138]
# Disable Generation of Event Identifiers
NEvtId = None  # KSP50048
EvtId = None  # KSP50043
cfl.Tcsend_DB('SASW DisCmd', NEvtId, EvtId, pool_name='LIVE')

#! CCS.BREAKPOINT

# TC(6,2): SASW LoadCmd [KSC50139]
# Load Memory using Absolute Addresses
WriteMemoryId = None  # KSP50203
StartAddress = None  # KSP50202
BlockLength = None  # KSP50199
BlockData = None  # KSP50198
cfl.Tcsend_DB('SASW LoadCmd', WriteMemoryId, StartAddress, BlockLength, BlockData, pool_name='LIVE')

#! CCS.BREAKPOINT

# TC(6,5): SASW DumpCmd [KSC50140]
# Dump Memory using Absolute Addresses
ReadMemoryId = None  # KSP50201
StartAddress = None  # KSP50202
BlockLength = None  # KSP50199
cfl.Tcsend_DB('SASW DumpCmd', ReadMemoryId, StartAddress, BlockLength, pool_name='LIVE')

#! CCS.BREAKPOINT

# TC(9,128): SASW TimeUpdt [KSC50142]
# Update Time
ObtTime = None  # KSP50372
cfl.Tcsend_DB('SASW TimeUpdt', ObtTime, pool_name='LIVE')

#! CCS.BREAKPOINT

# TC(13,8): SASW DownAbortCmd [KSC50147]
# Abort Downlink
SduId = None  # KSP50195
cfl.Tcsend_DB('SASW DownAbortCmd', SduId, pool_name='LIVE')

#! CCS.BREAKPOINT

# TC(13,9): SASW UpFirstCmd [KSC50148]
# First Uplink Part
SduId = None  # KSP50195
SduSeqNmb = None  # KSP50196
SduDataPartLength = None  # KSP50194
SduDataPart = None  # KSP50193
cfl.Tcsend_DB('SASW UpFirstCmd', SduId, SduSeqNmb, SduDataPartLength, SduDataPart, pool_name='LIVE')

#! CCS.BREAKPOINT

# TC(13,10): SASW UpInterCmd [KSC50149]
# Intermediate Uplink Part
SduId = None  # KSP50195
SduSeqNmb = None  # KSP50196
SduDataPartLength = None  # KSP50194
SduDataPart = None  # KSP50193
cfl.Tcsend_DB('SASW UpInterCmd', SduId, SduSeqNmb, SduDataPartLength, SduDataPart, pool_name='LIVE')

#! CCS.BREAKPOINT

# TC(13,11): SASW UpLastCmd [KSC50150]
# Last Uplink Part
SduId = None  # KSP50195
SduSeqNmb = None  # KSP50196
SduDataPartLength = None  # KSP50194
SduDataPart = None  # KSP50193
cfl.Tcsend_DB('SASW UpLastCmd', SduId, SduSeqNmb, SduDataPartLength, SduDataPart, pool_name='LIVE')

#! CCS.BREAKPOINT

# TC(13,129): SASW StartDownCmd [KSC50152]
# Trigger Large Packet Down-Transfer
SduId = None  # KSP50195
cfl.Tcsend_DB('SASW StartDownCmd', SduId, pool_name='LIVE')

#! CCS.BREAKPOINT

# TC(17,1): SASW AreYouAliveCmd [KSC50153]
# Perform Are-You-Alive Connection Test
cfl.Tcsend_DB('SASW AreYouAliveCmd', pool_name='LIVE')

#! CCS.BREAKPOINT

# TC(20,1): SASW RepParamValuesCmd [KSC50155]
# Report Parameter Values
ParamSetId = None  # KSP50281
cfl.Tcsend_DB('SASW RepParamValuesCmd', ParamSetId, pool_name='LIVE')

#! CCS.BREAKPOINT

# TC(20,3): SASW SetParValAdcRngsCmd [KSC50159]
# Set Parameter Values for ADC Ranges
# ParamSetId = ADC_RANGES  # KSP50281 [NOT EDITABLE]
P3V9WarnLowerLimit = None  # KSP50278
P3V9AlarmLowerLimit = None  # KSP50276
P3V9WarnUpperLimit = None  # KSP50279
P3V9AlarmUpperLimit = None  # KSP50277
P3V3WarnLowerLimit = None  # KSP50270
P3V3AlarmLowerLimit = None  # KSP50268
P3V3WarnUpperLimit = None  # KSP50271
P3V3AlarmUpperLimit = None  # KSP50269
P3V3_LVDSWarnLowerLimit = None  # KSP50274
P3V3_LVDSAlarmLowerLimit = None  # KSP50272
P3V3_LVDSWarnUpperLimit = None  # KSP50275
P3V3_LVDSAlarmUpperLimit = None  # KSP50273
P2V5WarnLowerLimit = None  # KSP50266
P2V5AlarmLowerLimit = None  # KSP50264
P2V5WarnUpperLimit = None  # KSP50267
P2V5AlarmUpperLimit = None  # KSP50265
P1V8WarnLowerLimit = None  # KSP50262
P1V8AlarmLowerLimit = None  # KSP50260
P1V8WarnUpperLimit = None  # KSP50263
P1V8AlarmUpperLimit = None  # KSP50261
P1V2WarnLowerLimit = None  # KSP50258
P1V2AlarmLowerLimit = None  # KSP50256
P1V2WarnUpperLimit = None  # KSP50259
P1V2AlarmUpperLimit = None  # KSP50257
RefWarnLowerLimit = None  # KSP50284
RefAlarmLowerLimit = None  # KSP50282
RefWarnUpperLimit = None  # KSP50285
RefAlarmUpperLimit = None  # KSP50283
TEMP1WarnLowerLimit = None  # KSP50291
TEMP1AlarmLowerLimit = None  # KSP50289
TEMP1WarnUpperLimit = None  # KSP50292
TEMP1AlarmUpperLimit = None  # KSP50290
TEMP_FEEWarnLowerLimit = None  # KSP50299
TEMP_FEEAlarmLowerLimit = None  # KSP50297
TEMP_FEEWarnUpperLimit = None  # KSP50300
TEMP_FEEAlarmUpperLimit = None  # KSP50298
TEMP_CCDWarnLowerLimit = None  # KSP50295
TEMP_CCDAlarmLowerLimit = None  # KSP50293
TEMP_CCDWarnUpperLimit = None  # KSP50296
TEMP_CCDAlarmUpperLimit = None  # KSP50294
I_FEE_ANAWarnLowerLimit = None  # KSP50237
I_FEE_ANAAlarmLowerLimit = None  # KSP50235
I_FEE_ANAWarnUpperLimit = None  # KSP50238
I_FEE_ANAAlarmUpperLimit = None  # KSP50236
I_FEE_DIGWarnLowerLimit = None  # KSP50241
I_FEE_DIGAlarmLowerLimit = None  # KSP50239
I_FEE_DIGWarnUpperLimit = None  # KSP50242
I_FEE_DIGAlarmUpperLimit = None  # KSP50240
I_DPUWarnLowerLimit = None  # KSP50233
I_DPUAlarmLowerLimit = None  # KSP50231
I_DPUWarnUpperLimit = None  # KSP50234
I_DPUAlarmUpperLimit = None  # KSP50232
I_RSEWarnLowerLimit = None  # KSP50249
I_RSEAlarmLowerLimit = None  # KSP50247
I_RSEWarnUpperLimit = None  # KSP50250
I_RSEAlarmUpperLimit = None  # KSP50248
I_HEATERWarnLowerLimit = None  # KSP50245
I_HEATERAlarmLowerLimit = None  # KSP50243
I_HEATERWarnUpperLimit = None  # KSP50246
I_HEATERAlarmUpperLimit = None  # KSP50244
TEMP_PSUWarnLowerLimit = None  # KSP50303
TEMP_PSUAlarmLowerLimit = None  # KSP50301
TEMP_PSUWarnUpperLimit = None  # KSP50304
TEMP_PSUAlarmUpperLimit = None  # KSP50302
ADCParamCrc = None  # KSP50225
cfl.Tcsend_DB('SASW SetParValAdcRngsCmd', P3V9WarnLowerLimit, P3V9AlarmLowerLimit, P3V9WarnUpperLimit, P3V9AlarmUpperLimit, P3V3WarnLowerLimit, P3V3AlarmLowerLimit, P3V3WarnUpperLimit, P3V3AlarmUpperLimit, P3V3_LVDSWarnLowerLimit, P3V3_LVDSAlarmLowerLimit, P3V3_LVDSWarnUpperLimit, P3V3_LVDSAlarmUpperLimit, P2V5WarnLowerLimit, P2V5AlarmLowerLimit, P2V5WarnUpperLimit, P2V5AlarmUpperLimit, P1V8WarnLowerLimit, P1V8AlarmLowerLimit, P1V8WarnUpperLimit, P1V8AlarmUpperLimit, P1V2WarnLowerLimit, P1V2AlarmLowerLimit, P1V2WarnUpperLimit, P1V2AlarmUpperLimit, RefWarnLowerLimit, RefAlarmLowerLimit, RefWarnUpperLimit, RefAlarmUpperLimit, TEMP1WarnLowerLimit, TEMP1AlarmLowerLimit, TEMP1WarnUpperLimit, TEMP1AlarmUpperLimit, TEMP_FEEWarnLowerLimit, TEMP_FEEAlarmLowerLimit, TEMP_FEEWarnUpperLimit, TEMP_FEEAlarmUpperLimit, TEMP_CCDWarnLowerLimit, TEMP_CCDAlarmLowerLimit, TEMP_CCDWarnUpperLimit, TEMP_CCDAlarmUpperLimit, I_FEE_ANAWarnLowerLimit, I_FEE_ANAAlarmLowerLimit, I_FEE_ANAWarnUpperLimit, I_FEE_ANAAlarmUpperLimit, I_FEE_DIGWarnLowerLimit, I_FEE_DIGAlarmLowerLimit, I_FEE_DIGWarnUpperLimit, I_FEE_DIGAlarmUpperLimit, I_DPUWarnLowerLimit, I_DPUAlarmLowerLimit, I_DPUWarnUpperLimit, I_DPUAlarmUpperLimit, I_RSEWarnLowerLimit, I_RSEAlarmLowerLimit, I_RSEWarnUpperLimit, I_RSEAlarmUpperLimit, I_HEATERWarnLowerLimit, I_HEATERAlarmLowerLimit, I_HEATERWarnUpperLimit, I_HEATERAlarmUpperLimit, TEMP_PSUWarnLowerLimit, TEMP_PSUAlarmLowerLimit, TEMP_PSUWarnUpperLimit, TEMP_PSUAlarmUpperLimit, ADCParamCrc, pool_name='LIVE')

#! CCS.BREAKPOINT

# TC(20,3): SASW SetParValHeatCtlCmd [KSC50160]
# Set Parameter Values for Heater Control of IASW
# ParamSetId = HEAT_CTRL_IASW  # KSP50281 [NOT EDITABLE]
HctrlParExecPer = None  # KSP50229
HctrlParMaxDeltaVoltage = None  # KSP50444
HctrlParVctrlLowerVolt = None  # KSP50448
HctrlParVctrlUpperVolt = None  # KSP50449
HctrlParTempRefLL = None  # KSP50446
HctrlParTempRefUL = None  # KSP50447
HctrlParTempRef = None  # KSP50230
HctrlParCoeffP = None  # KSP50228
HctrlParCoeffI = None  # KSP50443
HctrlParOffset = None  # KSP50445
ADCParamCrc = None  # KSP50225
cfl.Tcsend_DB('SASW SetParValHeatCtlCmd', HctrlParExecPer, HctrlParMaxDeltaVoltage, HctrlParVctrlLowerVolt, HctrlParVctrlUpperVolt, HctrlParTempRefLL, HctrlParTempRefUL, HctrlParTempRef, HctrlParCoeffP, HctrlParCoeffI, HctrlParOffset, ADCParamCrc, pool_name='LIVE')

#! CCS.BREAKPOINT

# TC(20,3): SASW SetParValRseParCmd [KSC50161]
# Set Parameter Values for RSE Parameters
# ParamSetId = RSE_PARAM  # KSP50281 [NOT EDITABLE]
MotorCurr = None  # KSP50255
SettlingTime = None  # KSP50288
ChopDutyCyc = None  # KSP50226
MaxMotorTemp = None  # KSP50253
MaxElecTemp = None  # KSP50251
MaxSteps = None  # KSP50254
RseConfig = None  # KSP50286
MaxMotorCurr = None  # KSP50252
EmergencySteps = None  # KSP50227
ParamCrc = None  # KSP50280
cfl.Tcsend_DB('SASW SetParValRseParCmd', MotorCurr, SettlingTime, ChopDutyCyc, MaxMotorTemp, MaxElecTemp, MaxSteps, RseConfig, MaxMotorCurr, EmergencySteps, ParamCrc, pool_name='LIVE')

#! CCS.BREAKPOINT

# TC(20,128): SASW ParamLoadArmCmd [KSC50162]
# Arm Parameter Load
cfl.Tcsend_DB('SASW ParamLoadArmCmd', pool_name='LIVE')

#! CCS.BREAKPOINT

# TC(20,129): SASW ParamLoadDisarmCmd [KSC50163]
# Disarm Parameter Load
cfl.Tcsend_DB('SASW ParamLoadDisarmCmd', pool_name='LIVE')

#! CCS.BREAKPOINT

# TC(191,1): SASW FdCheckEnbGlobCmd [KSC50164]
# Globally EnableFdChecks
cfl.Tcsend_DB('SASW FdCheckEnbGlobCmd', pool_name='LIVE')

#! CCS.BREAKPOINT

# TC(191,2): SASW FdCheckDisGlobCmd [KSC50165]
# Globally Disable FdChecks
cfl.Tcsend_DB('SASW FdCheckDisGlobCmd', pool_name='LIVE')

#! CCS.BREAKPOINT

# TC(191,3): SASW FdCheckEnbCmd [KSC50166]
# Enable FdCheck
FdChkId = None  # KSP50073
cfl.Tcsend_DB('SASW FdCheckEnbCmd', FdChkId, pool_name='LIVE')

#! CCS.BREAKPOINT

# TC(191,4): SASW FdCheckDisCmd [KSC50167]
# Disable FdCheck
FdChkId = None  # KSP50073
cfl.Tcsend_DB('SASW FdCheckDisCmd', FdChkId, pool_name='LIVE')

#! CCS.BREAKPOINT

# TC(191,5): SASW FdRecovEnbGlobCmd [KSC50168]
# Globally Enable Recovery Procedures
cfl.Tcsend_DB('SASW FdRecovEnbGlobCmd', pool_name='LIVE')

#! CCS.BREAKPOINT

# TC(191,6): SASW FdRecovDisGlobCmd [KSC50169]
# Globally Disable Recovery Procedures
cfl.Tcsend_DB('SASW FdRecovDisGlobCmd', pool_name='LIVE')

#! CCS.BREAKPOINT

# TC(191,7): SASW FdRecovEnbCmd [KSC50170]
# Enable Recovery Procedure
FdChkId = None  # KSP50073
cfl.Tcsend_DB('SASW FdRecovEnbCmd', FdChkId, pool_name='LIVE')

#! CCS.BREAKPOINT

# TC(191,8): SASW FdRecovDisCmd [KSC50171]
# Disable Recovery Procedure
FdChkId = None  # KSP50073
cfl.Tcsend_DB('SASW FdRecovDisCmd', FdChkId, pool_name='LIVE')

#! CCS.BREAKPOINT

# TC(193,1): SASW IaModePreSciCmd [KSC50172]
# Prepare Science
cfl.Tcsend_DB('SASW IaModePreSciCmd', pool_name='LIVE')

#! CCS.BREAKPOINT

# TC(193,2): SASW IaModeStrtSciCmd [KSC50173]
# Start Science
cfl.Tcsend_DB('SASW IaModeStrtSciCmd', pool_name='LIVE')

#! CCS.BREAKPOINT

# TC(193,3): SASW IaModeStpSciCmd [KSC50174]
# Stop Science
cfl.Tcsend_DB('SASW IaModeStpSciCmd', pool_name='LIVE')

#! CCS.BREAKPOINT

# TC(193,4): SASW IaModeGotoStbyCmd [KSC50175]
# Goto Standby
cfl.Tcsend_DB('SASW IaModeGotoStbyCmd', pool_name='LIVE')

#! CCS.BREAKPOINT

# TC(193,5): SASW IaModeStrtManCmd [KSC50176]
# Start Manual FEE Mode
cfl.Tcsend_DB('SASW IaModeStrtManCmd', pool_name='LIVE')

#! CCS.BREAKPOINT

# TC(193,6): SASW IaModeContrSwOffCmd [KSC50177]
# Controlled Switch-Off IASW
cfl.Tcsend_DB('SASW IaModeContrSwOffCmd', pool_name='LIVE')

#! CCS.BREAKPOINT

# TC(194,1): SASW AlgoStrtCmd [KSC50222]
# Start Algorithm
AlgoId = None  # KSP50004
cfl.Tcsend_DB('SASW AlgoStrtCmd', AlgoId, pool_name='LIVE')

#! CCS.BREAKPOINT

# TC(194,2): SASW AlgoStopCmd [KSC50180]
# Stop Algorithm
AlgoId = None  # KSP50004
cfl.Tcsend_DB('SASW AlgoStopCmd', AlgoId, pool_name='LIVE')

#! CCS.BREAKPOINT

# TC(194,3): SASW AlgoSuspCmd [KSC50181]
# Suspend Algorithm
AlgoId = None  # KSP50004
cfl.Tcsend_DB('SASW AlgoSuspCmd', AlgoId, pool_name='LIVE')

#! CCS.BREAKPOINT

# TC(194,4): SASW AlgoResCmd [KSC50182]
# Resume Algorithm
AlgoId = None  # KSP50004
cfl.Tcsend_DB('SASW AlgoResCmd', AlgoId, pool_name='LIVE')

#! CCS.BREAKPOINT

# TC(197,2): SASW BootRepGenCmd [KSC50184]
# Generate Boot Report
DpuMemoryId = None  # KSP50007
StartAddress = None  # KSP50017
cfl.Tcsend_DB('SASW BootRepGenCmd', DpuMemoryId, StartAddress, pool_name='LIVE')

#! CCS.BREAKPOINT

# TC(198,1): SASW ProcStrCmd_FEE_IN_A [KSC50212]
# FEE_IN_ALL_SYNC_PR Procedure Start Cmd
# ProcId = FEE_IN_ALL_SYNC_  # KSP50317 [NOT EDITABLE]
cfl.Tcsend_DB('SASW ProcStrCmd_FEE_IN_A', pool_name='LIVE')

#! CCS.BREAKPOINT

# TC(198,1): SASW ProcStrCmd_FEE_IN_S [KSC50213]
# FEE_IN_SYNC_PR Procedure Start Cmd
# ProcId = FEE_IN_SYNC_PR  # KSP50317 [NOT EDITABLE]
ProcFeeNParams = None  # KSP50318
ProcFeeParamId = None  # KSP50450
cfl.Tcsend_DB('SASW ProcStrCmd_FEE_IN_S', ProcFeeNParams, ProcFeeParamId, pool_name='LIVE')

#! CCS.BREAKPOINT

# TC(198,1): SASW ProcStrCmd_FEE_OUT_ [KSC50214]
# FEE_OUT_SYNC_PR Procedure Start Cmd
# ProcId = FEE_OUT_SYNC_PR  # KSP50317 [NOT EDITABLE]
ProcFeeNParams = None  # KSP50318
ProcFeeParamId = None  # KSP50450
ProcFeeParamValue = None  # KSP50451
cfl.Tcsend_DB('SASW ProcStrCmd_FEE_OUT_', ProcFeeNParams, ProcFeeParamId, ProcFeeParamValue, pool_name='LIVE')

#! CCS.BREAKPOINT

# TC(198,1): SASW ProcStrCmd_RSE_CONF [KSC50215]
# RSE_CONFIG_PR Procedure Start Cmd
# ProcId = RSE_CONFIG_PR  # KSP50317 [NOT EDITABLE]
ProcRseCmdId = None  # KSP50452
cfl.Tcsend_DB('SASW ProcStrCmd_RSE_CONF', ProcRseCmdId, pool_name='LIVE')

#! CCS.BREAKPOINT

# TC(198,1): SASW ProcStrCmd_RSE_STAT [KSC50216]
# RSE_STATUS_PR Procedure Start Cmd
# ProcId = RSE_STATUS_PR  # KSP50317 [NOT EDITABLE]
cfl.Tcsend_DB('SASW ProcStrCmd_RSE_STAT', pool_name='LIVE')

#! CCS.BREAKPOINT

# TC(198,2): SASW ProcStpCmd_FEE_IN_A [KSC50217]
# FEE_IN_ALL_SYNC_PR Procedure Stop Cmd
# ProcId = FEE_IN_ALL_SYNC_  # KSP50317 [NOT EDITABLE]
cfl.Tcsend_DB('SASW ProcStpCmd_FEE_IN_A', pool_name='LIVE')

#! CCS.BREAKPOINT

# TC(198,2): SASW ProcStpCmd_FEE_IN_S [KSC50218]
# FEE_IN_SYNC_PR Procedure Stop Cmd
# ProcId = FEE_IN_SYNC_PR  # KSP50317 [NOT EDITABLE]
cfl.Tcsend_DB('SASW ProcStpCmd_FEE_IN_S', pool_name='LIVE')

#! CCS.BREAKPOINT

# TC(198,2): SASW ProcStpCmd_FEE_OUT_ [KSC50219]
# FEE_OUT_SYNC_PR Procedure Stop Cmd
# ProcId = FEE_OUT_SYNC_PR  # KSP50317 [NOT EDITABLE]
cfl.Tcsend_DB('SASW ProcStpCmd_FEE_OUT_', pool_name='LIVE')

#! CCS.BREAKPOINT

# TC(198,2): SASW ProcStpCmd_RSE_CONF [KSC50220]
# RSE_CONFIG_PR Procedure Stop Cmd
# ProcId = RSE_CONFIG_PR  # KSP50317 [NOT EDITABLE]
cfl.Tcsend_DB('SASW ProcStpCmd_RSE_CONF', pool_name='LIVE')

#! CCS.BREAKPOINT

# TC(198,2): SASW ProcStpCmd_RSE_STAT [KSC50221]
# RSE_STATUS_PR Procedure Stop Cmd
# ProcId = RSE_STATUS_PR  # KSP50317 [NOT EDITABLE]
cfl.Tcsend_DB('SASW ProcStpCmd_RSE_STAT', pool_name='LIVE')

#! CCS.BREAKPOINT

# TC(210,1): SASW ResetDpuSafeCmd [KSC50187]
# Reset DPU to SAFE
cfl.Tcsend_DB('SASW ResetDpuSafeCmd', pool_name='LIVE')

#! CCS.BREAKPOINT

# TC(210,2): SASW WatchdogEnbCmd [KSC50188]
# Enable Watchdog
cfl.Tcsend_DB('SASW WatchdogEnbCmd', pool_name='LIVE')

#! CCS.BREAKPOINT

# TC(210,3): SASW WatchdogDisCmd [KSC50189]
# Disable Watchdog
cfl.Tcsend_DB('SASW WatchdogDisCmd', pool_name='LIVE')

#! CCS.BREAKPOINT

# TC(210,6): SASW LoadRegisterCmd [KSC50190]
# Load Register
RegAddr = None  # KSP50204
RegData = None  # KSP50205
VerifAddr = None  # KSP50206
VerifMask = None  # KSP50207
cfl.Tcsend_DB('SASW LoadRegisterCmd', RegAddr, RegData, VerifAddr, VerifMask, pool_name='LIVE')

#! CCS.BREAKPOINT

# TC(210,7): SASW LoadRegisterArmCmd [KSC50191]
# Arm Load Register
cfl.Tcsend_DB('SASW LoadRegisterArmCmd', pool_name='LIVE')

#! CCS.BREAKPOINT

# TC(210,8): SASW LoadRegisterDisarmC [KSC50192]
# Disarm Load Register
cfl.Tcsend_DB('SASW LoadRegisterDisarmC', pool_name='LIVE')

#! CCS.BREAKPOINT

# TC(211,1): SASW ParamUpdtBoolCmd [KSC50193]
# Update Parameter of type Boolean
# ParamType = PAR_BOOL  # KSP50215 [NOT EDITABLE]
NParams = None  # KSP50209
ParamId = None  # KSP50210
ArrayElemId = None  # KSP50208
ParamValueBool = None  # KSP50216
cfl.Tcsend_DB('SASW ParamUpdtBoolCmd', NParams, ParamId, ArrayElemId, ParamValueBool, pool_name='LIVE')

#! CCS.BREAKPOINT

# TC(211,1): SASW ParamUpdtInt8Cmd [KSC50194]
# Update Parameter of type INT8
# ParamType = PAR_INT8  # KSP50215 [NOT EDITABLE]
NParams = None  # KSP50209
ParamId = None  # KSP50210
ArrayElemId = None  # KSP50208
ParamValueInt8 = None  # KSP50221
cfl.Tcsend_DB('SASW ParamUpdtInt8Cmd', NParams, ParamId, ArrayElemId, ParamValueInt8, pool_name='LIVE')

#! CCS.BREAKPOINT

# TC(211,1): SASW ParamUpdtInt16Cmd [KSC50195]
# Update Parameter of type INT16
# ParamType = PAR_INT16  # KSP50215 [NOT EDITABLE]
NParams = None  # KSP50209
ParamId = None  # KSP50210
ArrayElemId = None  # KSP50208
ParamValueInt16 = None  # KSP50219
cfl.Tcsend_DB('SASW ParamUpdtInt16Cmd', NParams, ParamId, ArrayElemId, ParamValueInt16, pool_name='LIVE')

#! CCS.BREAKPOINT

# TC(211,1): SASW ParamUpdtInt32Cmd [KSC50196]
# Update Parameter of type INT32
# ParamType = PAR_INT32  # KSP50215 [NOT EDITABLE]
NParams = None  # KSP50209
ParamId = None  # KSP50210
ArrayElemId = None  # KSP50208
ParamValueInt32 = None  # KSP50220
cfl.Tcsend_DB('SASW ParamUpdtInt32Cmd', NParams, ParamId, ArrayElemId, ParamValueInt32, pool_name='LIVE')

#! CCS.BREAKPOINT

# TC(211,1): SASW ParamUpdtUint8Cmd [KSC50197]
# Update Parameter of type UINT8
# ParamType = PAR_UINT8  # KSP50215 [NOT EDITABLE]
NParams = None  # KSP50209
ParamId = None  # KSP50210
ArrayElemId = None  # KSP50208
ParamValueUint8 = None  # KSP50224
cfl.Tcsend_DB('SASW ParamUpdtUint8Cmd', NParams, ParamId, ArrayElemId, ParamValueUint8, pool_name='LIVE')

#! CCS.BREAKPOINT

# TC(211,1): SASW ParamUpdtUint16Cmd [KSC50198]
# Update Parameter of type UINT16
# ParamType = PAR_UINT16  # KSP50215 [NOT EDITABLE]
NParams = None  # KSP50209
ParamId = None  # KSP50210
ArrayElemId = None  # KSP50208
ParamValueUint16 = None  # KSP50222
cfl.Tcsend_DB('SASW ParamUpdtUint16Cmd', NParams, ParamId, ArrayElemId, ParamValueUint16, pool_name='LIVE')

#! CCS.BREAKPOINT

# TC(211,1): SASW ParamUpdtUint32Cmd [KSC50199]
# Update Parameter of type UINT32
# ParamType = PAR_UINT32  # KSP50215 [NOT EDITABLE]
NParams = None  # KSP50209
ParamId = None  # KSP50210
ArrayElemId = None  # KSP50208
ParamValueUint32 = None  # KSP50223
cfl.Tcsend_DB('SASW ParamUpdtUint32Cmd', NParams, ParamId, ArrayElemId, ParamValueUint32, pool_name='LIVE')

#! CCS.BREAKPOINT

# TC(211,1): SASW ParamUpdtFloatCmd [KSC50200]
# Update Parameter of type FLOAT
# ParamType = PAR_FLOAT  # KSP50215 [NOT EDITABLE]
NParams = None  # KSP50209
ParamId = None  # KSP50210
ArrayElemId = None  # KSP50208
ParamValueFloat = None  # KSP50218
cfl.Tcsend_DB('SASW ParamUpdtFloatCmd', NParams, ParamId, ArrayElemId, ParamValueFloat, pool_name='LIVE')

#! CCS.BREAKPOINT

# TC(211,1): SASW ParamUpdtCucCmd [KSC50201]
# Update Parameter of type CUC
# ParamType = PAR_CUC  # KSP50215 [NOT EDITABLE]
NParams = None  # KSP50209
ParamId = None  # KSP50210
ArrayElemId = None  # KSP50208
ParamValueCuc = None  # KSP50217
cfl.Tcsend_DB('SASW ParamUpdtCucCmd', NParams, ParamId, ArrayElemId, ParamValueCuc, pool_name='LIVE')

#! CCS.BREAKPOINT

# TC(212,1): SASW CopyCmd [KSC50202]
# Copy Data
SrcMemId = None  # KSP50022
SrcAddress = None  # KSP50021
DataSize = None  # KSP50019
TrgtMemId = None  # KSP50024
TrgtAddress = None  # KSP50023
cfl.Tcsend_DB('SASW CopyCmd', SrcMemId, SrcAddress, DataSize, TrgtMemId, TrgtAddress, pool_name='LIVE')

#! CCS.BREAKPOINT

# TC(212,2): SASW ComprCmd [KSC50203]
# Compress Data
SrcMemId = None  # KSP50022
SrcAddress = None  # KSP50021
DataSize = None  # KSP50019
ComprConfig = None  # KSP50018
TrgtMemId = None  # KSP50024
TrgtAddress = None  # KSP50023
cfl.Tcsend_DB('SASW ComprCmd', SrcMemId, SrcAddress, DataSize, ComprConfig, TrgtMemId, TrgtAddress, pool_name='LIVE')

#! CCS.BREAKPOINT

# TC(212,3): SASW DecomprCmd [KSC50204]
# Decompress Data
SrcMemId = None  # KSP50022
SrcAddress = None  # KSP50021
DataSize = None  # KSP50019
DecomprConfig = None  # KSP50020
TrgtMemId = None  # KSP50024
TrgtAddress = None  # KSP50023
cfl.Tcsend_DB('SASW DecomprCmd', SrcMemId, SrcAddress, DataSize, DecomprConfig, TrgtMemId, TrgtAddress, pool_name='LIVE')

#! CCS.BREAKPOINT

# TC(213,1): SASW SchedSegmCmd [KSC50205]
# Schedule Program Segment
SegmAddress = None  # KSP50197
cfl.Tcsend_DB('SASW SchedSegmCmd', SegmAddress, pool_name='LIVE')

#! CCS.BREAKPOINT

# TC(3,128): DBS_TC_REQUEST_HK [KTC40022]
# Request a Housekeeping Report
HK_REP_SID = 100  # KTP40001
cfl.Tcsend_DB('DBS_TC_REQUEST_HK', HK_REP_SID, pool_name='LIVE')

#! CCS.BREAKPOINT

# TC(3,131): DBS_TC_SET_HKREP_FREQ [KTC40001]
# Set Housekeeping Reporting Frequency
HK_REP_SID = 100  # KTP40001
HK_REP_PER = 32  # KTP40002
cfl.Tcsend_DB('DBS_TC_SET_HKREP_FREQ', HK_REP_SID, HK_REP_PER, pool_name='LIVE')

#! CCS.BREAKPOINT

# TC(5,5): DBS_TC_ENABLE_EVENT [KTC40002]
# Enables one or more event reports
EVENT_REP_CNT = 1  # KTP40010
EVENT_ID = "EVT_MEM_COR_RAM"  # KTP40011
cfl.Tcsend_DB('DBS_TC_ENABLE_EVENT', EVENT_REP_CNT, EVENT_ID, pool_name='LIVE')

#! CCS.BREAKPOINT

# TC(5,6): DBS_TC_DISABLE_EVENT [KTC40003]
# Disables one or more event reports
EVENT_REP_CNT = 1  # KTP40010
EVENT_ID = "EVT_MEM_COR_RAM"  # KTP40011
cfl.Tcsend_DB('DBS_TC_DISABLE_EVENT', EVENT_REP_CNT, EVENT_ID, pool_name='LIVE')

#! CCS.BREAKPOINT

# TC(6,2): DBS_TC_LOAD_MEMORY [KTC40004]
# Load data to the onboard memory
WR_MEM_MID = "DPU_RAM"  # KTP40030
WR_START_ADDR = 0x60000000  # KTP40031
WR_BLOCK_LEN = 4  # KTP40032
WR_BLOC_DATA = 0x00  # KTP40033
cfl.Tcsend_DB('DBS_TC_LOAD_MEMORY', WR_MEM_MID, WR_START_ADDR, WR_BLOCK_LEN, WR_BLOC_DATA, pool_name='LIVE')

#! CCS.BREAKPOINT

# TC(6,5): DBS_TC_DUMP_MEMORY [KTC40005]
# Dump data from the onboard memory
RD_MEM_MID = "DPU_RAM"  # KTP40050
RD_START_ADDR = 0x60000000  # KTP40051
RD_BLOCK_LEN = 4  # KTP40052
cfl.Tcsend_DB('DBS_TC_DUMP_MEMORY', RD_MEM_MID, RD_START_ADDR, RD_BLOCK_LEN, pool_name='LIVE')

#! CCS.BREAKPOINT

# TC(6,9): DBS_TC_CHECK_MEMORY [KTC40006]
# Check the onboard memory
CH_MEM_MID = "DPU_RAM"  # KTP40060
CH_START_ADDR = 0x60000000  # KTP40061
CH_BLOCK_LEN = 4  # KTP40062
cfl.Tcsend_DB('DBS_TC_CHECK_MEMORY', CH_MEM_MID, CH_START_ADDR, CH_BLOCK_LEN, pool_name='LIVE')

#! CCS.BREAKPOINT

# TC(6,129): DBS_TC_CLEAR_MEMORY [KTC40007]
# Clear a section of the the RAM
# CLR_MEM_MID = DPU_RAM  # KTP40070 [NOT EDITABLE]
CLR_START_ADDR = 0x60040000  # KTP40071
CLR_BLOCK_LEN = 33554432  # KTP40072
cfl.Tcsend_DB('DBS_TC_CLEAR_MEMORY', CLR_START_ADDR, CLR_BLOCK_LEN, pool_name='LIVE')

#! CCS.BREAKPOINT

# TC(9,128): DBS_TC_UPDATE_TIME [KTC40008]
# Set the onboard time
DPU_NEW_TIMESTAMP = 0  # KTP40080
cfl.Tcsend_DB('DBS_TC_UPDATE_TIME', DPU_NEW_TIMESTAMP, pool_name='LIVE')

#! CCS.BREAKPOINT

# TC(17,1): DBS_TC_TEST_CONNECTION [KTC40009]
# Test the connection to the DPU
cfl.Tcsend_DB('DBS_TC_TEST_CONNECTION', pool_name='LIVE')

#! CCS.BREAKPOINT

# TC(20,1): DBS_TC_DUMP_PARAMETERS [KTC40010]
# Dump parameters
PARAM_SID = "ADC_RANGES"  # KTP40100
cfl.Tcsend_DB('DBS_TC_DUMP_PARAMETERS', PARAM_SID, pool_name='LIVE')

#! CCS.BREAKPOINT

# TC(20,3): DBS_TC_PARLOAD_ADCRANGES [KTC40011]
# Load parameterset for ADC ranges
# PARAM_SID = ADC_RANGES  # KTP40100 [NOT EDITABLE]
P3V9_WARN_LOWER_RANGE = 0  # KTP40110
P3V9_FAIL_LOWER_RANGE = 0  # KTP40111
P3V9_WARN_UPPER_RANGE = 16382  # KTP40112
P3V9_FAIL_UPPER_RANGE = 16382  # KTP40113
P3V3_WARN_LOWER_RANGE = 0  # KTP40114
P3V3_FAIL_LOWER_RANGE = 0  # KTP40115
P3V3_WARN_UPPER_RANGE = 16382  # KTP40116
P3V3_FAIL_UPPER_RANGE = 16382  # KTP40117
P3V3_LVDS_WARN_LOWER_RAN = 0  # KTP40118
P3V3_LVDS_FAIL_LOWER_RAN = 0  # KTP40119
P3V3_LVDS_WARN_UPPER_RAN = 16382  # KTP40120
P3V3_LVDS_FAIL_UPPER_RAN = 16382  # KTP40121
P2V5_WARN_LOWER_RANGE = 0  # KTP40122
P2V5_FAIL_LOWER_RANGE = 0  # KTP40123
P2V5_WARN_UPPER_RANGE = 16382  # KTP40124
P2V5_FAIL_UPPER_RANGE = 16382  # KTP40125
P1V8_WARN_LOWER_RANGE = 0  # KTP40126
P1V8_FAIL_LOWER_RANGE = 0  # KTP40127
P1V8_WARN_UPPER_RANGE = 16382  # KTP40128
P1V8_FAIL_UPPER_RANGE = 16382  # KTP40129
P1V2_WARN_LOWER_RANGE = 0  # KTP40130
P1V2_FAIL_LOWER_RANGE = 0  # KTP40131
P1V2_WARN_UPPER_RANGE = 16382  # KTP40132
P1V2_FAIL_UPPER_RANGE = 16382  # KTP40133
REF_WARN_LOWER_RANGE = 0  # KTP40134
REF_FAIL_LOWER_RANGE = 0  # KTP40135
REF_WARN_UPPER_RANGE = 16382  # KTP40136
REF_FAIL_UPPER_RANGE = 16382  # KTP40137
TEMP1_WARN_LOWER_RANGE = 0  # KTP40138
TEMP1_FAIL_LOWER_RANGE = 0  # KTP40139
TEMP1_WARN_UPPER_RANGE = 16382  # KTP40140
TEMP1_FAIL_UPPER_RANGE = 16382  # KTP40141
TEMP_FEE_WARN_LOWER_RANG = 0  # KTP40142
TEMP_FEE_FAIL_LOWER_RANG = 0  # KTP40143
TEMP_FEE_WARN_UPPER_RANG = 16382  # KTP40144
TEMP_FEE_FAIL_UPPER_RANG = 16382  # KTP40145
TEMP_CDD_WARN_LOWER_RANG = 0  # KTP40146
TEMP_CDD_FAIL_LOWER_RANG = 0  # KTP40147
TEMP_CDD_WARN_UPPER_RANG = 16382  # KTP40148
TEMP_CDD_FAIL_UPPER_RANG = 16382  # KTP40149
I_FEE_ANA_WARN_LOWER_RAN = 0  # KTP40150
I_FEE_ANA_FAIL_LOWER_RAN = 0  # KTP40151
I_FEE_ANA_WARN_UPPER_RAN = 16382  # KTP40152
I_FEE_ANA_FAIL_UPPER_RAN = 16382  # KTP40153
I_FEE_DIG_WARN_LOWER_RAN = 0  # KTP40154
I_FEE_DIG_FAIL_LOWER_RAN = 0  # KTP40155
I_FEE_DIG_WARN_UPPER_RAN = 16382  # KTP40156
I_FEE_DIG_FAIL_UPPER_RAN = 16382  # KTP40157
I_DPU_WARN_LOWER_RANGE = 0  # KTP40158
I_DPU_FAIL_LOWER_RANGE = 0  # KTP40159
I_DPU_WARN_UPPER_RANGE = 16382  # KTP40160
I_DPU_FAIL_UPPER_RANGE = 16382  # KTP40161
I_RSE_WARN_LOWER_RANGE = 0  # KTP40162
I_RSE_FAIL_LOWER_RANGE = 0  # KTP40163
I_RSE_WARN_UPPER_RANGE = 16382  # KTP40164
I_RSE_FAIL_UPPER_RANGE = 16382  # KTP40165
I_HEATER_WARN_LOWER_RANG = 0  # KTP40166
I_HEATER_FAIL_LOWER_RANG = 0  # KTP40167
I_HEATER_WARN_UPPER_RANG = 16382  # KTP40168
I_HEATER_FAIL_UPPER_RANG = 16382  # KTP40169
TEMP_PSU_WARN_LOWER_RANG = 0  # KTP40170
TEMP_PSU_FAIL_LOWER_RANG = 0  # KTP40171
TEMP_PSU_WARN_UPPER_RANG = 16382  # KTP40172
TEMP_PSU_FAIL_UPPER_RANG = 16382  # KTP40173
PARAM_CRC = 0  # KTP40174
cfl.Tcsend_DB('DBS_TC_PARLOAD_ADCRANGES', P3V9_WARN_LOWER_RANGE, P3V9_FAIL_LOWER_RANGE, P3V9_WARN_UPPER_RANGE, P3V9_FAIL_UPPER_RANGE, P3V3_WARN_LOWER_RANGE, P3V3_FAIL_LOWER_RANGE, P3V3_WARN_UPPER_RANGE, P3V3_FAIL_UPPER_RANGE, P3V3_LVDS_WARN_LOWER_RAN, P3V3_LVDS_FAIL_LOWER_RAN, P3V3_LVDS_WARN_UPPER_RAN, P3V3_LVDS_FAIL_UPPER_RAN, P2V5_WARN_LOWER_RANGE, P2V5_FAIL_LOWER_RANGE, P2V5_WARN_UPPER_RANGE, P2V5_FAIL_UPPER_RANGE, P1V8_WARN_LOWER_RANGE, P1V8_FAIL_LOWER_RANGE, P1V8_WARN_UPPER_RANGE, P1V8_FAIL_UPPER_RANGE, P1V2_WARN_LOWER_RANGE, P1V2_FAIL_LOWER_RANGE, P1V2_WARN_UPPER_RANGE, P1V2_FAIL_UPPER_RANGE, REF_WARN_LOWER_RANGE, REF_FAIL_LOWER_RANGE, REF_WARN_UPPER_RANGE, REF_FAIL_UPPER_RANGE, TEMP1_WARN_LOWER_RANGE, TEMP1_FAIL_LOWER_RANGE, TEMP1_WARN_UPPER_RANGE, TEMP1_FAIL_UPPER_RANGE, TEMP_FEE_WARN_LOWER_RANG, TEMP_FEE_FAIL_LOWER_RANG, TEMP_FEE_WARN_UPPER_RANG, TEMP_FEE_FAIL_UPPER_RANG, TEMP_CDD_WARN_LOWER_RANG, TEMP_CDD_FAIL_LOWER_RANG, TEMP_CDD_WARN_UPPER_RANG, TEMP_CDD_FAIL_UPPER_RANG, I_FEE_ANA_WARN_LOWER_RAN, I_FEE_ANA_FAIL_LOWER_RAN, I_FEE_ANA_WARN_UPPER_RAN, I_FEE_ANA_FAIL_UPPER_RAN, I_FEE_DIG_WARN_LOWER_RAN, I_FEE_DIG_FAIL_LOWER_RAN, I_FEE_DIG_WARN_UPPER_RAN, I_FEE_DIG_FAIL_UPPER_RAN, I_DPU_WARN_LOWER_RANGE, I_DPU_FAIL_LOWER_RANGE, I_DPU_WARN_UPPER_RANGE, I_DPU_FAIL_UPPER_RANGE, I_RSE_WARN_LOWER_RANGE, I_RSE_FAIL_LOWER_RANGE, I_RSE_WARN_UPPER_RANGE, I_RSE_FAIL_UPPER_RANGE, I_HEATER_WARN_LOWER_RANG, I_HEATER_FAIL_LOWER_RANG, I_HEATER_WARN_UPPER_RANG, I_HEATER_FAIL_UPPER_RANG, TEMP_PSU_WARN_LOWER_RANG, TEMP_PSU_FAIL_LOWER_RANG, TEMP_PSU_WARN_UPPER_RANG, TEMP_PSU_FAIL_UPPER_RANG, PARAM_CRC, pool_name='LIVE')

#! CCS.BREAKPOINT

# TC(20,3): DBS_TC_PARLOAD_RSEPARAM [KTC40012]
# Load parameterset for RSE
# PARAM_SID = RSE_PARAM  # KTP40100 [NOT EDITABLE]
MOTOR_CUR = 0  # KTP40190
SETTL_TIME = 0  # KTP40191
CHOP_DUTY = 0  # KTP40192
MAX_MOTOR_TEMP = 0  # KTP40193
MAX_ELEC_TEMP = 0  # KTP40194
MAX_STEPS = 0  # KTP40195
RSE_CONFIG = 0  # KTP40196
MAX_MOTOR_CUR = 0  # KTP40197
EMERGENCY_STEPS = 0  # KTP40198
PARAM_CRC = 0  # KTP40174
cfl.Tcsend_DB('DBS_TC_PARLOAD_RSEPARAM', MOTOR_CUR, SETTL_TIME, CHOP_DUTY, MAX_MOTOR_TEMP, MAX_ELEC_TEMP, MAX_STEPS, RSE_CONFIG, MAX_MOTOR_CUR, EMERGENCY_STEPS, PARAM_CRC, pool_name='LIVE')

#! CCS.BREAKPOINT

# TC(20,128): DBS_TC_PARLOAD_ARM [KTC40013]
# Arm the software for loading of parameters to the MRAM
cfl.Tcsend_DB('DBS_TC_PARLOAD_ARM', pool_name='LIVE')

#! CCS.BREAKPOINT

# TC(20,129): DBS_TC_PARLOAD_DISARM [KTC40014]
# Disarm the software for loading of parameters
cfl.Tcsend_DB('DBS_TC_PARLOAD_DISARM', pool_name='LIVE')

#! CCS.BREAKPOINT

# TC(210,1): DBS_TC_RESET_TO_SAFE [KTC40015]
# Reset the DPU (and go to SAFE mode)
cfl.Tcsend_DB('DBS_TC_RESET_TO_SAFE', pool_name='LIVE')

#! CCS.BREAKPOINT

# TC(210,2): DBS_TC_ENABLE_WATCHDOG [KTC40016]
# Enable the watchdog of the DPU
cfl.Tcsend_DB('DBS_TC_ENABLE_WATCHDOG', pool_name='LIVE')

#! CCS.BREAKPOINT

# TC(210,3): DBS_TC_DISABLE_WATCHDOG [KTC40017]
# DISable the watchdog of the DPU
cfl.Tcsend_DB('DBS_TC_DISABLE_WATCHDOG', pool_name='LIVE')

#! CCS.BREAKPOINT

# TC(210,4): DBS_TC_BOOT_IASW [KTC40018]
# Start the Application Software
SW_MEM_MID = "DPU_RAM"  # KTP40260
SW_IMG_ADDR = 0x00000000  # KTP40261
SW_START_ADDR = 0x60040000  # KTP40262
SW_FREE1 = 0x00000000  # KTP40263
SW_FREE2 = 0x00000000  # KTP40264
SW_FREE3 = 0x00000000  # KTP40265
SW_FREE4 = 0x00000000  # KTP40266
SW_FREE5 = 0x00000000  # KTP40267
cfl.Tcsend_DB('DBS_TC_BOOT_IASW', SW_MEM_MID, SW_IMG_ADDR, SW_START_ADDR, SW_FREE1, SW_FREE2, SW_FREE3, SW_FREE4, SW_FREE5, pool_name='LIVE')

#! CCS.BREAKPOINT

# TC(210,6): DBS_TC_LOAD_REGISTER [KTC40019]
# Load data to the registers in the GR712RC or FPGA
LR_REG_ADDR = 0x20000000  # KTP40280
LR_REG_DATA = 0x0  # KTP40281
LR_VERI_ADDR = 0x20000000  # KTP40282
LR_VERI_MASK = 0xFFFFFFFF  # KTP40283
cfl.Tcsend_DB('DBS_TC_LOAD_REGISTER', LR_REG_ADDR, LR_REG_DATA, LR_VERI_ADDR, LR_VERI_MASK, pool_name='LIVE')

#! CCS.BREAKPOINT

# TC(210,7): DBS_TC_LOAD_REG_ARM [KTC40020]
# Arm the software for loading into a register
cfl.Tcsend_DB('DBS_TC_LOAD_REG_ARM', pool_name='LIVE')

#! CCS.BREAKPOINT

# TC(210,8): DBS_TC_LOAD_REG_DISARM [KTC40021]
# Disarm the software for loading into a register
cfl.Tcsend_DB('DBS_TC_LOAD_REG_DISARM', pool_name='LIVE')
