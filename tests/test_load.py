import pytest
import http.server
import requests
import json
import time
import logging
import webbrowser
from collections import defaultdict
import copy

import load as plugin
import auth
import tkinter as tk

# Import stubs
import config
import monitor

MOCK_HTTP_RESPONSES: list[str] = []
MOCK_HTTP_RESPONSE_CODES: list[int] = []
ACTUAL_HTTP_PUT_POST_REQUESTS: list[list[str, str]] = []

MOCK_HTTP_AUTH_DATA = """/auth?state=pOiorvXGIISkV0xXGOyKOmH4_oRqfV1ReaIXEAptVrc&code=4/0AQSTgQGARr4HjUmniyldb5X6uWI5ChkrAsE6h5xJDzmJf55xaPmDAF2UmRb0MaM-kYW3Cw&scope=https://www.googleapis.com/auth/drive.file"""
MOCK_HTTP_OVERVIEW_DATA = """{"sheets":[{"properties":{"sheetId":1943482414,"title":"System Info"}},{"properties":{"sheetId":565128439,"title":"SCS Offload"}},{"properties":{"sheetId":346465544,"title":"Tritons Reach"}},{"properties":{"sheetId":1275960297,"title":"T2F-7KX"}},{"properties":{"sheetId":812258018,"title":"Marasesti"}},{"properties":{"sheetId":1264641940,"title":"Roxy's Roost"}},{"properties":{"sheetId":1282942153,"title":"Galactic Bridge"}},{"properties":{"sheetId":1273206209,"title":"Nebulous Terraforming"}},{"properties":{"sheetId":1159569395,"title":"Transylvania"}},{"properties":{"sheetId":1041708629,"title":"CLB Voqooe Lagoon"}},{"properties":{"sheetId":344510017,"title":"Sword of Meridia"}},{"properties":{"sheetId":816116202,"title":"The Citadel"}},{"properties":{"sheetId":628529931,"title":"Atlaran Delta"}},{"properties":{"sheetId":2142664989,"title":"Red Lobster"}},{"properties":{"sheetId":1223817771,"title":"Igneels Tooth"}},{"properties":{"sheetId":1397023568,"title":"Jolly Roger"}},{"properties":{"sheetId":388336710,"title":"Cerebral Cortex"}},{"properties":{"sheetId":1760610269,"title":"Black hole in the wall"}},{"properties":{"sheetId":1002218299,"title":"Poseidon's Kiss"}},{"properties":{"sheetId":1210069199,"title":"Bifröst"}},{"properties":{"sheetId":1038714848,"title":"USS Ballistic"}},{"properties":{"sheetId":1143171463,"title":"NAC Hyperspace Bypass"}},{"properties":{"sheetId":1376529251,"title":"Stella Obscura"}},{"properties":{"sheetId":1204848219,"title":"Data"}},{"properties":{"sheetId":623399360,"title":"Carrier"}},{"properties":{"sheetId":566513196,"title":"CMDR - Marasesti"}},{"properties":{"sheetId":281677435,"title":"FC Tritons Reach"}},{"properties":{"sheetId":980092843,"title":"CMDR - T2F-7KX"}},{"properties":{"sheetId":905743757,"title":"CMDR-Roxys Roost"}},{"properties":{"sheetId":1217399628,"title":"CMDR - Galactic Bridge"}},{"properties":{"sheetId":133746159,"title":"CMDR - Nebulous Terraforming"}},{"properties":{"sheetId":1968049995,"title":"CMDR - CLB Voqooe Lagoon"}},{"properties":{"sheetId":74373547,"title":"Buy orders"}},{"properties":{"sheetId":161489343,"title":"EDMC Plugin Settings"}},{"properties":{"sheetId":897372416,"title":"Detail3-Steel"}},{"properties":{"sheetId":820007652,"title":"Detail2-Polymers"}},{"properties":{"sheetId":1309255245,"title":"Detail1-Medical Diagnostic Equi"}},{"properties":{"sheetId":253393435,"title":"Colonization"}},{"properties":{"sheetId":1831405150,"title":"Shoppinglist"}},{"properties":{"sheetId":299245359,"title":"Sheet3"}}]}"""
# vvv Add new lookups here vvv
## Remember to change the assert in plugin_start_stop!
MOCK_HTTP_EDMC_PLUGIN_SETTINGS_DATA = """{"spreadsheetId":"1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE","valueRanges":[{"range":"'EDMC Plugin Settings'!A1:C1001","majorDimension":"ROWS","values":[["Killswitches"],["Enabled","TRUE"],["Minimum Version","1.2.0"],["CMDR Info Update","TRUE"],["Carrier BuySell Order","TRUE"],["Carrier Location","TRUE"],["Carrier Jump","TRUE"],["Carrier Market Full","FALSE"],["SCS Sell Commodity","TRUE"],["CMDR BuySell Commodity","TRUE"],["Carrier Transfer","TRUE"],["Carrier Reconcile","FALSE"],["SCS Reconcile","FALSE"],["SCS Reconcile Delay In Seconds","60"],["SCS Data Populate","FALSE"],[],["Lookups"],["Carrier Location","I1"],["Carrier Buy Orders","H3:J22"],["Carrier Jump Location","I2"],["Carrier Sum Cargo","AA:AB"],["Carrier Starting Inventory","A1:C20"],["SCS Sheet","SCS Offload"],["System Info Sheet","System Info"],["CMDR Info","G:I"],["In Progress Systems","Data!A59:A88"],["SCS Progress Pivot","W4:BY"],["Reconcile Mutex","'SCS Offload'!X1"],["Systems With No Data","Data!BN:BN"],["Data System Table Start","Data!A59:A"],["Data System Table End Column", "BD"],[],["Commodity Mapping"],["ceramiccomposites","Ceramic Composites"],["cmmcomposite","CMM Composite"],["computercomponents","Computer Components"],["foodcartridges","Food Cartridges"],["fruitandvegetables","Fruit and Vedge"],["ceramicinsulatingmembrane","Insulating Membrane"],["insulatingmembrane","Insulating Membrane"],["liquidoxygen","Liquid Oxygen"],["medicaldiagnosticequipment","Medical Diagnostic Equipment"],["nonlethalweapons","Non-Lethal Weapons"],["powergenerators","Power Generators"],["waterpurifiers","Water Purifiers"]]},{"range":"'EDMC Plugin Settings'!J1:L1001","majorDimension":"ROWS","values":[["Carriers","","Sheet Name"],["Tritons Reach","K0X-94Z","Tritons Reach"],["Angry Whore -Tsh7-","T2F-7KX","T2F-7KX"],["Marasesti","V2Z-58Z","Marasesti"],["Roxy's Roost","Q0T-GQB","Roxy's Roost"],["Galactic Bridge","GZB-80Z","Galactic Bridge"],["Nebulous Terraforming","KBV-N9H","Nebulous Terraforming"],["CLB Voqooe Lagoon","G0Q-8KJ","CLB Voqooe Lagoon"],["Sword of Meridia","T9Z-LKT","Sword of Meridia"],["Atlaran Delta","H0M-1HB","Atlaran Delta"],["P.T.N Red Lobster","TZX-16K","Red Lobster"],["Igneels Tooth","X7H-9KW","Igneels Tooth"],["Jolly Roger","T3H-N6K","Jolly Roger"],["Cerebral Cortex","X8M-7VV","Cerebral Cortex"],["Black hole in the wall","HHY-45Z","Black hole in the wall"],["Poseidon's Kiss","LHM-2CZ","Poseidon's Kiss"],["Bifröst","T2W-69Z","Bifröst"],["USS Ballistic","TNL-L5H","USS Balistic"],["NAC Hyperspace Bypass","J9W-65Q","NAC Hyperspace Bypass"],["Stella Obscura","J4V-82Z","Stella Obscura"],["The Citadel","LNX-80Z","The Citadel"],["Transylvania","M3K-5SZ","Transylvania"]]},{"range":"'EDMC Plugin Settings'!O1:P1001","majorDimension":"ROWS","values":[["Markets","Set By Owner"],["X7H-9KW","TRUE"],["LHM-2CZ","TRUE"],["T3H-N6K","TRUE"]]},{"range":"'EDMC Plugin Settings'!S1:V1001","majorDimension":"ROWS","values":[["Sheet Functionality","Delivery","Timestamp","Buy Order Adjustment"],["SCS Offload","TRUE","TRUE","FALSE"],["Tritons Reach","TRUE","TRUE","FALSE"],["T2F-7KX","TRUE","TRUE","FALSE"],["Marasesti","TRUE","TRUE","FALSE"],["Roxy's Roost","TRUE","TRUE","FALSE"],["Galactic Bridge","TRUE","TRUE","FALSE"],["Nebulous Terraforming","TRUE","TRUE","FALSE"],["CLB Voqooe Lagoon","TRUE","TRUE","FALSE"],["Sword of Meridia","TRUE","TRUE","FALSE"],["Atlaran Delta","TRUE","TRUE","FALSE"],["Red Lobster","TRUE","TRUE","FALSE"],["Igneels Tooth","TRUE","TRUE","TRUE"],["Jolly Roger","TRUE","TRUE","FALSE"],["Cerebral Cortex","TRUE","TRUE","FALSE"],["Black hole in the wall","TRUE","TRUE","FALSE"],["Poseidon's Kiss","TRUE","TRUE","FALSE"],["Bifröst","TRUE","TRUE","FALSE"],["USS Ballistic","TRUE","TRUE","FALSE"],["NAC Hyperspace Bypass","TRUE","TRUE","FALSE"],["Stella Obscura","TRUE","TRUE","TRUE"],["The Citadel","TRUE","TRUE","FALSE"],["Transylvania","TRUE","TRUE","TRUE"]]}]}"""
# ^^^
MOCK_HTTP_ACTIVE_SYSTEMS_DATA = """{"spreadsheetId":"1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE","valueRanges":[{"range":"Data!A59:A88","majorDimension":"ROWS","values":[["System"],["Col 359 Sector IW-M d7-1"],["M7 Sector NE-W b3-0"],["Pipe (stem) Sector ZE-A d89"]]}]}"""
MOCK_HTTP_CMDR_INFO_DATA = """{"spreadsheetId":"1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE","valueRanges":[{"range":"'System Info'!G1:I1000","majorDimension":"ROWS","values":[["CMDR","Max Cap","Cap Ship"],["Starting Inventory"],["In Transit"],["Kalran Oarn","724","Marasesti"],["Lucifer Wolfgang"],["Exil","792","Marasesti"],["Bolton54","784","Tritons Reach"],["Von MD","752","Marasesti"],["Meeces2911","752","Igneels Tooth"],["ChromaSlip"],["Lord Thunderwind","784","T2F-7KX"],["Alycans"],["ZombieJoe"],["DeathMagnet","794"],["Chriton Suen","784","Marasesti"],["Jikard","724","Marasesti"],["Kiesman","","Marasesti"],["Double Standard","758","Marasesti"],["Caddymac","","Marasesti"],["BLASC","784","Marasesti"],["Beauseant","784","Black hole in the wall"],["Niokman","","Marasesti"],["Celok","","Marasesti"],["Deaththro18","780","Tritons Reach"],["Zenith2195","","Tritons Reach"],["Caerwyrn","","Tritons Reach"],["Reenuip","","Tritons Reach"],["Priapism","","Tritons Reach"],["THEWOLFE208","","Tritons Reach"],["Wolfe3","","Tritons Reach"],["Tristamen","","Tritons Reach"],["Gumbilicious","","T2F-7KX"],["Shyr","","T2F-7KX"],["Matt Flatlands","","T2F-7KX"],["Yossarian","","T2F-7KX"],["Henry Blackfeather","","T2F-7KX"],["Audio Kyrios","","T2F-7KX"],["Xavier Saskuatch","","T2F-7KX"],["xmotis","","T2F-7KX"],["neogia","784","Stella Obscura"],["Chriton Suen","","Marasesti"],["Jetreyu","784","Roxy's Roost"],["NicBic","0","The Citadel"],["TOGSolid","","Tritons Reach"],["Correction","","Roxy's Roost"],["GERTY08"],["Jador Mak","724","Nebulous Terraforming"],["Javeh"],["Atlantik JCX"],["Spartan086x","784","Sword of Meridia"],["Jaghut","","Jolly Roger"],["Violet Truth","","Red Lobster"],["mac Drake","784","Jolly Roger"],["Cerebral Chaos","790"],["J3D1T4IT"],["CryptoHash","8","NAC Hyperspace Bypass"],["War Intern"],["Dr Lichen","720","The Citadel"],["Tetteta","784","Fleet Carrier"],["bolton54","784"],["The Wise Mans Fear"],["Mercenary Venus","436"],["tetteta","30"]]}]}"""
MOCK_HTTP_EDMC_PLUGIN_USAGE_DATA = """{"range":"'EDMC Plugin Settings'!E1:G1001","majorDimension":"ROWS","values":[["Userlist","Version","Last Access (UTC)"],["Meeces2911","1.2.1","2025-04-10 06:30:36"],["Chriton Suen","1.0.3-beta2"],["Jador Mak","1.0.3-beta1"],["Jetreyu","1.2.0-beta1","2025-04-10 00:04:01"],["Lord Thunderwind","1.2.0","2025-04-04 13:41:20"],["mac Drake","1.2.0","2025-04-09 18:08:39"],["Beauseant","1.1.2","2025-04-09 00:38:40"],["neogia","1.2.0","2025-04-10 03:34:31"],["DeathMagnet","1.1.1","2025-04-10 03:43:19"],["CryptoHash","1.1.2","2025-04-02 14:48:28"],["NicBic","1.2.0","2025-04-09 18:36:10"],["tetteta","1.2.0","2025-04-06 20:12:59"],["bolton54","1.2.0","2025-04-09 19:36:25"],["Von MD","1.2.0","2025-04-06 15:29:04"],["Mercenary Venus","1.2.0","2025-04-05 23:58:42"]]}"""
MOCK_HTTP_EDMC_PLUGIN_USAGE_RES_DATA = """{"spreadsheetId":"1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE","tableRange":"'EDMC Plugin Settings'!E1:G16","updates":{"spreadsheetId":"1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE","updatedRange":"'EDMC Plugin Settings'!E17:G17","updatedRows":1,"updatedColumns":3,"updatedCells":3}}"""

logger = logging.getLogger()

class MockHTTPResponse:
    def __init__(self, *args, **kwargs):
        httpVerb = args[0][1] or '*UNKNOWN*'
        httpUrl = args[0][2] or '*UNKNOWN*'
        if httpVerb == "POST" or httpVerb == "PUT":
            httpBody = args[1]['json']
            ACTUAL_HTTP_PUT_POST_REQUESTS.append([httpUrl, copy.deepcopy(httpBody)])

    @property
    def status_code(self) -> int:
        res = MOCK_HTTP_RESPONSE_CODES.pop(0) if len(MOCK_HTTP_RESPONSE_CODES) > 0 else requests.codes.OK
        logger.debug(f'MockHTTPResponse::status_code returning: {res}, {len(MOCK_HTTP_RESPONSE_CODES)} remaining')
        return res

    @staticmethod
    def json():
        logger.critical(f'{len(MOCK_HTTP_RESPONSES)} HTTP Responses remaining')
        res = MOCK_HTTP_RESPONSES.pop(0) if len(MOCK_HTTP_RESPONSES) > 0 else { 'body': 'mock response' }
        #logger.debug(f'MockHTTPResponse::json returning: {res}')
        return res
    
    @staticmethod
    def raise_for_status() -> None:
        logger.debug('MockHTTPResponse::raise_for_status stubbed, skipping ')
        return None

@pytest.fixture()
def global_mocks(monkeypatch):
    # Return the next mock response in our list
    def mock_handle_request(*args, **kwargs) -> str:
        res = MOCK_HTTP_RESPONSES.pop(0) if len(MOCK_HTTP_RESPONSES) > 0 else 'mock response'
        logger.debug(f'global_mocks::mock_handle_request returning: {res}')
        return res
    
    def mock_webbrowser_open(*args, **kwargs) -> bool:
        logger.debug(f'webbrowser::open stubbed, called with: {args}')
        return True
    
    def mock_logging_error(*args, **kwargs):
        # Because exceptions are suppressed, any 'tracebacks' need to be flagged
        logger.critical('Changing all errors to CRITS')
        logger.critical(args)
        assert False
        #logger.error(args)
    
    monkeypatch.setattr(webbrowser, 'open', lambda *args, **kwargs: mock_webbrowser_open)
    monkeypatch.setattr(http.server.HTTPServer, 'handle_request', lambda *args, **kwargs: mock_handle_request)
    monkeypatch.setattr(auth.LocalHTTPServer, 'worker', lambda *args, **kwargs: logger.debug('LocalHTTPServer::worker stubbed, skipping '))
    monkeypatch.setattr(auth.LocalHTTPServer, 'response', '**** LocalHTTPServer::response stubbed ****')
    monkeypatch.setattr(requests, 'get', lambda *args, **kwargs: logger.critical('requests::get stubbed, skipping '))
    #monkeypatch.setattr(requests, 'post', lambda *args, **kwargs: logger.critical('requests::post stubbed, skipping '))
    monkeypatch.setattr(auth.Auth, 'auth', lambda *args, **kwargs: logger.debug('Auth::auth stubbed, skipping '))
    monkeypatch.setattr(requests.sessions.Session, 'request', lambda *args, **kwargs: MockHTTPResponse(args, kwargs))
    monkeypatch.setattr(logging, 'error', lambda *args, **kwargs: mock_logging_error)

@pytest.fixture(autouse=True)
def before_after_test(global_mocks):
    """Default any settings before the run of each test"""
    config.config.shutting_down = False
    ACTUAL_HTTP_PUT_POST_REQUESTS.clear()
    plugin_start_stop()

def _add_mocked_http_response(responseBody: str | None = None, responseCode: int | None = None):
    # Not particularly great framework, but it works for now...
    if responseBody:
        MOCK_HTTP_RESPONSES.append(responseBody)
    if responseCode:
        MOCK_HTTP_RESPONSE_CODES.append(responseCode)

def plugin_start_stop():
    MOCK_HTTP_RESPONSES.clear()
    MOCK_HTTP_RESPONSE_CODES.clear()

    _add_mocked_http_response(json.loads(MOCK_HTTP_OVERVIEW_DATA))               # Initial call to GET /spreadsheets in check_and_authorise_access_to_spreadsheet
    _add_mocked_http_response(json.loads(MOCK_HTTP_OVERVIEW_DATA))               # Second call to GET /spreadsheets in check_and_authorise_access_to_spreadsheet      #TODO: We should probably avoid doing this one
    _add_mocked_http_response(json.loads(MOCK_HTTP_EDMC_PLUGIN_SETTINGS_DATA))   # Call to GET /values:batchGet in populate_initial_settings
    _add_mocked_http_response(json.loads(MOCK_HTTP_ACTIVE_SYSTEMS_DATA))         # Second call to GET /values:batchGet populate_initial_settings after lookups are set
    _add_mocked_http_response(json.loads(MOCK_HTTP_CMDR_INFO_DATA))              # Call to GET /values:batchGet in populate_cmdr_data
    _add_mocked_http_response(json.loads(MOCK_HTTP_EDMC_PLUGIN_USAGE_DATA))      # Call to GET /values in record_plugin_usage
    _add_mocked_http_response(json.loads(MOCK_HTTP_EDMC_PLUGIN_USAGE_RES_DATA))  # Call to POST /values:append in record_plugin_usage
    _add_mocked_http_response(json.loads(MOCK_HTTP_EDMC_PLUGIN_USAGE_RES_DATA))  # Call to POST /values:append in record_plugin_usage (yes, we get the response twice)
    _add_mocked_http_response(json.loads(MOCK_HTTP_EDMC_PLUGIN_USAGE_RES_DATA))  # Call to POST /spreadsheets:batchUpdate in record_plugin_usage to set the formatting    

    plugin.plugin_start3("..\\")
    assert plugin.this.thread
    assert plugin.this.thread.is_alive()

    # Give the plugin a little time to start to avoid mixing the starting and quitting logs
    time.sleep(1)

    assert plugin.this.sheet
    assert plugin.this.sheet.lookupRanges
    assert len(plugin.this.sheet.lookupRanges) == 14

    assert plugin.this.thread

    config.config.shutting_down = True
    plugin.plugin_stop()
    assert plugin.this.thread == None

    # This shouldn't be necessary if we're checking for everything, but we're not for now
    MOCK_HTTP_RESPONSES.clear()
    MOCK_HTTP_RESPONSE_CODES.clear()
    assert len(MOCK_HTTP_RESPONSES) == 0
    assert len(MOCK_HTTP_RESPONSE_CODES) == 0

def test_journal_entry_Startup_LoadGame():
    """Test 'Startup' or 'LoadGame' events"""
    entry = {'timestamp': '2025-04-11T08:18:27Z', 'event': 'LoadGame', 'FID': '9001', 'Commander': 'Meeces2911', 'Horizons': True, 'Odyssey': True, 'Ship': 'Type9', 'Ship_Localised': 'Type-9 Heavy', 'ShipID': 10, 'ShipName': 'hauler', 'ShipIdent': 'MIKUNN', 'FuelLevel': 64.0, 'FuelCapacity': 64.0, 'GameMode': 'Open', 'Credits': 3620255325, 'Loan': 0, 'language': 'English/UK', 'gameversion': '4.1.1.0', 'build': 'r312744/r0 '}
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

    entry['StationType'] = 'FleetCarrier'
    entry['StationName'] = 'X7H-9KW'
    state = {'CargoCapacity': 512}
    plugin.journal_entry(cmdr=monitor.monitor.cmdr, is_beta=False, system=None, station='X7H-9KW', entry=entry, state=state)

    assert plugin.this.latestCarrierCallsign == 'X7H-9KW'
    assert plugin.this.cargoCapacity == 512

    # Expecting TYPE_CMDR_UPDATE and 2xTYPE_CARRIER_INTRANSIT_RECALC
    assert plugin.this.queue.qsize() == 3

    pr = plugin.this.queue.get_nowait()
    assert pr
    assert pr.type == plugin.PushRequest.TYPE_CMDR_UPDATE
    assert pr.cmdr == monitor.monitor.cmdr
    assert pr.station == 'X7H-9KW'

    pr = plugin.this.queue.get_nowait()
    assert pr
    assert pr.type == plugin.PushRequest.TYPE_CARRIER_INTRANSIT_RECALC
    assert pr.cmdr == monitor.monitor.cmdr
    assert pr.station == 'X7H-9KW'
    assert pr.data == None

    mock_scs_in_transit_data = """{"range":"'Igneels Tooth'!A1:E500","majorDimension":"ROWS","values":[["CMDR","Commodity","Units","Delivered","Timestamp"],["Starting Inventory","Aluminium","0"],["Starting Inventory","Ceramic Composites","0"],["Starting Inventory","CMM Composite","0"],["Starting Inventory","Computer Components","0"],["Starting Inventory","Copper","0"],["Starting Inventory","Food Cartridges","0"],["Starting Inventory","Fruit and Vedge","0"],["Starting Inventory","Insulating Membrane","0"],["Starting Inventory","Liquid Oxygen","0"],["Starting Inventory","Medical Diagnostic Equipment","0"],["Starting Inventory","Non-Lethal Weapons","0"],["Starting Inventory","Polymers","0"],["Starting Inventory","Power Generators","0"],["Starting Inventory","Semiconductors","0"],["Starting Inventory","Steel","0"],["Starting Inventory","Superconductors","0"],["Starting Inventory","Titanium","0"],["Starting Inventory","Water","0"],["Starting Inventory","Water Purifiers","0"],["cmdr_name","Steel",250,"FALSE"],["cmdr_name","Titanium",320,"FALSE"],["cmdr_name","Power Generators",20,"FALSE"]]}"""
    _add_mocked_http_response(json.loads(mock_scs_in_transit_data))
    ACTUAL_HTTP_PUT_POST_REQUESTS.clear()
    plugin.process_item(pr)
    assert len(plugin.this.sheet.inTransitCommodities) == 3

    pr = plugin.this.queue.get_nowait()
    assert pr
    assert pr.type == plugin.PushRequest.TYPE_CARRIER_INTRANSIT_RECALC
    assert pr.cmdr == monitor.monitor.cmdr
    assert pr.station == 'X7H-9KW'
    assert pr.data['clear'] == True

    ACTUAL_HTTP_PUT_POST_REQUESTS.clear()
    plugin.process_item(pr)
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
    _add_mocked_http_response(json.loads(mock_scs_reconcile_mutex))
    ACTUAL_HTTP_PUT_POST_REQUESTS.clear()
    plugin.process_item(pr)
    assert len(ACTUAL_HTTP_PUT_POST_REQUESTS) == 0

    # Previous reoncile that didn't finish correctly by us
    mock_scs_reconcile_mutex = """{"range":"'SCS Offload'!X1","majorDimension": "ROWS","values":[["cmdr_name"]]}"""
    _add_mocked_http_response(json.loads(mock_scs_reconcile_mutex))
    mock_scs_reconcile_mutext_set = """{"spreadsheetId":"1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE","updatedRange":"'SCS Offload'!X1","updatedRows":1,"updatedColumns":1,"updatedCells":1}"""
    _add_mocked_http_response(json.loads(mock_scs_reconcile_mutext_set))
    _add_mocked_http_response(json.loads(mock_scs_reconcile_mutext_set))
    mock_scs_progress_data = """{"range":"'SCS Offload'!W4:BY999","majorDimension":"ROWS","values":[["Delivered To","Advanced Catalysers","Agri-Medicines","Aluminium","Animal Meat","Basic Medicines","Battle Weapons","Beer","Bioreducing Lichen","Biowaste","Building Fabricators","Ceramic Composites","CMM Composite","Coffee","Combat Stabilizers","Computer Components","Copper","Crop Harvesters","Emergency Power Cells","Evacuation Shelter","Fish","Food Cartridges","Fruit and Vedge","Geological Equipment","Grain","H.E. Suits","Insulating Membrane","Land Enrichment Systems","Liquid Oxygen","Liquor","Medical Diagnostic Equipment","Micro Controllers","Microbial Furnaces","Military Grade Fabrics","Mineral Extractors","Muon Imager","Non-Lethal Weapons","Pesticides","Polymers","Power Generators","Reactive Armour","Resonating Separators","Robotics","Semiconductors","Steel","Structural Regulators","Superconductors","Surface Stabilisers","Survival Equipment","Tea","Thermal Cooling Units","Titanium","Water","Water Purifiers","Wine"],["","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0"],["Arietis Sector BV-P b5-4","","","9978","","","","","","","","","12023","","","199","749","","","","","243","150","","","","69","","2116","","26","","","","","","26","","1118","63","","","","","16973","","333","","","","","9961","2129","109"],["Beta Coronae Austrinae","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","784"],["Pru Euq RV-T b44-6","","","478","","","","","","","","","","","","60","240","","","","","90","50","","","","361","","280","","13","","","","","","","","538","19","","","","67","6261","","115","","","","","2374","777","37"],["M7 Sector CG-X d1-90","","","182","","","","","","","","37","986","","","","237","","","","","43","52","","","","319","","1722","","11","","","","","","0","","240","4","","","","21","1693","","96","","","","","4305","542","38","90"]]}"""
    _add_mocked_http_response(json.loads(mock_scs_progress_data))
    mock_scs_inflight_data = """{"range":"'SCS Offload'!CB4:EE999","majorDimension":"ROWS","values":[["Delivered To","Water Purifiers"],["M7 Sector CG-X d1-90","38"]]}"""
    _add_mocked_http_response(json.loads(mock_scs_inflight_data))
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
    _add_mocked_http_response(json.loads(mock_scs_reconcile_mutex))
    mock_scs_reconcile_mutext_set = """{"spreadsheetId":"1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE","updatedRange":"'SCS Offload'!X1","updatedRows":1,"updatedColumns":1,"updatedCells":1}"""
    _add_mocked_http_response(json.loads(mock_scs_reconcile_mutext_set))
    _add_mocked_http_response(json.loads(mock_scs_reconcile_mutext_set))
    mock_scs_progress_data = """{"range":"'SCS Offload'!W4:BY999","majorDimension":"ROWS","values":[["Delivered To","Advanced Catalysers","Agri-Medicines","Aluminium","Animal Meat","Basic Medicines","Battle Weapons","Beer","Bioreducing Lichen","Biowaste","Building Fabricators","Ceramic Composites","CMM Composite","Coffee","Combat Stabilizers","Computer Components","Copper","Crop Harvesters","Emergency Power Cells","Evacuation Shelter","Fish","Food Cartridges","Fruit and Vedge","Geological Equipment","Grain","H.E. Suits","Insulating Membrane","Land Enrichment Systems","Liquid Oxygen","Liquor","Medical Diagnostic Equipment","Micro Controllers","Microbial Furnaces","Military Grade Fabrics","Mineral Extractors","Muon Imager","Non-Lethal Weapons","Pesticides","Polymers","Power Generators","Reactive Armour","Resonating Separators","Robotics","Semiconductors","Steel","Structural Regulators","Superconductors","Surface Stabilisers","Survival Equipment","Tea","Thermal Cooling Units","Titanium","Water","Water Purifiers","Wine"],["","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0"],["Arietis Sector BV-P b5-4","","","9978","","","","","","","","","12023","","","199","749","","","","","243","150","","","","69","","2116","","26","","","","","","26","","1118","63","","","","","16973","","333","","","","","9961","2129","109"],["Beta Coronae Austrinae","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","784"],["Pru Euq RV-T b44-6","","","478","","","","","","","","","","","","60","240","","","","","90","50","","","","361","","280","","13","","","","","","","","538","19","","","","67","6261","","115","","","","","2374","777","37"],["M7 Sector CG-X d1-90","","","182","","","","","","","","37","986","","","","237","","","","","43","52","","","","319","","1722","","11","","","","","","0","","240","4","","","","21","1693","","96","","","","","4305","542","38","90"]]}"""
    _add_mocked_http_response(json.loads(mock_scs_progress_data))
    mock_scs_inflight_data = """{"range":"'SCS Offload'!CB4:EE999","majorDimension":"ROWS","values":[["Delivered To","Water Purifiers"],["M7 Sector CG-X d1-90","38"]]}"""
    _add_mocked_http_response(json.loads(mock_scs_inflight_data))
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

    assert plugin.this.queue.qsize() == 1   # There should just be the DATA_POPULATE one left
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

    pr = plugin.this.queue.get_nowait() # Skip the PROGRESS_UPDATE one
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
    _add_mocked_http_response(json.loads(mock_data_systems_table))
    plugin.process_item(pr)
    assert len(ACTUAL_HTTP_PUT_POST_REQUESTS) == 1

    req = ACTUAL_HTTP_PUT_POST_REQUESTS.pop(0)
    assert req[0] == "https://sheets.googleapis.com/v4/spreadsheets/1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE/values/Data!A159:BD159?valueInputOption=USER_ENTERED"
    assert req[1] == {"range": "Data!A159:BD159", "majorDimension": "ROWS", "values": [[None, None, 510, 515, 4319, 61, 247, 96, 52, 353, 1745, 12, 13, 517, 19, 67, 6749, 113, 5415, 709, 38, None, None, None, None, None, None, None, None, None, None, None, None, None, None, 9001, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, 4096]]}

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
        _add_mocked_http_response(json.loads(mock_new_scs_entry_response), requests.codes.OK)                           # Debug logging + status_check in insert_data
        _add_mocked_http_response(json.loads(mock_new_scs_entry_response))                                              # Check for 'updates' in add_to_scs_sheet
        _add_mocked_http_response(json.loads("""{"body": "Some reasponse we don't care about"}"""), requests.codes.OK)  # Debug logging + status_check in update_data
        _add_mocked_http_response(json.loads("""{"body": "???"}"""), requests.codes.OK)                                 # Debug logging + status_check in update_data
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
        _add_mocked_http_response(json.loads(mock_new_scs_entry_response), requests.codes.OK)                           # Debug logging + status_check in insert_data
        _add_mocked_http_response(json.loads(mock_new_scs_entry_response))                                              # Check for 'updates' in add_to_scs_sheet
        _add_mocked_http_response(json.loads("""{"body": "Some reasponse we don't care about"}"""), requests.codes.OK)  # Debug logging + status_check in update_data
        _add_mocked_http_response(json.loads("""{"body": "???"}"""), requests.codes.OK)                                 # Debug logging + status_check in update_data
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
    _add_mocked_http_response(json.loads(mock_system_info_systems))
    ACTUAL_HTTP_PUT_POST_REQUESTS.clear()
    plugin.process_item(pr)

    assert len(ACTUAL_HTTP_PUT_POST_REQUESTS) == 0

    # Then, lets assume its not known
    mock_system_info_systems = """{"range":"'System Info'!A1:A1000","majorDimension":"ROWS","values":[["System"],["COL 285 SECTOR DT-E B26-9"],["HIP 94491"],["Col 285 Sector DT-E b26-2"],["Col 285 Sector AG-O d6-122"],["Nunki"],["27 PHI SAGITTARII"],["COL 285 SECTOR RJ-E A55-5"],["HIP 90504"],["Col 285 Sector CH-Z a57-3"],["Col 285 Sector GN-X A58-0"],["HIP 89535"],["COL 285 SECTOR JY-Y C14-15"],["COL 285 SECTOR HD-Z C14-22"],["COL 285 SECTOR UH-W B30-4"],["HIP 88440"],["COL 359 SECTOR OR-V D2-120"],["COL 359 SECTOR OR-V D2-47"],["COL 359 SECTOR YL-K B10-3"],["COL 359 SECTOR CS-I B11-7"],["COL 285 SECTOR JY-Y C14-15"],["HIP 94491"],["HIP 94491"],["HIP 94491"],["Col 359 Sector BJ-R c5-21"],["Col 359 Sector GP-P c6-31"],["Col 359 Sector GP-P c6-3"],["Col 359 Sector SX-T d3-48"],["COL 359 SECTOR LE-F B13-6"],["COL 359 SECTOR SX-T D3-133"],["Col 359 Sector OR-V d2-146"],["Pipe (bowl) Sector ZO-A b3"],["Col 359 Sector FP-P c6-18"],["Col 359 Sector GP-P c6-20"],["HIP 89573"],["Pipe (stem) Sector YJ-A c7"],["Col 359 Sector OR-V d2-146"],["Pipe (stem) Sector ZE-A d151"],["Pipe (stem) Sector BA-Z b3"],["HIP 85257"],["Pipe (stem) Sector ZE-A d101"],["Pipe (stem) Sector BA-Z b2"],["Pipe (stem) Sector ZE-A d151"],["HIP 85257"],["Pipe (stem) Sector YE-Z b1"],["Pipe (stem) Sector ZE-Z b4"],["Pipe (stem) Sector DL-X b1-0"],["Pipe (stem) Sector DL-X b1-7"],["Pipe (Stem) Sector GW-W C1-27"],["Pipe (stem) Sector GW-W c1-28"],["Pipe (stem) Sector ZE-A d89"],["Pipe (Stem) Sector BQ-Y d80"],["Pipe (stem) Sector IH-V c2-18"],["Pipe (stem) Sector DL-Y d106"],["Pipe (stem) Sector KC-V c2-22"],["Pipe (stem) Sector DL-Y d66"],["Pipe (stem) Sector LN-S b4-1"],["Pipe (stem) Sector JX-T b3-2"],["Pipe (stem) Sector DL-Y d17"],["Pipe (stem) Sector MN-T c3-13"],["Pipe (stem) Sector OI-T c3-19"],["Pipe (stem) Sector ZA-N b7-4"],["Pipe (stem) Sector DH-L b8-0"],["Pipe (stem) Sector DL-Y d112"],["Pipe (stem) Sector CQ-Y d59"],["Pipe (stem) Sector GW-W c1-6"],["Pipe (stem) Sector KC-V c2-1"],["Col 285 Sector UG-I b24-5"],["Pipe (stem) Sector DH-L b8-4"],["Snake Sector FB-X c1-1"],["Snake Sector UJ-Q b5-4"],["Pipe (stem) Sector KC-V c2-1"],["HIP 84930"],["Snake Sector XP-O b6-2"],["Snake Sector ZK-O b6-3"],["Pipe (stem) Sector JC-V c2-23"],["Col 285 Sector GY-H c10-14"],["Snake Sector PI-T c3-14"],["Snake Sector HR-W d1-105"],["Col 359 Sector EQ-O d6-124"],["Col 359 Sector IW-M d7-10"],["Col 359 Sector PX-E b27-6"],["Col 359 Sector QX-E b27-1"],["Col 359 Sector TD-D b28-2"],["Col 359 Sector IW-M d7-67"],["Col 359 Sector WJ-B b29-3"],["Col 359 Sector AQ-Z b29-0"],["Col 359 Sector IW-M d7-37"],["Col 359 Sector NX-Z c14-17"],["Col 359 Sector MC-L d8-22"],["Col 359 Sector IW-M d7-1"],["Col 359 Sector MC-L d8-111"],["Col 359 Sector JC-W b31-4"],["M7 Sector NE-W b3-0"],["M7 Sector YZ-Y d47"],["M7 Sector YZ-Y d18"],["M7 Sector UQ-S b5-0"],["M7 Sector WK-W c2-10"],["M7 Sector WK-W c2-7"],["M7 Sector YW-Q b6-2"],["M7 Sector CG-X d1-90"],["M7 Sector FY-O b7-3"],["M7 Sector JE-N b8-6"],["M7 Sector HS-S c4-26"],["M7 Sector HS-S c4-12"],["M7 Sector VW-H b11-3"],["Col 359 Sector GL-D c13-2"],["M7 Sector LY-Q c5-16"],["M7 Sector GM-V d2-57"],["M7 Sector DJ-E b13-6"],["M7 Sector OE-P c6-4"],["M7 Sector CJ-E b13-0"],["M7 Sector OE-P c6-7"],["M7 Sector IA-B b15-6"],["M7 Sector IA-B b15-0"],["M7 Sector JS-T d3-131"],["M7 Sector QP-N c7-1"],["M7 Sector MG-Z b15-3"],["M7 Sector QM-X b16-5"],["M7 Sector UV-L C8-0"],["Arietis Sector BV-P b5-4"],["Pru Euq HY-Y b41-5"],["Pru Euq LE-X b42-4"],["Pru Euq JJ-X b42-6"],["Pru Euq NP-V b43-2"],["Pru Euq RV-T b44-6"],["R CrA Sector KC-V c2-22"],["Beta Coronae Austrinae"],["Pru Euq RV-T b44-5"],["M7 Sector VV-L c8-12"],["Col 285 Sector VO-N b21-0"],["Pru Euq VB-S b45-5"],["Pru Euq VB-S b45-1"],["Pru Euq ZD-I c23-14"],["Pru Euq YH-Q b46-3"],["Pru Euq LW-E d11-50"],["Pru Euq BZ-H c23-15"],["Pru Euq LW-E d11-59"],["Cephei Sector XO-A b2"],["Pru Euq CO-O b47-1"],["Pru Euq DK-G c24-1"],["Pru Euq JA-L b49-2"]]}"""
    _add_mocked_http_response(json.loads(mock_system_info_systems))
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
