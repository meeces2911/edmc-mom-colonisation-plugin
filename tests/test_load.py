import pytest
import requests
import json
import time
import logging
from collections import defaultdict

import load as plugin

# Import stubs
import config
import monitor

from .sharedFunctions import ACTUAL_HTTP_PUT_POST_REQUESTS, ACTUAL_HTTP_GET_REQUESTS
from .sharedFunctions import __plugin_start_stop, __global_mocks, __add_mocked_http_response

logger = logging.getLogger()

@pytest.fixture(autouse=True)
def before_after_test(__global_mocks):
    """Default any settings before the run of each test"""
    config.config.shutting_down = False
    ACTUAL_HTTP_PUT_POST_REQUESTS.clear()
    __plugin_start_stop()

def test_journal_entry_Startup_LoadGame():
    """Test 'Startup' or 'LoadGame' events"""
    entry = {'timestamp': '2025-04-11T08:18:27Z', 'event': 'LoadGame', 'FID': '9001', 'Commander': 'cmdr_name', 'Horizons': True, 'Odyssey': True, 'Ship': 'Type9', 'Ship_Localised': 'Type-9 Heavy', 'ShipID': 10, 'ShipName': 'hauler', 'ShipIdent': 'MIKUNN', 'FuelLevel': 64.0, 'FuelCapacity': 64.0, 'GameMode': 'Open', 'Credits': 3620255325, 'Loan': 0, 'language': 'English/UK', 'gameversion': '4.1.1.0', 'build': 'r312744/r0 '}
    state = {'Cargo': defaultdict(int, {'steel': 720}), 'CargoCapacity': 720}
    plugin.journal_entry(cmdr=monitor.monitor.cmdr, is_beta=False, system=None, station=None, entry=entry, state=state)
    
    assert plugin.this.cargoCapacity == 720

    # Expecting TYPE_CMDR_UPDATE and TYPE_CARRIER_INTRANSIT_RECALC
    assert plugin.this.queue.qsize() == 2

    pr = plugin.this.queue.get_nowait()
    assert pr
    assert pr.type == plugin.PushRequest.TYPE_CMDR_UPDATE
    assert pr.cmdr == monitor.monitor.cmdr
    assert pr.station == None

    pr = plugin.this.queue.get_nowait()
    assert pr
    assert pr.type == plugin.PushRequest.TYPE_CARRIER_INTRANSIT_RECALC
    assert pr.cmdr == monitor.monitor.cmdr
    assert pr.station == None

    ########################################
    ## Docked to same carrier as assigned ##
    ########################################

    plugin.this.cmdrsAssignedCarrierName.set('Igneels Tooth')
    entry['StationType'] = 'FleetCarrier'
    entry['StationName'] = 'X7H-9KW'
    state = {'Cargo': defaultdict(), 'CargoCapacity': 512}
    plugin.journal_entry(cmdr=monitor.monitor.cmdr, is_beta=False, system=None, station='X7H-9KW', entry=entry, state=state)

    assert plugin.this.latestCarrierCallsign == 'X7H-9KW'
    assert plugin.this.cargoCapacity == 512

    # Expecting TYPE_CMDR_UPDATE and 2xTYPE_CARRIER_INTRANSIT_RECALC for assigned carrier and 2xTYPE_CARRIER_INTRANSIT_RECALC for docked carrier
    assert plugin.this.queue.qsize() == 5

    pr = plugin.this.queue.get_nowait()
    assert pr
    assert pr.type == plugin.PushRequest.TYPE_CMDR_UPDATE
    assert pr.cmdr == monitor.monitor.cmdr
    assert pr.station == 'X7H-9KW'

    # The one to fetch the latest in-transit data from the sheet
    pr = plugin.this.queue.get_nowait()
    assert pr
    assert pr.type == plugin.PushRequest.TYPE_CARRIER_INTRANSIT_RECALC
    assert pr.cmdr == monitor.monitor.cmdr
    assert pr.station == None  # None = assignedCarrier
    assert pr.data == None

    mock_scs_in_transit_data = """{"range":"'Igneels Tooth'!A1:E500","majorDimension":"ROWS","values":[["CMDR","Commodity","Units","Delivered","Timestamp"],["Starting Inventory","Aluminium","0"],["Starting Inventory","Ceramic Composites","0"],["Starting Inventory","CMM Composite","0"],["Starting Inventory","Computer Components","0"],["Starting Inventory","Copper","0"],["Starting Inventory","Food Cartridges","0"],["Starting Inventory","Fruit and Vedge","0"],["Starting Inventory","Insulating Membrane","0"],["Starting Inventory","Liquid Oxygen","0"],["Starting Inventory","Medical Diagnostic Equipment","0"],["Starting Inventory","Non-Lethal Weapons","0"],["Starting Inventory","Polymers","0"],["Starting Inventory","Power Generators","0"],["Starting Inventory","Semiconductors","0"],["Starting Inventory","Steel","0"],["Starting Inventory","Superconductors","0"],["Starting Inventory","Titanium","0"],["Starting Inventory","Water","0"],["Starting Inventory","Water Purifiers","0"],["cmdr_name","Steel",250,"FALSE"],["cmdr_name","Titanium",320,"FALSE"],["cmdr_name","Power Generators",20,"FALSE"]]}"""
    __add_mocked_http_response(json.loads(mock_scs_in_transit_data))
    ACTUAL_HTTP_GET_REQUESTS.clear()
    ACTUAL_HTTP_PUT_POST_REQUESTS.clear()
    plugin.process_item(pr)
    assert len(ACTUAL_HTTP_GET_REQUESTS) == 1
    assert ACTUAL_HTTP_GET_REQUESTS.pop(0) == "https://sheets.googleapis.com/v4/spreadsheets/1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE/values/'Igneels Tooth'!A:E"
    assert len(ACTUAL_HTTP_PUT_POST_REQUESTS) == 0
    assert len(plugin.this.sheet.inTransitCommodities) == 3
    assert plugin.this.sheet.inTransitCommodities == {'steel': {"'Igneels Tooth'!A21:E21": 250}, 'titanium': {"'Igneels Tooth'!A22:E22": 320}, 'powergenerators': {"'Igneels Tooth'!A23:E23": 20}}

    pr = plugin.this.queue.get_nowait()
    assert pr
    assert pr.type == plugin.PushRequest.TYPE_CARRIER_INTRANSIT_RECALC
    assert pr.cmdr == monitor.monitor.cmdr
    assert pr.station == None  # None = assignedCarrier
    assert pr.data['clear'] == True

    mock_scs_in_transit_data = """{"range":"'Igneels Tooth'!A21:E21","majorDimension":"ROWS","values":[["cmdr_name","Steel","250","FALSE","2025-06-21 04:55:49"]]}"""
    __add_mocked_http_response(json.loads(mock_scs_in_transit_data))
    mock_scs_in_transit_data = """{"range":"'Igneels Tooth'!A22:E22","majorDimension":"ROWS","values":[["cmdr_name","Titanium","320","FALSE","2025-06-21 04:55:49"]]}"""
    __add_mocked_http_response(json.loads(mock_scs_in_transit_data))
    mock_scs_in_transit_data = """{"range":"'Igneels Tooth'!A23:E23","majorDimension":"ROWS","values":[["cmdr_name","Power Generators","20","FALSE","2025-06-21 04:55:49"]]}"""
    __add_mocked_http_response(json.loads(mock_scs_in_transit_data))
    ACTUAL_HTTP_GET_REQUESTS.clear()
    ACTUAL_HTTP_PUT_POST_REQUESTS.clear()
    plugin.process_item(pr)
    assert len(ACTUAL_HTTP_GET_REQUESTS) == 3
    assert len(ACTUAL_HTTP_PUT_POST_REQUESTS) == 1
    
    assert ACTUAL_HTTP_GET_REQUESTS.pop(0) == "https://sheets.googleapis.com/v4/spreadsheets/1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE/values/'Igneels Tooth'!A21:E21"
    assert ACTUAL_HTTP_GET_REQUESTS.pop(0) == "https://sheets.googleapis.com/v4/spreadsheets/1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE/values/'Igneels Tooth'!A22:E22"
    assert ACTUAL_HTTP_GET_REQUESTS.pop(0) == "https://sheets.googleapis.com/v4/spreadsheets/1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE/values/'Igneels Tooth'!A23:E23"

    req = ACTUAL_HTTP_PUT_POST_REQUESTS.pop(0)
    assert req[0] == "https://sheets.googleapis.com/v4/spreadsheets/1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE:batchUpdate"
    assert req[1] == {"requests": [{"deleteRange": {"range": {"sheetId": 1223817771, "startRowIndex": 20, "endRowIndex": 21, "startColumnIndex": 0, "endColumnIndex": 5}, "shiftDimension": "ROWS"}}, {"deleteRange": {"range": {"sheetId": 1223817771, "startRowIndex": 20, "endRowIndex": 21, "startColumnIndex": 0, "endColumnIndex": 5}, "shiftDimension": "ROWS"}}, {"deleteRange": {"range": {"sheetId": 1223817771, "startRowIndex": 20, "endRowIndex": 21, "startColumnIndex": 0, "endColumnIndex": 5}, "shiftDimension": "ROWS"}}]}

    assert len(plugin.this.sheet.inTransitCommodities) == 0

    ########################
    ## These next 2 should be queued, but skipped, as they are effectively the same as the ones we've just processed above
    ########################

    # The one to fetch the latest in-transit data from the sheet
    pr = plugin.this.queue.get_nowait()
    assert pr
    assert pr.type == plugin.PushRequest.TYPE_CARRIER_INTRANSIT_RECALC
    assert pr.cmdr == monitor.monitor.cmdr
    assert pr.station == 'X7H-9KW'  # = dockedCarrier
    assert pr.data == None

    ACTUAL_HTTP_GET_REQUESTS.clear()
    ACTUAL_HTTP_PUT_POST_REQUESTS.clear()
    plugin.process_item(pr)
    assert len(ACTUAL_HTTP_GET_REQUESTS) == 0
    assert len(ACTUAL_HTTP_PUT_POST_REQUESTS) == 0
    assert len(plugin.this.sheet.inTransitCommodities) == 0

    pr = plugin.this.queue.get_nowait()
    assert pr
    assert pr.type == plugin.PushRequest.TYPE_CARRIER_INTRANSIT_RECALC
    assert pr.cmdr == monitor.monitor.cmdr
    assert pr.station == 'X7H-9KW'  # = dockedCarrier
    assert pr.data['clear'] == True

    ACTUAL_HTTP_GET_REQUESTS.clear()
    ACTUAL_HTTP_PUT_POST_REQUESTS.clear()
    plugin.process_item(pr)
    assert len(ACTUAL_HTTP_GET_REQUESTS) == 0
    assert len(ACTUAL_HTTP_PUT_POST_REQUESTS) == 0
    assert len(plugin.this.sheet.inTransitCommodities) == 0

    #############################################
    ## Docked to DIFFERENT carrier as assigned ##
    #############################################

    plugin.this.cmdrsAssignedCarrierName.set('NAC Hyperspace Bypass')
    entry['StationType'] = 'FleetCarrier'
    entry['StationName'] = 'X7H-9KW'
    state = {'Cargo': defaultdict(), 'CargoCapacity': 512}
    plugin.journal_entry(cmdr=monitor.monitor.cmdr, is_beta=False, system=None, station='X7H-9KW', entry=entry, state=state)

    assert plugin.this.latestCarrierCallsign == 'X7H-9KW'
    assert plugin.this.cargoCapacity == 512

    # Expecting TYPE_CMDR_UPDATE and 2xTYPE_CARRIER_INTRANSIT_RECALC for assigned carrier and 2xTYPE_CARRIER_INTRANSIT_RECALC for docked carrier
    assert plugin.this.queue.qsize() == 5

    pr = plugin.this.queue.get_nowait()
    assert pr
    assert pr.type == plugin.PushRequest.TYPE_CMDR_UPDATE
    assert pr.cmdr == monitor.monitor.cmdr
    assert pr.station == 'X7H-9KW'

    # The one to fetch the latest in-transit data from the sheet
    pr = plugin.this.queue.get_nowait()
    assert pr
    assert pr.type == plugin.PushRequest.TYPE_CARRIER_INTRANSIT_RECALC
    assert pr.cmdr == monitor.monitor.cmdr
    assert pr.station == None  # None = assignedCarrier
    assert pr.data == None

    mock_scs_in_transit_data = """{"range":"'NAC Hyperspace Bypass'!A1:E500","majorDimension":"ROWS","values":[["CMDR","Commodity","Units","Delivered","Timestamp"],["Starting Inventory","Aluminium","0"],["Starting Inventory","Ceramic Composites","0"],["Starting Inventory","CMM Composite","0"],["Starting Inventory","Computer Components","0"],["Starting Inventory","Copper","0"],["Starting Inventory","Food Cartridges","0"],["Starting Inventory","Fruit and Vedge","0"],["Starting Inventory","Insulating Membrane","0"],["Starting Inventory","Liquid Oxygen","0"],["Starting Inventory","Medical Diagnostic Equipment","0"],["Starting Inventory","Non-Lethal Weapons","0"],["Starting Inventory","Polymers","0"],["Starting Inventory","Power Generators","0"],["Starting Inventory","Semiconductors","0"],["Starting Inventory","Steel","0"],["Starting Inventory","Superconductors","0"],["Starting Inventory","Titanium","0"],["Starting Inventory","Water","0"],["Starting Inventory","Water Purifiers","0"],["cmdr_name","Steel",250,"FALSE"],["cmdr_name","Titanium",320,"FALSE"],["cmdr_name","Power Generators",20,"FALSE"]]}"""
    __add_mocked_http_response(json.loads(mock_scs_in_transit_data))
    ACTUAL_HTTP_GET_REQUESTS.clear()
    ACTUAL_HTTP_PUT_POST_REQUESTS.clear()
    plugin.process_item(pr)
    assert len(ACTUAL_HTTP_GET_REQUESTS) == 1
    assert ACTUAL_HTTP_GET_REQUESTS.pop(0) == "https://sheets.googleapis.com/v4/spreadsheets/1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE/values/'NAC Hyperspace Bypass'!A:E"
    assert len(ACTUAL_HTTP_PUT_POST_REQUESTS) == 0
    assert len(plugin.this.sheet.inTransitCommodities) == 3
    assert plugin.this.sheet.inTransitCommodities == {'steel': {"'NAC Hyperspace Bypass'!A21:E21": 250}, 'titanium': {"'NAC Hyperspace Bypass'!A22:E22": 320}, 'powergenerators': {"'NAC Hyperspace Bypass'!A23:E23": 20}}

    pr = plugin.this.queue.get_nowait()
    assert pr
    assert pr.type == plugin.PushRequest.TYPE_CARRIER_INTRANSIT_RECALC
    assert pr.cmdr == monitor.monitor.cmdr
    assert pr.station == None  # None = assignedCarrier
    assert pr.data['clear'] == True

    mock_scs_in_transit_data = """{"range":"'NAC Hyperspace Bypass'!A21:E21","majorDimension":"ROWS","values":[["cmdr_name","Steel","250","FALSE","2025-06-21 04:55:49"]]}"""
    __add_mocked_http_response(json.loads(mock_scs_in_transit_data))
    mock_scs_in_transit_data = """{"range":"'NAC Hyperspace Bypass'!A22:E22","majorDimension":"ROWS","values":[["cmdr_name","Titanium","320","FALSE","2025-06-21 04:55:49"]]}"""
    __add_mocked_http_response(json.loads(mock_scs_in_transit_data))
    mock_scs_in_transit_data = """{"range":"'NAC Hyperspace Bypass'!A23:E23","majorDimension":"ROWS","values":[["cmdr_name","Power Generators","20","FALSE","2025-06-21 04:55:49"]]}"""
    __add_mocked_http_response(json.loads(mock_scs_in_transit_data))
    ACTUAL_HTTP_GET_REQUESTS.clear()
    ACTUAL_HTTP_PUT_POST_REQUESTS.clear()
    plugin.process_item(pr)
    assert len(ACTUAL_HTTP_GET_REQUESTS) == 3
    assert len(ACTUAL_HTTP_PUT_POST_REQUESTS) == 1
    
    assert ACTUAL_HTTP_GET_REQUESTS.pop(0) == "https://sheets.googleapis.com/v4/spreadsheets/1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE/values/'NAC Hyperspace Bypass'!A21:E21"
    assert ACTUAL_HTTP_GET_REQUESTS.pop(0) == "https://sheets.googleapis.com/v4/spreadsheets/1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE/values/'NAC Hyperspace Bypass'!A22:E22"
    assert ACTUAL_HTTP_GET_REQUESTS.pop(0) == "https://sheets.googleapis.com/v4/spreadsheets/1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE/values/'NAC Hyperspace Bypass'!A23:E23"

    req = ACTUAL_HTTP_PUT_POST_REQUESTS.pop(0)
    assert req[0] == "https://sheets.googleapis.com/v4/spreadsheets/1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE:batchUpdate"
    assert req[1] == {"requests": [{"deleteRange": {"range": {"sheetId": 1143171463, "startRowIndex": 20, "endRowIndex": 21, "startColumnIndex": 0, "endColumnIndex": 5}, "shiftDimension": "ROWS"}}, {"deleteRange": {"range": {"sheetId": 1143171463, "startRowIndex": 20, "endRowIndex": 21, "startColumnIndex": 0, "endColumnIndex": 5}, "shiftDimension": "ROWS"}}, {"deleteRange": {"range": {"sheetId": 1143171463, "startRowIndex": 20, "endRowIndex": 21, "startColumnIndex": 0, "endColumnIndex": 5}, "shiftDimension": "ROWS"}}]}

    assert len(plugin.this.sheet.inTransitCommodities) == 0

    # The one to fetch the latest in-transit data from the sheet
    pr = plugin.this.queue.get_nowait()
    assert pr
    assert pr.type == plugin.PushRequest.TYPE_CARRIER_INTRANSIT_RECALC
    assert pr.cmdr == monitor.monitor.cmdr
    assert pr.station == 'X7H-9KW'
    assert pr.data == None

    mock_scs_in_transit_data = """{"range":"'Igneels Tooth'!A1:E500","majorDimension":"ROWS","values":[["CMDR","Commodity","Units","Delivered","Timestamp"],["Starting Inventory","Aluminium","0"],["Starting Inventory","Ceramic Composites","0"],["Starting Inventory","CMM Composite","0"],["Starting Inventory","Computer Components","0"],["Starting Inventory","Copper","0"],["Starting Inventory","Food Cartridges","0"],["Starting Inventory","Fruit and Vedge","0"],["Starting Inventory","Insulating Membrane","0"],["Starting Inventory","Liquid Oxygen","0"],["Starting Inventory","Medical Diagnostic Equipment","0"],["Starting Inventory","Non-Lethal Weapons","0"],["Starting Inventory","Polymers","0"],["Starting Inventory","Power Generators","0"],["Starting Inventory","Semiconductors","0"],["Starting Inventory","Steel","0"],["Starting Inventory","Superconductors","0"],["Starting Inventory","Titanium","0"],["Starting Inventory","Water","0"],["Starting Inventory","Water Purifiers","0"],["cmdr_name","Steel",250,"FALSE"],["cmdr_name","Titanium",320,"FALSE"],["cmdr_name","Power Generators",20,"FALSE"]]}"""
    __add_mocked_http_response(json.loads(mock_scs_in_transit_data))
    ACTUAL_HTTP_GET_REQUESTS.clear()
    ACTUAL_HTTP_PUT_POST_REQUESTS.clear()
    plugin.process_item(pr)
    assert len(ACTUAL_HTTP_GET_REQUESTS) == 1
    assert ACTUAL_HTTP_GET_REQUESTS.pop(0) == "https://sheets.googleapis.com/v4/spreadsheets/1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE/values/'Igneels Tooth'!A:E"
    assert len(ACTUAL_HTTP_PUT_POST_REQUESTS) == 0
    assert len(plugin.this.sheet.inTransitCommodities) == 3
    assert plugin.this.sheet.inTransitCommodities == {'steel': {"'Igneels Tooth'!A21:E21": 250}, 'titanium': {"'Igneels Tooth'!A22:E22": 320}, 'powergenerators': {"'Igneels Tooth'!A23:E23": 20}}

    pr = plugin.this.queue.get_nowait()
    assert pr
    assert pr.type == plugin.PushRequest.TYPE_CARRIER_INTRANSIT_RECALC
    assert pr.cmdr == monitor.monitor.cmdr
    assert pr.station == 'X7H-9KW'
    assert pr.data['clear'] == True

    mock_scs_in_transit_data = """{"range":"'Igneels Tooth'!A21:E21","majorDimension":"ROWS","values":[["cmdr_name","Steel","250","FALSE","2025-06-21 04:55:49"]]}"""
    __add_mocked_http_response(json.loads(mock_scs_in_transit_data))
    mock_scs_in_transit_data = """{"range":"'Igneels Tooth'!A22:E22","majorDimension":"ROWS","values":[["cmdr_name","Titanium","320","FALSE","2025-06-21 04:55:49"]]}"""
    __add_mocked_http_response(json.loads(mock_scs_in_transit_data))
    mock_scs_in_transit_data = """{"range":"'Igneels Tooth'!A23:E23","majorDimension":"ROWS","values":[["cmdr_name","Power Generators","20","FALSE","2025-06-21 04:55:49"]]}"""
    __add_mocked_http_response(json.loads(mock_scs_in_transit_data))
    ACTUAL_HTTP_GET_REQUESTS.clear()
    ACTUAL_HTTP_PUT_POST_REQUESTS.clear()
    plugin.process_item(pr)
    assert len(ACTUAL_HTTP_GET_REQUESTS) == 3
    assert len(ACTUAL_HTTP_PUT_POST_REQUESTS) == 1
    
    assert ACTUAL_HTTP_GET_REQUESTS.pop(0) == "https://sheets.googleapis.com/v4/spreadsheets/1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE/values/'Igneels Tooth'!A21:E21"
    assert ACTUAL_HTTP_GET_REQUESTS.pop(0) == "https://sheets.googleapis.com/v4/spreadsheets/1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE/values/'Igneels Tooth'!A22:E22"
    assert ACTUAL_HTTP_GET_REQUESTS.pop(0) == "https://sheets.googleapis.com/v4/spreadsheets/1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE/values/'Igneels Tooth'!A23:E23"

    req = ACTUAL_HTTP_PUT_POST_REQUESTS.pop(0)
    assert req[0] == "https://sheets.googleapis.com/v4/spreadsheets/1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE:batchUpdate"
    assert req[1] == {"requests": [{"deleteRange": {"range": {"sheetId": 1223817771, "startRowIndex": 20, "endRowIndex": 21, "startColumnIndex": 0, "endColumnIndex": 5}, "shiftDimension": "ROWS"}}, {"deleteRange": {"range": {"sheetId": 1223817771, "startRowIndex": 20, "endRowIndex": 21, "startColumnIndex": 0, "endColumnIndex": 5}, "shiftDimension": "ROWS"}}, {"deleteRange": {"range": {"sheetId": 1223817771, "startRowIndex": 20, "endRowIndex": 21, "startColumnIndex": 0, "endColumnIndex": 5}, "shiftDimension": "ROWS"}}]}

    assert len(plugin.this.sheet.inTransitCommodities) == 0

def test_journal_entry_Location():
    entry = { "timestamp":"2025-04-13T00:21:42Z", "event":"Location", "DistFromStarLS":1026.624901, "Docked":True, "StationName":"X7H-9KW", "StationType":"FleetCarrier", "MarketID":3707348992, "StationFaction":{ "Name":"FleetCarrier" }, "StationGovernment":"$government_Carrier;", "StationGovernment_Localised":"Private Ownership", "StationServices":[ "dock", "autodock", "commodities", "contacts", "crewlounge", "rearm", "refuel", "repair", "engineer", "flightcontroller", "stationoperations", "stationMenu", "carriermanagement", "carrierfuel", "socialspace" ], "StationEconomy":"$economy_Carrier;", "StationEconomy_Localised":"Private Enterprise", "StationEconomies":[ { "Name":"$economy_Carrier;", "Name_Localised":"Private Enterprise", "Proportion":1.000000 } ], "Taxi":False, "Multicrew":False, "StarSystem":"Zlotrimi", "SystemAddress":3618249902459, "StarPos":[-16.00000,-23.21875,139.56250], "SystemAllegiance":"Federation", "SystemEconomy":"$economy_Refinery;", "SystemEconomy_Localised":"Refinery", "SystemSecondEconomy":"$economy_Extraction;", "SystemSecondEconomy_Localised":"Extraction", "SystemGovernment":"$government_Corporate;", "SystemGovernment_Localised":"Corporate", "SystemSecurity":"$SYSTEM_SECURITY_medium;", "SystemSecurity_Localised":"Medium Security", "Population":930301705, "Body":"Zlotrimi A 4", "BodyID":7, "BodyType":"Planet", "Powers":[ "Yuri Grom" ], "PowerplayState":"Unoccupied", "PowerplayConflictProgress":[ { "Power":"Yuri Grom", "ConflictProgress":0.074167 } ], "Factions":[ { "Name":"Revolutionary Zlotrimi Green Party", "FactionState":"None", "Government":"Democracy", "Influence":0.096742, "Allegiance":"Federation", "Happiness":"$Faction_HappinessBand2;", "Happiness_Localised":"Happy", "MyReputation":0.000000, "PendingStates":[ { "State":"Election", "Trend":0 } ] }, { "Name":"Zlotrimi Purple Creative Hldgs", "FactionState":"None", "Government":"Corporate", "Influence":0.019743, "Allegiance":"Independent", "Happiness":"$Faction_HappinessBand2;", "Happiness_Localised":"Happy", "MyReputation":0.000000 }, { "Name":"Citizen Party of Adju", "FactionState":"Expansion", "Government":"Communism", "Influence":0.096742, "Allegiance":"Independent", "Happiness":"$Faction_HappinessBand2;", "Happiness_Localised":"Happy", "MyReputation":0.000000, "PendingStates":[ { "State":"Election", "Trend":0 } ], "ActiveStates":[ { "State":"Expansion" } ] }, { "Name":"Zlotrimi Law Party", "FactionState":"None", "Government":"Dictatorship", "Influence":0.053307, "Allegiance":"Independent", "Happiness":"$Faction_HappinessBand2;", "Happiness_Localised":"Happy", "MyReputation":0.000000 }, { "Name":"Manite Inc", "FactionState":"Expansion", "Government":"Corporate", "Influence":0.674235, "Allegiance":"Federation", "Happiness":"$Faction_HappinessBand2;", "Happiness_Localised":"Happy", "MyReputation":7.278460, "RecoveringStates":[ { "State":"Drought", "Trend":0 } ], "ActiveStates":[ { "State":"Boom" }, { "State":"Expansion" } ] }, { "Name":"Zlotrimi Commodities", "FactionState":"None", "Government":"Corporate", "Influence":0.037512, "Allegiance":"Independent", "Happiness":"$Faction_HappinessBand2;", "Happiness_Localised":"Happy", "MyReputation":0.000000 }, { "Name":"Zlotrimi Justice Party", "FactionState":"None", "Government":"Dictatorship", "Influence":0.021718, "Allegiance":"Independent", "Happiness":"$Faction_HappinessBand2;", "Happiness_Localised":"Happy", "MyReputation":0.000000 } ], "SystemFaction":{ "Name":"Manite Inc", "FactionState":"Expansion" }, "Conflicts":[ { "WarType":"election", "Status":"pending", "Faction1":{ "Name":"Revolutionary Zlotrimi Green Party", "Stake":"Cosmic Oversight Core", "WonDays":0 }, "Faction2":{ "Name":"Citizen Party of Adju", "Stake":"Gubarev Port", "WonDays":0 } } ] }
    plugin.journal_entry(cmdr=monitor.monitor.cmdr, is_beta=False, system="Zlotrimi", station="X7H-9KW", entry=entry, state=None)

    assert plugin.this.queue.qsize() == 0

    entry = { "timestamp":"2025-04-13T00:21:42Z", "event":"Location", "DistFromStarLS":1026.624901, "Docked":True, "StationName":"X7H-9KW", "StationType":"FleetCarrier", "MarketID":3707348992, "StationFaction":{ "Name":"FleetCarrier" }, "StationGovernment":"$government_Carrier;", "StationGovernment_Localised":"Private Ownership", "StationServices":[ "dock", "autodock", "commodities", "contacts", "crewlounge", "rearm", "refuel", "repair", "engineer", "flightcontroller", "stationoperations", "stationMenu", "carriermanagement", "carrierfuel", "socialspace" ], "StationEconomy":"$economy_Carrier;", "StationEconomy_Localised":"Private Enterprise", "StationEconomies":[ { "Name":"$economy_Carrier;", "Name_Localised":"Private Enterprise", "Proportion":1.000000 } ], "Taxi":False, "Multicrew":False, "StarSystem":"Zlotrimi", "SystemAddress":3618249902459, "StarPos":[-16.00000,-23.21875,139.56250], "SystemAllegiance":"Federation", "SystemEconomy":"$economy_Refinery;", "SystemEconomy_Localised":"Refinery", "SystemSecondEconomy":"$economy_Extraction;", "SystemSecondEconomy_Localised":"Extraction", "SystemGovernment":"$government_Corporate;", "SystemGovernment_Localised":"Corporate", "SystemSecurity":"$SYSTEM_SECURITY_medium;", "SystemSecurity_Localised":"Medium Security", "Population":930301705, "Body":"Zlotrimi A 4", "BodyID":7, "BodyType":"Planet", "Powers":[ "Yuri Grom" ], "PowerplayState":"Unoccupied", "PowerplayConflictProgress":[ { "Power":"Yuri Grom", "ConflictProgress":0.074167 } ], "Factions":[ { "Name":"Revolutionary Zlotrimi Green Party", "FactionState":"None", "Government":"Democracy", "Influence":0.096742, "Allegiance":"Federation", "Happiness":"$Faction_HappinessBand2;", "Happiness_Localised":"Happy", "MyReputation":0.000000, "PendingStates":[ { "State":"Election", "Trend":0 } ] }, { "Name":"Zlotrimi Purple Creative Hldgs", "FactionState":"None", "Government":"Corporate", "Influence":0.019743, "Allegiance":"Independent", "Happiness":"$Faction_HappinessBand2;", "Happiness_Localised":"Happy", "MyReputation":0.000000 }, { "Name":"Citizen Party of Adju", "FactionState":"Expansion", "Government":"Communism", "Influence":0.096742, "Allegiance":"Independent", "Happiness":"$Faction_HappinessBand2;", "Happiness_Localised":"Happy", "MyReputation":0.000000, "PendingStates":[ { "State":"Election", "Trend":0 } ], "ActiveStates":[ { "State":"Expansion" } ] }, { "Name":"Zlotrimi Law Party", "FactionState":"None", "Government":"Dictatorship", "Influence":0.053307, "Allegiance":"Independent", "Happiness":"$Faction_HappinessBand2;", "Happiness_Localised":"Happy", "MyReputation":0.000000 }, { "Name":"Manite Inc", "FactionState":"Expansion", "Government":"Corporate", "Influence":0.674235, "Allegiance":"Federation", "Happiness":"$Faction_HappinessBand2;", "Happiness_Localised":"Happy", "MyReputation":7.278460, "RecoveringStates":[ { "State":"Drought", "Trend":0 } ], "ActiveStates":[ { "State":"Boom" }, { "State":"Expansion" } ] }, { "Name":"Zlotrimi Commodities", "FactionState":"None", "Government":"Corporate", "Influence":0.037512, "Allegiance":"Independent", "Happiness":"$Faction_HappinessBand2;", "Happiness_Localised":"Happy", "MyReputation":0.000000 }, { "Name":"Zlotrimi Justice Party", "FactionState":"None", "Government":"Dictatorship", "Influence":0.021718, "Allegiance":"Independent", "Happiness":"$Faction_HappinessBand2;", "Happiness_Localised":"Happy", "MyReputation":0.000000 } ], "SystemFaction":{ "Name":"Manite Inc", "FactionState":"Expansion" }, "Conflicts":[ { "WarType":"election", "Status":"pending", "Faction1":{ "Name":"Revolutionary Zlotrimi Green Party", "Stake":"Cosmic Oversight Core", "WonDays":0 }, "Faction2":{ "Name":"Citizen Party of Adju", "Stake":"Gubarev Port", "WonDays":0 } } ] }
    plugin.journal_entry(cmdr=monitor.monitor.cmdr, is_beta=False, system="Zlotrimi", station=None, entry=entry, state=None)

    assert plugin.this.queue.qsize() == 0

    # TODO: Do we care about asserting out logging statements ?
    # If not, then all we're doing is just checking that no exception happens

def test_journal_entry_FSDJump():
    entry = { "timestamp":"2025-05-16T07:02:41Z", "event":"FSDJump", "Taxi":False, "Multicrew":False, "StarSystem":"Ukko", "SystemAddress":2484395313515, "StarPos":[32.56250,37.37500,39.65625], "SystemAllegiance":"Independent", "SystemEconomy":"$economy_Military;", "SystemEconomy_Localised":"Military", "SystemSecondEconomy":"$economy_Colony;", "SystemSecondEconomy_Localised":"Colony", "SystemGovernment":"$government_Democracy;", "SystemGovernment_Localised":"Democracy", "SystemSecurity":"$SYSTEM_SECURITY_low;", "SystemSecurity_Localised":"Low Security", "Population":653495, "Body":"Ukko A", "BodyID":2, "BodyType":"Star", "Powers":[ "Edmund Mahon", "Felicia Winters", "Yuri Grom" ], "PowerplayState":"Unoccupied", "PowerplayConflictProgress":[ { "Power":"Edmund Mahon", "ConflictProgress":0.000000 }, { "Power":"Felicia Winters", "ConflictProgress":0.003117 }, { "Power":"Yuri Grom", "ConflictProgress":0.000000 } ], "JumpDist":7.299, "FuelUsed":0.103423, "FuelLevel":56.816853, "Factions":[ { "Name":"LP 798-44 Purple Raiders", "FactionState":"None", "Government":"Anarchy", "Influence":0.021956, "Allegiance":"Independent", "Happiness":"$Faction_HappinessBand2;", "Happiness_Localised":"Happy", "MyReputation":0.000000, "PendingStates":[ { "State":"Retreat", "Trend":0 } ] }, { "Name":"LP 798-44 for Equality", "FactionState":"None", "Government":"Democracy", "Influence":0.146707, "Allegiance":"Independent", "Happiness":"$Faction_HappinessBand2;", "Happiness_Localised":"Happy", "MyReputation":0.000000 }, { "Name":"Terra-EX Astro Corp", "FactionState":"None", "Government":"Corporate", "Influence":0.185629, "Allegiance":"Federation", "Happiness":"$Faction_HappinessBand2;", "Happiness_Localised":"Happy", "MyReputation":71.791298, "RecoveringStates":[ { "State":"Expansion", "Trend":0 } ] }, { "Name":"Sidewinder Syndicate", "FactionState":"Boom", "Government":"Democracy", "Influence":0.645709, "Allegiance":"Independent", "Happiness":"$Faction_HappinessBand3;", "Happiness_Localised":"Content", "MyReputation":0.000000, "RecoveringStates":[ { "State":"Expansion", "Trend":0 } ], "ActiveStates":[ { "State":"Boom" } ] } ], "SystemFaction":{ "Name":"Sidewinder Syndicate", "FactionState":"Boom" } }
    plugin.journal_entry(cmdr=monitor.monitor.cmdr, is_beta=False, system="Zlotrimi", station=None, entry=entry, state=None)

    assert plugin.this.queue.qsize() == 0

    # TODO: Do we care about asserting out logging statements ?
    # If not, then all we're doing is just checking that no exception happens

def test_journal_entry_Docked():   
    plugin.this.cargoCapacity = 720
    plugin.this.latestCarrierCallsign = None
    
    entry = { "timestamp":"2025-05-16T07:09:00Z", "event":"Docked", "StationName":"X7H-9KW", "StationType":"FleetCarrier", "Taxi":False, "Multicrew":False, "StarSystem":"Ukko", "SystemAddress":2484395313515, "MarketID":3707348992, "StationFaction":{ "Name":"FleetCarrier" }, "StationGovernment":"$government_Carrier;", "StationGovernment_Localised":"Private Ownership", "StationServices":[ "dock", "autodock", "commodities", "contacts", "crewlounge", "rearm", "refuel", "repair", "engineer", "flightcontroller", "stationoperations", "stationMenu", "carriermanagement", "carrierfuel", "socialspace" ], "StationEconomy":"$economy_Carrier;", "StationEconomy_Localised":"Private Enterprise", "StationEconomies":[ { "Name":"$economy_Carrier;", "Name_Localised":"Private Enterprise", "Proportion":1.000000 } ], "DistFromStarLS":25771.605003, "LandingPads":{ "Small":4, "Medium":4, "Large":8 } }
    state = {'Cargo': defaultdict(int, {'steel': 720}), 'CargoCapacity': 720}
    plugin.journal_entry(cmdr=monitor.monitor.cmdr, is_beta=False, system="Zlotrimi", station="X7H-9KW", entry=entry, state=state)
    
    assert plugin.this.queue.qsize() == 2
    assert plugin.this.latestCarrierCallsign == "X7H-9KW"

    pr = plugin.this.queue.get_nowait()
    assert pr
    assert pr.type == plugin.PushRequest.TYPE_CARRIER_LOC_UPDATE
    assert pr.cmdr == monitor.monitor.cmdr
    assert pr.station == "X7H-9KW"
    assert pr.data == "Zlotrimi"

    pr = plugin.this.queue.get_nowait()
    assert pr
    assert pr.type == plugin.PushRequest.TYPE_CARRIER_JUMP
    assert pr.cmdr == monitor.monitor.cmdr
    assert pr.station == "X7H-9KW"
    assert pr.data == {}

    # Change ship/capacity
    state = {'Cargo': defaultdict(int, {'steel': 720}), 'CargoCapacity': 512}
    plugin.journal_entry(cmdr=monitor.monitor.cmdr, is_beta=False, system="Zlotrimi", station="X7H-9KW", entry=entry, state=state)

    assert plugin.this.queue.qsize() == 3

    pr = plugin.this.queue.get_nowait()
    assert pr
    assert pr.type == plugin.PushRequest.TYPE_CARRIER_LOC_UPDATE
    assert pr.cmdr == monitor.monitor.cmdr
    assert pr.station == "X7H-9KW"
    assert pr.data == "Zlotrimi"

    pr = plugin.this.queue.get_nowait()
    assert pr
    assert pr.type == plugin.PushRequest.TYPE_CARRIER_JUMP
    assert pr.cmdr == monitor.monitor.cmdr
    assert pr.station == "X7H-9KW"
    assert pr.data == {}

    pr = plugin.this.queue.get_nowait()
    assert pr
    assert pr.type == plugin.PushRequest.TYPE_CMDR_UPDATE
    assert pr.cmdr == monitor.monitor.cmdr
    assert pr.station == "X7H-9KW"
    assert pr.data == None

    # Dock to SCS that we don't know about yet
    entry = { "timestamp":"2025-05-10T06:21:18Z", "event":"Docked", "StationName":"$EXT_PANEL_ColonisationShip; Dupont Territories", "StationType":"SurfaceStation", "Taxi":False, "Multicrew":False, "StarSystem":"Pru Euq OG-J b50-5", "SystemAddress":11664728663985, "MarketID":3950902274, "StationFaction":{ "Name":"Brewer Corporation" }, "StationGovernment":"$government_Corporate;", "StationGovernment_Localised":"Corporate", "StationServices":[ "dock", "autodock", "commodities", "contacts", "missions", "rearm", "refuel", "repair", "engineer", "facilitator", "flightcontroller", "stationoperations", "searchrescue", "stationMenu", "colonisationcontribution" ], "StationEconomy":"$economy_Colony;", "StationEconomy_Localised":"Colony", "StationEconomies":[ { "Name":"$economy_Colony;", "Name_Localised":"Colony", "Proportion":1.000000 } ], "DistFromStarLS":912.564607, "LandingPads":{ "Small":8, "Medium":8, "Large":16 } }
    plugin.journal_entry(cmdr=monitor.monitor.cmdr, is_beta=False, system="Pru Euq OG-J b50-5", station="$EXT_PANEL_ColonisationShip; Dupont Territories", entry=entry, state=state)

    assert plugin.this.queue.qsize() == 1

    pr = plugin.this.queue.get_nowait()
    assert pr
    assert pr.type == plugin.PushRequest.TYPE_SCS_SYSTEM_ADD
    assert pr.cmdr == monitor.monitor.cmdr
    assert pr.station == "Pru Euq OG-J b50-5"
    assert pr.data == entry

def test_journal_entry_Cargo():
    entry = { "timestamp":"2025-06-13T21:00:21Z", "event":"Cargo", "Vessel":"Ship", "Count":0 }
    plugin.journal_entry(cmdr=monitor.monitor.cmdr, is_beta=False, system="Zlotrimi", station="Fraley Orbital", entry=entry, state=None)

    assert plugin.this.queue.qsize() == 1
    
    pr = plugin.this.queue.get_nowait()
    assert pr
    assert pr.type == plugin.PushRequest.TYPE_CARRIER_INTRANSIT_RECALC
    assert pr.cmdr == monitor.monitor.cmdr
    assert pr.station == "Fraley Orbital"
    assert pr.data == {'clear': True}

    plugin.this.cmdrsAssignedCarrierName.set('Igneels Tooth')
    plugin.this.sheet.inTransitCommodities = {
        'aluminium': {
            "'Igneels Tooth'!A21:E21": 52
        },
        'steel': {
            "'NAC Hyperspace Bypass'!A81:E81": 700
        }
    }
    mock_in_transit_response = """{"range":"'Igneels Tooth'!A21:E21","majorDimension":"ROWS","values":[["cmdr_name","Aluminium","52","FALSE","2025-06-17 19:17:40"]]}"""
    __add_mocked_http_response(json.loads(mock_in_transit_response))
    mock_in_transit_response = """{"range":"'NAC Hyperspace Bypass'!A81:E81","majorDimension":"ROWS","values":[["cmdr_name","Steel","700","FALSE","2025-06-17 19:17:40"]]}"""
    __add_mocked_http_response(json.loads(mock_in_transit_response))
    ACTUAL_HTTP_PUT_POST_REQUESTS.clear()
    plugin.process_item(pr)
    assert len(ACTUAL_HTTP_PUT_POST_REQUESTS) == 1

    req = ACTUAL_HTTP_PUT_POST_REQUESTS.pop(0)
    assert req[0] == "https://sheets.googleapis.com/v4/spreadsheets/1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE:batchUpdate"
    assert req[1] == {"requests": [{"deleteRange": {"range": {"sheetId": 1223817771, "startRowIndex": 20, "endRowIndex": 21, "startColumnIndex": 0, "endColumnIndex": 5}, "shiftDimension": "ROWS"}}, {"deleteRange": {"range": {"sheetId": 1143171463, "startRowIndex": 80, "endRowIndex": 81, "startColumnIndex": 0, "endColumnIndex": 5}, "shiftDimension": "ROWS"}}]}

    entry = { "timestamp":"2025-06-13T21:00:21Z", "event":"Cargo", "Vessel":"Ship", "Count":20 }
    plugin.journal_entry(cmdr=monitor.monitor.cmdr, is_beta=False, system="Zlotrimi", station="Fraley Orbital", entry=entry, state=None)

    assert plugin.this.queue.qsize() == 0

def test_journal_entry_ColonisationConstructionDepot():
    plugin.this.sheet.systemsInProgress.append("M7 Sector CG-X d1-90")
    plugin.this.dataPopulatedForSystems = []
    plugin.this.nextSCSReconcileTime = int(time.time())

    assert plugin.this.sheet.lookupRanges[plugin.this.sheet.LOOKUP_SCS_PROGRESS_PIVOT] == "W4:BY"
    assert plugin.this.sheet.lookupRanges[plugin.this.sheet.LOOKUP_SCS_RECONCILE_MUTEX] == "'SCS Offload'!X1"

    entry = {'timestamp': '2025-04-13T04:17:39Z', 'event': 'ColonisationConstructionDepot', 'MarketID': 3956667650, 'ConstructionProgress': 0.0, 'ConstructionComplete': False, 'ConstructionFailed': False, 'ResourcesRequired': [{'Name': '$aluminium_name;', 'Name_Localised': 'Aluminium', 'RequiredAmount': 510, 'ProvidedAmount': 200, 'Payment': 3239}, {'Name': '$ceramiccomposites_name;', 'Name_Localised': 'Ceramic Composites', 'RequiredAmount': 515, 'ProvidedAmount': 50, 'Payment': 724}, {'Name': '$cmmcomposite_name;', 'Name_Localised': 'CMM Composite', 'RequiredAmount': 4319, 'ProvidedAmount': 1024, 'Payment': 6788}, {'Name': '$computercomponents_name;', 'Name_Localised': 'Computer Components', 'RequiredAmount': 61, 'ProvidedAmount': 0, 'Payment': 1112}, {'Name': '$copper_name;', 'Name_Localised': 'Copper', 'RequiredAmount': 247, 'ProvidedAmount': 242, 'Payment': 1050}, {'Name': '$foodcartridges_name;', 'Name_Localised': 'Food Cartridges', 'RequiredAmount': 96, 'ProvidedAmount': 45, 'Payment': 673}, {'Name': '$fruitandvegetables_name;', 'Name_Localised': 'Fruit and Vegetables', 'RequiredAmount': 52, 'ProvidedAmount': 52, 'Payment': 865}, {'Name': '$insulatingmembrane_name;', 'Name_Localised': 'Insulating Membrane', 'RequiredAmount': 353, 'ProvidedAmount': 336, 'Payment': 11788}, {'Name': '$liquidoxygen_name;', 'Name_Localised': 'Liquid oxygen', 'RequiredAmount': 1745, 'ProvidedAmount': 1745, 'Payment': 2260}, {'Name': '$medicaldiagnosticequipment_name;', 'Name_Localised': 'Medical Diagnostic Equipment', 'RequiredAmount': 12, 'ProvidedAmount': 12, 'Payment': 3609}, {'Name': '$nonlethalweapons_name;', 'Name_Localised': 'Non-Lethal Weapons', 'RequiredAmount': 13, 'ProvidedAmount': 0, 'Payment': 2503}, {'Name': '$polymers_name;', 'Name_Localised': 'Polymers', 'RequiredAmount': 517, 'ProvidedAmount': 254, 'Payment': 682}, {'Name': '$powergenerators_name;', 'Name_Localised': 'Power Generators', 'RequiredAmount': 19, 'ProvidedAmount': 4, 'Payment': 3072}, {'Name': '$semiconductors_name;', 'Name_Localised': 'Semiconductors', 'RequiredAmount': 67, 'ProvidedAmount': 23, 'Payment': 1526}, {'Name': '$steel_name;', 'Name_Localised': 'Steel', 'RequiredAmount': 6749, 'ProvidedAmount': 1859, 'Payment': 5057}, {'Name': '$superconductors_name;', 'Name_Localised': 'Superconductors', 'RequiredAmount': 113, 'ProvidedAmount': 99, 'Payment': 7657}, {'Name': '$titanium_name;', 'Name_Localised': 'Titanium', 'RequiredAmount': 5415, 'ProvidedAmount': 4321, 'Payment': 5360}, {'Name': '$water_name;', 'Name_Localised': 'Water', 'RequiredAmount': 709, 'ProvidedAmount': 602, 'Payment': 662}, {'Name': '$waterpurifiers_name;', 'Name_Localised': 'Water Purifiers', 'RequiredAmount': 38, 'ProvidedAmount': 0, 'Payment': 849}]}
    plugin.journal_entry(cmdr=monitor.monitor.cmdr, is_beta=False, system="M7 Sector CG-X d1-90", station="$EXT_PANEL_ColonisationShip; Low Reach", entry=entry, state=None)

    assert plugin.this.queue.qsize() == 2   # Should be PushRequests for both SCS_PROGRESS_UPDATE and SCS_DATA_POPULATE
    assert plugin.this.nextSCSReconcileTime > int(time.time()) + 59
    
    pr = plugin.this.queue.get_nowait()
    assert pr
    assert pr.type == plugin.PushRequest.TYPE_SCS_DATA_POPULATE
    assert pr.cmdr == monitor.monitor.cmdr
    assert pr.station == "M7 Sector CG-X d1-90"

    pr = plugin.this.queue.get_nowait()
    assert pr
    assert pr.type == plugin.PushRequest.TYPE_SCS_PROGRESS_UPDATE
    assert pr.cmdr == monitor.monitor.cmdr
    assert pr.station == "M7 Sector CG-X d1-90"

    plugin.this.killswitches[plugin.KILLSWITCH_SCS_RECONCILE] = 'false'
    plugin.this.killswitches[plugin.KILLSWITCH_SCS_DATA_POPULATE] = 'false'
    plugin.process_item(pr)
    # TODO: How do we assert that this did, in fact, do nothing

    # Reconcile currently running by another cmdr
    plugin.this.killswitches[plugin.KILLSWITCH_SCS_RECONCILE] = 'true'
    mock_scs_reconcile_mutex = """{"range":"'SCS Offload'!X1","majorDimension":"ROWS","values":[["other_cmdr_name"]]}"""
    __add_mocked_http_response(json.loads(mock_scs_reconcile_mutex))
    ACTUAL_HTTP_PUT_POST_REQUESTS.clear()
    plugin.process_item(pr)
    assert len(ACTUAL_HTTP_PUT_POST_REQUESTS) == 0

    # Previous reoncile that didn't finish correctly by us
    mock_scs_reconcile_mutex = """{"range":"'SCS Offload'!X1","majorDimension": "ROWS","values":[["cmdr_name"]]}"""
    __add_mocked_http_response(json.loads(mock_scs_reconcile_mutex))
    mock_scs_reconcile_mutext_set = """{"spreadsheetId":"1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE","updatedRange":"'SCS Offload'!X1","updatedRows":1,"updatedColumns":1,"updatedCells":1}"""
    __add_mocked_http_response(json.loads(mock_scs_reconcile_mutext_set))
    __add_mocked_http_response(json.loads(mock_scs_reconcile_mutext_set))
    mock_scs_progress_data = """{"range":"'SCS Offload'!W4:BY999","majorDimension":"ROWS","values":[["Delivered To","Advanced Catalysers","Agri-Medicines","Aluminium","Animal Meat","Basic Medicines","Battle Weapons","Beer","Bioreducing Lichen","Biowaste","Building Fabricators","Ceramic Composites","CMM Composite","Coffee","Combat Stabilizers","Computer Components","Copper","Crop Harvesters","Emergency Power Cells","Evacuation Shelter","Fish","Food Cartridges","Fruit and Vedge","Geological Equipment","Grain","H.E. Suits","Insulating Membrane","Land Enrichment Systems","Liquid Oxygen","Liquor","Medical Diagnostic Equipment","Micro Controllers","Microbial Furnaces","Military Grade Fabrics","Mineral Extractors","Muon Imager","Non-Lethal Weapons","Pesticides","Polymers","Power Generators","Reactive Armour","Resonating Separators","Robotics","Semiconductors","Steel","Structural Regulators","Superconductors","Surface Stabilisers","Survival Equipment","Tea","Thermal Cooling Units","Titanium","Water","Water Purifiers","Wine"],["","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0"],["Arietis Sector BV-P b5-4","","","9978","","","","","","","","","12023","","","199","749","","","","","243","150","","","","69","","2116","","26","","","","","","26","","1118","63","","","","","16973","","333","","","","","9961","2129","109"],["Beta Coronae Austrinae","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","784"],["Pru Euq RV-T b44-6","","","478","","","","","","","","","","","","60","240","","","","","90","50","","","","361","","280","","13","","","","","","","","538","19","","","","67","6261","","115","","","","","2374","777","37"],["M7 Sector CG-X d1-90","","","182","","","","","","","","37","986","","","","237","","","","","43","52","","","","319","","1722","","11","","","","","","0","","240","4","","","","21","1693","","96","","","","","4305","542","38","90"]]}"""
    __add_mocked_http_response(json.loads(mock_scs_progress_data))
    mock_scs_inflight_data = """{"range":"'SCS Offload'!CB4:EE999","majorDimension":"ROWS","values":[["Delivered To","Water Purifiers"],["M7 Sector CG-X d1-90","38"]]}"""
    __add_mocked_http_response(json.loads(mock_scs_inflight_data))
    ACTUAL_HTTP_PUT_POST_REQUESTS.clear()
    plugin.process_item(pr)

    assert len(ACTUAL_HTTP_PUT_POST_REQUESTS) == 3
    
    # SCS Reconcile Mutex Set
    req = ACTUAL_HTTP_PUT_POST_REQUESTS.pop(0)
    assert req[0] == "https://sheets.googleapis.com/v4/spreadsheets/1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE/values/'SCS Offload'!X1?valueInputOption=USER_ENTERED"
    assert req[1] == {"range": "'SCS Offload'!X1", "majorDimension": "ROWS", "values": [["cmdr_name"]]}

    # SCS Offload Corrections
    req = ACTUAL_HTTP_PUT_POST_REQUESTS.pop(0)
    assert req[0] == "https://sheets.googleapis.com/v4/spreadsheets/1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE/values/'SCS Offload'!A:A:append?valueInputOption=USER_ENTERED"
    assert req[1] == {'range': "'SCS Offload'!A:A", 'majorDimension': 'ROWS', 'values': [['Aluminium', 'M7 Sector CG-X d1-90', 18, True, '2025-04-13 04:17:39'], ['Ceramic Composites', 'M7 Sector CG-X d1-90', 13, True, '2025-04-13 04:17:39'], ['CMM Composite', 'M7 Sector CG-X d1-90', 38, True, '2025-04-13 04:17:39'], ['Copper', 'M7 Sector CG-X d1-90', 5, True, '2025-04-13 04:17:39'], ['Food Cartridges', 'M7 Sector CG-X d1-90', 2, True, '2025-04-13 04:17:39'], ['Insulating Membrane', 'M7 Sector CG-X d1-90', 17, True, '2025-04-13 04:17:39'], ['Liquid Oxygen', 'M7 Sector CG-X d1-90', 23, True, '2025-04-13 04:17:39'], ['Medical Diagnostic Equipment', 'M7 Sector CG-X d1-90', 1, True, '2025-04-13 04:17:39'], ['Polymers', 'M7 Sector CG-X d1-90', 14, True, '2025-04-13 04:17:39'], ['Semiconductors', 'M7 Sector CG-X d1-90', 2, True, '2025-04-13 04:17:39'], ['Steel', 'M7 Sector CG-X d1-90', 166, True, '2025-04-13 04:17:39'], ['Superconductors', 'M7 Sector CG-X d1-90', 3, True, '2025-04-13 04:17:39'], ['Titanium', 'M7 Sector CG-X d1-90', 16, True, '2025-04-13 04:17:39'], ['Water', 'M7 Sector CG-X d1-90', 60, True, '2025-04-13 04:17:39']]}

    # SCS Reconcile Mutex Clear
    req = ACTUAL_HTTP_PUT_POST_REQUESTS.pop(0)
    assert req[0] == "https://sheets.googleapis.com/v4/spreadsheets/1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE/values/'SCS Offload'!X1?valueInputOption=USER_ENTERED"
    assert req[1] == {"range": "'SCS Offload'!X1", "majorDimension": "ROWS", "values": [[""]]}

    # No reconcile currently running
    mock_scs_reconcile_mutex = """{"range":"'SCS Offload'!X1","majorDimension": "ROWS"}"""
    __add_mocked_http_response(json.loads(mock_scs_reconcile_mutex))
    mock_scs_reconcile_mutext_set = """{"spreadsheetId":"1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE","updatedRange":"'SCS Offload'!X1","updatedRows":1,"updatedColumns":1,"updatedCells":1}"""
    __add_mocked_http_response(json.loads(mock_scs_reconcile_mutext_set))
    __add_mocked_http_response(json.loads(mock_scs_reconcile_mutext_set))
    mock_scs_progress_data = """{"range":"'SCS Offload'!W4:BY999","majorDimension":"ROWS","values":[["Delivered To","Advanced Catalysers","Agri-Medicines","Aluminium","Animal Meat","Basic Medicines","Battle Weapons","Beer","Bioreducing Lichen","Biowaste","Building Fabricators","Ceramic Composites","CMM Composite","Coffee","Combat Stabilizers","Computer Components","Copper","Crop Harvesters","Emergency Power Cells","Evacuation Shelter","Fish","Food Cartridges","Fruit and Vedge","Geological Equipment","Grain","H.E. Suits","Insulating Membrane","Land Enrichment Systems","Liquid Oxygen","Liquor","Medical Diagnostic Equipment","Micro Controllers","Microbial Furnaces","Military Grade Fabrics","Mineral Extractors","Muon Imager","Non-Lethal Weapons","Pesticides","Polymers","Power Generators","Reactive Armour","Resonating Separators","Robotics","Semiconductors","Steel","Structural Regulators","Superconductors","Surface Stabilisers","Survival Equipment","Tea","Thermal Cooling Units","Titanium","Water","Water Purifiers","Wine"],["","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0"],["Arietis Sector BV-P b5-4","","","9978","","","","","","","","","12023","","","199","749","","","","","243","150","","","","69","","2116","","26","","","","","","26","","1118","63","","","","","16973","","333","","","","","9961","2129","109"],["Beta Coronae Austrinae","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","784"],["Pru Euq RV-T b44-6","","","478","","","","","","","","","","","","60","240","","","","","90","50","","","","361","","280","","13","","","","","","","","538","19","","","","67","6261","","115","","","","","2374","777","37"],["M7 Sector CG-X d1-90","","","182","","","","","","","","37","986","","","","237","","","","","43","52","","","","319","","1722","","11","","","","","","0","","240","4","","","","21","1693","","96","","","","","4305","542","38","90"]]}"""
    __add_mocked_http_response(json.loads(mock_scs_progress_data))
    mock_scs_inflight_data = """{"range":"'SCS Offload'!CB4:EE999","majorDimension":"ROWS","values":[["Delivered To","Water Purifiers"],["M7 Sector CG-X d1-90","38"]]}"""
    __add_mocked_http_response(json.loads(mock_scs_inflight_data))
    ACTUAL_HTTP_PUT_POST_REQUESTS.clear()
    plugin.process_item(pr)

    assert len(ACTUAL_HTTP_PUT_POST_REQUESTS) == 3
    
    # SCS Reconcile Mutex Set
    req = ACTUAL_HTTP_PUT_POST_REQUESTS.pop(0)
    assert req[0] == "https://sheets.googleapis.com/v4/spreadsheets/1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE/values/'SCS Offload'!X1?valueInputOption=USER_ENTERED"
    assert req[1] == {"range": "'SCS Offload'!X1", "majorDimension": "ROWS", "values": [["cmdr_name"]]}

    # SCS Offload Corrections
    req = ACTUAL_HTTP_PUT_POST_REQUESTS.pop(0)
    assert req[0] == "https://sheets.googleapis.com/v4/spreadsheets/1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE/values/'SCS Offload'!A:A:append?valueInputOption=USER_ENTERED"
    assert req[1] == {'range': "'SCS Offload'!A:A", 'majorDimension': 'ROWS', 'values': [['Aluminium', 'M7 Sector CG-X d1-90', 18, True, '2025-04-13 04:17:39'], ['Ceramic Composites', 'M7 Sector CG-X d1-90', 13, True, '2025-04-13 04:17:39'], ['CMM Composite', 'M7 Sector CG-X d1-90', 38, True, '2025-04-13 04:17:39'], ['Copper', 'M7 Sector CG-X d1-90', 5, True, '2025-04-13 04:17:39'], ['Food Cartridges', 'M7 Sector CG-X d1-90', 2, True, '2025-04-13 04:17:39'], ['Insulating Membrane', 'M7 Sector CG-X d1-90', 17, True, '2025-04-13 04:17:39'], ['Liquid Oxygen', 'M7 Sector CG-X d1-90', 23, True, '2025-04-13 04:17:39'], ['Medical Diagnostic Equipment', 'M7 Sector CG-X d1-90', 1, True, '2025-04-13 04:17:39'], ['Polymers', 'M7 Sector CG-X d1-90', 14, True, '2025-04-13 04:17:39'], ['Semiconductors', 'M7 Sector CG-X d1-90', 2, True, '2025-04-13 04:17:39'], ['Steel', 'M7 Sector CG-X d1-90', 166, True, '2025-04-13 04:17:39'], ['Superconductors', 'M7 Sector CG-X d1-90', 3, True, '2025-04-13 04:17:39'], ['Titanium', 'M7 Sector CG-X d1-90', 16, True, '2025-04-13 04:17:39'], ['Water', 'M7 Sector CG-X d1-90', 60, True, '2025-04-13 04:17:39']]}

    # SCS Reconcile Mutex Clear
    req = ACTUAL_HTTP_PUT_POST_REQUESTS.pop(0)
    assert req[0] == "https://sheets.googleapis.com/v4/spreadsheets/1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE/values/'SCS Offload'!X1?valueInputOption=USER_ENTERED"
    assert req[1] == {"range": "'SCS Offload'!X1", "majorDimension": "ROWS", "values": [[""]]}

    # Now lets have another one come through '15 seconds later' and make sure we ignore it
    plugin.journal_entry(cmdr=monitor.monitor.cmdr, is_beta=False, system="M7 Sector CG-X d1-90", station="$EXT_PANEL_ColonisationShip; Low Reach", entry=entry, state=None)

    assert plugin.this.queue.qsize() == 0
    assert plugin.this.nextSCSReconcileTime > int(time.time())

def test_journal_entry_ColonisationConstructionDepot_PopulateSystemData():
    plugin.this.sheet.systemsInProgress.append("M7 Sector CG-X d1-90")
    plugin.this.dataPopulatedForSystems = []
    plugin.this.nextSCSReconcileTime = int(time.time())

    assert plugin.this.sheet.lookupRanges[plugin.this.sheet.LOOKUP_SCS_SYSTEMS_WITH_NO_DATA] == "Data!BN:BN"
    assert plugin.this.sheet.lookupRanges[plugin.this.sheet.LOOKUP_DATA_SYSTEM_TABLE] == "Data!A59:A"

    entry = {'timestamp':'2025-04-13T04:17:39Z','event':'ColonisationConstructionDepot','MarketID':3956667650,'ConstructionProgress':0.0,'ConstructionComplete':False,'ConstructionFailed':False,'ResourcesRequired':[{'Name':'$aluminium_name;','Name_Localised':'Aluminium','RequiredAmount':510,'ProvidedAmount':0,'Payment':3239},{'Name':'$ceramiccomposites_name;','Name_Localised':'Ceramic Composites','RequiredAmount':515,'ProvidedAmount':0,'Payment':724},{'Name':'$cmmcomposite_name;','Name_Localised':'CMM Composite','RequiredAmount':4319,'ProvidedAmount':0,'Payment':6788},{'Name':'$computercomponents_name;','Name_Localised':'Computer Components','RequiredAmount':61,'ProvidedAmount':0,'Payment':1112},{'Name':'$copper_name;','Name_Localised':'Copper','RequiredAmount':247,'ProvidedAmount':0,'Payment':1050},{'Name':'$foodcartridges_name;','Name_Localised':'Food Cartridges','RequiredAmount':96,'ProvidedAmount':0,'Payment':673},{'Name':'$fruitandvegetables_name;','Name_Localised':'Fruit and Vegetables','RequiredAmount':52,'ProvidedAmount':0,'Payment':865},{'Name':'$insulatingmembrane_name;','Name_Localised':'Insulating Membrane','RequiredAmount':353,'ProvidedAmount':0,'Payment':11788},{'Name':'$liquidoxygen_name;','Name_Localised':'Liquid oxygen','RequiredAmount':1745,'ProvidedAmount':0,'Payment':2260},{'Name':'$medicaldiagnosticequipment_name;','Name_Localised':'Medical Diagnostic Equipment','RequiredAmount':12,'ProvidedAmount':0,'Payment':3609},{'Name':'$nonlethalweapons_name;','Name_Localised':'Non-Lethal Weapons','RequiredAmount':13,'ProvidedAmount':0,'Payment':2503},{'Name':'$polymers_name;','Name_Localised':'Polymers','RequiredAmount':517,'ProvidedAmount':0,'Payment':682},{'Name':'$powergenerators_name;','Name_Localised':'Power Generators','RequiredAmount':19,'ProvidedAmount':0,'Payment':3072},{'Name':'$semiconductors_name;','Name_Localised':'Semiconductors','RequiredAmount':67,'ProvidedAmount':0,'Payment':1526},{'Name':'$steel_name;','Name_Localised':'Steel','RequiredAmount':6749,'ProvidedAmount':0,'Payment':5057},{'Name':'$superconductors_name;','Name_Localised':'Superconductors','RequiredAmount':113,'ProvidedAmount':0,'Payment':7657},{'Name':'$titanium_name;','Name_Localised':'Titanium','RequiredAmount':5415,'ProvidedAmount':0,'Payment':5360},{'Name':'$water_name;','Name_Localised':'Water','RequiredAmount':709,'ProvidedAmount':0,'Payment':662},{'Name':'$waterpurifiers_name;','Name_Localised':'Water Purifiers','RequiredAmount':38,'ProvidedAmount':0,'Payment':849},{'Name':'$wine_name;','Name_Localised':'Wine','RequiredAmount':9001,'ProvidedAmount':0,'Payment':999999},{'Name':'$coffee_name;','Name_Localised':'Coffee','RequiredAmount':4096,'ProvidedAmount':0,'Payment':2048}]}
    plugin.journal_entry(cmdr=monitor.monitor.cmdr, is_beta=False, system="M7 Sector CG-X d1-90", station="$EXT_PANEL_ColonisationShip; Low Reach", entry=entry, state=None)

    assert plugin.this.queue.qsize() == 2   # Should be PushRequests for both SCS_PROGRESS_UPDATE and SCS_DATA_POPULATE

    pr = plugin.this.queue.get_nowait()
    assert pr
    assert pr.type == plugin.PushRequest.TYPE_SCS_DATA_POPULATE
    assert pr.cmdr == monitor.monitor.cmdr
    assert pr.station == "M7 Sector CG-X d1-90"

    ACTUAL_HTTP_PUT_POST_REQUESTS.clear()

    plugin.this.killswitches[plugin.KILLSWITCH_SCS_RECONCILE] = 'false'
    plugin.this.killswitches[plugin.KILLSWITCH_SCS_DATA_POPULATE] = 'false'
    plugin.process_item(pr)
    assert len(ACTUAL_HTTP_PUT_POST_REQUESTS) == 0

    plugin.this.killswitches[plugin.KILLSWITCH_SCS_DATA_POPULATE] = 'true'
    mock_data_systems_table = """{"spreadsheetId":"1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE","valueRanges":[{"range":"Data!A59:A1000","majorDimension":"ROWS","values":[["System"],["COL 285 SECTOR DT-E B26-9"],["HIP 94491"],["Col 285 Sector DT-E b26-2"],["Col 285 Sector AG-O d6-122"],["Nunki"],["27 PHI SAGITTARII"],["COL 285 SECTOR RJ-E A55-5"],["HIP 90504"],["Col 285 Sector CH-Z a57-3"],["Col 285 Sector GN-X A58-0"],["HIP 89535"],["COL 285 SECTOR JY-Y C14-15"],["COL 285 SECTOR HD-Z C14-22"],["COL 285 SECTOR UH-W B30-4"],["HIP 88440"],["COL 359 SECTOR OR-V D2-120"],["COL 359 SECTOR OR-V D2-47"],["COL 359 SECTOR YL-K B10-3"],["COL 359 SECTOR CS-I B11-7"],["COL 285 SECTOR JY-Y C14-15"],["HIP 94491"],["HIP 94491"],["HIP 94491"],["Col 359 Sector BJ-R c5-21"],["Col 359 Sector GP-P c6-31"],["Col 359 Sector GP-P c6-3"],["Col 359 Sector SX-T d3-48"],["COL 359 SECTOR LE-F B13-6"],["COL 359 SECTOR SX-T D3-133"],["Col 359 Sector OR-V d2-146"],["Pipe (bowl) Sector ZO-A b3"],["Col 359 Sector FP-P c6-18"],["Col 359 Sector GP-P c6-20"],["HIP 89573"],["Pipe (stem) Sector YJ-A c7"],["Col 359 Sector OR-V d2-146"],["Pipe (stem) Sector ZE-A d151"],["Pipe (stem) Sector BA-Z b3"],["HIP 85257"],["Pipe (stem) Sector ZE-A d101"],["Pipe (stem) Sector BA-Z b2"],["Pipe (stem) Sector ZE-A d151"],["HIP 85257"],["Pipe (stem) Sector YE-Z b1"],["Pipe (stem) Sector ZE-Z b4"],["Pipe (stem) Sector DL-X b1-0"],["Pipe (stem) Sector DL-X b1-7"],["Pipe (Stem) Sector GW-W C1-27"],["Pipe (stem) Sector GW-W c1-28"],["Pipe (stem) Sector ZE-A d89"],["Pipe (Stem) Sector BQ-Y d80"],["Pipe (stem) Sector IH-V c2-18"],["Pipe (stem) Sector DL-Y d106"],["Pipe (stem) Sector KC-V c2-22"],["Pipe (stem) Sector DL-Y d66"],["Pipe (stem) Sector LN-S b4-1"],["Pipe (stem) Sector JX-T b3-2"],["Pipe (stem) Sector DL-Y d17"],["Pipe (stem) Sector MN-T c3-13"],["Pipe (stem) Sector OI-T c3-19"],["Pipe (stem) Sector ZA-N b7-4"],["Pipe (stem) Sector DH-L b8-0"],["Pipe (stem) Sector DL-Y d112"],["Pipe (stem) Sector CQ-Y d59"],["Pipe (stem) Sector GW-W c1-6"],["Pipe (stem) Sector KC-V c2-1"],["Col 285 Sector UG-I b24-5"],["Pipe (stem) Sector DH-L b8-4"],["Snake Sector FB-X c1-1"],["Snake Sector UJ-Q b5-4"],["Pipe (stem) Sector KC-V c2-1"],["HIP 84930"],["Snake Sector XP-O b6-2"],["Snake Sector ZK-O b6-3"],["Pipe (stem) Sector JC-V c2-23"],["Col 285 Sector GY-H c10-14"],["Snake Sector PI-T c3-14"],["Snake Sector HR-W d1-105"],["Col 359 Sector EQ-O d6-124"],["Col 359 Sector IW-M d7-10"],["Col 359 Sector PX-E b27-6"],["Col 359 Sector QX-E b27-1"],["Col 359 Sector TD-D b28-2"],["Col 359 Sector IW-M d7-67"],["Col 359 Sector WJ-B b29-3"],["Col 359 Sector AQ-Z b29-0"],["Col 359 Sector IW-M d7-37"],["Col 359 Sector NX-Z c14-17"],["Col 359 Sector MC-L d8-22"],["Col 359 Sector IW-M d7-1"],["Col 359 Sector MC-L d8-111"],["Col 359 Sector JC-W b31-4"],["M7 Sector NE-W b3-0"],["M7 Sector YZ-Y d47"],["M7 Sector YZ-Y d18"],["M7 Sector UQ-S b5-0"],["M7 Sector WK-W c2-10"],["M7 Sector WK-W c2-7"],["M7 Sector YW-Q b6-2"],["M7 Sector CG-X d1-90"],["M7 Sector FY-O b7-3"],["M7 Sector JE-N b8-6"],["M7 Sector HS-S c4-26"],["M7 Sector HS-S c4-12"],["M7 Sector GM-V d2-107"],["M7 Sector VW-H b11-3"],["Col 359 Sector GL-D c13-2"],["M7 Sector LY-Q c5-16"],["M7 Sector GM-V d2-57"],["M7 Sector DJ-E b13-6"],["M7 Sector OE-P c6-4"],["M7 Sector CJ-E b13-0"],["M7 Sector OE-P c6-7"],["M7 Sector IA-B b15-6"],["M7 Sector IA-B b15-0"],["M7 Sector JS-T d3-131"],["M7 Sector QP-N c7-1"],["M7 Sector MG-Z b15-3"],["M7 Sector QM-X b16-5"],["M7 Sector UV-L C8-0"],["Arietis Sector BV-P b5-4"],["Pru Euq HY-Y b41-5"],["Pru Euq LE-X b42-4"],["Pru Euq JJ-X b42-6"],["Pru Euq NP-V b43-2"],["Pru Euq RV-T b44-6"],["R CrA Sector KC-V c2-22"],["Beta Coronae Austrinae"],["Pru Euq RV-T b44-5"],["M7 Sector VV-L c8-12"],["Col 285 Sector VO-N b21-0"],["Pru Euq VB-S b45-5"],["Pru Euq VB-S b45-1"],["Pru Euq ZD-I c23-14"],["Pru Euq YH-Q b46-3"],["Pru Euq LW-E d11-50"],["Pru Euq BZ-H c23-15"],["Pru Euq LW-E d11-59"],["Cephei Sector XO-A b2"],["Pru Euq CO-O b47-1"],["Pru Euq DK-G c24-1"],["Pru Euq JA-L b49-2"],["Pru Euq KA-L b49-5"],["Pru Euq PC-D d12-83"],["Pru Euq LW-E d11-61"],["Pru Euq OG-J b50-5"]]},{"range":"Data!A59:BD59","majorDimension":"ROWS","values":[["System","Building","Aluminium","Ceramic Composites","CMM Composite","Computer Components","Copper","Food Cartridges","Fruit and Vedge","Insulating Membrane","Liquid Oxygen","Medical Diagnostic Equipment","Non-Lethal Weapons","Polymers","Power Generators","Semiconductors","Steel","Superconductors","Titanium","Water","Water Purifiers","Land Enrichment Systems","Surface Stabilisers","Building Fabricators","Structural Regulators","Evacuation Shelter","Emergency Power Cells","Survival Equipment","Micro Controllers","Grain","Pesticides","Agri-Medicines","Crop Harvesters","Biowaste","Beer","Wine","Liquor","Battle Weapons","Reactive Armour","Thermal Cooling Units","Microbial Furnaces","Mineral Extractors","H.E. Suits","Robotics","Resonating Separators","Bioreducing Lichen","Geological Equipment","Muon Imager","Basic Medicines","Combat Stabilizers","Military Grade Fabrics","Advanced Catalysers","Animal Meat","Fish","Tea","Coffee"]]}]}"""
    __add_mocked_http_response(json.loads(mock_data_systems_table))
    plugin.process_item(pr)
    assert len(ACTUAL_HTTP_PUT_POST_REQUESTS) == 1

    req = ACTUAL_HTTP_PUT_POST_REQUESTS.pop(0)
    assert req[0] == "https://sheets.googleapis.com/v4/spreadsheets/1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE/values/Data!A159:BD159?valueInputOption=USER_ENTERED"
    assert req[1] == {"range": "Data!A159:BD159", "majorDimension": "ROWS", "values": [[None, None, 510, 515, 4319, 61, 247, 96, 52, 353, 1745, 12, 13, 517, 19, 67, 6749, 113, 5415, 709, 38, None, None, None, None, None, None, None, None, None, None, None, None, None, None, 9001, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, 4096]]}

    assert plugin.this.queue.qsize() == 1   # Should just be the SCS_PROGRESS_UPDATE one left
    pr = plugin.this.queue.get_nowait()
    assert pr
    assert pr.type == plugin.PushRequest.TYPE_SCS_PROGRESS_UPDATE
    assert pr.cmdr == monitor.monitor.cmdr
    assert pr.station == "M7 Sector CG-X d1-90"

def test_journal_entry_ColonisationContribution():
    plugin.this.sheet.systemsInProgress.append("M7 Sector CG-X d1-90")
    plugin.this.sheet.sheetFunctionality['SCS Offload'] = {
        "Delivery": False,
        "Timestamp": False
    }
    config.test_mom_feature_track_delivery = False

    entry = {'timestamp':'2025-04-13T08:36:25Z','event':'ColonisationContribution','MarketID':3956737026,'Contributions':[{'Name':'$Aluminium_name;','Name_Localised':'Aluminium','Amount':102},{'Name':'$CeramicComposites_name;','Name_Localised':'Ceramic Composites','Amount':503},{'Name':'$ComputerComponents_name;','Name_Localised':'Computer Components','Amount':52},{'Name':'$FoodCartridges_name;','Name_Localised':'Food Cartridges','Amount':20},{'Name':'$MedicalDiagnosticEquipment_name;','Name_Localised':'Medical Diagnostic Equipment','Amount':13},{'Name':'$NonLethalWeapons_name;','Name_Localised':'Non-Lethal Weapons','Amount':11},{'Name':'$PowerGenerators_name;','Name_Localised':'Power Generators','Amount':17},{'Name':'$WaterPurifiers_name;','Name_Localised':'Water Purifiers','Amount':34}]}
    plugin.journal_entry(cmdr=monitor.monitor.cmdr, is_beta=False, system="M7 Sector CG-X d1-90", station="$EXT_PANEL_ColonisationShip; Low Reach", entry=entry, state=None)

    assert plugin.this.queue.qsize() == 1

    pr = plugin.this.queue.get_nowait()
    assert pr
    assert pr.type == plugin.PushRequest.TYPE_SCS_SELL
    assert pr.cmdr == monitor.monitor.cmdr
    assert pr.station == "M7 Sector CG-X d1-90"

    ACTUAL_HTTP_PUT_POST_REQUESTS.clear()

    plugin.this.killswitches[plugin.KILLSWITCH_SCS_SELL] = 'false'
    plugin.process_item(pr)
    assert len(ACTUAL_HTTP_PUT_POST_REQUESTS) == 0

    plugin.this.killswitches[plugin.KILLSWITCH_SCS_SELL] = 'true'
    plugin.process_item(pr)
    assert len(ACTUAL_HTTP_PUT_POST_REQUESTS) == 8  # Delivery tracking disabled, so no formatting requests

    req = ACTUAL_HTTP_PUT_POST_REQUESTS.pop(0)
    assert req[0] == "https://sheets.googleapis.com/v4/spreadsheets/1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE/values/'SCS Offload'!A:A:append?valueInputOption=USER_ENTERED"
    assert req[1] == {"range": "'SCS Offload'!A:A", "majorDimension": "ROWS", "values": [["Aluminium", "M7 Sector CG-X d1-90", 102]]}
    req = ACTUAL_HTTP_PUT_POST_REQUESTS.pop(0)
    assert req[0] == "https://sheets.googleapis.com/v4/spreadsheets/1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE/values/'SCS Offload'!A:A:append?valueInputOption=USER_ENTERED"
    assert req[1] == {"range": "'SCS Offload'!A:A", "majorDimension": "ROWS", "values": [["Ceramic Composites", "M7 Sector CG-X d1-90", 503]]}
    req = ACTUAL_HTTP_PUT_POST_REQUESTS.pop(0)
    assert req[0] == "https://sheets.googleapis.com/v4/spreadsheets/1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE/values/'SCS Offload'!A:A:append?valueInputOption=USER_ENTERED"
    assert req[1] == {"range": "'SCS Offload'!A:A", "majorDimension": "ROWS", "values": [["Computer Components", "M7 Sector CG-X d1-90", 52]]}
    req = ACTUAL_HTTP_PUT_POST_REQUESTS.pop(0)
    assert req[0] == "https://sheets.googleapis.com/v4/spreadsheets/1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE/values/'SCS Offload'!A:A:append?valueInputOption=USER_ENTERED"
    assert req[1] == {"range": "'SCS Offload'!A:A", "majorDimension": "ROWS", "values": [["Food Cartridges", "M7 Sector CG-X d1-90", 20]]}
    req = ACTUAL_HTTP_PUT_POST_REQUESTS.pop(0)
    assert req[0] == "https://sheets.googleapis.com/v4/spreadsheets/1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE/values/'SCS Offload'!A:A:append?valueInputOption=USER_ENTERED"
    assert req[1] == {"range": "'SCS Offload'!A:A", "majorDimension": "ROWS", "values": [["Medical Diagnostic Equipment", "M7 Sector CG-X d1-90", 13]]}
    req = ACTUAL_HTTP_PUT_POST_REQUESTS.pop(0)
    assert req[0] == "https://sheets.googleapis.com/v4/spreadsheets/1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE/values/'SCS Offload'!A:A:append?valueInputOption=USER_ENTERED"
    assert req[1] == {"range": "'SCS Offload'!A:A", "majorDimension": "ROWS", "values": [["Non-Lethal Weapons", "M7 Sector CG-X d1-90", 11]]}
    req = ACTUAL_HTTP_PUT_POST_REQUESTS.pop(0)
    assert req[0] == "https://sheets.googleapis.com/v4/spreadsheets/1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE/values/'SCS Offload'!A:A:append?valueInputOption=USER_ENTERED"
    assert req[1] == {"range": "'SCS Offload'!A:A", "majorDimension": "ROWS", "values": [["Power Generators", "M7 Sector CG-X d1-90", 17]]}
    req = ACTUAL_HTTP_PUT_POST_REQUESTS.pop(0)
    assert req[0] == "https://sheets.googleapis.com/v4/spreadsheets/1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE/values/'SCS Offload'!A:A:append?valueInputOption=USER_ENTERED"
    assert req[1] == {"range": "'SCS Offload'!A:A", "majorDimension": "ROWS", "values": [["Water Purifiers", "M7 Sector CG-X d1-90", 34]]}

    plugin.this.sheet.sheetFunctionality['SCS Offload'] = {
        "Delivery": False,
        "Timestamp": True
    }
    ACTUAL_HTTP_PUT_POST_REQUESTS.clear()

    plugin.process_item(pr)
    assert len(ACTUAL_HTTP_PUT_POST_REQUESTS) == 8  # Delivery tracking disabled, so no formatting requests

    req = ACTUAL_HTTP_PUT_POST_REQUESTS.pop(0)
    assert req[0] == "https://sheets.googleapis.com/v4/spreadsheets/1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE/values/'SCS Offload'!A:A:append?valueInputOption=USER_ENTERED"
    assert req[1] == {"range": "'SCS Offload'!A:A", "majorDimension": "ROWS", "values": [["Aluminium", "M7 Sector CG-X d1-90", 102, None, "2025-04-13 08:36:25"]]}
    req = ACTUAL_HTTP_PUT_POST_REQUESTS.pop(0)
    assert req[0] == "https://sheets.googleapis.com/v4/spreadsheets/1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE/values/'SCS Offload'!A:A:append?valueInputOption=USER_ENTERED"
    assert req[1] == {"range": "'SCS Offload'!A:A", "majorDimension": "ROWS", "values": [["Ceramic Composites", "M7 Sector CG-X d1-90", 503, None, "2025-04-13 08:36:25"]]}
    req = ACTUAL_HTTP_PUT_POST_REQUESTS.pop(0)
    assert req[0] == "https://sheets.googleapis.com/v4/spreadsheets/1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE/values/'SCS Offload'!A:A:append?valueInputOption=USER_ENTERED"
    assert req[1] == {"range": "'SCS Offload'!A:A", "majorDimension": "ROWS", "values": [["Computer Components", "M7 Sector CG-X d1-90", 52, None, "2025-04-13 08:36:25"]]}
    req = ACTUAL_HTTP_PUT_POST_REQUESTS.pop(0)
    assert req[0] == "https://sheets.googleapis.com/v4/spreadsheets/1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE/values/'SCS Offload'!A:A:append?valueInputOption=USER_ENTERED"
    assert req[1] == {"range": "'SCS Offload'!A:A", "majorDimension": "ROWS", "values": [["Food Cartridges", "M7 Sector CG-X d1-90", 20, None, "2025-04-13 08:36:25"]]}
    req = ACTUAL_HTTP_PUT_POST_REQUESTS.pop(0)
    assert req[0] == "https://sheets.googleapis.com/v4/spreadsheets/1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE/values/'SCS Offload'!A:A:append?valueInputOption=USER_ENTERED"
    assert req[1] == {"range": "'SCS Offload'!A:A", "majorDimension": "ROWS", "values": [["Medical Diagnostic Equipment", "M7 Sector CG-X d1-90", 13, None, "2025-04-13 08:36:25"]]}
    req = ACTUAL_HTTP_PUT_POST_REQUESTS.pop(0)
    assert req[0] == "https://sheets.googleapis.com/v4/spreadsheets/1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE/values/'SCS Offload'!A:A:append?valueInputOption=USER_ENTERED"
    assert req[1] == {"range": "'SCS Offload'!A:A", "majorDimension": "ROWS", "values": [["Non-Lethal Weapons", "M7 Sector CG-X d1-90", 11, None, "2025-04-13 08:36:25"]]}
    req = ACTUAL_HTTP_PUT_POST_REQUESTS.pop(0)
    assert req[0] == "https://sheets.googleapis.com/v4/spreadsheets/1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE/values/'SCS Offload'!A:A:append?valueInputOption=USER_ENTERED"
    assert req[1] == {"range": "'SCS Offload'!A:A", "majorDimension": "ROWS", "values": [["Power Generators", "M7 Sector CG-X d1-90", 17, None, "2025-04-13 08:36:25"]]}
    req = ACTUAL_HTTP_PUT_POST_REQUESTS.pop(0)
    assert req[0] == "https://sheets.googleapis.com/v4/spreadsheets/1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE/values/'SCS Offload'!A:A:append?valueInputOption=USER_ENTERED"
    assert req[1] == {"range": "'SCS Offload'!A:A", "majorDimension": "ROWS", "values": [["Water Purifiers", "M7 Sector CG-X d1-90", 34, None, "2025-04-13 08:36:25"]]}

    plugin.this.sheet.sheetFunctionality['SCS Offload'] = {
        "Delivery": True,
        "Timestamp": False
    }
    config.test_mom_feature_track_delivery = True
    ACTUAL_HTTP_PUT_POST_REQUESTS.clear()
    for idx in range(71, 79, 1):
        mock_new_scs_entry_response = """{"spreadsheetId":"1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE","tableRange":"'SCS Offload'!A1:E""" + str(idx) + """","updates":{"spreadsheetId":"1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE","updatedRange":"'SCS Offload'!A""" + str(idx+1) + ":D" + str(idx+1) + """","updatedRows":1,"updatedColumns":3,"updatedCells":3}}"""
        __add_mocked_http_response(json.loads(mock_new_scs_entry_response), requests.codes.OK)                           # Debug logging + status_check in insert_data
        __add_mocked_http_response(json.loads(mock_new_scs_entry_response))                                              # Check for 'updates' in add_to_scs_sheet
        __add_mocked_http_response(json.loads("""{"body": "Some reasponse we don't care about"}"""), requests.codes.OK)  # Debug logging + status_check in update_data
        __add_mocked_http_response(json.loads("""{"body": "???"}"""), requests.codes.OK)                                 # Debug logging + status_check in update_data
    plugin.process_item(pr)
    assert len(ACTUAL_HTTP_PUT_POST_REQUESTS) == 8 * 2 # 1x Actual update to SCS Offload, 1x Formatting update

    req = ACTUAL_HTTP_PUT_POST_REQUESTS.pop(0)
    assert req[0] == "https://sheets.googleapis.com/v4/spreadsheets/1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE/values/'SCS Offload'!A:A:append?valueInputOption=USER_ENTERED"
    assert req[1] == {"range": "'SCS Offload'!A:A", "majorDimension": "ROWS", "values": [["Aluminium", "M7 Sector CG-X d1-90", 102, True]]}
    req = ACTUAL_HTTP_PUT_POST_REQUESTS.pop(0)
    assert req[0] == "https://sheets.googleapis.com/v4/spreadsheets/1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE:batchUpdate"
    assert req[1] == {"requests": [{ "repeatCell": { "range": {"sheetId": 565128439, "startRowIndex": 71, "endRowIndex": 72, "startColumnIndex": 3, "endColumnIndex": 4}, "cell": {"dataValidation": {"condition": {"type": "BOOLEAN"}}}, "fields": "dataValidation.condition"}}]}
    
    req = ACTUAL_HTTP_PUT_POST_REQUESTS.pop(0)
    assert req[0] == "https://sheets.googleapis.com/v4/spreadsheets/1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE/values/'SCS Offload'!A:A:append?valueInputOption=USER_ENTERED"
    assert req[1] == {"range": "'SCS Offload'!A:A", "majorDimension": "ROWS", "values": [["Ceramic Composites", "M7 Sector CG-X d1-90", 503, True]]}
    req = ACTUAL_HTTP_PUT_POST_REQUESTS.pop(0)
    assert req[0] == "https://sheets.googleapis.com/v4/spreadsheets/1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE:batchUpdate"
    assert req[1] == {"requests": [{ "repeatCell": { "range": {"sheetId": 565128439, "startRowIndex": 72, "endRowIndex": 73, "startColumnIndex": 3, "endColumnIndex": 4}, "cell": {"dataValidation": {"condition": {"type": "BOOLEAN"}}}, "fields": "dataValidation.condition"}}]}
    
    req = ACTUAL_HTTP_PUT_POST_REQUESTS.pop(0)
    assert req[0] == "https://sheets.googleapis.com/v4/spreadsheets/1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE/values/'SCS Offload'!A:A:append?valueInputOption=USER_ENTERED"
    assert req[1] == {"range": "'SCS Offload'!A:A", "majorDimension": "ROWS", "values": [["Computer Components", "M7 Sector CG-X d1-90", 52, True]]}
    req = ACTUAL_HTTP_PUT_POST_REQUESTS.pop(0)
    assert req[0] == "https://sheets.googleapis.com/v4/spreadsheets/1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE:batchUpdate"
    assert req[1] == {"requests": [{ "repeatCell": { "range": {"sheetId": 565128439, "startRowIndex": 73, "endRowIndex": 74, "startColumnIndex": 3, "endColumnIndex": 4}, "cell": {"dataValidation": {"condition": {"type": "BOOLEAN"}}}, "fields": "dataValidation.condition"}}]}

    req = ACTUAL_HTTP_PUT_POST_REQUESTS.pop(0)
    assert req[0] == "https://sheets.googleapis.com/v4/spreadsheets/1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE/values/'SCS Offload'!A:A:append?valueInputOption=USER_ENTERED"
    assert req[1] == {"range": "'SCS Offload'!A:A", "majorDimension": "ROWS", "values": [["Food Cartridges", "M7 Sector CG-X d1-90", 20, True]]}
    req = ACTUAL_HTTP_PUT_POST_REQUESTS.pop(0)
    assert req[0] == "https://sheets.googleapis.com/v4/spreadsheets/1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE:batchUpdate"
    assert req[1] == {"requests": [{ "repeatCell": { "range": {"sheetId": 565128439, "startRowIndex": 74, "endRowIndex": 75, "startColumnIndex": 3, "endColumnIndex": 4}, "cell": {"dataValidation": {"condition": {"type": "BOOLEAN"}}}, "fields": "dataValidation.condition"}}]}

    req = ACTUAL_HTTP_PUT_POST_REQUESTS.pop(0)
    assert req[0] == "https://sheets.googleapis.com/v4/spreadsheets/1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE/values/'SCS Offload'!A:A:append?valueInputOption=USER_ENTERED"
    assert req[1] == {"range": "'SCS Offload'!A:A", "majorDimension": "ROWS", "values": [["Medical Diagnostic Equipment", "M7 Sector CG-X d1-90", 13, True]]}
    req = ACTUAL_HTTP_PUT_POST_REQUESTS.pop(0)
    assert req[0] == "https://sheets.googleapis.com/v4/spreadsheets/1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE:batchUpdate"
    assert req[1] == {"requests": [{ "repeatCell": { "range": {"sheetId": 565128439, "startRowIndex": 75, "endRowIndex": 76, "startColumnIndex": 3, "endColumnIndex": 4}, "cell": {"dataValidation": {"condition": {"type": "BOOLEAN"}}}, "fields": "dataValidation.condition"}}]}

    req = ACTUAL_HTTP_PUT_POST_REQUESTS.pop(0)
    assert req[0] == "https://sheets.googleapis.com/v4/spreadsheets/1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE/values/'SCS Offload'!A:A:append?valueInputOption=USER_ENTERED"
    assert req[1] == {"range": "'SCS Offload'!A:A", "majorDimension": "ROWS", "values": [["Non-Lethal Weapons", "M7 Sector CG-X d1-90", 11, True]]}
    req = ACTUAL_HTTP_PUT_POST_REQUESTS.pop(0)
    assert req[0] == "https://sheets.googleapis.com/v4/spreadsheets/1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE:batchUpdate"
    assert req[1] == {"requests": [{ "repeatCell": { "range": {"sheetId": 565128439, "startRowIndex": 76, "endRowIndex": 77, "startColumnIndex": 3, "endColumnIndex": 4}, "cell": {"dataValidation": {"condition": {"type": "BOOLEAN"}}}, "fields": "dataValidation.condition"}}]}

    req = ACTUAL_HTTP_PUT_POST_REQUESTS.pop(0)
    assert req[0] == "https://sheets.googleapis.com/v4/spreadsheets/1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE/values/'SCS Offload'!A:A:append?valueInputOption=USER_ENTERED"
    assert req[1] == {"range": "'SCS Offload'!A:A", "majorDimension": "ROWS", "values": [["Power Generators", "M7 Sector CG-X d1-90", 17, True]]}
    req = ACTUAL_HTTP_PUT_POST_REQUESTS.pop(0)
    assert req[0] == "https://sheets.googleapis.com/v4/spreadsheets/1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE:batchUpdate"
    assert req[1] == {"requests": [{ "repeatCell": { "range": {"sheetId": 565128439, "startRowIndex": 77, "endRowIndex": 78, "startColumnIndex": 3, "endColumnIndex": 4}, "cell": {"dataValidation": {"condition": {"type": "BOOLEAN"}}}, "fields": "dataValidation.condition"}}]}

    req = ACTUAL_HTTP_PUT_POST_REQUESTS.pop(0)
    assert req[0] == "https://sheets.googleapis.com/v4/spreadsheets/1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE/values/'SCS Offload'!A:A:append?valueInputOption=USER_ENTERED"
    assert req[1] == {"range": "'SCS Offload'!A:A", "majorDimension": "ROWS", "values": [["Water Purifiers", "M7 Sector CG-X d1-90", 34, True]]}
    req = ACTUAL_HTTP_PUT_POST_REQUESTS.pop(0)
    assert req[0] == "https://sheets.googleapis.com/v4/spreadsheets/1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE:batchUpdate"
    assert req[1] == {"requests": [{ "repeatCell": { "range": {"sheetId": 565128439, "startRowIndex": 78, "endRowIndex": 79, "startColumnIndex": 3, "endColumnIndex": 4}, "cell": {"dataValidation": {"condition": {"type": "BOOLEAN"}}}, "fields": "dataValidation.condition"}}]}

    plugin.this.sheet.sheetFunctionality['SCS Offload'] = {
        "Delivery": True,
        "Timestamp": True
    }
    config.test_mom_feature_track_delivery = True
    ACTUAL_HTTP_PUT_POST_REQUESTS.clear()
    for idx in range(71, 79, 1):
        mock_new_scs_entry_response = """{"spreadsheetId":"1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE","tableRange":"'SCS Offload'!A1:E""" + str(idx) + """","updates":{"spreadsheetId":"1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE","updatedRange":"'SCS Offload'!A""" + str(idx+1) + ":D" + str(idx+1) + """","updatedRows":1,"updatedColumns":3,"updatedCells":3}}"""
        __add_mocked_http_response(json.loads(mock_new_scs_entry_response), requests.codes.OK)                           # Debug logging + status_check in insert_data
        __add_mocked_http_response(json.loads(mock_new_scs_entry_response))                                              # Check for 'updates' in add_to_scs_sheet
        __add_mocked_http_response(json.loads("""{"body": "Some reasponse we don't care about"}"""), requests.codes.OK)  # Debug logging + status_check in update_data
        __add_mocked_http_response(json.loads("""{"body": "???"}"""), requests.codes.OK)                                 # Debug logging + status_check in update_data
    plugin.process_item(pr)
    assert len(ACTUAL_HTTP_PUT_POST_REQUESTS) == 8 * 2 # 1x Actual update to SCS Offload, 1x Formatting update

    req = ACTUAL_HTTP_PUT_POST_REQUESTS.pop(0)
    assert req[0] == "https://sheets.googleapis.com/v4/spreadsheets/1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE/values/'SCS Offload'!A:A:append?valueInputOption=USER_ENTERED"
    assert req[1] == {"range": "'SCS Offload'!A:A", "majorDimension": "ROWS", "values": [["Aluminium", "M7 Sector CG-X d1-90", 102, True, "2025-04-13 08:36:25"]]}
    req = ACTUAL_HTTP_PUT_POST_REQUESTS.pop(0)
    assert req[0] == "https://sheets.googleapis.com/v4/spreadsheets/1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE:batchUpdate"
    assert req[1] == {"requests": [{ "repeatCell": { "range": {"sheetId": 565128439, "startRowIndex": 71, "endRowIndex": 72, "startColumnIndex": 3, "endColumnIndex": 4}, "cell": {"dataValidation": {"condition": {"type": "BOOLEAN"}}}, "fields": "dataValidation.condition"}}]}
    
    req = ACTUAL_HTTP_PUT_POST_REQUESTS.pop(0)
    assert req[0] == "https://sheets.googleapis.com/v4/spreadsheets/1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE/values/'SCS Offload'!A:A:append?valueInputOption=USER_ENTERED"
    assert req[1] == {"range": "'SCS Offload'!A:A", "majorDimension": "ROWS", "values": [["Ceramic Composites", "M7 Sector CG-X d1-90", 503, True, "2025-04-13 08:36:25"]]}
    req = ACTUAL_HTTP_PUT_POST_REQUESTS.pop(0)
    assert req[0] == "https://sheets.googleapis.com/v4/spreadsheets/1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE:batchUpdate"
    assert req[1] == {"requests": [{ "repeatCell": { "range": {"sheetId": 565128439, "startRowIndex": 72, "endRowIndex": 73, "startColumnIndex": 3, "endColumnIndex": 4}, "cell": {"dataValidation": {"condition": {"type": "BOOLEAN"}}}, "fields": "dataValidation.condition"}}]}
    
    req = ACTUAL_HTTP_PUT_POST_REQUESTS.pop(0)
    assert req[0] == "https://sheets.googleapis.com/v4/spreadsheets/1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE/values/'SCS Offload'!A:A:append?valueInputOption=USER_ENTERED"
    assert req[1] == {"range": "'SCS Offload'!A:A", "majorDimension": "ROWS", "values": [["Computer Components", "M7 Sector CG-X d1-90", 52, True, "2025-04-13 08:36:25"]]}
    req = ACTUAL_HTTP_PUT_POST_REQUESTS.pop(0)
    assert req[0] == "https://sheets.googleapis.com/v4/spreadsheets/1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE:batchUpdate"
    assert req[1] == {"requests": [{ "repeatCell": { "range": {"sheetId": 565128439, "startRowIndex": 73, "endRowIndex": 74, "startColumnIndex": 3, "endColumnIndex": 4}, "cell": {"dataValidation": {"condition": {"type": "BOOLEAN"}}}, "fields": "dataValidation.condition"}}]}

    req = ACTUAL_HTTP_PUT_POST_REQUESTS.pop(0)
    assert req[0] == "https://sheets.googleapis.com/v4/spreadsheets/1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE/values/'SCS Offload'!A:A:append?valueInputOption=USER_ENTERED"
    assert req[1] == {"range": "'SCS Offload'!A:A", "majorDimension": "ROWS", "values": [["Food Cartridges", "M7 Sector CG-X d1-90", 20, True, "2025-04-13 08:36:25"]]}
    req = ACTUAL_HTTP_PUT_POST_REQUESTS.pop(0)
    assert req[0] == "https://sheets.googleapis.com/v4/spreadsheets/1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE:batchUpdate"
    assert req[1] == {"requests": [{ "repeatCell": { "range": {"sheetId": 565128439, "startRowIndex": 74, "endRowIndex": 75, "startColumnIndex": 3, "endColumnIndex": 4}, "cell": {"dataValidation": {"condition": {"type": "BOOLEAN"}}}, "fields": "dataValidation.condition"}}]}

    req = ACTUAL_HTTP_PUT_POST_REQUESTS.pop(0)
    assert req[0] == "https://sheets.googleapis.com/v4/spreadsheets/1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE/values/'SCS Offload'!A:A:append?valueInputOption=USER_ENTERED"
    assert req[1] == {"range": "'SCS Offload'!A:A", "majorDimension": "ROWS", "values": [["Medical Diagnostic Equipment", "M7 Sector CG-X d1-90", 13, True, "2025-04-13 08:36:25"]]}
    req = ACTUAL_HTTP_PUT_POST_REQUESTS.pop(0)
    assert req[0] == "https://sheets.googleapis.com/v4/spreadsheets/1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE:batchUpdate"
    assert req[1] == {"requests": [{ "repeatCell": { "range": {"sheetId": 565128439, "startRowIndex": 75, "endRowIndex": 76, "startColumnIndex": 3, "endColumnIndex": 4}, "cell": {"dataValidation": {"condition": {"type": "BOOLEAN"}}}, "fields": "dataValidation.condition"}}]}

    req = ACTUAL_HTTP_PUT_POST_REQUESTS.pop(0)
    assert req[0] == "https://sheets.googleapis.com/v4/spreadsheets/1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE/values/'SCS Offload'!A:A:append?valueInputOption=USER_ENTERED"
    assert req[1] == {"range": "'SCS Offload'!A:A", "majorDimension": "ROWS", "values": [["Non-Lethal Weapons", "M7 Sector CG-X d1-90", 11, True, "2025-04-13 08:36:25"]]}
    req = ACTUAL_HTTP_PUT_POST_REQUESTS.pop(0)
    assert req[0] == "https://sheets.googleapis.com/v4/spreadsheets/1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE:batchUpdate"
    assert req[1] == {"requests": [{ "repeatCell": { "range": {"sheetId": 565128439, "startRowIndex": 76, "endRowIndex": 77, "startColumnIndex": 3, "endColumnIndex": 4}, "cell": {"dataValidation": {"condition": {"type": "BOOLEAN"}}}, "fields": "dataValidation.condition"}}]}

    req = ACTUAL_HTTP_PUT_POST_REQUESTS.pop(0)
    assert req[0] == "https://sheets.googleapis.com/v4/spreadsheets/1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE/values/'SCS Offload'!A:A:append?valueInputOption=USER_ENTERED"
    assert req[1] == {"range": "'SCS Offload'!A:A", "majorDimension": "ROWS", "values": [["Power Generators", "M7 Sector CG-X d1-90", 17, True, "2025-04-13 08:36:25"]]}
    req = ACTUAL_HTTP_PUT_POST_REQUESTS.pop(0)
    assert req[0] == "https://sheets.googleapis.com/v4/spreadsheets/1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE:batchUpdate"
    assert req[1] == {"requests": [{ "repeatCell": { "range": {"sheetId": 565128439, "startRowIndex": 77, "endRowIndex": 78, "startColumnIndex": 3, "endColumnIndex": 4}, "cell": {"dataValidation": {"condition": {"type": "BOOLEAN"}}}, "fields": "dataValidation.condition"}}]}

    req = ACTUAL_HTTP_PUT_POST_REQUESTS.pop(0)
    assert req[0] == "https://sheets.googleapis.com/v4/spreadsheets/1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE/values/'SCS Offload'!A:A:append?valueInputOption=USER_ENTERED"
    assert req[1] == {"range": "'SCS Offload'!A:A", "majorDimension": "ROWS", "values": [["Water Purifiers", "M7 Sector CG-X d1-90", 34, True, "2025-04-13 08:36:25"]]}
    req = ACTUAL_HTTP_PUT_POST_REQUESTS.pop(0)
    assert req[0] == "https://sheets.googleapis.com/v4/spreadsheets/1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE:batchUpdate"
    assert req[1] == {"requests": [{ "repeatCell": { "range": {"sheetId": 565128439, "startRowIndex": 78, "endRowIndex": 79, "startColumnIndex": 3, "endColumnIndex": 4}, "cell": {"dataValidation": {"condition": {"type": "BOOLEAN"}}}, "fields": "dataValidation.condition"}}]}

def test_journal_entry_ColonisationBeaconDeployed():
    #add_in_progress_scs_system
    entry = { "timestamp":"2025-04-14T06:47:06Z", "event":"ColonisationBeaconDeployed" }
    plugin.journal_entry(cmdr=monitor.monitor.cmdr, is_beta=False, system="M7 Sector GM-V d2-107", station=None, entry=entry, state=None)

    assert plugin.this.queue.qsize() == 1
    pr = plugin.this.queue.get_nowait()
    assert pr
    assert pr.type == plugin.PushRequest.TYPE_SCS_SYSTEM_ADD
    assert pr.cmdr == monitor.monitor.cmdr
    assert pr.station == "M7 Sector GM-V d2-107"

    # No killswitch on this one ... should there be ?
    #plugin.this.killswitches[plugin.KILLSWITCH_SCS_RECONCILE] = 'false'
    #plugin.process_item(pr)
    # TODO: How do we assert that this did, in fact, do nothing

    # First, lets assume the system is already known to us
    mock_system_info_systems = """{"range":"'System Info'!A1:A1000","majorDimension":"ROWS","values":[["System"],["COL 285 SECTOR DT-E B26-9"],["HIP 94491"],["Col 285 Sector DT-E b26-2"],["Col 285 Sector AG-O d6-122"],["Nunki"],["27 PHI SAGITTARII"],["COL 285 SECTOR RJ-E A55-5"],["HIP 90504"],["Col 285 Sector CH-Z a57-3"],["Col 285 Sector GN-X A58-0"],["HIP 89535"],["COL 285 SECTOR JY-Y C14-15"],["COL 285 SECTOR HD-Z C14-22"],["COL 285 SECTOR UH-W B30-4"],["HIP 88440"],["COL 359 SECTOR OR-V D2-120"],["COL 359 SECTOR OR-V D2-47"],["COL 359 SECTOR YL-K B10-3"],["COL 359 SECTOR CS-I B11-7"],["COL 285 SECTOR JY-Y C14-15"],["HIP 94491"],["HIP 94491"],["HIP 94491"],["Col 359 Sector BJ-R c5-21"],["Col 359 Sector GP-P c6-31"],["Col 359 Sector GP-P c6-3"],["Col 359 Sector SX-T d3-48"],["COL 359 SECTOR LE-F B13-6"],["COL 359 SECTOR SX-T D3-133"],["Col 359 Sector OR-V d2-146"],["Pipe (bowl) Sector ZO-A b3"],["Col 359 Sector FP-P c6-18"],["Col 359 Sector GP-P c6-20"],["HIP 89573"],["Pipe (stem) Sector YJ-A c7"],["Col 359 Sector OR-V d2-146"],["Pipe (stem) Sector ZE-A d151"],["Pipe (stem) Sector BA-Z b3"],["HIP 85257"],["Pipe (stem) Sector ZE-A d101"],["Pipe (stem) Sector BA-Z b2"],["Pipe (stem) Sector ZE-A d151"],["HIP 85257"],["Pipe (stem) Sector YE-Z b1"],["Pipe (stem) Sector ZE-Z b4"],["Pipe (stem) Sector DL-X b1-0"],["Pipe (stem) Sector DL-X b1-7"],["Pipe (Stem) Sector GW-W C1-27"],["Pipe (stem) Sector GW-W c1-28"],["Pipe (stem) Sector ZE-A d89"],["Pipe (Stem) Sector BQ-Y d80"],["Pipe (stem) Sector IH-V c2-18"],["Pipe (stem) Sector DL-Y d106"],["Pipe (stem) Sector KC-V c2-22"],["Pipe (stem) Sector DL-Y d66"],["Pipe (stem) Sector LN-S b4-1"],["Pipe (stem) Sector JX-T b3-2"],["Pipe (stem) Sector DL-Y d17"],["Pipe (stem) Sector MN-T c3-13"],["Pipe (stem) Sector OI-T c3-19"],["Pipe (stem) Sector ZA-N b7-4"],["Pipe (stem) Sector DH-L b8-0"],["Pipe (stem) Sector DL-Y d112"],["Pipe (stem) Sector CQ-Y d59"],["Pipe (stem) Sector GW-W c1-6"],["Pipe (stem) Sector KC-V c2-1"],["Col 285 Sector UG-I b24-5"],["Pipe (stem) Sector DH-L b8-4"],["Snake Sector FB-X c1-1"],["Snake Sector UJ-Q b5-4"],["Pipe (stem) Sector KC-V c2-1"],["HIP 84930"],["Snake Sector XP-O b6-2"],["Snake Sector ZK-O b6-3"],["Pipe (stem) Sector JC-V c2-23"],["Col 285 Sector GY-H c10-14"],["Snake Sector PI-T c3-14"],["Snake Sector HR-W d1-105"],["Col 359 Sector EQ-O d6-124"],["Col 359 Sector IW-M d7-10"],["Col 359 Sector PX-E b27-6"],["Col 359 Sector QX-E b27-1"],["Col 359 Sector TD-D b28-2"],["Col 359 Sector IW-M d7-67"],["Col 359 Sector WJ-B b29-3"],["Col 359 Sector AQ-Z b29-0"],["Col 359 Sector IW-M d7-37"],["Col 359 Sector NX-Z c14-17"],["Col 359 Sector MC-L d8-22"],["Col 359 Sector IW-M d7-1"],["Col 359 Sector MC-L d8-111"],["Col 359 Sector JC-W b31-4"],["M7 Sector NE-W b3-0"],["M7 Sector YZ-Y d47"],["M7 Sector YZ-Y d18"],["M7 Sector UQ-S b5-0"],["M7 Sector WK-W c2-10"],["M7 Sector WK-W c2-7"],["M7 Sector YW-Q b6-2"],["M7 Sector CG-X d1-90"],["M7 Sector FY-O b7-3"],["M7 Sector JE-N b8-6"],["M7 Sector HS-S c4-26"],["M7 Sector HS-S c4-12"],["M7 Sector GM-V d2-107"],["M7 Sector VW-H b11-3"],["Col 359 Sector GL-D c13-2"],["M7 Sector LY-Q c5-16"],["M7 Sector GM-V d2-57"],["M7 Sector DJ-E b13-6"],["M7 Sector OE-P c6-4"],["M7 Sector CJ-E b13-0"],["M7 Sector OE-P c6-7"],["M7 Sector IA-B b15-6"],["M7 Sector IA-B b15-0"],["M7 Sector JS-T d3-131"],["M7 Sector QP-N c7-1"],["M7 Sector MG-Z b15-3"],["M7 Sector QM-X b16-5"],["M7 Sector UV-L C8-0"],["Arietis Sector BV-P b5-4"],["Pru Euq HY-Y b41-5"],["Pru Euq LE-X b42-4"],["Pru Euq JJ-X b42-6"],["Pru Euq NP-V b43-2"],["Pru Euq RV-T b44-6"],["R CrA Sector KC-V c2-22"],["Beta Coronae Austrinae"],["Pru Euq RV-T b44-5"],["M7 Sector VV-L c8-12"],["Col 285 Sector VO-N b21-0"],["Pru Euq VB-S b45-5"],["Pru Euq VB-S b45-1"],["Pru Euq ZD-I c23-14"],["Pru Euq YH-Q b46-3"],["Pru Euq LW-E d11-50"],["Pru Euq BZ-H c23-15"],["Pru Euq LW-E d11-59"],["Cephei Sector XO-A b2"],["Pru Euq CO-O b47-1"],["Pru Euq DK-G c24-1"],["Pru Euq JA-L b49-2"]]}"""
    __add_mocked_http_response(json.loads(mock_system_info_systems))
    ACTUAL_HTTP_PUT_POST_REQUESTS.clear()
    plugin.process_item(pr)

    assert len(ACTUAL_HTTP_PUT_POST_REQUESTS) == 0

    # Then, lets assume its not known
    mock_system_info_systems = """{"range":"'System Info'!A1:A1000","majorDimension":"ROWS","values":[["System"],["COL 285 SECTOR DT-E B26-9"],["HIP 94491"],["Col 285 Sector DT-E b26-2"],["Col 285 Sector AG-O d6-122"],["Nunki"],["27 PHI SAGITTARII"],["COL 285 SECTOR RJ-E A55-5"],["HIP 90504"],["Col 285 Sector CH-Z a57-3"],["Col 285 Sector GN-X A58-0"],["HIP 89535"],["COL 285 SECTOR JY-Y C14-15"],["COL 285 SECTOR HD-Z C14-22"],["COL 285 SECTOR UH-W B30-4"],["HIP 88440"],["COL 359 SECTOR OR-V D2-120"],["COL 359 SECTOR OR-V D2-47"],["COL 359 SECTOR YL-K B10-3"],["COL 359 SECTOR CS-I B11-7"],["COL 285 SECTOR JY-Y C14-15"],["HIP 94491"],["HIP 94491"],["HIP 94491"],["Col 359 Sector BJ-R c5-21"],["Col 359 Sector GP-P c6-31"],["Col 359 Sector GP-P c6-3"],["Col 359 Sector SX-T d3-48"],["COL 359 SECTOR LE-F B13-6"],["COL 359 SECTOR SX-T D3-133"],["Col 359 Sector OR-V d2-146"],["Pipe (bowl) Sector ZO-A b3"],["Col 359 Sector FP-P c6-18"],["Col 359 Sector GP-P c6-20"],["HIP 89573"],["Pipe (stem) Sector YJ-A c7"],["Col 359 Sector OR-V d2-146"],["Pipe (stem) Sector ZE-A d151"],["Pipe (stem) Sector BA-Z b3"],["HIP 85257"],["Pipe (stem) Sector ZE-A d101"],["Pipe (stem) Sector BA-Z b2"],["Pipe (stem) Sector ZE-A d151"],["HIP 85257"],["Pipe (stem) Sector YE-Z b1"],["Pipe (stem) Sector ZE-Z b4"],["Pipe (stem) Sector DL-X b1-0"],["Pipe (stem) Sector DL-X b1-7"],["Pipe (Stem) Sector GW-W C1-27"],["Pipe (stem) Sector GW-W c1-28"],["Pipe (stem) Sector ZE-A d89"],["Pipe (Stem) Sector BQ-Y d80"],["Pipe (stem) Sector IH-V c2-18"],["Pipe (stem) Sector DL-Y d106"],["Pipe (stem) Sector KC-V c2-22"],["Pipe (stem) Sector DL-Y d66"],["Pipe (stem) Sector LN-S b4-1"],["Pipe (stem) Sector JX-T b3-2"],["Pipe (stem) Sector DL-Y d17"],["Pipe (stem) Sector MN-T c3-13"],["Pipe (stem) Sector OI-T c3-19"],["Pipe (stem) Sector ZA-N b7-4"],["Pipe (stem) Sector DH-L b8-0"],["Pipe (stem) Sector DL-Y d112"],["Pipe (stem) Sector CQ-Y d59"],["Pipe (stem) Sector GW-W c1-6"],["Pipe (stem) Sector KC-V c2-1"],["Col 285 Sector UG-I b24-5"],["Pipe (stem) Sector DH-L b8-4"],["Snake Sector FB-X c1-1"],["Snake Sector UJ-Q b5-4"],["Pipe (stem) Sector KC-V c2-1"],["HIP 84930"],["Snake Sector XP-O b6-2"],["Snake Sector ZK-O b6-3"],["Pipe (stem) Sector JC-V c2-23"],["Col 285 Sector GY-H c10-14"],["Snake Sector PI-T c3-14"],["Snake Sector HR-W d1-105"],["Col 359 Sector EQ-O d6-124"],["Col 359 Sector IW-M d7-10"],["Col 359 Sector PX-E b27-6"],["Col 359 Sector QX-E b27-1"],["Col 359 Sector TD-D b28-2"],["Col 359 Sector IW-M d7-67"],["Col 359 Sector WJ-B b29-3"],["Col 359 Sector AQ-Z b29-0"],["Col 359 Sector IW-M d7-37"],["Col 359 Sector NX-Z c14-17"],["Col 359 Sector MC-L d8-22"],["Col 359 Sector IW-M d7-1"],["Col 359 Sector MC-L d8-111"],["Col 359 Sector JC-W b31-4"],["M7 Sector NE-W b3-0"],["M7 Sector YZ-Y d47"],["M7 Sector YZ-Y d18"],["M7 Sector UQ-S b5-0"],["M7 Sector WK-W c2-10"],["M7 Sector WK-W c2-7"],["M7 Sector YW-Q b6-2"],["M7 Sector CG-X d1-90"],["M7 Sector FY-O b7-3"],["M7 Sector JE-N b8-6"],["M7 Sector HS-S c4-26"],["M7 Sector HS-S c4-12"],["M7 Sector VW-H b11-3"],["Col 359 Sector GL-D c13-2"],["M7 Sector LY-Q c5-16"],["M7 Sector GM-V d2-57"],["M7 Sector DJ-E b13-6"],["M7 Sector OE-P c6-4"],["M7 Sector CJ-E b13-0"],["M7 Sector OE-P c6-7"],["M7 Sector IA-B b15-6"],["M7 Sector IA-B b15-0"],["M7 Sector JS-T d3-131"],["M7 Sector QP-N c7-1"],["M7 Sector MG-Z b15-3"],["M7 Sector QM-X b16-5"],["M7 Sector UV-L C8-0"],["Arietis Sector BV-P b5-4"],["Pru Euq HY-Y b41-5"],["Pru Euq LE-X b42-4"],["Pru Euq JJ-X b42-6"],["Pru Euq NP-V b43-2"],["Pru Euq RV-T b44-6"],["R CrA Sector KC-V c2-22"],["Beta Coronae Austrinae"],["Pru Euq RV-T b44-5"],["M7 Sector VV-L c8-12"],["Col 285 Sector VO-N b21-0"],["Pru Euq VB-S b45-5"],["Pru Euq VB-S b45-1"],["Pru Euq ZD-I c23-14"],["Pru Euq YH-Q b46-3"],["Pru Euq LW-E d11-50"],["Pru Euq BZ-H c23-15"],["Pru Euq LW-E d11-59"],["Cephei Sector XO-A b2"],["Pru Euq CO-O b47-1"],["Pru Euq DK-G c24-1"],["Pru Euq JA-L b49-2"]]}"""
    __add_mocked_http_response(json.loads(mock_system_info_systems))
    ACTUAL_HTTP_PUT_POST_REQUESTS.clear()

    # Make sure our system isn't already in the list of in progress ones
    assert len(plugin.this.sheet.systemsInProgress) == 3
    assert "M7 Sector GM-V d2-107" not in plugin.this.sheet.systemsInProgress

    plugin.process_item(pr)

    assert len(ACTUAL_HTTP_PUT_POST_REQUESTS) == 1

    # Add new entry to System Info table
    req = ACTUAL_HTTP_PUT_POST_REQUESTS.pop(0)
    assert req[0] == "https://sheets.googleapis.com/v4/spreadsheets/1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE/values/'System Info'!A:A:append?valueInputOption=USER_ENTERED"
    assert req[1] == {"range": "'System Info'!A:A", "majorDimension": "ROWS", "values": [["M7 Sector GM-V d2-107", None, None, "cmdr_name", "In Progress"]]}
    assert len(plugin.this.sheet.systemsInProgress) == 4
    assert "M7 Sector GM-V d2-107" in plugin.this.sheet.systemsInProgress

def test_journal_entry_MarketBuy_FromStation():
    entry = {'timestamp': '2025-06-21T03:16:52Z', 'event': 'MarketBuy', 'MarketID': 3710912768, 'Type': 'steel', 'Count': 700, 'BuyPrice': 2013, 'TotalCost': 1409100}
    plugin.journal_entry(cmdr=monitor.monitor.cmdr, is_beta=False, system="Zlotrimi", station="Fraley Orbital", entry=entry, state=None)

    assert plugin.this.queue.qsize() == 1
    
    pr = plugin.this.queue.get_nowait()
    assert pr
    assert pr.type == plugin.PushRequest.TYPE_CMDR_BUY
    assert pr.cmdr == monitor.monitor.cmdr
    assert pr.station == "Fraley Orbital"
    assert pr.data == {'timestamp': '2025-06-21T03:16:52Z', 'event': 'MarketBuy', 'MarketID': 3710912768, 'Type': 'steel', 'Count': 700, 'BuyPrice': 2013, 'TotalCost': 1409100, 'System': 'Zlotrimi'}

    plugin.this.cmdrsAssignedCarrierName.set('')
    plugin.this.killswitches[plugin.KILLSWITCH_CMDR_BUYSELL] = 'false'
    ACTUAL_HTTP_PUT_POST_REQUESTS.clear()
    plugin.process_item(pr)
    assert len(ACTUAL_HTTP_PUT_POST_REQUESTS) == 0

    plugin.this.cmdrsAssignedCarrierName.set('Igneels Tooth')
    plugin.this.killswitches[plugin.KILLSWITCH_CMDR_BUYSELL] = 'false'
    ACTUAL_HTTP_PUT_POST_REQUESTS.clear()
    plugin.process_item(pr)
    assert len(ACTUAL_HTTP_PUT_POST_REQUESTS) == 0

    plugin.this.cmdrsAssignedCarrierName.set('Igneels Tooth')
    plugin.this.killswitches[plugin.KILLSWITCH_CMDR_BUYSELL] = 'true'
    mock_carrier_add_res = """{"spreadsheetId":"1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE","tableRange":"'Igneels Tooth'!A1:E20","updates":{"spreadsheetId":"1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE","updatedRange":"'Igneels Tooth'!A21:E21","updatedRows":1,"updatedColumns":5,"updatedCells":5,"updatedData":{"range":"'Igneels Tooth'!A21:E21","majorDimension":"ROWS","values":[["cmdr_name","Steel","700","FALSE","2025-06-21 04:55:49"]]}}}"""
    __add_mocked_http_response(json.loads(mock_carrier_add_res))
    __add_mocked_http_response(json.loads(mock_carrier_add_res))
    mock_format_checkbox_res = """{"spreadsheetId":"1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE","replies":[{}]}"""
    __add_mocked_http_response(json.loads(mock_format_checkbox_res))
    ACTUAL_HTTP_PUT_POST_REQUESTS.clear()
    plugin.process_item(pr)
    assert len(ACTUAL_HTTP_PUT_POST_REQUESTS) == 2

    req = ACTUAL_HTTP_PUT_POST_REQUESTS.pop(0)
    assert req[0] == "https://sheets.googleapis.com/v4/spreadsheets/1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE/values/'Igneels Tooth'!A:A:append?valueInputOption=USER_ENTERED&includeValuesInResponse=true"
    assert req[1] == {"range": "'Igneels Tooth'!A:A", "majorDimension": "ROWS", "values": [["cmdr_name", "Steel", 700, False, "2025-06-21 03:16:52"]]}

    req = ACTUAL_HTTP_PUT_POST_REQUESTS.pop(0)
    assert req[0] == "https://sheets.googleapis.com/v4/spreadsheets/1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE:batchUpdate"
    assert req[1] == {"requests": [{"repeatCell": {"range": {"sheetId": 1223817771, "startRowIndex": 20, "endRowIndex": 21, "startColumnIndex": 3, "endColumnIndex": 4}, "cell": {"dataValidation": {"condition": {"type": "BOOLEAN"}}}, "fields": "dataValidation.condition"}}]}

    #################################################
    ## CMDR Buy from station (existing in-transit) ##
    #################################################

    plugin.this.cmdrsAssignedCarrierName.set('Igneels Tooth')
    plugin.this.sheet.inTransitCommodities = {
        'steel': {
            "'Igneels Tooth'!A31:E31": 52,
            "'NAC Hyperspace Bypass'!A81:E81": 70
        },
        'aluminium': {
            "'NAC Hyperspace Bypass'!A82:E82": 45
        }
    }
    mock_carrier_update_res = """{"spreadsheetId":"1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE","updatedRange":"'Igneels Tooth'!A31:E31","updatedRows":1,"updatedColumns":5,"updatedCells":5}"""
    __add_mocked_http_response(json.loads(mock_carrier_update_res))
    __add_mocked_http_response(json.loads(mock_carrier_update_res))
    mock_format_checkbox_res = """{"spreadsheetId":"1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE","replies":[{}]}"""
    __add_mocked_http_response(json.loads(mock_format_checkbox_res))
    ACTUAL_HTTP_PUT_POST_REQUESTS.clear()
    plugin.process_item(pr)
    assert len(ACTUAL_HTTP_PUT_POST_REQUESTS) == 2

    req = ACTUAL_HTTP_PUT_POST_REQUESTS.pop(0)
    assert req[0] == "https://sheets.googleapis.com/v4/spreadsheets/1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE/values/'Igneels Tooth'!A31:E31?valueInputOption=USER_ENTERED"
    assert req[1] == {"range": "'Igneels Tooth'!A31:E31", "majorDimension": "ROWS", "values": [["cmdr_name", "Steel", (700 + 52), False, "2025-06-21 03:16:52"]]}

    req = ACTUAL_HTTP_PUT_POST_REQUESTS.pop(0)
    assert req[0] == "https://sheets.googleapis.com/v4/spreadsheets/1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE:batchUpdate"
    assert req[1] == {"requests": [{"repeatCell": {"range": {"sheetId": 1223817771, "startRowIndex": 30, "endRowIndex": 31, "startColumnIndex": 3, "endColumnIndex": 4}, "cell": {"dataValidation": {"condition": {"type": "BOOLEAN"}}}, "fields": "dataValidation.condition"}}]}

def test_journal_entry_MarketBuy_FromFleetCarrier():
    assert plugin.this.sheet.systemsInProgress
    assert plugin.this.sheet.lastFiftyCompletedSystems
    assert len(plugin.this.sheet.lastFiftyCompletedSystems) == 50
    assert plugin.this.sheet.lastFiftyCompletedSystems[0] == 'Bleae Thua WK-R c4-4'

    entry = {'timestamp': '2025-06-21T03:16:52Z', 'event': 'MarketBuy', 'MarketID': 3710912768, 'Type': 'steel', 'Count': 700, 'BuyPrice': 2013, 'TotalCost': 1409100}
    plugin.journal_entry(cmdr=monitor.monitor.cmdr, is_beta=False, system="Bleae Thua WK-R c4-4", station="J9W-65Q", entry=entry, state=None)

    assert plugin.this.queue.qsize() == 1
    
    pr = plugin.this.queue.get_nowait()
    assert pr
    assert pr.type == plugin.PushRequest.TYPE_CARRIER_CMDR_BUY
    assert pr.cmdr == monitor.monitor.cmdr
    assert pr.station == "J9W-65Q"
    assert pr.data == {'timestamp': '2025-06-21T03:16:52Z', 'event': 'MarketBuy', 'MarketID': 3710912768, 'Type': 'steel', 'Count': 700, 'BuyPrice': 2013, 'TotalCost': 1409100, 'System': 'Bleae Thua WK-R c4-4'}

    plugin.this.featureAssumeCarrierUnloadToSCS.set(False)
    plugin.this.killswitches[plugin.KILLSWITCH_CMDR_BUYSELL] = 'false'
    ACTUAL_HTTP_PUT_POST_REQUESTS.clear()
    plugin.process_item(pr)
    assert len(ACTUAL_HTTP_PUT_POST_REQUESTS) == 0

    plugin.this.featureAssumeCarrierUnloadToSCS.set(False)
    plugin.this.killswitches[plugin.KILLSWITCH_CMDR_BUYSELL] = 'true'
    mock_carrier_add_res = """{"spreadsheetId":"1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE","updatedRange":"'NAC Hyperspace Bypass'!A26:E26","updatedRows":1,"updatedColumns":5,"updatedCells":5}"""
    __add_mocked_http_response(json.loads(mock_carrier_add_res))
    __add_mocked_http_response(json.loads(mock_carrier_add_res))
    mock_format_checkbox_res = """{"spreadsheetId":"1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE","replies":[{}]}"""
    __add_mocked_http_response(json.loads(mock_format_checkbox_res))
    ACTUAL_HTTP_PUT_POST_REQUESTS.clear()
    plugin.process_item(pr)
    assert len(ACTUAL_HTTP_PUT_POST_REQUESTS) == 2

    req = ACTUAL_HTTP_PUT_POST_REQUESTS.pop(0)
    assert req[0] == "https://sheets.googleapis.com/v4/spreadsheets/1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE/values/'NAC Hyperspace Bypass'!A:A:append?valueInputOption=USER_ENTERED&includeValuesInResponse=true"
    assert req[1] == {"range": "'NAC Hyperspace Bypass'!A:A", "majorDimension": "ROWS", "values": [["cmdr_name", "Steel", -700, True, "2025-06-21 03:16:52"]]}

    req = ACTUAL_HTTP_PUT_POST_REQUESTS.pop(0)
    assert req[0] == "https://sheets.googleapis.com/v4/spreadsheets/1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE:batchUpdate"
    assert req[1] == {"requests": [{"repeatCell": {"range": {"sheetId": 1143171463, "startRowIndex": 25, "endRowIndex": 26, "startColumnIndex": 3, "endColumnIndex": 4}, "cell": {"dataValidation": {"condition": {"type": "BOOLEAN"}}}, "fields": "dataValidation.condition"}}]}

    ##########################################
    ## Assume Carrier Unload for SCS = true ##
    ##########################################

    plugin.this.featureAssumeCarrierUnloadToSCS.set(True)
    plugin.this.killswitches[plugin.KILLSWITCH_CMDR_BUYSELL] = 'true'
    mock_carrier_add_res = """{"spreadsheetId":"1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE","updatedRange":"'NAC Hyperspace Bypass'!A26:E26","updatedRows":1,"updatedColumns":5,"updatedCells":5}"""
    __add_mocked_http_response(json.loads(mock_carrier_add_res))
    __add_mocked_http_response(json.loads(mock_carrier_add_res))
    mock_format_checkbox_res = """{"spreadsheetId":"1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE","replies":[{}]}"""
    __add_mocked_http_response(json.loads(mock_format_checkbox_res))
    mock_carrier_add_res = """{"spreadsheetId":"1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE","updatedRange":"'SCS Offload'!A359:E359","updatedRows":1,"updatedColumns":5,"updatedCells":5}"""
    __add_mocked_http_response(json.loads(mock_carrier_add_res))
    __add_mocked_http_response(json.loads(mock_carrier_add_res))
    __add_mocked_http_response(json.loads(mock_carrier_add_res))  # TODO: What why is this extra one required ?
    mock_format_checkbox_res = """{"spreadsheetId":"1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE","replies":[{}]}"""
    __add_mocked_http_response(json.loads(mock_format_checkbox_res))
    ACTUAL_HTTP_PUT_POST_REQUESTS.clear()
    plugin.process_item(pr)
    assert len(ACTUAL_HTTP_PUT_POST_REQUESTS) == 4

    req = ACTUAL_HTTP_PUT_POST_REQUESTS.pop(0)
    assert req[0] == "https://sheets.googleapis.com/v4/spreadsheets/1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE/values/'NAC Hyperspace Bypass'!A:A:append?valueInputOption=USER_ENTERED&includeValuesInResponse=true"
    assert req[1] == {"range": "'NAC Hyperspace Bypass'!A:A", "majorDimension": "ROWS", "values": [["cmdr_name", "Steel", -700, True, "2025-06-21 03:16:52"]]}

    req = ACTUAL_HTTP_PUT_POST_REQUESTS.pop(0)
    assert req[0] == "https://sheets.googleapis.com/v4/spreadsheets/1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE:batchUpdate"
    assert req[1] == {"requests": [{"repeatCell": {"range": {"sheetId": 1143171463, "startRowIndex": 25, "endRowIndex": 26, "startColumnIndex": 3, "endColumnIndex": 4}, "cell": {"dataValidation": {"condition": {"type": "BOOLEAN"}}}, "fields": "dataValidation.condition"}}]}

    req = ACTUAL_HTTP_PUT_POST_REQUESTS.pop(0)
    assert req[0] == "https://sheets.googleapis.com/v4/spreadsheets/1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE/values/'SCS Offload'!A:A:append?valueInputOption=USER_ENTERED&includeValuesInResponse=true"
    assert req[1] == {"range": "'SCS Offload'!A:A", "majorDimension": "ROWS", "values": [["Steel", "Bleae Thua WK-R c4-4", 700, False, "2025-06-21 03:16:52"]]}

    req = ACTUAL_HTTP_PUT_POST_REQUESTS.pop(0)
    assert req[0] == "https://sheets.googleapis.com/v4/spreadsheets/1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE:batchUpdate"
    assert req[1] == {"requests": [{"repeatCell": {"range": {"sheetId": 565128439, "startRowIndex": 358, "endRowIndex": 359, "startColumnIndex": 3, "endColumnIndex": 4}, "cell": {"dataValidation": {"condition": {"type": "BOOLEAN"}}}, "fields": "dataValidation.condition"}}]}

    assert plugin.this.sheet.inTransitCommodities == {
        'steel': {
            "'SCS Offload'!A359:E359": 700
        }
    }

def test_journal_entry_CarrierTradeOrder_BuyOrder():
    plugin.this.latestCarrierCallsign = "X7H-9KW"
    plugin.this.myCarrierCallsign = "X7H-9KW"
    plugin.this.myCarrierId = 3707348992

    entry = { 'timestamp': '2025-09-26T09:40:02Z', 'event': 'CarrierTradeOrder', 'CarrierID': 3707348992, 'CarrierType': 'FleetCarrier', 'BlackMarket': False, 'Commodity': 'nonlethalweapons', 'Commodity_Localised': 'Non-Lethal Weapons', 'PurchaseOrder': 9, 'Price': 1848 }
    plugin.journal_entry(cmdr=monitor.monitor.cmdr, is_beta=False, system="", station="", entry=entry, state=None)

    assert plugin.this.queue.qsize() == 1
    
    pr = plugin.this.queue.get_nowait()
    assert pr
    assert pr.type == plugin.PushRequest.TYPE_CARRIER_BUY_SELL_ORDER_UPDATE
    assert pr.cmdr == monitor.monitor.cmdr
    assert pr.station == "X7H-9KW"
    assert pr.data == { 'timestamp': '2025-09-26T09:40:02Z', 'event': 'CarrierTradeOrder', 'CarrierID': 3707348992, 'CarrierType': 'FleetCarrier', 'BlackMarket': False, 'Commodity': 'nonlethalweapons', 'Commodity_Localised': 'Non-Lethal Weapons', 'PurchaseOrder': 9, 'Price': 1848 }

    # Disabled by killswitch
    plugin.this.killswitches[plugin.KILLSWITCH_CARRIER_BUYSELL_ORDER] = 'false'
    ACTUAL_HTTP_PUT_POST_REQUESTS.clear()
    plugin.process_item(pr)
    assert len(ACTUAL_HTTP_PUT_POST_REQUESTS) == 0

    # Buy Order Adjustment - disabled
    plugin.this.killswitches[plugin.KILLSWITCH_CARRIER_BUYSELL_ORDER] = 'true'
    plugin.this.sheet.sheetFunctionality['Igneels Tooth'].setdefault('Buy Order Adjustment', False)
    mock_carrier_buy_order_table = """{"range":"'Igneels Tooth'!H3:J22","majorDimension":"ROWS","values":[["Commodity","Buy Order","Demand"],["Aluminium","543","491"],["Ceramic Composites","552","539"],["CMM Composite","4816","2726"],["Computer Components","65","62"],["Copper","257","245"],["Food Cartridges","100","95"],["Fruit and Vedge","53","50"],["Insulating Membrane","371","345"],["Liquid Oxygen","1902","1717"],["Medical Diagnostic Equipment","13","13"],["Non-Lethal Weapons","9001","9001"],["Polymers","555","506"],["Power Generators","20","20"],["Semiconductors","72","70"],["Steel","7053","0"],["Superconductors","119","115"],["Titanium","5847","0"],["Water","789","744"],["Water Purifiers","40","37"]]}"""
    __add_mocked_http_response(json.loads(mock_carrier_buy_order_table))
    __add_mocked_http_response(json.loads(mock_carrier_buy_order_table))
    ACTUAL_HTTP_PUT_POST_REQUESTS.clear()
    plugin.process_item(pr)
    assert len(ACTUAL_HTTP_PUT_POST_REQUESTS) == 1

    req = ACTUAL_HTTP_PUT_POST_REQUESTS.pop(0)
    assert req[0] == "https://sheets.googleapis.com/v4/spreadsheets/1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE/values/'Igneels Tooth'!H3:J22?valueInputOption=USER_ENTERED"
    assert req[1] == {"range": "'Igneels Tooth'!H3:J22", "majorDimension": "ROWS", "values": [["Commodity", "Buy Order", None], ["Aluminium", "543", None], ["Ceramic Composites", "552", None], ["CMM Composite", "4816", None], ["Computer Components", "65", None], ["Copper", "257", None], ["Food Cartridges", "100", None], ["Fruit and Vedge", "53", None], ["Insulating Membrane", "371", None], ["Liquid Oxygen", "1902", None], ["Medical Diagnostic Equipment", "13", None], ["Non-Lethal Weapons", 9, None], ["Polymers", "555", None], ["Power Generators", "20", None], ["Semiconductors", "72", None], ["Steel", "7053", None], ["Superconductors", "119", None], ["Titanium", "5847", None], ["Water", "789", None], ["Water Purifiers", "40", None]]}

    # Buy Order Adjustment - enabled
    plugin.this.killswitches[plugin.KILLSWITCH_CARRIER_BUYSELL_ORDER] = 'true'
    plugin.this.sheet.sheetFunctionality['Igneels Tooth'].setdefault('Buy Order Adjustment', True)
    mock_carrier_starting_inventory = """{"range":"'Igneels Tooth'!A1:C20","majorDimension":"ROWS","values":[["CMDR","Commodity","Units"],["Starting Inventory","Aluminium","52"],["Starting Inventory","Ceramic Composites","13"],["Starting Inventory","CMM Composite","83"],["Starting Inventory","Computer Components","2"],["Starting Inventory","Copper",""],["Starting Inventory","Food Cartridges","4"],["Starting Inventory","Fruit and Vedge","1"],["Starting Inventory","Insulating Membrane","7"],["Starting Inventory","Liquid Oxygen","24"],["Starting Inventory","Medical Diagnostic Equipment","0"],["Starting Inventory","Non-Lethal Weapons","4"],["Starting Inventory","Polymers","49"],["Starting Inventory","Power Generators",""],["Starting Inventory","Semiconductors","3"],["Starting Inventory","Steel","294"],["Starting Inventory","Superconductors","6"],["Starting Inventory","Titanium","98"],["Starting Inventory","Water","32"],["Starting Inventory","Water Purifiers",""]]}"""
    __add_mocked_http_response(json.loads(mock_carrier_starting_inventory))
    mock_carrier_buy_order_table = """{"range":"'Igneels Tooth'!H3:J22","majorDimension":"ROWS","values":[["Commodity","Buy Order","Demand"],["Aluminium","543","491"],["Ceramic Composites","552","539"],["CMM Composite","4816","2726"],["Computer Components","65","62"],["Copper","257","245"],["Food Cartridges","100","95"],["Fruit and Vedge","53","50"],["Insulating Membrane","371","345"],["Liquid Oxygen","1902","1717"],["Medical Diagnostic Equipment","13","13"],["Non-Lethal Weapons","9001","9001"],["Polymers","555","506"],["Power Generators","20","20"],["Semiconductors","72","70"],["Steel","7053","0"],["Superconductors","119","115"],["Titanium","5847","0"],["Water","789","744"],["Water Purifiers","40","37"]]}"""
    __add_mocked_http_response(json.loads(mock_carrier_buy_order_table))
    __add_mocked_http_response(json.loads(mock_carrier_buy_order_table))
    ACTUAL_HTTP_PUT_POST_REQUESTS.clear()
    plugin.process_item(pr)
    assert len(ACTUAL_HTTP_PUT_POST_REQUESTS) == 1

    req = ACTUAL_HTTP_PUT_POST_REQUESTS.pop(0)
    assert req[0] == "https://sheets.googleapis.com/v4/spreadsheets/1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE/values/'Igneels Tooth'!H3:J22?valueInputOption=USER_ENTERED"
    assert req[1] == {"range": "'Igneels Tooth'!H3:J22", "majorDimension": "ROWS", "values": [["Commodity", "Buy Order", None], ["Aluminium", "543", None], ["Ceramic Composites", "552", None], ["CMM Composite", "4816", None], ["Computer Components", "65", None], ["Copper", "257", None], ["Food Cartridges", "100", None], ["Fruit and Vedge", "53", None], ["Insulating Membrane", "371", None], ["Liquid Oxygen", "1902", None], ["Medical Diagnostic Equipment", "13", None], ["Non-Lethal Weapons", 13, None], ["Polymers", "555", None], ["Power Generators", "20", None], ["Semiconductors", "72", None], ["Steel", "7053", None], ["Superconductors", "119", None], ["Titanium", "5847", None], ["Water", "789", None], ["Water Purifiers", "40", None]]}

def test_journal_entry_CarrierTradeOrder_SellOrder():
    plugin.this.latestCarrierCallsign = "X7H-9KW"
    plugin.this.myCarrierCallsign = "X7H-9KW"
    plugin.this.myCarrierId = 3707348992

    entry = { 'timestamp': '2025-09-26T09:40:02Z', 'event': 'CarrierTradeOrder', 'CarrierID': 3707348992, 'CarrierType': 'FleetCarrier', 'BlackMarket': False, 'Commodity': 'nonlethalweapons', 'Commodity_Localised': 'Non-Lethal Weapons', 'SaleOrder': 13, 'Price': 1848 }
    plugin.journal_entry(cmdr=monitor.monitor.cmdr, is_beta=False, system="", station="", entry=entry, state=None)

    assert plugin.this.queue.qsize() == 1
    
    pr = plugin.this.queue.get_nowait()
    assert pr
    assert pr.type == plugin.PushRequest.TYPE_CARRIER_BUY_SELL_ORDER_UPDATE
    assert pr.cmdr == monitor.monitor.cmdr
    assert pr.station == "X7H-9KW"
    assert pr.data == { 'timestamp': '2025-09-26T09:40:02Z', 'event': 'CarrierTradeOrder', 'CarrierID': 3707348992, 'CarrierType': 'FleetCarrier', 'BlackMarket': False, 'Commodity': 'nonlethalweapons', 'Commodity_Localised': 'Non-Lethal Weapons', 'SaleOrder': 13, 'Price': 1848 }

    # Disabled by killswitch
    plugin.this.killswitches[plugin.KILLSWITCH_CARRIER_BUYSELL_ORDER] = 'false'
    ACTUAL_HTTP_PUT_POST_REQUESTS.clear()
    plugin.process_item(pr)
    assert len(ACTUAL_HTTP_PUT_POST_REQUESTS) == 0

    # Buy Order Adjustment - disabled
    plugin.this.killswitches[plugin.KILLSWITCH_CARRIER_BUYSELL_ORDER] = 'true'
    plugin.this.sheet.sheetFunctionality['Igneels Tooth'].setdefault('Buy Order Adjustment', False)
    mock_carrier_buy_order_table = """{"range":"'Igneels Tooth'!H3:J22","majorDimension":"ROWS","values":[["Commodity","Buy Order","Demand"],["Aluminium","543","491"],["Ceramic Composites","552","539"],["CMM Composite","4816","2726"],["Computer Components","65","62"],["Copper","257","245"],["Food Cartridges","100","95"],["Fruit and Vedge","53","50"],["Insulating Membrane","371","345"],["Liquid Oxygen","1902","1717"],["Medical Diagnostic Equipment","13","13"],["Non-Lethal Weapons","9001","9001"],["Polymers","555","506"],["Power Generators","20","20"],["Semiconductors","72","70"],["Steel","7053","0"],["Superconductors","119","115"],["Titanium","5847","0"],["Water","789","744"],["Water Purifiers","40","37"]]}"""
    __add_mocked_http_response(json.loads(mock_carrier_buy_order_table))
    __add_mocked_http_response(json.loads(mock_carrier_buy_order_table))
    ACTUAL_HTTP_PUT_POST_REQUESTS.clear()
    plugin.process_item(pr)
    assert len(ACTUAL_HTTP_PUT_POST_REQUESTS) == 1

    req = ACTUAL_HTTP_PUT_POST_REQUESTS.pop(0)
    assert req[0] == "https://sheets.googleapis.com/v4/spreadsheets/1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE/values/'Igneels Tooth'!H3:J22?valueInputOption=USER_ENTERED"
    assert req[1] == {"range": "'Igneels Tooth'!H3:J22", "majorDimension": "ROWS", "values": [["Commodity", "Buy Order", None], ["Aluminium", "543", None], ["Ceramic Composites", "552", None], ["CMM Composite", "4816", None], ["Computer Components", "65", None], ["Copper", "257", None], ["Food Cartridges", "100", None], ["Fruit and Vedge", "53", None], ["Insulating Membrane", "371", None], ["Liquid Oxygen", "1902", None], ["Medical Diagnostic Equipment", "13", None], ["Non-Lethal Weapons", "", None], ["Polymers", "555", None], ["Power Generators", "20", None], ["Semiconductors", "72", None], ["Steel", "7053", None], ["Superconductors", "119", None], ["Titanium", "5847", None], ["Water", "789", None], ["Water Purifiers", "40", None]]}

    # Buy Order Adjustment - enabled
    plugin.this.killswitches[plugin.KILLSWITCH_CARRIER_BUYSELL_ORDER] = 'true'
    plugin.this.sheet.sheetFunctionality['Igneels Tooth'].setdefault('Buy Order Adjustment', True)
    mock_carrier_starting_inventory = """{"range":"'Igneels Tooth'!A1:C20","majorDimension":"ROWS","values":[["CMDR","Commodity","Units"],["Starting Inventory","Aluminium","52"],["Starting Inventory","Ceramic Composites","13"],["Starting Inventory","CMM Composite","83"],["Starting Inventory","Computer Components","2"],["Starting Inventory","Copper",""],["Starting Inventory","Food Cartridges","4"],["Starting Inventory","Fruit and Vedge","1"],["Starting Inventory","Insulating Membrane","7"],["Starting Inventory","Liquid Oxygen","24"],["Starting Inventory","Medical Diagnostic Equipment","0"],["Starting Inventory","Non-Lethal Weapons","13"],["Starting Inventory","Polymers","49"],["Starting Inventory","Power Generators",""],["Starting Inventory","Semiconductors","3"],["Starting Inventory","Steel","294"],["Starting Inventory","Superconductors","6"],["Starting Inventory","Titanium","98"],["Starting Inventory","Water","32"],["Starting Inventory","Water Purifiers",""]]}"""
    __add_mocked_http_response(json.loads(mock_carrier_starting_inventory))
    mock_carrier_buy_order_table = """{"range":"'Igneels Tooth'!H3:J22","majorDimension":"ROWS","values":[["Commodity","Buy Order","Demand"],["Aluminium","543","491"],["Ceramic Composites","552","539"],["CMM Composite","4816","2726"],["Computer Components","65","62"],["Copper","257","245"],["Food Cartridges","100","95"],["Fruit and Vedge","53","50"],["Insulating Membrane","371","345"],["Liquid Oxygen","1902","1717"],["Medical Diagnostic Equipment","13","13"],["Non-Lethal Weapons","13","0"],["Polymers","555","506"],["Power Generators","20","20"],["Semiconductors","72","70"],["Steel","7053","0"],["Superconductors","119","115"],["Titanium","5847","0"],["Water","789","744"],["Water Purifiers","40","37"]]}"""
    __add_mocked_http_response(json.loads(mock_carrier_buy_order_table))
    __add_mocked_http_response(json.loads(mock_carrier_buy_order_table))
    ACTUAL_HTTP_PUT_POST_REQUESTS.clear()
    plugin.process_item(pr)
    assert len(ACTUAL_HTTP_PUT_POST_REQUESTS) == 1

    req = ACTUAL_HTTP_PUT_POST_REQUESTS.pop(0)
    assert req[0] == "https://sheets.googleapis.com/v4/spreadsheets/1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE/values/'Igneels Tooth'!H3:J22?valueInputOption=USER_ENTERED"
    assert req[1] == {"range": "'Igneels Tooth'!H3:J22", "majorDimension": "ROWS", "values": [["Commodity", "Buy Order", None], ["Aluminium", "543", None], ["Ceramic Composites", "552", None], ["CMM Composite", "4816", None], ["Computer Components", "65", None], ["Copper", "257", None], ["Food Cartridges", "100", None], ["Fruit and Vedge", "53", None], ["Insulating Membrane", "371", None], ["Liquid Oxygen", "1902", None], ["Medical Diagnostic Equipment", "13", None], ["Non-Lethal Weapons", 13, None], ["Polymers", "555", None], ["Power Generators", "20", None], ["Semiconductors", "72", None], ["Steel", "7053", None], ["Superconductors", "119", None], ["Titanium", "5847", None], ["Water", "789", None], ["Water Purifiers", "40", None]]}

def test_journal_entry_CarrierTradeOrder_CancelOrder():
    plugin.this.latestCarrierCallsign = "X7H-9KW"
    plugin.this.myCarrierCallsign = "X7H-9KW"
    plugin.this.myCarrierId = 3707348992

    entry = { 'timestamp': '2025-09-26T09:40:02Z', 'event': 'CarrierTradeOrder', 'CarrierID': 3707348992, 'CarrierType': 'FleetCarrier', 'BlackMarket': False, 'Commodity': 'nonlethalweapons', 'Commodity_Localised': 'Non-Lethal Weapons', 'CancelTrade': True }
    plugin.journal_entry(cmdr=monitor.monitor.cmdr, is_beta=False, system="", station="", entry=entry, state=None)

    assert plugin.this.queue.qsize() == 1
    
    pr = plugin.this.queue.get_nowait()
    assert pr
    assert pr.type == plugin.PushRequest.TYPE_CARRIER_BUY_SELL_ORDER_UPDATE
    assert pr.cmdr == monitor.monitor.cmdr
    assert pr.station == "X7H-9KW"
    assert pr.data == { 'timestamp': '2025-09-26T09:40:02Z', 'event': 'CarrierTradeOrder', 'CarrierID': 3707348992, 'CarrierType': 'FleetCarrier', 'BlackMarket': False, 'Commodity': 'nonlethalweapons', 'Commodity_Localised': 'Non-Lethal Weapons', 'CancelTrade': True }

    # Disabled by killswitch
    plugin.this.killswitches[plugin.KILLSWITCH_CARRIER_BUYSELL_ORDER] = 'false'
    ACTUAL_HTTP_PUT_POST_REQUESTS.clear()
    plugin.process_item(pr)
    assert len(ACTUAL_HTTP_PUT_POST_REQUESTS) == 0

    # Buy Order Adjustment - disabled
    plugin.this.killswitches[plugin.KILLSWITCH_CARRIER_BUYSELL_ORDER] = 'true'
    plugin.this.sheet.sheetFunctionality['Igneels Tooth'].setdefault('Buy Order Adjustment', False)
    mock_carrier_buy_order_table = """{"range":"'Igneels Tooth'!H3:J22","majorDimension":"ROWS","values":[["Commodity","Buy Order","Demand"],["Aluminium","543","491"],["Ceramic Composites","552","539"],["CMM Composite","4816","2726"],["Computer Components","65","62"],["Copper","257","245"],["Food Cartridges","100","95"],["Fruit and Vedge","53","50"],["Insulating Membrane","371","345"],["Liquid Oxygen","1902","1717"],["Medical Diagnostic Equipment","13","13"],["Non-Lethal Weapons","9001","9001"],["Polymers","555","506"],["Power Generators","20","20"],["Semiconductors","72","70"],["Steel","7053","0"],["Superconductors","119","115"],["Titanium","5847","0"],["Water","789","744"],["Water Purifiers","40","37"]]}"""
    __add_mocked_http_response(json.loads(mock_carrier_buy_order_table))
    __add_mocked_http_response(json.loads(mock_carrier_buy_order_table))
    ACTUAL_HTTP_PUT_POST_REQUESTS.clear()
    plugin.process_item(pr)
    assert len(ACTUAL_HTTP_PUT_POST_REQUESTS) == 1

    req = ACTUAL_HTTP_PUT_POST_REQUESTS.pop(0)
    assert req[0] == "https://sheets.googleapis.com/v4/spreadsheets/1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE/values/'Igneels Tooth'!H3:J22?valueInputOption=USER_ENTERED"
    assert req[1] == {"range": "'Igneels Tooth'!H3:J22", "majorDimension": "ROWS", "values": [["Commodity", "Buy Order", None], ["Aluminium", "543", None], ["Ceramic Composites", "552", None], ["CMM Composite", "4816", None], ["Computer Components", "65", None], ["Copper", "257", None], ["Food Cartridges", "100", None], ["Fruit and Vedge", "53", None], ["Insulating Membrane", "371", None], ["Liquid Oxygen", "1902", None], ["Medical Diagnostic Equipment", "13", None], ["Non-Lethal Weapons", "", None], ["Polymers", "555", None], ["Power Generators", "20", None], ["Semiconductors", "72", None], ["Steel", "7053", None], ["Superconductors", "119", None], ["Titanium", "5847", None], ["Water", "789", None], ["Water Purifiers", "40", None]]}

    # Buy Order Adjustment - enabled
    plugin.this.killswitches[plugin.KILLSWITCH_CARRIER_BUYSELL_ORDER] = 'true'
    plugin.this.sheet.sheetFunctionality['Igneels Tooth'].setdefault('Buy Order Adjustment', True)
    mock_carrier_starting_inventory = """{"range":"'Igneels Tooth'!A1:C20","majorDimension":"ROWS","values":[["CMDR","Commodity","Units"],["Starting Inventory","Aluminium","52"],["Starting Inventory","Ceramic Composites","13"],["Starting Inventory","CMM Composite","83"],["Starting Inventory","Computer Components","2"],["Starting Inventory","Copper",""],["Starting Inventory","Food Cartridges","4"],["Starting Inventory","Fruit and Vedge","1"],["Starting Inventory","Insulating Membrane","7"],["Starting Inventory","Liquid Oxygen","24"],["Starting Inventory","Medical Diagnostic Equipment","0"],["Starting Inventory","Non-Lethal Weapons","13"],["Starting Inventory","Polymers","49"],["Starting Inventory","Power Generators",""],["Starting Inventory","Semiconductors","3"],["Starting Inventory","Steel","294"],["Starting Inventory","Superconductors","6"],["Starting Inventory","Titanium","98"],["Starting Inventory","Water","32"],["Starting Inventory","Water Purifiers",""]]}"""
    __add_mocked_http_response(json.loads(mock_carrier_starting_inventory))
    mock_carrier_buy_order_table = """{"range":"'Igneels Tooth'!H3:J22","majorDimension":"ROWS","values":[["Commodity","Buy Order","Demand"],["Aluminium","543","491"],["Ceramic Composites","552","539"],["CMM Composite","4816","2726"],["Computer Components","65","62"],["Copper","257","245"],["Food Cartridges","100","95"],["Fruit and Vedge","53","50"],["Insulating Membrane","371","345"],["Liquid Oxygen","1902","1717"],["Medical Diagnostic Equipment","13","13"],["Non-Lethal Weapons","13","0"],["Polymers","555","506"],["Power Generators","20","20"],["Semiconductors","72","70"],["Steel","7053","0"],["Superconductors","119","115"],["Titanium","5847","0"],["Water","789","744"],["Water Purifiers","40","37"]]}"""
    __add_mocked_http_response(json.loads(mock_carrier_buy_order_table))
    __add_mocked_http_response(json.loads(mock_carrier_buy_order_table))
    ACTUAL_HTTP_PUT_POST_REQUESTS.clear()
    plugin.process_item(pr)
    assert len(ACTUAL_HTTP_PUT_POST_REQUESTS) == 1

    req = ACTUAL_HTTP_PUT_POST_REQUESTS.pop(0)
    assert req[0] == "https://sheets.googleapis.com/v4/spreadsheets/1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE/values/'Igneels Tooth'!H3:J22?valueInputOption=USER_ENTERED"
    assert req[1] == {"range": "'Igneels Tooth'!H3:J22", "majorDimension": "ROWS", "values": [["Commodity", "Buy Order", None], ["Aluminium", "543", None], ["Ceramic Composites", "552", None], ["CMM Composite", "4816", None], ["Computer Components", "65", None], ["Copper", "257", None], ["Food Cartridges", "100", None], ["Fruit and Vedge", "53", None], ["Insulating Membrane", "371", None], ["Liquid Oxygen", "1902", None], ["Medical Diagnostic Equipment", "13", None], ["Non-Lethal Weapons", 13, None], ["Polymers", "555", None], ["Power Generators", "20", None], ["Semiconductors", "72", None], ["Steel", "7053", None], ["Superconductors", "119", None], ["Titanium", "5847", None], ["Water", "789", None], ["Water Purifiers", "40", None]]}

def test_journal_entry_CarrierTradeOrder_BuyOrder_Squadron():
    plugin.this.latestCarrierCallsign = "MERC"
    plugin.this.myCarrierCallsign = "X7H-9KW"
    plugin.this.myCarrierId = 3707348992
    plugin.this.squadCarrierCallsign = "MERC"
    plugin.this.squadCarrierId = 3713242624

    # I'm assuming this is what the event looks like based on similar changes to the other events when on/interacting with the squad carrier
    entry = { 'timestamp': '2025-09-26T09:40:02Z', 'event': 'CarrierTradeOrder', 'CarrierID': 3713242624, 'CarrierType': 'SquadronCarrier', 'BlackMarket': False, 'Commodity': 'nonlethalweapons', 'Commodity_Localised': 'Non-Lethal Weapons', 'PurchaseOrder': 9, 'Price': 1848 }
    plugin.journal_entry(cmdr=monitor.monitor.cmdr, is_beta=False, system="", station="", entry=entry, state=None)

    assert plugin.this.queue.qsize() == 1
    
    pr = plugin.this.queue.get_nowait()
    assert pr
    assert pr.type == plugin.PushRequest.TYPE_CARRIER_BUY_SELL_ORDER_UPDATE
    assert pr.cmdr == monitor.monitor.cmdr
    assert pr.station == "MERC"
    assert pr.data == { 'timestamp': '2025-09-26T09:40:02Z', 'event': 'CarrierTradeOrder', 'CarrierID': 3713242624, 'CarrierType': 'SquadronCarrier', 'BlackMarket': False, 'Commodity': 'nonlethalweapons', 'Commodity_Localised': 'Non-Lethal Weapons', 'PurchaseOrder': 9, 'Price': 1848 }

    # Disabled by killswitch
    plugin.this.killswitches[plugin.KILLSWITCH_CARRIER_BUYSELL_ORDER] = 'false'
    ACTUAL_HTTP_PUT_POST_REQUESTS.clear()
    plugin.process_item(pr)
    assert len(ACTUAL_HTTP_PUT_POST_REQUESTS) == 0

    # Buy Order Adjustment - disabled
    plugin.this.killswitches[plugin.KILLSWITCH_CARRIER_BUYSELL_ORDER] = 'true'
    plugin.this.sheet.sheetFunctionality['The Highwayman'].setdefault('Buy Order Adjustment', False)
    mock_carrier_buy_order_table = """{"range":"'The Highwayman'!H3:J22","majorDimension":"ROWS","values":[["Commodity","Buy Order","Demand"],["Aluminium","543","491"],["Ceramic Composites","552","539"],["CMM Composite","4816","2726"],["Computer Components","65","62"],["Copper","257","245"],["Food Cartridges","100","95"],["Fruit and Vedge","53","50"],["Insulating Membrane","371","345"],["Liquid Oxygen","1902","1717"],["Medical Diagnostic Equipment","13","13"],["Non-Lethal Weapons","9001","9001"],["Polymers","555","506"],["Power Generators","20","20"],["Semiconductors","72","70"],["Steel","7053","0"],["Superconductors","119","115"],["Titanium","5847","0"],["Water","789","744"],["Water Purifiers","40","37"]]}"""
    __add_mocked_http_response(json.loads(mock_carrier_buy_order_table))
    __add_mocked_http_response(json.loads(mock_carrier_buy_order_table))
    ACTUAL_HTTP_PUT_POST_REQUESTS.clear()
    plugin.process_item(pr)
    assert len(ACTUAL_HTTP_PUT_POST_REQUESTS) == 1

    req = ACTUAL_HTTP_PUT_POST_REQUESTS.pop(0)
    assert req[0] == "https://sheets.googleapis.com/v4/spreadsheets/1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE/values/'The Highwayman'!H3:J22?valueInputOption=USER_ENTERED"
    assert req[1] == {"range": "'The Highwayman'!H3:J22", "majorDimension": "ROWS", "values": [["Commodity", "Buy Order", None], ["Aluminium", "543", None], ["Ceramic Composites", "552", None], ["CMM Composite", "4816", None], ["Computer Components", "65", None], ["Copper", "257", None], ["Food Cartridges", "100", None], ["Fruit and Vedge", "53", None], ["Insulating Membrane", "371", None], ["Liquid Oxygen", "1902", None], ["Medical Diagnostic Equipment", "13", None], ["Non-Lethal Weapons", 9, None], ["Polymers", "555", None], ["Power Generators", "20", None], ["Semiconductors", "72", None], ["Steel", "7053", None], ["Superconductors", "119", None], ["Titanium", "5847", None], ["Water", "789", None], ["Water Purifiers", "40", None]]}

    # Buy Order Adjustment - enabled
    plugin.this.killswitches[plugin.KILLSWITCH_CARRIER_BUYSELL_ORDER] = 'true'
    plugin.this.sheet.sheetFunctionality['The Highwayman'].setdefault('Buy Order Adjustment', True)
    mock_carrier_starting_inventory = """{"range":"'The Highwayman'!A1:C20","majorDimension":"ROWS","values":[["CMDR","Commodity","Units"],["Starting Inventory","Aluminium","52"],["Starting Inventory","Ceramic Composites","13"],["Starting Inventory","CMM Composite","83"],["Starting Inventory","Computer Components","2"],["Starting Inventory","Copper",""],["Starting Inventory","Food Cartridges","4"],["Starting Inventory","Fruit and Vedge","1"],["Starting Inventory","Insulating Membrane","7"],["Starting Inventory","Liquid Oxygen","24"],["Starting Inventory","Medical Diagnostic Equipment","0"],["Starting Inventory","Non-Lethal Weapons","4"],["Starting Inventory","Polymers","49"],["Starting Inventory","Power Generators",""],["Starting Inventory","Semiconductors","3"],["Starting Inventory","Steel","294"],["Starting Inventory","Superconductors","6"],["Starting Inventory","Titanium","98"],["Starting Inventory","Water","32"],["Starting Inventory","Water Purifiers",""]]}"""
    __add_mocked_http_response(json.loads(mock_carrier_starting_inventory))
    mock_carrier_buy_order_table = """{"range":"'The Highwayman'!H3:J22","majorDimension":"ROWS","values":[["Commodity","Buy Order","Demand"],["Aluminium","543","491"],["Ceramic Composites","552","539"],["CMM Composite","4816","2726"],["Computer Components","65","62"],["Copper","257","245"],["Food Cartridges","100","95"],["Fruit and Vedge","53","50"],["Insulating Membrane","371","345"],["Liquid Oxygen","1902","1717"],["Medical Diagnostic Equipment","13","13"],["Non-Lethal Weapons","9001","9001"],["Polymers","555","506"],["Power Generators","20","20"],["Semiconductors","72","70"],["Steel","7053","0"],["Superconductors","119","115"],["Titanium","5847","0"],["Water","789","744"],["Water Purifiers","40","37"]]}"""
    __add_mocked_http_response(json.loads(mock_carrier_buy_order_table))
    __add_mocked_http_response(json.loads(mock_carrier_buy_order_table))
    ACTUAL_HTTP_PUT_POST_REQUESTS.clear()
    plugin.process_item(pr)
    assert len(ACTUAL_HTTP_PUT_POST_REQUESTS) == 1

    req = ACTUAL_HTTP_PUT_POST_REQUESTS.pop(0)
    assert req[0] == "https://sheets.googleapis.com/v4/spreadsheets/1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE/values/'The Highwayman'!H3:J22?valueInputOption=USER_ENTERED"
    assert req[1] == {"range": "'The Highwayman'!H3:J22", "majorDimension": "ROWS", "values": [["Commodity", "Buy Order", None], ["Aluminium", "543", None], ["Ceramic Composites", "552", None], ["CMM Composite", "4816", None], ["Computer Components", "65", None], ["Copper", "257", None], ["Food Cartridges", "100", None], ["Fruit and Vedge", "53", None], ["Insulating Membrane", "371", None], ["Liquid Oxygen", "1902", None], ["Medical Diagnostic Equipment", "13", None], ["Non-Lethal Weapons", 13, None], ["Polymers", "555", None], ["Power Generators", "20", None], ["Semiconductors", "72", None], ["Steel", "7053", None], ["Superconductors", "119", None], ["Titanium", "5847", None], ["Water", "789", None], ["Water Purifiers", "40", None]]}

def test_journal_entry_CarrierTradeOrder_SellOrder_Squadron():
    plugin.this.latestCarrierCallsign = "MERC"
    plugin.this.myCarrierCallsign = "X7H-9KW"
    plugin.this.myCarrierId = 3707348992
    plugin.this.squadCarrierCallsign = "MERC"
    plugin.this.squadCarrierId = 3713242624

    entry = { 'timestamp': '2025-09-26T09:40:02Z', 'event': 'CarrierTradeOrder', 'CarrierID': 3713242624, 'CarrierType': 'SquadronCarrier', 'BlackMarket': False, 'Commodity': 'nonlethalweapons', 'Commodity_Localised': 'Non-Lethal Weapons', 'SaleOrder': 13, 'Price': 1848 }
    plugin.journal_entry(cmdr=monitor.monitor.cmdr, is_beta=False, system="", station="", entry=entry, state=None)

    assert plugin.this.queue.qsize() == 1
    
    pr = plugin.this.queue.get_nowait()
    assert pr
    assert pr.type == plugin.PushRequest.TYPE_CARRIER_BUY_SELL_ORDER_UPDATE
    assert pr.cmdr == monitor.monitor.cmdr
    assert pr.station == "MERC"
    assert pr.data == { 'timestamp': '2025-09-26T09:40:02Z', 'event': 'CarrierTradeOrder', 'CarrierID': 3713242624, 'CarrierType': 'SquadronCarrier', 'BlackMarket': False, 'Commodity': 'nonlethalweapons', 'Commodity_Localised': 'Non-Lethal Weapons', 'SaleOrder': 13, 'Price': 1848 }

    # Disabled by killswitch
    plugin.this.killswitches[plugin.KILLSWITCH_CARRIER_BUYSELL_ORDER] = 'false'
    ACTUAL_HTTP_PUT_POST_REQUESTS.clear()
    plugin.process_item(pr)
    assert len(ACTUAL_HTTP_PUT_POST_REQUESTS) == 0

    # Buy Order Adjustment - disabled
    plugin.this.killswitches[plugin.KILLSWITCH_CARRIER_BUYSELL_ORDER] = 'true'
    plugin.this.sheet.sheetFunctionality['The Highwayman'].setdefault('Buy Order Adjustment', False)
    mock_carrier_buy_order_table = """{"range":"'The Highwayman'!H3:J22","majorDimension":"ROWS","values":[["Commodity","Buy Order","Demand"],["Aluminium","543","491"],["Ceramic Composites","552","539"],["CMM Composite","4816","2726"],["Computer Components","65","62"],["Copper","257","245"],["Food Cartridges","100","95"],["Fruit and Vedge","53","50"],["Insulating Membrane","371","345"],["Liquid Oxygen","1902","1717"],["Medical Diagnostic Equipment","13","13"],["Non-Lethal Weapons","9001","9001"],["Polymers","555","506"],["Power Generators","20","20"],["Semiconductors","72","70"],["Steel","7053","0"],["Superconductors","119","115"],["Titanium","5847","0"],["Water","789","744"],["Water Purifiers","40","37"]]}"""
    __add_mocked_http_response(json.loads(mock_carrier_buy_order_table))
    __add_mocked_http_response(json.loads(mock_carrier_buy_order_table))
    ACTUAL_HTTP_PUT_POST_REQUESTS.clear()
    plugin.process_item(pr)
    assert len(ACTUAL_HTTP_PUT_POST_REQUESTS) == 1

    req = ACTUAL_HTTP_PUT_POST_REQUESTS.pop(0)
    assert req[0] == "https://sheets.googleapis.com/v4/spreadsheets/1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE/values/'The Highwayman'!H3:J22?valueInputOption=USER_ENTERED"
    assert req[1] == {"range": "'The Highwayman'!H3:J22", "majorDimension": "ROWS", "values": [["Commodity", "Buy Order", None], ["Aluminium", "543", None], ["Ceramic Composites", "552", None], ["CMM Composite", "4816", None], ["Computer Components", "65", None], ["Copper", "257", None], ["Food Cartridges", "100", None], ["Fruit and Vedge", "53", None], ["Insulating Membrane", "371", None], ["Liquid Oxygen", "1902", None], ["Medical Diagnostic Equipment", "13", None], ["Non-Lethal Weapons", "", None], ["Polymers", "555", None], ["Power Generators", "20", None], ["Semiconductors", "72", None], ["Steel", "7053", None], ["Superconductors", "119", None], ["Titanium", "5847", None], ["Water", "789", None], ["Water Purifiers", "40", None]]}

    # Buy Order Adjustment - enabled
    plugin.this.killswitches[plugin.KILLSWITCH_CARRIER_BUYSELL_ORDER] = 'true'
    plugin.this.sheet.sheetFunctionality['The Highwayman'].setdefault('Buy Order Adjustment', True)
    mock_carrier_starting_inventory = """{"range":"'The Highwayman'!A1:C20","majorDimension":"ROWS","values":[["CMDR","Commodity","Units"],["Starting Inventory","Aluminium","52"],["Starting Inventory","Ceramic Composites","13"],["Starting Inventory","CMM Composite","83"],["Starting Inventory","Computer Components","2"],["Starting Inventory","Copper",""],["Starting Inventory","Food Cartridges","4"],["Starting Inventory","Fruit and Vedge","1"],["Starting Inventory","Insulating Membrane","7"],["Starting Inventory","Liquid Oxygen","24"],["Starting Inventory","Medical Diagnostic Equipment","0"],["Starting Inventory","Non-Lethal Weapons","13"],["Starting Inventory","Polymers","49"],["Starting Inventory","Power Generators",""],["Starting Inventory","Semiconductors","3"],["Starting Inventory","Steel","294"],["Starting Inventory","Superconductors","6"],["Starting Inventory","Titanium","98"],["Starting Inventory","Water","32"],["Starting Inventory","Water Purifiers",""]]}"""
    __add_mocked_http_response(json.loads(mock_carrier_starting_inventory))
    mock_carrier_buy_order_table = """{"range":"'The Highwayman'!H3:J22","majorDimension":"ROWS","values":[["Commodity","Buy Order","Demand"],["Aluminium","543","491"],["Ceramic Composites","552","539"],["CMM Composite","4816","2726"],["Computer Components","65","62"],["Copper","257","245"],["Food Cartridges","100","95"],["Fruit and Vedge","53","50"],["Insulating Membrane","371","345"],["Liquid Oxygen","1902","1717"],["Medical Diagnostic Equipment","13","13"],["Non-Lethal Weapons","13","0"],["Polymers","555","506"],["Power Generators","20","20"],["Semiconductors","72","70"],["Steel","7053","0"],["Superconductors","119","115"],["Titanium","5847","0"],["Water","789","744"],["Water Purifiers","40","37"]]}"""
    __add_mocked_http_response(json.loads(mock_carrier_buy_order_table))
    __add_mocked_http_response(json.loads(mock_carrier_buy_order_table))
    ACTUAL_HTTP_PUT_POST_REQUESTS.clear()
    plugin.process_item(pr)
    assert len(ACTUAL_HTTP_PUT_POST_REQUESTS) == 1

    req = ACTUAL_HTTP_PUT_POST_REQUESTS.pop(0)
    assert req[0] == "https://sheets.googleapis.com/v4/spreadsheets/1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE/values/'The Highwayman'!H3:J22?valueInputOption=USER_ENTERED"
    assert req[1] == {"range": "'The Highwayman'!H3:J22", "majorDimension": "ROWS", "values": [["Commodity", "Buy Order", None], ["Aluminium", "543", None], ["Ceramic Composites", "552", None], ["CMM Composite", "4816", None], ["Computer Components", "65", None], ["Copper", "257", None], ["Food Cartridges", "100", None], ["Fruit and Vedge", "53", None], ["Insulating Membrane", "371", None], ["Liquid Oxygen", "1902", None], ["Medical Diagnostic Equipment", "13", None], ["Non-Lethal Weapons", 13, None], ["Polymers", "555", None], ["Power Generators", "20", None], ["Semiconductors", "72", None], ["Steel", "7053", None], ["Superconductors", "119", None], ["Titanium", "5847", None], ["Water", "789", None], ["Water Purifiers", "40", None]]}

def test_journal_entry_CarrierTradeOrder_CancelOrder_Squadron():
    plugin.this.latestCarrierCallsign = "MERC"
    plugin.this.myCarrierCallsign = "X7H-9KW"
    plugin.this.myCarrierId = 3707348992
    plugin.this.squadCarrierCallsign = "MERC"
    plugin.this.squadCarrierId = 3713242624

    entry = { 'timestamp': '2025-09-26T09:40:02Z', 'event': 'CarrierTradeOrder', 'CarrierID': 3713242624, 'CarrierType': 'SquadronCarrier', 'BlackMarket': False, 'Commodity': 'nonlethalweapons', 'Commodity_Localised': 'Non-Lethal Weapons', 'CancelTrade': True }
    plugin.journal_entry(cmdr=monitor.monitor.cmdr, is_beta=False, system="", station="", entry=entry, state=None)

    assert plugin.this.queue.qsize() == 1
    
    pr = plugin.this.queue.get_nowait()
    assert pr
    assert pr.type == plugin.PushRequest.TYPE_CARRIER_BUY_SELL_ORDER_UPDATE
    assert pr.cmdr == monitor.monitor.cmdr
    assert pr.station == "MERC"
    assert pr.data == { 'timestamp': '2025-09-26T09:40:02Z', 'event': 'CarrierTradeOrder', 'CarrierID': 3713242624, 'CarrierType': 'SquadronCarrier', 'BlackMarket': False, 'Commodity': 'nonlethalweapons', 'Commodity_Localised': 'Non-Lethal Weapons', 'CancelTrade': True }

    # Disabled by killswitch
    plugin.this.killswitches[plugin.KILLSWITCH_CARRIER_BUYSELL_ORDER] = 'false'
    ACTUAL_HTTP_PUT_POST_REQUESTS.clear()
    plugin.process_item(pr)
    assert len(ACTUAL_HTTP_PUT_POST_REQUESTS) == 0

    # Buy Order Adjustment - disabled
    plugin.this.killswitches[plugin.KILLSWITCH_CARRIER_BUYSELL_ORDER] = 'true'
    plugin.this.sheet.sheetFunctionality['The Highwayman'].setdefault('Buy Order Adjustment', False)
    mock_carrier_buy_order_table = """{"range":"'The Highwayman'!H3:J22","majorDimension":"ROWS","values":[["Commodity","Buy Order","Demand"],["Aluminium","543","491"],["Ceramic Composites","552","539"],["CMM Composite","4816","2726"],["Computer Components","65","62"],["Copper","257","245"],["Food Cartridges","100","95"],["Fruit and Vedge","53","50"],["Insulating Membrane","371","345"],["Liquid Oxygen","1902","1717"],["Medical Diagnostic Equipment","13","13"],["Non-Lethal Weapons","9001","9001"],["Polymers","555","506"],["Power Generators","20","20"],["Semiconductors","72","70"],["Steel","7053","0"],["Superconductors","119","115"],["Titanium","5847","0"],["Water","789","744"],["Water Purifiers","40","37"]]}"""
    __add_mocked_http_response(json.loads(mock_carrier_buy_order_table))
    __add_mocked_http_response(json.loads(mock_carrier_buy_order_table))
    ACTUAL_HTTP_PUT_POST_REQUESTS.clear()
    plugin.process_item(pr)
    assert len(ACTUAL_HTTP_PUT_POST_REQUESTS) == 1

    req = ACTUAL_HTTP_PUT_POST_REQUESTS.pop(0)
    assert req[0] == "https://sheets.googleapis.com/v4/spreadsheets/1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE/values/'The Highwayman'!H3:J22?valueInputOption=USER_ENTERED"
    assert req[1] == {"range": "'The Highwayman'!H3:J22", "majorDimension": "ROWS", "values": [["Commodity", "Buy Order", None], ["Aluminium", "543", None], ["Ceramic Composites", "552", None], ["CMM Composite", "4816", None], ["Computer Components", "65", None], ["Copper", "257", None], ["Food Cartridges", "100", None], ["Fruit and Vedge", "53", None], ["Insulating Membrane", "371", None], ["Liquid Oxygen", "1902", None], ["Medical Diagnostic Equipment", "13", None], ["Non-Lethal Weapons", "", None], ["Polymers", "555", None], ["Power Generators", "20", None], ["Semiconductors", "72", None], ["Steel", "7053", None], ["Superconductors", "119", None], ["Titanium", "5847", None], ["Water", "789", None], ["Water Purifiers", "40", None]]}

    # Buy Order Adjustment - enabled
    plugin.this.killswitches[plugin.KILLSWITCH_CARRIER_BUYSELL_ORDER] = 'true'
    plugin.this.sheet.sheetFunctionality['The Highwayman'].setdefault('Buy Order Adjustment', True)
    mock_carrier_starting_inventory = """{"range":"'The Highwayman'!A1:C20","majorDimension":"ROWS","values":[["CMDR","Commodity","Units"],["Starting Inventory","Aluminium","52"],["Starting Inventory","Ceramic Composites","13"],["Starting Inventory","CMM Composite","83"],["Starting Inventory","Computer Components","2"],["Starting Inventory","Copper",""],["Starting Inventory","Food Cartridges","4"],["Starting Inventory","Fruit and Vedge","1"],["Starting Inventory","Insulating Membrane","7"],["Starting Inventory","Liquid Oxygen","24"],["Starting Inventory","Medical Diagnostic Equipment","0"],["Starting Inventory","Non-Lethal Weapons","13"],["Starting Inventory","Polymers","49"],["Starting Inventory","Power Generators",""],["Starting Inventory","Semiconductors","3"],["Starting Inventory","Steel","294"],["Starting Inventory","Superconductors","6"],["Starting Inventory","Titanium","98"],["Starting Inventory","Water","32"],["Starting Inventory","Water Purifiers",""]]}"""
    __add_mocked_http_response(json.loads(mock_carrier_starting_inventory))
    mock_carrier_buy_order_table = """{"range":"'The Highwayman'!H3:J22","majorDimension":"ROWS","values":[["Commodity","Buy Order","Demand"],["Aluminium","543","491"],["Ceramic Composites","552","539"],["CMM Composite","4816","2726"],["Computer Components","65","62"],["Copper","257","245"],["Food Cartridges","100","95"],["Fruit and Vedge","53","50"],["Insulating Membrane","371","345"],["Liquid Oxygen","1902","1717"],["Medical Diagnostic Equipment","13","13"],["Non-Lethal Weapons","13","0"],["Polymers","555","506"],["Power Generators","20","20"],["Semiconductors","72","70"],["Steel","7053","0"],["Superconductors","119","115"],["Titanium","5847","0"],["Water","789","744"],["Water Purifiers","40","37"]]}"""
    __add_mocked_http_response(json.loads(mock_carrier_buy_order_table))
    __add_mocked_http_response(json.loads(mock_carrier_buy_order_table))
    ACTUAL_HTTP_PUT_POST_REQUESTS.clear()
    plugin.process_item(pr)
    assert len(ACTUAL_HTTP_PUT_POST_REQUESTS) == 1

    req = ACTUAL_HTTP_PUT_POST_REQUESTS.pop(0)
    assert req[0] == "https://sheets.googleapis.com/v4/spreadsheets/1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE/values/'The Highwayman'!H3:J22?valueInputOption=USER_ENTERED"
    assert req[1] == {"range": "'The Highwayman'!H3:J22", "majorDimension": "ROWS", "values": [["Commodity", "Buy Order", None], ["Aluminium", "543", None], ["Ceramic Composites", "552", None], ["CMM Composite", "4816", None], ["Computer Components", "65", None], ["Copper", "257", None], ["Food Cartridges", "100", None], ["Fruit and Vedge", "53", None], ["Insulating Membrane", "371", None], ["Liquid Oxygen", "1902", None], ["Medical Diagnostic Equipment", "13", None], ["Non-Lethal Weapons", 13, None], ["Polymers", "555", None], ["Power Generators", "20", None], ["Semiconductors", "72", None], ["Steel", "7053", None], ["Superconductors", "119", None], ["Titanium", "5847", None], ["Water", "789", None], ["Water Purifiers", "40", None]]}

def test_journal_entry_CarrierJumpRequest():
    plugin.this.latestCarrierCallsign = "X7H-9KW"
    plugin.this.myCarrierCallsign = "X7H-9KW"
    plugin.this.myCarrierId = 3707348992

    entry = { 'timestamp': '2025-03-09T02:44:36Z', 'event': 'CarrierJumpRequest', 'CarrierType': 'FleetCarrier', 'CarrierID': 3707348992, 'SystemName': 'LTT 8001', 'Body': 'LTT 8001 A 2', 'SystemAddress': 3107442365154, 'BodyID': 6, 'DepartureTime': '2025-03-09T03:36:10Z' }
    plugin.journal_entry(cmdr=monitor.monitor.cmdr, is_beta=False, system=None, station=None, entry=entry, state=None)

    assert plugin.this.queue.qsize() == 1
    
    pr = plugin.this.queue.get_nowait()
    assert pr
    assert pr.type == plugin.PushRequest.TYPE_CARRIER_JUMP
    assert pr.cmdr == monitor.monitor.cmdr
    assert pr.station == "X7H-9KW"
    assert pr.data == { 'timestamp': '2025-03-09T02:44:36Z', 'event': 'CarrierJumpRequest', 'CarrierType': 'FleetCarrier', 'CarrierID': 3707348992, 'SystemName': 'LTT 8001', 'Body': 'LTT 8001 A 2', 'SystemAddress': 3107442365154, 'BodyID': 6, 'DepartureTime': '2025-03-09T03:36:10Z' }

    # Disabled by killswitch
    plugin.this.killswitches[plugin.KILLSWITCH_CARRIER_JUMP] = 'false'
    ACTUAL_HTTP_PUT_POST_REQUESTS.clear()
    plugin.process_item(pr)
    assert len(ACTUAL_HTTP_PUT_POST_REQUESTS) == 0

    plugin.this.killswitches[plugin.KILLSWITCH_CARRIER_JUMP] = 'true'
    ACTUAL_HTTP_PUT_POST_REQUESTS.clear()
    plugin.process_item(pr)
    assert len(ACTUAL_HTTP_PUT_POST_REQUESTS) == 1

    req = ACTUAL_HTTP_PUT_POST_REQUESTS.pop(0)
    assert req[0] == "https://sheets.googleapis.com/v4/spreadsheets/1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE/values/'Igneels Tooth'!I2?valueInputOption=USER_ENTERED"
    assert req[1] == {'range': "'Igneels Tooth'!I2", 'majorDimension': 'ROWS', 'values': [['LTT 8001 A 2', '2025-03-09 03:36:10']]}

def test_journal_entry_CarrierJumpRequest_Squadron():
    plugin.this.latestCarrierCallsign = "MERC"
    plugin.this.myCarrierCallsign = "X7H-9KW"
    plugin.this.myCarrierId = 3707348992
    plugin.this.squadCarrierCallsign = "MERC"
    plugin.this.squadCarrierId = 3713242624

    entry = { 'timestamp': '2025-03-09T02:44:36Z', 'event': 'CarrierJumpRequest', 'CarrierType': 'SquadronCarrier', 'CarrierID': 3713242624, 'SystemName': 'LTT 8001', 'Body': 'LTT 8001 A 2', 'SystemAddress': 3107442365154, 'BodyID': 6, 'DepartureTime': '2025-03-09T03:36:10Z' }
    plugin.journal_entry(cmdr=monitor.monitor.cmdr, is_beta=False, system=None, station=None, entry=entry, state=None)

    assert plugin.this.queue.qsize() == 1
    
    pr = plugin.this.queue.get_nowait()
    assert pr
    assert pr.type == plugin.PushRequest.TYPE_CARRIER_JUMP
    assert pr.cmdr == monitor.monitor.cmdr
    assert pr.station == "MERC"
    assert pr.data == { 'timestamp': '2025-03-09T02:44:36Z', 'event': 'CarrierJumpRequest', 'CarrierType': 'SquadronCarrier', 'CarrierID': 3713242624, 'SystemName': 'LTT 8001', 'Body': 'LTT 8001 A 2', 'SystemAddress': 3107442365154, 'BodyID': 6, 'DepartureTime': '2025-03-09T03:36:10Z' }

    # Disabled by killswitch
    plugin.this.killswitches[plugin.KILLSWITCH_CARRIER_JUMP] = 'false'
    ACTUAL_HTTP_PUT_POST_REQUESTS.clear()
    plugin.process_item(pr)
    assert len(ACTUAL_HTTP_PUT_POST_REQUESTS) == 0

    plugin.this.killswitches[plugin.KILLSWITCH_CARRIER_JUMP] = 'true'
    ACTUAL_HTTP_PUT_POST_REQUESTS.clear()
    plugin.process_item(pr)
    assert len(ACTUAL_HTTP_PUT_POST_REQUESTS) == 1

    req = ACTUAL_HTTP_PUT_POST_REQUESTS.pop(0)
    assert req[0] == "https://sheets.googleapis.com/v4/spreadsheets/1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE/values/'The Highwayman'!I2?valueInputOption=USER_ENTERED"
    assert req[1] == {'range': "'The Highwayman'!I2", 'majorDimension': 'ROWS', 'values': [['LTT 8001 A 2', '2025-03-09 03:36:10']]}

def test_journal_entry_CarrierJumpCancelled():
    plugin.this.latestCarrierCallsign = "X7H-9KW"
    plugin.this.myCarrierCallsign = "X7H-9KW"
    plugin.this.myCarrierId = 3707348992

    entry = {'timestamp': '2025-10-03T23:23:20Z', 'event': 'CarrierJumpCancelled', 'CarrierType': 'FleetCarrier', 'CarrierID': 3707348992}
    plugin.journal_entry(cmdr=monitor.monitor.cmdr, is_beta=False, system=None, station=None, entry=entry, state=None)

    assert plugin.this.queue.qsize() == 1
    
    pr = plugin.this.queue.get_nowait()
    assert pr
    assert pr.type == plugin.PushRequest.TYPE_CARRIER_JUMP
    assert pr.cmdr == monitor.monitor.cmdr
    assert pr.station == "X7H-9KW"
    assert pr.data == {'timestamp': '2025-10-03T23:23:20Z', 'event': 'CarrierJumpCancelled', 'CarrierType': 'FleetCarrier', 'CarrierID': 3707348992}

    # Disabled by killswitch
    plugin.this.killswitches[plugin.KILLSWITCH_CARRIER_JUMP] = 'false'
    ACTUAL_HTTP_PUT_POST_REQUESTS.clear()
    plugin.process_item(pr)
    assert len(ACTUAL_HTTP_PUT_POST_REQUESTS) == 0

    plugin.this.killswitches[plugin.KILLSWITCH_CARRIER_JUMP] = 'true'
    ACTUAL_HTTP_PUT_POST_REQUESTS.clear()
    plugin.process_item(pr)
    assert len(ACTUAL_HTTP_PUT_POST_REQUESTS) == 1

    req = ACTUAL_HTTP_PUT_POST_REQUESTS.pop(0)
    assert req[0] == "https://sheets.googleapis.com/v4/spreadsheets/1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE/values/'Igneels Tooth'!I2?valueInputOption=USER_ENTERED"
    assert req[1] == {'range': "'Igneels Tooth'!I2", 'majorDimension': 'ROWS', 'values': [['', '']]}

def test_journal_entry_CarrierJumpCancelled_Squadron():
    plugin.this.latestCarrierCallsign = "MERC"
    plugin.this.myCarrierCallsign = "X7H-9KW"
    plugin.this.myCarrierId = 3707348992
    plugin.this.squadCarrierCallsign = "MERC"
    plugin.this.squadCarrierId = 3713242624

    entry = {'timestamp': '2025-10-03T23:26:46Z', 'event': 'CarrierJumpCancelled', 'CarrierType': 'SquadronCarrier', 'CarrierID': 3713242624}
    plugin.journal_entry(cmdr=monitor.monitor.cmdr, is_beta=False, system=None, station=None, entry=entry, state=None)

    assert plugin.this.queue.qsize() == 1
    
    pr = plugin.this.queue.get_nowait()
    assert pr
    assert pr.type == plugin.PushRequest.TYPE_CARRIER_JUMP
    assert pr.cmdr == monitor.monitor.cmdr
    assert pr.station == "MERC"
    assert pr.data == {'timestamp': '2025-10-03T23:26:46Z', 'event': 'CarrierJumpCancelled', 'CarrierType': 'SquadronCarrier', 'CarrierID': 3713242624}

    # Disabled by killswitch
    plugin.this.killswitches[plugin.KILLSWITCH_CARRIER_JUMP] = 'false'
    ACTUAL_HTTP_PUT_POST_REQUESTS.clear()
    plugin.process_item(pr)
    assert len(ACTUAL_HTTP_PUT_POST_REQUESTS) == 0

    plugin.this.killswitches[plugin.KILLSWITCH_CARRIER_JUMP] = 'true'
    ACTUAL_HTTP_PUT_POST_REQUESTS.clear()
    plugin.process_item(pr)
    assert len(ACTUAL_HTTP_PUT_POST_REQUESTS) == 1

    req = ACTUAL_HTTP_PUT_POST_REQUESTS.pop(0)
    assert req[0] == "https://sheets.googleapis.com/v4/spreadsheets/1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE/values/'The Highwayman'!I2?valueInputOption=USER_ENTERED"
    assert req[1] == {'range': "'The Highwayman'!I2", 'majorDimension': 'ROWS', 'values': [['', '']]}

