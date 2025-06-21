import pytest
import logging
import re
import requests
import time

import sheet as plugin

# Import stubs
import config

from .sharedFunctions import ACTUAL_HTTP_PUT_POST_REQUESTS, ACTUAL_HTTP_GET_REQUESTS, MOCK_HTTP_RESPONSES, MOCK_HTTP_RESPONSE_CODES
from .sharedFunctions import __global_mocks, __add_mocked_http_response

logger = logging.getLogger()

@pytest.fixture(autouse=True)
def before_after_test(__global_mocks):
    """Default any settings before the run of each test"""
    config.config.shutting_down = False
    ACTUAL_HTTP_PUT_POST_REQUESTS.clear()
    ACTUAL_HTTP_GET_REQUESTS.clear()
    MOCK_HTTP_RESPONSES.clear()
    MOCK_HTTP_RESPONSE_CODES.clear()

def test__A1_to_index():
    sheet = plugin.Sheet(None, None)
    
    [col, row] = sheet._A1_to_index('A59')
    assert col == 0
    assert row == 58

    [col, row] = sheet._A1_to_index('BD')
    assert col == 55
    assert row == -1

    [col, row] = sheet._A1_to_index('AAA')
    assert col == 702
    assert row == -1

    [col, row] = sheet._A1_to_index('ACZ')
    assert col == 779
    assert row == -1

def test__get_datetime_string():
    sheet = plugin.Sheet(None, None)

    ts = sheet._get_datetime_string()
    assert ts
    assert re.search('\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}', ts)

    ts = sheet._get_datetime_string(None)
    assert ts
    assert re.search('\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}', ts)

    ts = sheet._get_datetime_string('2025-05-10T06:52:59Z')
    assert ts
    assert re.search('\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}', ts)
    assert ts == '2025-05-10 06:52:59'

    ts = sheet._get_datetime_string('')
    assert ts == ''

def test_populate_initial_settings(monkeypatch):
    monkeypatch.setattr(plugin.Sheet, 'check_and_authorise_access_to_spreadsheet', lambda *args, **kwargs: logger.debug('Sheet::check_and_authorise_access_to_spreadsheet stubbed, skipping '))

    session = requests.Session()
    sheet = plugin.Sheet(None, session)

    mock_edmc_plugin_settings_data = {
        'spreadsheetId': '1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE',
        'valueRanges': [
            {
                'range': "'EDMC Plugin Settings'!A1:C1001",
                'majorDimension': 'ROWS',
                'values': [
                    ['Killswitches'],
                    ['Enabled', 'TRUE'],
                    ['Minimum Version', '1.2.0'],
                    ['CMDR Info Update', 'TRUE'],
                    ['Carrier BuySell Order', 'TRUE'],
                    ['SCS Reconcile Delay In Seconds', '60'],
                    ['SCS Data Populate', 'FALSE'],
                    [],
                    ['Lookups'],
                    ['Carrier Location', 'I1'],
                    ['Carrier Buy Orders', 'H3:J22'],
                    ['Carrier Jump Location', 'I2'],
                    ['SCS Sheet', 'SCS Offload'],
                    ['System Info Sheet', 'System Info'],
                    ['In Progress Systems', 'Data!A59:A88'],
                    ['Reconcile Mutex', "'SCS Offload'!X1"],
                    ['Systems With No Data', 'Data!BN:BN'],
                    [],
                    ['Commodity Mapping'],
                    ['ceramiccomposites', 'Ceramic Composites'],
                    ['cmmcomposite', 'CMM Composite'],
                    ['computercomponents', 'Computer Components'],
                    ['foodcartridges','Food Cartridges'],
                    ['fruitandvegetables', 'Fruit and Vedge'],
                    ['ceramicinsulatingmembrane', 'Insulating Membrane'],
                    ['insulatingmembrane', 'Insulating Membrane'],
                    ['liquidoxygen', 'Liquid Oxygen'],
                    ['medicaldiagnosticequipment', 'Medical Diagnostic Equipment'],
                    ['nonlethalweapons', 'Non-Lethal Weapons'],
                    ['powergenerators', 'Power Generators'],
                    ['waterpurifiers', 'Water Purifiers']
                ]
            },
            {
                'range': "'EDMC Plugin Settings'!J1:L1001",
                'majorDimension': 'ROWS',
                'values': [
                    ['Carriers', '', 'Sheet Name'],
                    ['Tritons Reach', 'K0X-94Z', 'Tritons Reach'],
                    ['Angry Whore -Tsh7-', 'T2F-7KX', 'T2F-7KX'],
                    ['Marasesti', 'V2Z-58Z', 'Marasesti'],
                    ["Roxy's Roost", 'Q0T-GQB', "Roxy's Roost"],
                    ['Galactic Bridge', 'GZB-80Z', 'Galactic Bridge'],
                    ['P.T.N Red Lobster', 'TZX-16K', 'Red Lobster'],
                    ['Igneels Tooth', 'X7H-9KW', 'Igneels Tooth'],
                    ["Poseidon's Kiss", 'LHM-2CZ', "Poseidon's Kiss"],
                    ['Bifröst', 'T2W-69Z', 'Bifröst'],
                    ['NAC Hyperspace Bypass', 'J9W-65Q', 'NAC Hyperspace Bypass'],
                ]
            },
            {
                'range': "'EDMC Plugin Settings'!O1:P1001",
                'majorDimension': 'ROWS',
                'values': [
                    ['Markets', 'Set By Owner'],
                    ['X7H-9KW', 'TRUE'],
                    ['LHM-2CZ', 'TRUE'],
                    ['T3H-N6K', 'TRUE']
                ]
            },
            {
                'range': "'EDMC Plugin Settings'!S1:V1001",
                'majorDimension': 'ROWS',
                'values': [
                    ['Sheet Functionality', 'Delivery', 'Timestamp', 'Buy Order Adjustment'],
                    ['SCS Offload', 'TRUE', 'TRUE', 'FALSE'],
                    ['Tritons Reach', 'TRUE', 'TRUE', 'FALSE'],
                    ['T2F-7KX', 'TRUE', 'TRUE', 'FALSE'],
                    ["Roxy's Roost", 'TRUE', 'TRUE', 'FALSE'],
                    ['Igneels Tooth', 'TRUE', 'TRUE', 'TRUE'],
                    ["Poseidon's Kiss", 'TRUE', 'TRUE', 'FALSE'],
                    ['Bifröst', 'TRUE', 'TRUE', 'FALSE'],
                ]
            }
        ]
    }

    # Eight known systems
    mock_active_systems_data = {
        'spreadsheetId': '1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE',
        'valueRanges': [
            {
                'range': 'Data!BH2:BH30',
                'majorDimension': 'ROWS',
                'values': [
                    ['Col 359 Sector IW-M d7-1'],
                    ['M7 Sector NE-W b3-0'],
                    ['Pipe (stem) Sector ZE-A d89']
                ]
            },
            {
                'range': "'System Info'!A1:A1000",
                'majorDimension': 'ROWS',
                'values': [
                    ["System"],
                    ["COL 285 SECTOR DT-E B26-9"],
                    ["HIP 94491"],
                    ["Col 285 Sector DT-E b26-2"],
                    ["Col 285 Sector AG-O d6-122"],
                    ["Nunki"],
                    ["27 PHI SAGITTARII"],
                    ["COL 285 SECTOR RJ-E A55-5"],
                    ["HIP 90504"]
                ]
            }
        ]
    }

    # (First) Fifty known systems
    mock_active_systems_update_data = {
        'spreadsheetId': '1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE',
        'valueRanges': [
            {
                'range': 'Data!BH2:BH30',
                'majorDimension': 'ROWS',
                'values': [
                    ['Col 359 Sector IW-M d7-1'],
                    ['M7 Sector NE-W b3-0'],
                    ['Pipe (stem) Sector ZE-A d89']
                ]
            },
            {
                'range': "'System Info'!A10:A1000",
                'majorDimension': 'ROWS',
                'values': [
                    ["System"],
					["COL 285 SECTOR DT-E B26-9"],
                    ["HIP 94491"],
                    ["Col 285 Sector DT-E b26-2"],
                    ["Col 285 Sector AG-O d6-122"],
                    ["Nunki"],
                    ["27 PHI SAGITTARII"],
                    ["COL 285 SECTOR RJ-E A55-5"],
                    ["HIP 90504"],
                    ["Col 285 Sector CH-Z a57-3"],
                    ["Col 285 Sector GN-X A58-0"],
                    ["HIP 89535"],
                    ["COL 285 SECTOR JY-Y C14-15"],
                    ["COL 285 SECTOR HD-Z C14-22"],
                    ["COL 285 SECTOR UH-W B30-4"],
                    ["HIP 88440"],
                    ["COL 359 SECTOR OR-V D2-120"],
                    ["COL 359 SECTOR OR-V D2-47"],
                    ["COL 359 SECTOR YL-K B10-3"],
                    ["COL 359 SECTOR CS-I B11-7"],
                    ["COL 285 SECTOR JY-Y C14-15"],
                    ["HIP 94491"],
                    ["HIP 94491"],
                    ["HIP 94491"],
                    ["Col 359 Sector BJ-R c5-21"],
                    ["Col 359 Sector GP-P c6-31"],
                    ["Col 359 Sector GP-P c6-3"],
                    ["Col 359 Sector SX-T d3-48"],
                    ["COL 359 SECTOR LE-F B13-6"],
                    ["COL 359 SECTOR SX-T D3-133"],
                    ["Col 359 Sector OR-V d2-146"],
                    ["Pipe (bowl) Sector ZO-A b3"],
                    ["Col 359 Sector FP-P c6-18"],
                    ["Col 359 Sector GP-P c6-20"],
                    ["HIP 89573"],
                    ["Pipe (stem) Sector YJ-A c7"],
                    ["Col 359 Sector OR-V d2-146"],
                    ["Pipe (stem) Sector ZE-A d151"],
                    ["Pipe (stem) Sector BA-Z b3"],
                    ["HIP 85257"],
                    ["Pipe (stem) Sector ZE-A d101"],
                    ["Pipe (stem) Sector BA-Z b2"],
                    ["Pipe (stem) Sector ZE-A d151"],
                    ["HIP 85257"],
                    ["Pipe (stem) Sector YE-Z b1"],
                    ["Pipe (stem) Sector ZE-Z b4"],
                    ["Pipe (stem) Sector DL-X b1-0"],
                    ["Pipe (stem) Sector DL-X b1-7"],
                    ["Pipe (Stem) Sector GW-W C1-27"],
                    ["Pipe (stem) Sector GW-W c1-28"],
                    ["Pipe (stem) Sector ZE-A d89"]
                ]
            }
        ]
    }

    # next 161 known systems
    mock_active_systems_update2_data = {
        'spreadsheetId': '1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE',
        'valueRanges': [
            {
                'range': 'Data!BH2:BH30',
                'majorDimension': 'ROWS',
                'values': [
                    ['Col 359 Sector IW-M d7-1'],
                    ['M7 Sector NE-W b3-0'],
                    ['Pipe (stem) Sector ZE-A d89']
                ]
            },
            {
                'range': "'System Info'!A10:A1000",
                'majorDimension': 'ROWS',
                'values': [
                    ["COL 285 SECTOR DT-E B26-9"],
                    ["HIP 94491"],
                    ["Col 285 Sector DT-E b26-2"],
                    ["Col 285 Sector AG-O d6-122"],
                    ["Nunki"],
                    ["27 PHI SAGITTARII"],
                    ["COL 285 SECTOR RJ-E A55-5"],
                    ["HIP 90504"],
                    ["Col 285 Sector CH-Z a57-3"],
                    ["Col 285 Sector GN-X A58-0"],
                    ["HIP 89535"],
                    ["COL 285 SECTOR JY-Y C14-15"],
                    ["COL 285 SECTOR HD-Z C14-22"],
                    ["COL 285 SECTOR UH-W B30-4"],
                    ["HIP 88440"],
                    ["COL 359 SECTOR OR-V D2-120"],
                    ["COL 359 SECTOR OR-V D2-47"],
                    ["COL 359 SECTOR YL-K B10-3"],
                    ["COL 359 SECTOR CS-I B11-7"],
                    ["COL 285 SECTOR JY-Y C14-15"],
                    ["HIP 94491"],
                    ["HIP 94491"],
                    ["HIP 94491"],
                    ["Col 359 Sector BJ-R c5-21"],
                    ["Col 359 Sector GP-P c6-31"],
                    ["Col 359 Sector GP-P c6-3"],
                    ["Col 359 Sector SX-T d3-48"],
                    ["COL 359 SECTOR LE-F B13-6"],
                    ["COL 359 SECTOR SX-T D3-133"],
                    ["Col 359 Sector OR-V d2-146"],
                    ["Pipe (bowl) Sector ZO-A b3"],
                    ["Col 359 Sector FP-P c6-18"],
                    ["Col 359 Sector GP-P c6-20"],
                    ["HIP 89573"],
                    ["Pipe (stem) Sector YJ-A c7"],
                    ["Col 359 Sector OR-V d2-146"],
                    ["Pipe (stem) Sector ZE-A d151"],
                    ["Pipe (stem) Sector BA-Z b3"],
                    ["HIP 85257"],
                    ["Pipe (stem) Sector ZE-A d101"],
                    ["Pipe (stem) Sector BA-Z b2"],
                    ["Pipe (stem) Sector ZE-A d151"],
                    ["HIP 85257"],
                    ["Pipe (stem) Sector YE-Z b1"],
                    ["Pipe (stem) Sector ZE-Z b4"],
                    ["Pipe (stem) Sector DL-X b1-0"],
                    ["Pipe (stem) Sector DL-X b1-7"],
                    ["Pipe (Stem) Sector GW-W C1-27"],
                    ["Pipe (stem) Sector GW-W c1-28"],
                    ["Pipe (stem) Sector ZE-A d89"],
					["Pipe (Stem) Sector BQ-Y d80"],
                    ["Pipe (stem) Sector IH-V c2-18"],
                    ["Pipe (stem) Sector DL-Y d106"],
                    ["Pipe (stem) Sector KC-V c2-22"],
                    ["Pipe (stem) Sector DL-Y d66"],
                    ["Pipe (stem) Sector LN-S b4-1"],
                    ["Pipe (stem) Sector JX-T b3-2"],
                    ["Pipe (stem) Sector DL-Y d17"],
                    ["Pipe (stem) Sector MN-T c3-13"],
                    ["Pipe (stem) Sector OI-T c3-19"],
                    ["Pipe (stem) Sector ZA-N b7-4"],
                    ["Pipe (stem) Sector DH-L b8-0"],
                    ["Pipe (stem) Sector DL-Y d112"],
                    ["Pipe (stem) Sector CQ-Y d59"],
                    ["Pipe (stem) Sector GW-W c1-6"],
                    ["Pipe (stem) Sector KC-V c2-1"],
                    ["Col 285 Sector UG-I b24-5"],
                    ["Pipe (stem) Sector DH-L b8-4"],
                    ["Snake Sector FB-X c1-1"],
                    ["Snake Sector UJ-Q b5-4"],
                    ["HIP 84930"],
                    ["Snake Sector XP-O b6-2"],
                    ["Snake Sector ZK-O b6-3"],
                    ["Pipe (stem) Sector JC-V c2-23"],
                    ["Col 285 Sector GY-H c10-14"],
                    ["Snake Sector PI-T c3-14"],
                    ["Snake Sector HR-W d1-105"],
                    ["Col 359 Sector EQ-O d6-124"],
                    ["Col 359 Sector IW-M d7-10"],
                    ["Col 359 Sector PX-E b27-6"],
                    ["Col 359 Sector QX-E b27-1"],
                    ["Col 359 Sector TD-D b28-2"],
                    ["Col 359 Sector IW-M d7-67"],
                    ["Col 359 Sector WJ-B b29-3"],
                    ["Col 359 Sector AQ-Z b29-0"],
                    ["Col 359 Sector IW-M d7-37"],
                    ["Col 359 Sector NX-Z c14-17"],
                    ["Col 359 Sector MC-L d8-22"],
                    ["Col 359 Sector IW-M d7-1"],
                    ["Col 359 Sector MC-L d8-111"],
                    ["Col 359 Sector JC-W b31-4"],
                    ["M7 Sector NE-W b3-0"],
                    ["M7 Sector YZ-Y d47"],
                    ["M7 Sector YZ-Y d18"],
                    ["M7 Sector UQ-S b5-0"],
                    ["M7 Sector WK-W c2-10"],
                    ["M7 Sector WK-W c2-7"],
                    ["M7 Sector YW-Q b6-2"],
                    ["M7 Sector CG-X d1-90"],
                    ["M7 Sector FY-O b7-3"],
                    ["M7 Sector JE-N b8-6"],
                    ["M7 Sector HS-S c4-26"],
                    ["M7 Sector HS-S c4-12"],
                    ["M7 Sector GM-V d2-107"],
                    ["M7 Sector VW-H b11-3"],
                    ["Col 359 Sector GL-D c13-2"],
                    ["M7 Sector LY-Q c5-16"],
                    ["M7 Sector GM-V d2-57"],
                    ["M7 Sector DJ-E b13-6"],
                    ["M7 Sector OE-P c6-4"],
                    ["M7 Sector CJ-E b13-0"],
                    ["M7 Sector OE-P c6-7"],
                    ["M7 Sector IA-B b15-6"],
                    ["M7 Sector IA-B b15-0"],
                    ["M7 Sector JS-T d3-131"],
                    ["M7 Sector QP-N c7-1"],
                    ["M7 Sector MG-Z b15-3"],
                    ["M7 Sector QM-X b16-5"],
                    ["M7 Sector UV-L C8-0"],
                    ["Arietis Sector BV-P b5-4"],
                    ["Pru Euq HY-Y b41-5"],
                    ["Pru Euq LE-X b42-4"],
                    ["Pru Euq JJ-X b42-6"],
                    ["Pru Euq NP-V b43-2"],
                    ["Pru Euq RV-T b44-6"],
                    ["R CrA Sector KC-V c2-22"],
                    ["Beta Coronae Austrinae"],
                    ["Pru Euq RV-T b44-5"],
                    ["M7 Sector VV-L c8-12"],
                    ["Col 285 Sector VO-N b21-0"],
                    ["Pru Euq VB-S b45-5"],
                    ["Pru Euq VB-S b45-1"],
                    ["Pru Euq ZD-I c23-14"],
                    ["Pru Euq YH-Q b46-3"],
                    ["Pru Euq LW-E d11-50"],
                    ["Pru Euq BZ-H c23-15"],
                    ["Pru Euq LW-E d11-59"],
                    ["Cephei Sector XO-A b2"],
                    ["Pru Euq CO-O b47-1"],
                    ["Pru Euq DK-G c24-1"],
                    ["Pru Euq JA-L b49-2"],
                    ["Pru Euq KA-L b49-5"],
                    ["Pru Euq PC-D d12-83"],
                    ["Pru Euq LW-E d11-61"],
                    ["Pru Euq OG-J b50-5"],
                    ["Pru Euq HQ-E c25-5"],
                    ["Pru Euq HQ-E c25-16"],
                    ["Pru Euq TI-B d13-88"],
                    ["Pru Euq TI-B d13-132"],
                    ["Pru Euq LW-C c26-0"],
                    ["Pru Euq TI-B d13-80"],
                    ["Pru Euq TI-B d13-13"],
                    ["Pru Euq PC-B c27-6"],
                    ["Pru Euq DF-C b54-7"],
                    ["Pru Euq HL-A b55-5"],
                    ["Pru Euq TI-B d13-15"],
                    ["Pru Euq TI-B d13-32"],
                    ["Pru Euq SI-Z c27-0"],
                    ["Pru Euq SI-Z c27-12"],
                    ["Pru Euq OX-W B56-6"],
                    ["Pru Euq WO-X c28-6"],
                    ["Pru Euq WO-X c28-13"],
                    ["Pru Euq WO-X c28-11"],
                    ["Pru Euq YJ-X c28-23"],
                    ["Pru Euq YJ-X c28-35"],
                    ["Pru Euq ZJ-X c28-4"],
                    ["Pru Euq AF-T b58-8"],
                    ["Pru Euq ZJ-X c28-17"],
                    ["Pru Euq AF-T b58-5"],
                    ["Bleae Thua FB-A c35"],
                    ["Pru Euq WT-U b57-10"],
                    ["Bleae Thua LN-Y b8"],
                    ["Bleae Thua LN-Y b3"],
                    ["Pru Euq XO-Z d13-11"],
                    ["Bleae Thua MN-Y b2"],
                    ["Swoiwns CV-L a117-2"],
                    ["Bleae Thua SO-W b1-7"],
                    ["Swoiwns SK-C d14-104"],
                    ["Swoiwns CQ-L a117-4"],
                    ["Swoiwns GW-J a118-0"],
                    ["Bleae Thua JH-Y c6"],
                    ["Bleae Thua WU-U b2-8"],
                    ["Swoiwns HR-J a118-0"],
                    ["Bleae Thua JH-Y c31"],
                    ["Pru Euq PX-W b56-3"],
                    ["Swoiwns ET-E b59-6"],
                    ["Bleae Thua AB-T b3-6"],
                    ["HD 165921"],
                    ["Bleae Thua AB-T b3-7"],
                    ["Bleae Thua XF-T b3-8"],
                    ["Bleae Thua BM-R b4-5"],
                    ["Bleae Thua MN-W c1-15"],
                    ["Bleae Thua OY-U c2-22"],
                    ["Bleae Thua DX-P b5-4"],
                    ["Bleae Thua EB-A c23"],
                    ["Bleae Thua OY-U c2-14"],
                    ["Bleae Thua GD-O b6-6"],
                    ["Swoiwns NG-D c29-11"],
                    ["Bleae Thua GD-O b6-3"],
                    ["Bleae Thua XM-W d1-108"],
                    ["Bleae Thua MN-W c1-2"],
                    ["Bleae Thua XM-W d1-16"],
                    ["Bleae Thua LJ-M b7-1"],
                    ["Bleae Thua PP-K b8-0"],
                    ["Bleae Thua PP-K b8-2"],
                    ["Bleae Thua XM-W d1-19"],
                    ["Bleae Thua TV-I b9-3"],
                    ["Bleae Thua WK-R c4-4"],
                    ["Bleae Thua WK-R c4-17"],
                    ["Bleae Thua AI-F b11-4"],
                    ["Bleae Thua AR-P c5-24"]
                ]
            }
        ]
    }

    # (Last) Fifty known systems
    mock_active_systems_update3_data = {
        'spreadsheetId': '1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE',
        'valueRanges': [
            {
                'range': 'Data!BH2:BH30',
                'majorDimension': 'ROWS',
                'values': [
                    ['Col 359 Sector IW-M d7-1'],
                    ['M7 Sector NE-W b3-0'],
                    ['Pipe (stem) Sector ZE-A d89']
                ]
            },
            {
                'range': "'System Info'!A10:A1000",
                'majorDimension': 'ROWS',
                'values': [
					["Pru Euq WO-X c28-13"],
                    ["Pru Euq WO-X c28-11"],
                    ["Pru Euq YJ-X c28-23"],
                    ["Pru Euq YJ-X c28-35"],
                    ["Pru Euq ZJ-X c28-4"],
                    ["Pru Euq AF-T b58-8"],
                    ["Pru Euq ZJ-X c28-17"],
                    ["Pru Euq AF-T b58-5"],
                    ["Bleae Thua FB-A c35"],
                    ["Pru Euq WT-U b57-10"],
                    ["Bleae Thua LN-Y b8"],
                    ["Bleae Thua LN-Y b3"],
                    ["Pru Euq XO-Z d13-11"],
                    ["Bleae Thua MN-Y b2"],
                    ["Swoiwns CV-L a117-2"],
                    ["Bleae Thua SO-W b1-7"],
                    ["Swoiwns SK-C d14-104"],
                    ["Swoiwns CQ-L a117-4"],
                    ["Swoiwns GW-J a118-0"],
                    ["Bleae Thua JH-Y c6"],
                    ["Bleae Thua WU-U b2-8"],
                    ["Swoiwns HR-J a118-0"],
                    ["Bleae Thua JH-Y c31"],
                    ["Pru Euq PX-W b56-3"],
                    ["Swoiwns ET-E b59-6"],
                    ["Bleae Thua AB-T b3-6"],
                    ["HD 165921"],
                    ["Bleae Thua AB-T b3-7"],
                    ["Bleae Thua XF-T b3-8"],
                    ["Bleae Thua BM-R b4-5"],
                    ["Bleae Thua MN-W c1-15"],
                    ["Bleae Thua OY-U c2-22"],
                    ["Bleae Thua DX-P b5-4"],
                    ["Bleae Thua EB-A c23"],
                    ["Bleae Thua OY-U c2-14"],
                    ["Bleae Thua GD-O b6-6"],
                    ["Swoiwns NG-D c29-11"],
                    ["Bleae Thua GD-O b6-3"],
                    ["Bleae Thua XM-W d1-108"],
                    ["Bleae Thua MN-W c1-2"],
                    ["Bleae Thua XM-W d1-16"],
                    ["Bleae Thua LJ-M b7-1"],
                    ["Bleae Thua PP-K b8-0"],
                    ["Bleae Thua PP-K b8-2"],
                    ["Bleae Thua XM-W d1-19"],
                    ["Bleae Thua TV-I b9-3"],
                    ["Bleae Thua WK-R c4-4"],
                    ["Bleae Thua WK-R c4-17"],
                    ["Bleae Thua AI-F b11-4"],
                    ["Bleae Thua AR-P c5-24"]
                ]
            }
        ]
    }

    __add_mocked_http_response(mock_edmc_plugin_settings_data)
    __add_mocked_http_response(mock_active_systems_data)
    assert len(MOCK_HTTP_RESPONSES) == 2

    ACTUAL_HTTP_GET_REQUESTS.clear()
    sheet.populate_initial_settings()

    assert len(ACTUAL_HTTP_GET_REQUESTS) == 2
    assert ACTUAL_HTTP_GET_REQUESTS.pop(0) == "https://sheets.googleapis.com/v4/spreadsheets/1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE/values:batchGet?ranges='EDMC Plugin Settings'!A:C&ranges='EDMC Plugin Settings'!J:L&ranges='EDMC Plugin Settings'!O:P&ranges='EDMC Plugin Settings'!S:V&majorDimension=ROWS&valueRenderOption=FORMATTED_VALUE"
    assert ACTUAL_HTTP_GET_REQUESTS.pop(0) == "https://sheets.googleapis.com/v4/spreadsheets/1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE/values:batchGet?ranges=Data!A59:A88&ranges='System Info'!A1:A&majorDimension=ROWS&valueRenderOption=FORMATTED_VALUE"

    assert sheet.killswitches == {
        'enabled': 'true',
        'minimum version': '1.2.0',
        'cmdr info update': 'true',
        'carrier buysell order': 'true',
        'scs reconcile delay in seconds': '60',
        'scs data populate': 'false',
        'last updated': int(time.time())        # This could result in a flakey test, but mocking time is... not a great idea
    }

    assert sheet.lookupRanges == {
        'Carrier Location': 'I1',
        'Carrier Buy Orders': 'H3:J22',
        'Carrier Jump Location': 'I2',
        'SCS Sheet': 'SCS Offload',
        'System Info Sheet': 'System Info',
        'In Progress Systems': 'Data!A59:A88',
        'Reconcile Mutex': "'SCS Offload'!X1",
        'Systems With No Data': 'Data!BN:BN'
    }

    assert sheet.commodityNamesToNice == {
        'ceramiccomposites': 'Ceramic Composites',
        'cmmcomposite': 'CMM Composite',
        'computercomponents': 'Computer Components',
        'foodcartridges': 'Food Cartridges',
        'fruitandvegetables': 'Fruit and Vedge',
        'ceramicinsulatingmembrane': 'Insulating Membrane',
        'insulatingmembrane': 'Insulating Membrane',
        'liquidoxygen': 'Liquid Oxygen',
        'medicaldiagnosticequipment': 'Medical Diagnostic Equipment',
        'nonlethalweapons': 'Non-Lethal Weapons',
        'powergenerators': 'Power Generators',
        'waterpurifiers': 'Water Purifiers'
    }

    assert sheet.commodityNamesFromNice == {
        'Ceramic Composites': 'ceramiccomposites',
        'CMM Composite': 'cmmcomposite',
        'Computer Components': 'computercomponents',
        'Food Cartridges': 'foodcartridges',
        'Fruit and Vedge': 'fruitandvegetables',
        'Insulating Membrane': 'ceramicinsulatingmembrane',
        'Insulating Membrane': 'insulatingmembrane',
        'Liquid Oxygen': 'liquidoxygen',
        'Medical Diagnostic Equipment': 'medicaldiagnosticequipment',
        'Non-Lethal Weapons': 'nonlethalweapons',
        'Power Generators': 'powergenerators',
        'Water Purifiers': 'waterpurifiers'
    }

    assert sheet.carrierTabNames == {
        'K0X-94Z': 'Tritons Reach',
        'T2F-7KX': 'T2F-7KX',
        'V2Z-58Z': 'Marasesti',
        'Q0T-GQB': "Roxy's Roost",
        'GZB-80Z': 'Galactic Bridge',
        'TZX-16K': 'Red Lobster',
        'X7H-9KW': 'Igneels Tooth',
        'LHM-2CZ': "Poseidon's Kiss",
        'T2W-69Z': 'Bifröst',
        'J9W-65Q': 'NAC Hyperspace Bypass'
    }

    assert sheet.marketUpdatesSetBy == {
        'X7H-9KW': {
            'setByOwner': True
        },
        'LHM-2CZ': {
            'setByOwner': True
        },
        'T3H-N6K': {
            'setByOwner': True
        }
    }

    assert sheet.sheetFunctionality == {
        'SCS Offload': {
            'Delivery': True,
            'Timestamp': True,
            'Buy Order Adjustment': False
        },
        'Tritons Reach': {
            'Delivery': True,
            'Timestamp': True,
            'Buy Order Adjustment': False
        },
        'T2F-7KX': {
            'Delivery': True,
            'Timestamp': True,
            'Buy Order Adjustment': False
        },
        "Roxy's Roost": {
            'Delivery': True,
            'Timestamp': True,
            'Buy Order Adjustment': False
        },
        'Igneels Tooth': {
            'Delivery': True,
            'Timestamp': True,
            'Buy Order Adjustment': True
        },
        "Poseidon's Kiss": {
            'Delivery': True,
            'Timestamp': True,
            'Buy Order Adjustment': False
        },
        'Bifröst': {
            'Delivery': True,
            'Timestamp': True,
            'Buy Order Adjustment': False
        }
    }

    assert sheet.systemsInProgress == [
        'Col 359 Sector IW-M d7-1',
        'M7 Sector NE-W b3-0',
        'Pipe (stem) Sector ZE-A d89'
    ]

    assert sheet.highestKnownSystemRow == 8 + 1    # Including the header row
    assert len(sheet.lastFiftyCompletedSystems) == 8
    assert sheet.lastFiftyCompletedSystems == [
        'HIP 90504',
        'COL 285 SECTOR RJ-E A55-5',
        '27 PHI SAGITTARII',
        'Nunki',
        'Col 285 Sector AG-O d6-122',
        'Col 285 Sector DT-E b26-2',
        'HIP 94491',
        'COL 285 SECTOR DT-E B26-9',
    ]

    __add_mocked_http_response(mock_edmc_plugin_settings_data)
    __add_mocked_http_response(mock_active_systems_update_data)
    assert len(MOCK_HTTP_RESPONSES) == 2

    ACTUAL_HTTP_GET_REQUESTS.clear()
    sheet.populate_initial_settings()

    assert len(ACTUAL_HTTP_GET_REQUESTS) == 2
    assert ACTUAL_HTTP_GET_REQUESTS.pop(0) == "https://sheets.googleapis.com/v4/spreadsheets/1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE/values:batchGet?ranges='EDMC Plugin Settings'!A:C&ranges='EDMC Plugin Settings'!J:L&ranges='EDMC Plugin Settings'!O:P&ranges='EDMC Plugin Settings'!S:V&majorDimension=ROWS&valueRenderOption=FORMATTED_VALUE"
    assert ACTUAL_HTTP_GET_REQUESTS.pop(0) == "https://sheets.googleapis.com/v4/spreadsheets/1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE/values:batchGet?ranges=Data!A59:A88&ranges='System Info'!A1:A&majorDimension=ROWS&valueRenderOption=FORMATTED_VALUE"

    assert sheet.highestKnownSystemRow == 51
    assert len(sheet.lastFiftyCompletedSystems) == 43   # There are some 'duplicates' in here... For now, ignore them, as it doesn't matter for our usecase in determining whether its a known system or not
    assert sheet.lastFiftyCompletedSystems == [
        "Pipe (stem) Sector ZE-A d89",
        "Pipe (stem) Sector GW-W c1-28",
        "Pipe (Stem) Sector GW-W C1-27",
        "Pipe (stem) Sector DL-X b1-7",
        "Pipe (stem) Sector DL-X b1-0",
        "Pipe (stem) Sector ZE-Z b4",
        "Pipe (stem) Sector YE-Z b1",
        "HIP 85257",
        "Pipe (stem) Sector ZE-A d151",
        "Pipe (stem) Sector BA-Z b2",
        "Pipe (stem) Sector ZE-A d101",
        "Pipe (stem) Sector BA-Z b3",
        "Col 359 Sector OR-V d2-146",
        "Pipe (stem) Sector YJ-A c7",
        "HIP 89573",
        "Col 359 Sector GP-P c6-20",
        "Col 359 Sector FP-P c6-18",
        "Pipe (bowl) Sector ZO-A b3",
        "COL 359 SECTOR SX-T D3-133",
        "COL 359 SECTOR LE-F B13-6",
        "Col 359 Sector SX-T d3-48",
        "Col 359 Sector GP-P c6-3",
        "Col 359 Sector GP-P c6-31",
        "Col 359 Sector BJ-R c5-21",
        "HIP 94491",
        "COL 285 SECTOR JY-Y C14-15",
        "COL 359 SECTOR CS-I B11-7",
        "COL 359 SECTOR YL-K B10-3",
        "COL 359 SECTOR OR-V D2-47",
        "COL 359 SECTOR OR-V D2-120",
        "HIP 88440",
        "COL 285 SECTOR UH-W B30-4",
        "COL 285 SECTOR HD-Z C14-22",
        "HIP 89535",
        "Col 285 Sector GN-X A58-0",
        "Col 285 Sector CH-Z a57-3",
        "HIP 90504",
        "COL 285 SECTOR RJ-E A55-5",
        "27 PHI SAGITTARII",
        "Nunki",
        "Col 285 Sector AG-O d6-122",
        "Col 285 Sector DT-E b26-2",
        "COL 285 SECTOR DT-E B26-9"
    ]

    __add_mocked_http_response(mock_edmc_plugin_settings_data)
    __add_mocked_http_response(mock_active_systems_update2_data)
    assert len(MOCK_HTTP_RESPONSES) == 2

    ACTUAL_HTTP_GET_REQUESTS.clear()
    sheet.populate_initial_settings()

    assert len(ACTUAL_HTTP_GET_REQUESTS) == 2
    assert ACTUAL_HTTP_GET_REQUESTS.pop(0) == "https://sheets.googleapis.com/v4/spreadsheets/1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE/values:batchGet?ranges='EDMC Plugin Settings'!A:C&ranges='EDMC Plugin Settings'!J:L&ranges='EDMC Plugin Settings'!O:P&ranges='EDMC Plugin Settings'!S:V&majorDimension=ROWS&valueRenderOption=FORMATTED_VALUE"
    assert ACTUAL_HTTP_GET_REQUESTS.pop(0) == "https://sheets.googleapis.com/v4/spreadsheets/1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE/values:batchGet?ranges=Data!A59:A88&ranges='System Info'!A2:A&majorDimension=ROWS&valueRenderOption=FORMATTED_VALUE"

    assert sheet.highestKnownSystemRow == 51 + 161
    assert len(sheet.lastFiftyCompletedSystems) == 50   # There are some 'duplicates' in here... For now, ignore them, as it doesn't matter for our usecase in determining whether its a known system or not
    assert sheet.lastFiftyCompletedSystems == [
        "Bleae Thua AR-P c5-24",
        "Bleae Thua AI-F b11-4",
        "Bleae Thua WK-R c4-17",
        "Bleae Thua WK-R c4-4",
        "Bleae Thua TV-I b9-3",
        "Bleae Thua XM-W d1-19",
        "Bleae Thua PP-K b8-2",
        "Bleae Thua PP-K b8-0",
        "Bleae Thua LJ-M b7-1",
        "Bleae Thua XM-W d1-16",
        "Bleae Thua MN-W c1-2",
        "Bleae Thua XM-W d1-108",
        "Bleae Thua GD-O b6-3",
        "Swoiwns NG-D c29-11",
        "Bleae Thua GD-O b6-6",
        "Bleae Thua OY-U c2-14",
        "Bleae Thua EB-A c23",
        "Bleae Thua DX-P b5-4",
        "Bleae Thua OY-U c2-22",
        "Bleae Thua MN-W c1-15",
        "Bleae Thua BM-R b4-5",
        "Bleae Thua XF-T b3-8",
        "Bleae Thua AB-T b3-7",
        "HD 165921",
        "Bleae Thua AB-T b3-6",
        "Swoiwns ET-E b59-6",
        "Pru Euq PX-W b56-3",
        "Bleae Thua JH-Y c31",
        "Swoiwns HR-J a118-0",
        "Bleae Thua WU-U b2-8",
        "Bleae Thua JH-Y c6",
        "Swoiwns GW-J a118-0",
        "Swoiwns CQ-L a117-4",
        "Swoiwns SK-C d14-104",
        "Bleae Thua SO-W b1-7",
        "Swoiwns CV-L a117-2",
        "Bleae Thua MN-Y b2",
        "Pru Euq XO-Z d13-11",
        "Bleae Thua LN-Y b3",
        "Bleae Thua LN-Y b8",
        "Pru Euq WT-U b57-10",
        "Bleae Thua FB-A c35",
        "Pru Euq AF-T b58-5",
        "Pru Euq ZJ-X c28-17",
        "Pru Euq AF-T b58-8",
        "Pru Euq ZJ-X c28-4",
        "Pru Euq YJ-X c28-35",
        "Pru Euq YJ-X c28-23",
        "Pru Euq WO-X c28-11",
        "Pru Euq WO-X c28-13"
    ]

    __add_mocked_http_response(mock_edmc_plugin_settings_data)
    __add_mocked_http_response(mock_active_systems_update3_data)
    assert len(MOCK_HTTP_RESPONSES) == 2

    ACTUAL_HTTP_GET_REQUESTS.clear()
    sheet.populate_initial_settings()

    assert len(ACTUAL_HTTP_GET_REQUESTS) == 2
    assert ACTUAL_HTTP_GET_REQUESTS.pop(0) == "https://sheets.googleapis.com/v4/spreadsheets/1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE/values:batchGet?ranges='EDMC Plugin Settings'!A:C&ranges='EDMC Plugin Settings'!J:L&ranges='EDMC Plugin Settings'!O:P&ranges='EDMC Plugin Settings'!S:V&majorDimension=ROWS&valueRenderOption=FORMATTED_VALUE"
    assert ACTUAL_HTTP_GET_REQUESTS.pop(0) == "https://sheets.googleapis.com/v4/spreadsheets/1eTM0sXZ1Jr-L-u6ywuhaRwezWnJsRRnYlQStCyv2IZE/values:batchGet?ranges=Data!A59:A88&ranges='System Info'!A163:A&majorDimension=ROWS&valueRenderOption=FORMATTED_VALUE"

    assert sheet.highestKnownSystemRow == 212
    assert len(sheet.lastFiftyCompletedSystems) == 50   # There are some 'duplicates' in here... For now, ignore them, as it doesn't matter for our usecase in determining whether its a known system or not
    assert sheet.lastFiftyCompletedSystems == [
        "Bleae Thua AR-P c5-24",
        "Bleae Thua AI-F b11-4",
        "Bleae Thua WK-R c4-17",
        "Bleae Thua WK-R c4-4",
        "Bleae Thua TV-I b9-3",
        "Bleae Thua XM-W d1-19",
        "Bleae Thua PP-K b8-2",
        "Bleae Thua PP-K b8-0",
        "Bleae Thua LJ-M b7-1",
        "Bleae Thua XM-W d1-16",
        "Bleae Thua MN-W c1-2",
        "Bleae Thua XM-W d1-108",
        "Bleae Thua GD-O b6-3",
        "Swoiwns NG-D c29-11",
        "Bleae Thua GD-O b6-6",
        "Bleae Thua OY-U c2-14",
        "Bleae Thua EB-A c23",
        "Bleae Thua DX-P b5-4",
        "Bleae Thua OY-U c2-22",
        "Bleae Thua MN-W c1-15",
        "Bleae Thua BM-R b4-5",
        "Bleae Thua XF-T b3-8",
        "Bleae Thua AB-T b3-7",
        "HD 165921",
        "Bleae Thua AB-T b3-6",
        "Swoiwns ET-E b59-6",
        "Pru Euq PX-W b56-3",
        "Bleae Thua JH-Y c31",
        "Swoiwns HR-J a118-0",
        "Bleae Thua WU-U b2-8",
        "Bleae Thua JH-Y c6",
        "Swoiwns GW-J a118-0",
        "Swoiwns CQ-L a117-4",
        "Swoiwns SK-C d14-104",
        "Bleae Thua SO-W b1-7",
        "Swoiwns CV-L a117-2",
        "Bleae Thua MN-Y b2",
        "Pru Euq XO-Z d13-11",
        "Bleae Thua LN-Y b3",
        "Bleae Thua LN-Y b8",
        "Pru Euq WT-U b57-10",
        "Bleae Thua FB-A c35",
        "Pru Euq AF-T b58-5",
        "Pru Euq ZJ-X c28-17",
        "Pru Euq AF-T b58-8",
        "Pru Euq ZJ-X c28-4",
        "Pru Euq YJ-X c28-35",
        "Pru Euq YJ-X c28-23",
        "Pru Euq WO-X c28-11",
        "Pru Euq WO-X c28-13"
    ]
