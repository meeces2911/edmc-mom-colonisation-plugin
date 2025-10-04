import pytest
import requests
import copy
import http.server
import webbrowser
import json
import time

import load as plugin
import config
import auth

import logging

logger = logging.getLogger()

MOCK_HTTP_RESPONSES: list[str] = []
MOCK_HTTP_RESPONSE_CODES: list[int] = []
ACTUAL_HTTP_PUT_POST_REQUESTS: list[list[str, str]] = []
ACTUAL_HTTP_GET_REQUESTS: list[str] = []

MOCK_HTTP_AUTH_DATA = """/auth?state=pOiorvXGIISkV0xXGOyKOmH4_oRqfV1ReaIXEAptVrc&code=4/0AQSTgQGARr4HjUmniyldb5X6uWI5ChkrAsE6h5xJDzmJf55xaPmDAF2UmRb0MaM-kYW3Cw&scope=https://www.googleapis.com/auth/drive.file"""
MOCK_HTTP_OVERVIEW_DATA = """{"sheets":[{"properties":{"sheetId":1943482414,"title":"System Info"}},{"properties":{"sheetId":565128439,"title":"SCS Offload"}},{"properties":{"sheetId":346465544,"title":"Tritons Reach"}},{"properties":{"sheetId":1275960297,"title":"T2F-7KX"}},{"properties":{"sheetId":812258018,"title":"Marasesti"}},{"properties":{"sheetId":1264641940,"title":"Roxy's Roost"}},{"properties":{"sheetId":1282942153,"title":"Galactic Bridge"}},{"properties":{"sheetId":1273206209,"title":"Nebulous Terraforming"}},{"properties":{"sheetId":1159569395,"title":"Transylvania"}},{"properties":{"sheetId":1041708629,"title":"CLB Voqooe Lagoon"}},{"properties":{"sheetId":344510017,"title":"Sword of Meridia"}},{"properties":{"sheetId":816116202,"title":"The Citadel"}},{"properties":{"sheetId":628529931,"title":"Atlaran Delta"}},{"properties":{"sheetId":2142664989,"title":"Red Lobster"}},{"properties":{"sheetId":1223817771,"title":"Igneels Tooth"}},{"properties":{"sheetId":1397023568,"title":"Jolly Roger"}},{"properties":{"sheetId":388336710,"title":"Cerebral Cortex"}},{"properties":{"sheetId":1760610269,"title":"Black hole in the wall"}},{"properties":{"sheetId":1002218299,"title":"Poseidon's Kiss"}},{"properties":{"sheetId":1210069199,"title":"Bifröst"}},{"properties":{"sheetId":1038714848,"title":"USS Ballistic"}},{"properties":{"sheetId":1143171463,"title":"NAC Hyperspace Bypass"}},{"properties":{"sheetId":1376529251,"title":"Stella Obscura"}},{"properties":{"sheetId":1204848219,"title":"Data"}},{"properties":{"sheetId":623399360,"title":"Carrier"}},{"properties":{"sheetId":566513196,"title":"CMDR - Marasesti"}},{"properties":{"sheetId":281677435,"title":"FC Tritons Reach"}},{"properties":{"sheetId":980092843,"title":"CMDR - T2F-7KX"}},{"properties":{"sheetId":905743757,"title":"CMDR-Roxys Roost"}},{"properties":{"sheetId":1217399628,"title":"CMDR - Galactic Bridge"}},{"properties":{"sheetId":133746159,"title":"CMDR - Nebulous Terraforming"}},{"properties":{"sheetId":1968049995,"title":"CMDR - CLB Voqooe Lagoon"}},{"properties":{"sheetId":74373547,"title":"Buy orders"}},{"properties":{"sheetId":161489343,"title":"EDMC Plugin Settings"}},{"properties":{"sheetId":897372416,"title":"Detail3-Steel"}},{"properties":{"sheetId":820007652,"title":"Detail2-Polymers"}},{"properties":{"sheetId":1309255245,"title":"Detail1-Medical Diagnostic Equi"}},{"properties":{"sheetId":253393435,"title":"Colonization"}},{"properties":{"sheetId":1831405150,"title":"Shoppinglist"}},{"properties":{"sheetId":299245359,"title":"Sheet3"}}]}"""
# vvv Add new lookups here vvv
## Remember to change the assert in plugin_start_stop!
MOCK_HTTP_EDMC_PLUGIN_SETTINGS_DATA = """{"spreadsheetId":"1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE","valueRanges":[{"range":"'EDMC Plugin Settings'!A1:C1001","majorDimension":"ROWS","values":[["Killswitches"],["Enabled","TRUE"],["Minimum Version","1.2.0"],["CMDR Info Update","TRUE"],["Carrier BuySell Order","TRUE"],["Carrier Location","TRUE"],["Carrier Jump","TRUE"],["Carrier Market Full","FALSE"],["SCS Sell Commodity","TRUE"],["CMDR BuySell Commodity","TRUE"],["Carrier Transfer","TRUE"],["Carrier Reconcile","FALSE"],["SCS Reconcile","FALSE"],["SCS Reconcile Delay In Seconds","60"],["SCS Data Populate","FALSE"],[],["Lookups"],["Carrier Location","I1"],["Carrier Buy Orders","H3:J22"],["Carrier Jump Location","I2"],["Carrier Sum Cargo","AA:AB"],["Carrier Starting Inventory","A1:C20"],["SCS Sheet","SCS Offload"],["System Info Sheet","System Info"],["CMDR Info","G:I"],["In Progress Systems","Data!A59:A88"],["SCS Progress Pivot","W4:BY"],["SCS Progress In-Transit Pivot","CB4:EE"],["Reconcile Mutex","'SCS Offload'!X1"],["Systems With No Data","Data!BN:BN"],["Data System Table Start","Data!A59:A"],["Data System Table End Column","BD"],[],["Commodity Mapping"],["ceramiccomposites","Ceramic Composites"],["cmmcomposite","CMM Composite"],["computercomponents","Computer Components"],["foodcartridges","Food Cartridges"],["fruitandvegetables","Fruit and Vedge"],["ceramicinsulatingmembrane","Insulating Membrane"],["insulatingmembrane","Insulating Membrane"],["liquidoxygen","Liquid Oxygen"],["medicaldiagnosticequipment","Medical Diagnostic Equipment"],["nonlethalweapons","Non-Lethal Weapons"],["powergenerators","Power Generators"],["waterpurifiers","Water Purifiers"]]},{"range":"'EDMC Plugin Settings'!J1:L1001","majorDimension":"ROWS","values":[["Carriers","","Sheet Name"],["Tritons Reach","K0X-94Z","Tritons Reach"],["Angry Whore -Tsh7-","T2F-7KX","T2F-7KX"],["Marasesti","V2Z-58Z","Marasesti"],["Roxy's Roost","Q0T-GQB","Roxy's Roost"],["Galactic Bridge","GZB-80Z","Galactic Bridge"],["Nebulous Terraforming","KBV-N9H","Nebulous Terraforming"],["CLB Voqooe Lagoon","G0Q-8KJ","CLB Voqooe Lagoon"],["Sword of Meridia","T9Z-LKT","Sword of Meridia"],["Atlaran Delta","H0M-1HB","Atlaran Delta"],["P.T.N Red Lobster","TZX-16K","Red Lobster"],["Igneels Tooth","X7H-9KW","Igneels Tooth"],["Jolly Roger","T3H-N6K","Jolly Roger"],["Cerebral Cortex","X8M-7VV","Cerebral Cortex"],["Black hole in the wall","HHY-45Z","Black hole in the wall"],["Poseidon's Kiss","LHM-2CZ","Poseidon's Kiss"],["Bifröst","T2W-69Z","Bifröst"],["USS Ballistic","TNL-L5H","USS Balistic"],["NAC Hyperspace Bypass","J9W-65Q","NAC Hyperspace Bypass"],["Stella Obscura","J4V-82Z","Stella Obscura"],["The Citadel","LNX-80Z","The Citadel"],["Transylvania","M3K-5SZ","Transylvania"],["The Highwayman","MERC","The Highwayman"]]},{"range":"'EDMC Plugin Settings'!O1:P1001","majorDimension":"ROWS","values":[["Markets","Set By Owner"],["X7H-9KW","TRUE"],["LHM-2CZ","TRUE"],["T3H-N6K","TRUE"]]},{"range":"'EDMC Plugin Settings'!S1:V1001","majorDimension":"ROWS","values":[["Sheet Functionality","Delivery","Timestamp","Buy Order Adjustment"],["SCS Offload","TRUE","TRUE","FALSE"],["Tritons Reach","TRUE","TRUE","FALSE"],["T2F-7KX","TRUE","TRUE","FALSE"],["Marasesti","TRUE","TRUE","FALSE"],["Roxy's Roost","TRUE","TRUE","FALSE"],["Galactic Bridge","TRUE","TRUE","FALSE"],["Nebulous Terraforming","TRUE","TRUE","FALSE"],["CLB Voqooe Lagoon","TRUE","TRUE","FALSE"],["Sword of Meridia","TRUE","TRUE","FALSE"],["Atlaran Delta","TRUE","TRUE","FALSE"],["Red Lobster","TRUE","TRUE","FALSE"],["Igneels Tooth","TRUE","TRUE","TRUE"],["Jolly Roger","TRUE","TRUE","FALSE"],["Cerebral Cortex","TRUE","TRUE","FALSE"],["Black hole in the wall","TRUE","TRUE","FALSE"],["Poseidon's Kiss","TRUE","TRUE","FALSE"],["Bifröst","TRUE","TRUE","FALSE"],["USS Ballistic","TRUE","TRUE","FALSE"],["NAC Hyperspace Bypass","TRUE","TRUE","FALSE"],["Stella Obscura","TRUE","TRUE","TRUE"],["The Citadel","TRUE","TRUE","FALSE"],["Transylvania","TRUE","TRUE","TRUE"],["The Highwayman","TRUE","TRUE","TRUE"]]}]}"""
# ^^^
MOCK_HTTP_ACTIVE_SYSTEMS_DATA = """{"spreadsheetId":"1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE","valueRanges":[{"range":"Data!BH2:BH30","majorDimension":"ROWS","values":[["Col 359 Sector IW-M d7-1"],["M7 Sector NE-W b3-0"],["Pipe (stem) Sector ZE-A d89"]]},{"range":"'System Info'!A1:A1000","majorDimension":"ROWS","values":[["System"],["COL 285 SECTOR DT-E B26-9"],["HIP 94491"],["Col 285 Sector DT-E b26-2"],["Col 285 Sector AG-O d6-122"],["Nunki"],["27 PHI SAGITTARII"],["COL 285 SECTOR RJ-E A55-5"],["HIP 90504"],["Col 285 Sector CH-Z a57-3"],["Col 285 Sector GN-X A58-0"],["HIP 89535"],["COL 285 SECTOR JY-Y C14-15"],["COL 285 SECTOR HD-Z C14-22"],["COL 285 SECTOR UH-W B30-4"],["HIP 88440"],["COL 359 SECTOR OR-V D2-120"],["COL 359 SECTOR OR-V D2-47"],["COL 359 SECTOR YL-K B10-3"],["COL 359 SECTOR CS-I B11-7"],["COL 285 SECTOR JY-Y C14-15"],["HIP 94491"],["HIP 94491"],["HIP 94491"],["Col 359 Sector BJ-R c5-21"],["Col 359 Sector GP-P c6-31"],["Col 359 Sector GP-P c6-3"],["Col 359 Sector SX-T d3-48"],["COL 359 SECTOR LE-F B13-6"],["COL 359 SECTOR SX-T D3-133"],["Col 359 Sector OR-V d2-146"],["Pipe (bowl) Sector ZO-A b3"],["Col 359 Sector FP-P c6-18"],["Col 359 Sector GP-P c6-20"],["HIP 89573"],["Pipe (stem) Sector YJ-A c7"],["Col 359 Sector OR-V d2-146"],["Pipe (stem) Sector ZE-A d151"],["Pipe (stem) Sector BA-Z b3"],["HIP 85257"],["Pipe (stem) Sector ZE-A d101"],["Pipe (stem) Sector BA-Z b2"],["Pipe (stem) Sector ZE-A d151"],["HIP 85257"],["Pipe (stem) Sector YE-Z b1"],["Pipe (stem) Sector ZE-Z b4"],["Pipe (stem) Sector DL-X b1-0"],["Pipe (stem) Sector DL-X b1-7"],["Pipe (Stem) Sector GW-W C1-27"],["Pipe (stem) Sector GW-W c1-28"],["Pipe (stem) Sector ZE-A d89"],["Pipe (Stem) Sector BQ-Y d80"],["Pipe (stem) Sector IH-V c2-18"],["Pipe (stem) Sector DL-Y d106"],["Pipe (stem) Sector KC-V c2-22"],["Pipe (stem) Sector DL-Y d66"],["Pipe (stem) Sector LN-S b4-1"],["Pipe (stem) Sector JX-T b3-2"],["Pipe (stem) Sector DL-Y d17"],["Pipe (stem) Sector MN-T c3-13"],["Pipe (stem) Sector OI-T c3-19"],["Pipe (stem) Sector ZA-N b7-4"],["Pipe (stem) Sector DH-L b8-0"],["Pipe (stem) Sector DL-Y d112"],["Pipe (stem) Sector CQ-Y d59"],["Pipe (stem) Sector GW-W c1-6"],["Pipe (stem) Sector KC-V c2-1"],["Col 285 Sector UG-I b24-5"],["Pipe (stem) Sector DH-L b8-4"],["Snake Sector FB-X c1-1"],["Snake Sector UJ-Q b5-4"],["Pipe (stem) Sector KC-V c2-1"],["HIP 84930"],["Snake Sector XP-O b6-2"],["Snake Sector ZK-O b6-3"],["Pipe (stem) Sector JC-V c2-23"],["Col 285 Sector GY-H c10-14"],["Snake Sector PI-T c3-14"],["Snake Sector HR-W d1-105"],["Col 359 Sector EQ-O d6-124"],["Col 359 Sector IW-M d7-10"],["Col 359 Sector PX-E b27-6"],["Col 359 Sector QX-E b27-1"],["Col 359 Sector TD-D b28-2"],["Col 359 Sector IW-M d7-67"],["Col 359 Sector WJ-B b29-3"],["Col 359 Sector AQ-Z b29-0"],["Col 359 Sector IW-M d7-37"],["Col 359 Sector NX-Z c14-17"],["Col 359 Sector MC-L d8-22"],["Col 359 Sector IW-M d7-1"],["Col 359 Sector MC-L d8-111"],["Col 359 Sector JC-W b31-4"],["M7 Sector NE-W b3-0"],["Bleae Thua WK-R c4-4"]]}]}"""
MOCK_HTTP_CMDR_INFO_DATA = """{"spreadsheetId":"1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE","valueRanges":[{"range":"'System Info'!G1:I1000","majorDimension":"ROWS","values":[["CMDR","Max Cap","Cap Ship"],["Starting Inventory"],["In Transit"],["Kalran Oarn","724","Marasesti"],["Lucifer Wolfgang"],["Exil","792","Marasesti"],["Bolton54","784","Tritons Reach"],["Von MD","752","Marasesti"],["Meeces2911","752","Igneels Tooth"],["ChromaSlip"],["Lord Thunderwind","784","T2F-7KX"],["Alycans"],["ZombieJoe"],["DeathMagnet","794"],["Chriton Suen","784","Marasesti"],["Jikard","724","Marasesti"],["Kiesman","","Marasesti"],["Double Standard","758","Marasesti"],["Caddymac","","Marasesti"],["BLASC","784","Marasesti"],["Beauseant","784","Black hole in the wall"],["Niokman","","Marasesti"],["Celok","","Marasesti"],["Deaththro18","780","Tritons Reach"],["Zenith2195","","Tritons Reach"],["Caerwyrn","","Tritons Reach"],["Reenuip","","Tritons Reach"],["Priapism","","Tritons Reach"],["THEWOLFE208","","Tritons Reach"],["Wolfe3","","Tritons Reach"],["Tristamen","","Tritons Reach"],["Gumbilicious","","T2F-7KX"],["Shyr","","T2F-7KX"],["Matt Flatlands","","T2F-7KX"],["Yossarian","","T2F-7KX"],["Henry Blackfeather","","T2F-7KX"],["Audio Kyrios","","T2F-7KX"],["Xavier Saskuatch","","T2F-7KX"],["xmotis","","T2F-7KX"],["neogia","784","Stella Obscura"],["Chriton Suen","","Marasesti"],["Jetreyu","784","Roxy's Roost"],["NicBic","0","The Citadel"],["TOGSolid","","Tritons Reach"],["Correction","","Roxy's Roost"],["GERTY08"],["Jador Mak","724","Nebulous Terraforming"],["Javeh"],["Atlantik JCX"],["Spartan086x","784","Sword of Meridia"],["Jaghut","","Jolly Roger"],["Violet Truth","","Red Lobster"],["mac Drake","784","Jolly Roger"],["Cerebral Chaos","790"],["J3D1T4IT"],["CryptoHash","8","NAC Hyperspace Bypass"],["War Intern"],["Dr Lichen","720","The Citadel"],["Tetteta","784","Fleet Carrier"],["bolton54","784"],["The Wise Mans Fear"],["Mercenary Venus","436"],["tetteta","30"]]}]}"""
MOCK_HTTP_EDMC_PLUGIN_USAGE_DATA = """{"range":"'EDMC Plugin Settings'!E1:G1001","majorDimension":"ROWS","values":[["Userlist","Version","Last Access (UTC)"],["Meeces2911","1.2.1","2025-04-10 06:30:36"],["Chriton Suen","1.0.3-beta2"],["Jador Mak","1.0.3-beta1"],["Jetreyu","1.2.0-beta1","2025-04-10 00:04:01"],["Lord Thunderwind","1.2.0","2025-04-04 13:41:20"],["mac Drake","1.2.0","2025-04-09 18:08:39"],["Beauseant","1.1.2","2025-04-09 00:38:40"],["neogia","1.2.0","2025-04-10 03:34:31"],["DeathMagnet","1.1.1","2025-04-10 03:43:19"],["CryptoHash","1.1.2","2025-04-02 14:48:28"],["NicBic","1.2.0","2025-04-09 18:36:10"],["tetteta","1.2.0","2025-04-06 20:12:59"],["bolton54","1.2.0","2025-04-09 19:36:25"],["Von MD","1.2.0","2025-04-06 15:29:04"],["Mercenary Venus","1.2.0","2025-04-05 23:58:42"]]}"""
MOCK_HTTP_EDMC_PLUGIN_USAGE_RES_DATA = """{"spreadsheetId":"1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE","tableRange":"'EDMC Plugin Settings'!E1:G16","updates":{"spreadsheetId":"1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE","updatedRange":"'EDMC Plugin Settings'!E17:G17","updatedRows":1,"updatedColumns":3,"updatedCells":3}}"""

class MockHTTPResponse:
    def __init__(self, *args, **kwargs):
        httpVerb = args[0][1] or '*UNKNOWN*'
        httpUrl = args[0][2] or '*UNKNOWN*'
        if httpVerb == "POST" or httpVerb == "PUT":
            httpBody = args[1]['json']
            ACTUAL_HTTP_PUT_POST_REQUESTS.append([httpUrl, copy.deepcopy(httpBody)])
        elif httpVerb == "GET":
            ACTUAL_HTTP_GET_REQUESTS.append(httpUrl)

    @property
    def status_code(self) -> int:
        res = MOCK_HTTP_RESPONSE_CODES.pop(0) if len(MOCK_HTTP_RESPONSE_CODES) > 0 else requests.codes.OK
        logger.debug(f'MockHTTPResponse::status_code returning: {res}, {len(MOCK_HTTP_RESPONSE_CODES)} remaining')
        return res

    @staticmethod
    def json():
        res = MOCK_HTTP_RESPONSES.pop(0) if len(MOCK_HTTP_RESPONSES) > 0 else { 'body': 'mock response' }
        logger.critical(f'{len(MOCK_HTTP_RESPONSES)} HTTP Responses remaining')
        #logger.debug(f'MockHTTPResponse::json returning: {res}')
        return res
    
    @staticmethod
    def raise_for_status() -> None:
        logger.debug('MockHTTPResponse::raise_for_status stubbed, skipping ')
        return None

@pytest.fixture()
def __global_mocks(monkeypatch):
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

def __add_mocked_http_response(responseBody: str | None = None, responseCode: int | None = None):
    # Not particularly great framework, but it works for now...
    if responseBody:
        MOCK_HTTP_RESPONSES.append(responseBody)
    if responseCode:
        MOCK_HTTP_RESPONSE_CODES.append(responseCode)

def __plugin_start_stop():
    MOCK_HTTP_RESPONSES.clear()
    MOCK_HTTP_RESPONSE_CODES.clear()

    __add_mocked_http_response(json.loads(MOCK_HTTP_OVERVIEW_DATA))               # Initial call to GET /spreadsheets in check_and_authorise_access_to_spreadsheet
    __add_mocked_http_response(json.loads(MOCK_HTTP_OVERVIEW_DATA))               # Second call to GET /spreadsheets in check_and_authorise_access_to_spreadsheet      #TODO: We should probably avoid doing this one
    __add_mocked_http_response(json.loads(MOCK_HTTP_EDMC_PLUGIN_SETTINGS_DATA))   # Call to GET /values:batchGet in populate_initial_settings
    __add_mocked_http_response(json.loads(MOCK_HTTP_ACTIVE_SYSTEMS_DATA))         # Second call to GET /values:batchGet populate_initial_settings after lookups are set
    __add_mocked_http_response(json.loads(MOCK_HTTP_CMDR_INFO_DATA))              # Call to GET /values:batchGet in populate_cmdr_data
    __add_mocked_http_response(json.loads(MOCK_HTTP_EDMC_PLUGIN_USAGE_DATA))      # Call to GET /values in record_plugin_usage
    __add_mocked_http_response(json.loads(MOCK_HTTP_EDMC_PLUGIN_USAGE_RES_DATA))  # Call to POST /values:append in record_plugin_usage
    __add_mocked_http_response(json.loads(MOCK_HTTP_EDMC_PLUGIN_USAGE_RES_DATA))  # Call to POST /values:append in record_plugin_usage (yes, we get the response twice)
    __add_mocked_http_response(json.loads(MOCK_HTTP_EDMC_PLUGIN_USAGE_RES_DATA))  # Call to POST /spreadsheets:batchUpdate in record_plugin_usage to set the formatting    

    plugin.plugin_start3("..\\")
    assert plugin.this.thread
    assert plugin.this.thread.is_alive()

    # Give the plugin a little time to start to avoid mixing the starting and quitting logs
    time.sleep(1)

    assert plugin.this.sheet
    assert plugin.this.sheet.lookupRanges
    assert len(plugin.this.sheet.lookupRanges) == 15
    assert plugin.this.sheet.carrierTabNames
    assert len(plugin.this.sheet.carrierTabNames) == 22

    assert plugin.this.thread

    config.config.shutting_down = True
    plugin.plugin_stop()
    assert plugin.this.thread == None

    # This shouldn't be necessary if we're checking for everything, but we're not for now
    MOCK_HTTP_RESPONSES.clear()
    MOCK_HTTP_RESPONSE_CODES.clear()
    assert len(MOCK_HTTP_RESPONSES) == 0
    assert len(MOCK_HTTP_RESPONSE_CODES) == 0
