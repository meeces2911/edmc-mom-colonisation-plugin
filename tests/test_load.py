import pytest
import http.server
import requests
import json
import time
import logging
import webbrowser

import load as plugin
import auth
import tkinter as tk

MOCK_HTTP_RESPONSES: list[str] = []
MOCK_HTTP_RESPONSE_CODES: list[int] = []

MOCK_HTTP_AUTH_DATA = """/auth?state=pOiorvXGIISkV0xXGOyKOmH4_oRqfV1ReaIXEAptVrc&code=4/0AQSTgQGARr4HjUmniyldb5X6uWI5ChkrAsE6h5xJDzmJf55xaPmDAF2UmRb0MaM-kYW3Cw&scope=https://www.googleapis.com/auth/drive.file"""
MOCK_HTTP_OVERVIEW_DATA = """{"sheets":[{"properties":{"sheetId":1943482414,"title":"System Info"}},{"properties":{"sheetId":565128439,"title":"SCS Offload"}},{"properties":{"sheetId":346465544,"title":"Tritons Reach"}},{"properties":{"sheetId":1275960297,"title":"T2F-7KX"}},{"properties":{"sheetId":812258018,"title":"Marasesti"}},{"properties":{"sheetId":1264641940,"title":"Roxy's Roost"}},{"properties":{"sheetId":1282942153,"title":"Galactic Bridge"}},{"properties":{"sheetId":1273206209,"title":"Nebulous Terraforming"}},{"properties":{"sheetId":1159569395,"title":"Transylvania"}},{"properties":{"sheetId":1041708629,"title":"CLB Voqooe Lagoon"}},{"properties":{"sheetId":344510017,"title":"Sword of Meridia"}},{"properties":{"sheetId":816116202,"title":"The Citadel"}},{"properties":{"sheetId":628529931,"title":"Atlaran Delta"}},{"properties":{"sheetId":2142664989,"title":"Red Lobster"}},{"properties":{"sheetId":1223817771,"title":"Igneels Tooth"}},{"properties":{"sheetId":1397023568,"title":"Jolly Roger"}},{"properties":{"sheetId":388336710,"title":"Cerebral Cortex"}},{"properties":{"sheetId":1760610269,"title":"Black hole in the wall"}},{"properties":{"sheetId":1002218299,"title":"Poseidon's Kiss"}},{"properties":{"sheetId":1210069199,"title":"Bifröst"}},{"properties":{"sheetId":1038714848,"title":"USS Ballistic"}},{"properties":{"sheetId":1143171463,"title":"NAC Hyperspace Bypass"}},{"properties":{"sheetId":1376529251,"title":"Stella Obscura"}},{"properties":{"sheetId":1204848219,"title":"Data"}},{"properties":{"sheetId":623399360,"title":"Carrier"}},{"properties":{"sheetId":566513196,"title":"CMDR - Marasesti"}},{"properties":{"sheetId":281677435,"title":"FC Tritons Reach"}},{"properties":{"sheetId":980092843,"title":"CMDR - T2F-7KX"}},{"properties":{"sheetId":905743757,"title":"CMDR-Roxys Roost"}},{"properties":{"sheetId":1217399628,"title":"CMDR - Galactic Bridge"}},{"properties":{"sheetId":133746159,"title":"CMDR - Nebulous Terraforming"}},{"properties":{"sheetId":1968049995,"title":"CMDR - CLB Voqooe Lagoon"}},{"properties":{"sheetId":74373547,"title":"Buy orders"}},{"properties":{"sheetId":161489343,"title":"EDMC Plugin Settings"}},{"properties":{"sheetId":897372416,"title":"Detail3-Steel"}},{"properties":{"sheetId":820007652,"title":"Detail2-Polymers"}},{"properties":{"sheetId":1309255245,"title":"Detail1-Medical Diagnostic Equi"}},{"properties":{"sheetId":253393435,"title":"Colonization"}},{"properties":{"sheetId":1831405150,"title":"Shoppinglist"}},{"properties":{"sheetId":299245359,"title":"Sheet3"}}]}"""
MOCK_HTTP_EDMC_PLUGIN_SETTINGS_DATA = """{"spreadsheetId":"1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE","valueRanges":[{"range":"'EDMC Plugin Settings'!A1:C1001","majorDimension":"ROWS","values":[["Killswitches"],["Enabled","TRUE"],["Minimum Version","1.2.0"],["CMDR Info Update","TRUE"],["Carrier BuySell Order","TRUE"],["Carrier Location","TRUE"],["Carrier Jump","TRUE"],["Carrier Market Full","FALSE"],["SCS Sell Commodity","TRUE"],["CMDR BuySell Commodity","TRUE"],["Carrier Transfer","TRUE"],["Carrier Reconcile","FALSE"],[],["Lookups"],["Carrier Location","I1"],["Carrier Buy Orders","H3:J22"],["Carrier Jump Location","I2"],["Carrier Sum Cargo","AA:AB"],["Carrier Starting Inventory","A1:C20"],["SCS Sheet","SCS Offload"],["System Info Sheet","System Info"],["CMDR Info","G:I"],["In Progress Systems","Data!A59:A88"],[],["Commodity Mapping"],["ceramiccomposites","Ceramic Composites"],["cmmcomposite","CMM Composite"],["computercomponents","Computer Components"],["foodcartridges","Food Cartridges"],["fruitandvegetables","Fruit and Vedge"],["ceramicinsulatingmembrane","Insulating Membrane"],["insulatingmembrane","Insulating Membrane"],["liquidoxygen","Liquid Oxygen"],["medicaldiagnosticequipment","Medical Diagnostic Equipment"],["nonlethalweapons","Non-Lethal Weapons"],["powergenerators","Power Generators"],["waterpurifiers","Water Purifiers"]]},{"range":"'EDMC Plugin Settings'!J1:L1001","majorDimension":"ROWS","values":[["Carriers","","Sheet Name"],["Tritons Reach","K0X-94Z","Tritons Reach"],["Angry Whore -Tsh7-","T2F-7KX","T2F-7KX"],["Marasesti","V2Z-58Z","Marasesti"],["Roxy's Roost","Q0T-GQB","Roxy's Roost"],["Galactic Bridge","GZB-80Z","Galactic Bridge"],["Nebulous Terraforming","KBV-N9H","Nebulous Terraforming"],["CLB Voqooe Lagoon","G0Q-8KJ","CLB Voqooe Lagoon"],["Sword of Meridia","T9Z-LKT","Sword of Meridia"],["Atlaran Delta","H0M-1HB","Atlaran Delta"],["P.T.N Red Lobster","TZX-16K","Red Lobster"],["Igneels Tooth","X7H-9KW","Igneels Tooth"],["Jolly Roger","T3H-N6K","Jolly Roger"],["Cerebral Cortex","X8M-7VV","Cerebral Cortex"],["Black hole in the wall","HHY-45Z","Black hole in the wall"],["Poseidon's Kiss","LHM-2CZ","Poseidon's Kiss"],["Bifröst","T2W-69Z","Bifröst"],["USS Ballistic","TNL-L5H","USS Balistic"],["NAC Hyperspace Bypass","J9W-65Q","NAC Hyperspace Bypass"],["Stella Obscura","J4V-82Z","Stella Obscura"],["The Citadel","LNX-80Z","The Citadel"],["Transylvania","M3K-5SZ","Transylvania"]]},{"range":"'EDMC Plugin Settings'!O1:P1001","majorDimension":"ROWS","values":[["Markets","Set By Owner"],["X7H-9KW","TRUE"],["LHM-2CZ","TRUE"],["T3H-N6K","TRUE"]]},{"range":"'EDMC Plugin Settings'!S1:V1001","majorDimension":"ROWS","values":[["Sheet Functionality","Delivery","Timestamp","Buy Order Adjustment"],["SCS Offload","TRUE","TRUE","FALSE"],["Tritons Reach","TRUE","TRUE","FALSE"],["T2F-7KX","TRUE","TRUE","FALSE"],["Marasesti","TRUE","TRUE","FALSE"],["Roxy's Roost","TRUE","TRUE","FALSE"],["Galactic Bridge","TRUE","TRUE","FALSE"],["Nebulous Terraforming","TRUE","TRUE","FALSE"],["CLB Voqooe Lagoon","TRUE","TRUE","FALSE"],["Sword of Meridia","TRUE","TRUE","FALSE"],["Atlaran Delta","TRUE","TRUE","FALSE"],["Red Lobster","TRUE","TRUE","FALSE"],["Igneels Tooth","TRUE","TRUE","TRUE"],["Jolly Roger","TRUE","TRUE","FALSE"],["Cerebral Cortex","TRUE","TRUE","FALSE"],["Black hole in the wall","TRUE","TRUE","FALSE"],["Poseidon's Kiss","TRUE","TRUE","FALSE"],["Bifröst","TRUE","TRUE","FALSE"],["USS Ballistic","TRUE","TRUE","FALSE"],["NAC Hyperspace Bypass","TRUE","TRUE","FALSE"],["Stella Obscura","TRUE","TRUE","TRUE"],["The Citadel","TRUE","TRUE","FALSE"],["Transylvania","TRUE","TRUE","TRUE"]]}]}"""
MOCK_HTTP_ACTIVE_SYSTEMS_DATA = """{"spreadsheetId":"1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE","valueRanges":[{"range":"Data!A59:A88","majorDimension":"ROWS","values":[["System"],["Col 359 Sector IW-M d7-1"],["M7 Sector NE-W b3-0"],["Pipe (stem) Sector ZE-A d89"]]}]}"""
MOCK_HTTP_CMDR_INFO_DATA = """{"spreadsheetId":"1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE","valueRanges":[{"range":"'System Info'!G1:I1000","majorDimension":"ROWS","values":[["CMDR","Max Cap","Cap Ship"],["Starting Inventory"],["In Transit"],["Kalran Oarn","724","Marasesti"],["Lucifer Wolfgang"],["Exil","792","Marasesti"],["Bolton54","784","Tritons Reach"],["Von MD","752","Marasesti"],["Meeces2911","752","Igneels Tooth"],["ChromaSlip"],["Lord Thunderwind","784","T2F-7KX"],["Alycans"],["ZombieJoe"],["DeathMagnet","794"],["Chriton Suen","784","Marasesti"],["Jikard","724","Marasesti"],["Kiesman","","Marasesti"],["Double Standard","758","Marasesti"],["Caddymac","","Marasesti"],["BLASC","784","Marasesti"],["Beauseant","784","Black hole in the wall"],["Niokman","","Marasesti"],["Celok","","Marasesti"],["Deaththro18","780","Tritons Reach"],["Zenith2195","","Tritons Reach"],["Caerwyrn","","Tritons Reach"],["Reenuip","","Tritons Reach"],["Priapism","","Tritons Reach"],["THEWOLFE208","","Tritons Reach"],["Wolfe3","","Tritons Reach"],["Tristamen","","Tritons Reach"],["Gumbilicious","","T2F-7KX"],["Shyr","","T2F-7KX"],["Matt Flatlands","","T2F-7KX"],["Yossarian","","T2F-7KX"],["Henry Blackfeather","","T2F-7KX"],["Audio Kyrios","","T2F-7KX"],["Xavier Saskuatch","","T2F-7KX"],["xmotis","","T2F-7KX"],["neogia","784","Stella Obscura"],["Chriton Suen","","Marasesti"],["Jetreyu","784","Roxy's Roost"],["NicBic","0","The Citadel"],["TOGSolid","","Tritons Reach"],["Correction","","Roxy's Roost"],["GERTY08"],["Jador Mak","724","Nebulous Terraforming"],["Javeh"],["Atlantik JCX"],["Spartan086x","784","Sword of Meridia"],["Jaghut","","Jolly Roger"],["Violet Truth","","Red Lobster"],["mac Drake","784","Jolly Roger"],["Cerebral Chaos","790"],["J3D1T4IT"],["CryptoHash","8","NAC Hyperspace Bypass"],["War Intern"],["Dr Lichen","720","The Citadel"],["Tetteta","784","Fleet Carrier"],["bolton54","784"],["The Wise Mans Fear"],["Mercenary Venus","436"],["tetteta","30"]]}]}"""
MOCK_HTTP_EDMC_PLUGIN_USAGE_DATA = """{"range":"'EDMC Plugin Settings'!E1:G1001","majorDimension":"ROWS","values":[["Userlist","Version","Last Access (UTC)"],["Meeces2911","1.2.1","2025-04-10 06:30:36"],["Chriton Suen","1.0.3-beta2"],["Jador Mak","1.0.3-beta1"],["Jetreyu","1.2.0-beta1","2025-04-10 00:04:01"],["Lord Thunderwind","1.2.0","2025-04-04 13:41:20"],["mac Drake","1.2.0","2025-04-09 18:08:39"],["Beauseant","1.1.2","2025-04-09 00:38:40"],["neogia","1.2.0","2025-04-10 03:34:31"],["DeathMagnet","1.1.1","2025-04-10 03:43:19"],["CryptoHash","1.1.2","2025-04-02 14:48:28"],["NicBic","1.2.0","2025-04-09 18:36:10"],["tetteta","1.2.0","2025-04-06 20:12:59"],["bolton54","1.2.0","2025-04-09 19:36:25"],["Von MD","1.2.0","2025-04-06 15:29:04"],["Mercenary Venus","1.2.0","2025-04-05 23:58:42"]]}"""
MOCK_HTTP_EDMC_PLUGIN_USAGE_RES_DATA = """{"spreadsheetId":"1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE","tableRange":"'EDMC Plugin Settings'!E1:G16","updates":{"spreadsheetId":"1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE","updatedRange":"'EDMC Plugin Settings'!E17:G17","updatedRows":1,"updatedColumns":3,"updatedCells":3}}"""

logger = logging.getLogger()

class MockResponse:
    @property
    def status_code(self) -> int:
        res = MOCK_HTTP_RESPONSE_CODES.pop(0) if len(MOCK_HTTP_RESPONSE_CODES) > 0 else requests.codes.bad
        logger.debug(f'MockResponse::status_code returning: {res}')
        return res

    @staticmethod
    def json():
        res = MOCK_HTTP_RESPONSES.pop(0) if len(MOCK_HTTP_RESPONSES) > 0 else { 'body': 'mock response' }
        logger.debug(f'MockResponse::json returning: {res}')
        return res
    
    @staticmethod
    def raise_for_status() -> None:
        logger.debug('MockResponse::raise_for_status stubbed, skipping ')
        return None

@pytest.fixture(autouse=True)
def global_mocks(monkeypatch):
    # Return the next mock response in our list
    def mock_handle_request(*args, **kwargs):
        res = MOCK_HTTP_RESPONSES.pop(0) if len(MOCK_HTTP_RESPONSES) > 0 else 'mock response'
        logger.debug(f'global_mocks::mock_handle_request returning: {res}')
        return res
    
    def mock_webbrowser_open(*args, **kwargs) -> bool:
        logger.debug(f'webbrowser::open stubbed, called with: {args}')
        return True
    
    monkeypatch.setattr(webbrowser, 'open', lambda *args, **kwargs: mock_webbrowser_open)
    monkeypatch.setattr(http.server.HTTPServer, 'handle_request', lambda *args, **kwargs: mock_handle_request)
    monkeypatch.setattr(auth.LocalHTTPServer, 'worker', lambda *args, **kwargs: print('LocalHTTPServer::worker stubbed, skipping '))
    monkeypatch.setattr(auth.LocalHTTPServer, 'response', '**** LocalHTTPServer::response stubbed ****')
    monkeypatch.setattr(requests, 'get', lambda *args, **kwargs: print('requests::get stubbed, skipping '))
    monkeypatch.setattr(requests, 'post', lambda *args, **kwargs: print('requests::post stubbed, skipping '))
    monkeypatch.setattr(auth.Auth, 'auth', lambda *args, **kwargs: print('Auth::auth stubbed, skipping '))
    monkeypatch.setattr(requests.sessions.Session, 'request', lambda *args, **kwargs: MockResponse())

def _add_mocked_http_response(responseBody: str | None, responseCode: int | None):
    # Not particularly great framework, but it works for now...
    if responseBody:
        MOCK_HTTP_RESPONSES.append(responseBody)

    if responseCode:
        MOCK_HTTP_RESPONSE_CODES.append(responseCode)

@pytest.mark.timeout(5)
def test_plugin_start_stop():
    MOCK_HTTP_RESPONSES.clear()
    MOCK_HTTP_RESPONSE_CODES.clear()

    _add_mocked_http_response(json.loads(MOCK_HTTP_OVERVIEW_DATA), requests.codes.OK)               # Initial call to GET /spreadsheets in check_and_authorise_access_to_spreadsheet
    _add_mocked_http_response(json.loads(MOCK_HTTP_OVERVIEW_DATA), requests.codes.OK)               # Second call to GET /spreadsheets in check_and_authorise_access_to_spreadsheet      #TODO: We should probably avoid doing this one
    _add_mocked_http_response(json.loads(MOCK_HTTP_EDMC_PLUGIN_SETTINGS_DATA), requests.codes.OK)   # Call to GET /values:batchGet in populate_initial_settings
    _add_mocked_http_response(json.loads(MOCK_HTTP_ACTIVE_SYSTEMS_DATA), requests.codes.OK)         # Second call to GET /values:batchGet populate_initial_settings after lookups are set
    _add_mocked_http_response(json.loads(MOCK_HTTP_CMDR_INFO_DATA), requests.codes.OK)              # Call to GET /values:batchGet in populate_cmdr_data
    _add_mocked_http_response(json.loads(MOCK_HTTP_EDMC_PLUGIN_USAGE_DATA), requests.codes.OK)      # Call to GET /values in record_plugin_usage
    _add_mocked_http_response(json.loads(MOCK_HTTP_EDMC_PLUGIN_USAGE_RES_DATA), requests.codes.OK)  # Call to POST /values:append in record_plugin_usage
    _add_mocked_http_response(json.loads(MOCK_HTTP_EDMC_PLUGIN_USAGE_RES_DATA), requests.codes.OK)  # Call to POST /values:append in record_plugin_usage (yes, we get the response twice)
    

    plugin.plugin_start3("..\\")

    # Give the plugin a little time to start to avoid mixing the starting and quitting logs
    time.sleep(1)

    assert plugin.this.thread
    assert plugin.this.thread.is_alive()

    plugin.plugin_stop()
    assert plugin.this.thread == None

@pytest.mark.timeout(5)
def test_plugin_initial_startup():
    pass
    #plugin.initial_startup()
    #assert plugin.this.auth
    #assert plugin.this.sheet

    #assert plugin.this.killswitches

def test_clear_auth_token():
    pass
    #plugin.this.clearAuthButton = tk.Button()
    #plugin.clear_token_and_disable_button()