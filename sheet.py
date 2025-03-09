import logging
import requests
import time
import webbrowser
import tkinter as tk
import json

from config import config, appname
from auth import Auth, LocalHTTPServer
from pathlib import Path

plugin_name = Path(__file__).resolve().parent.name
logger = logging.getLogger(f'{appname}.{plugin_name}')

class Sheet:
    BASE_SHEET_END_POINT = 'https://sheets.googleapis.com'
    SPREADSHEET_ID = '1dB8Zty_tGoEHFjXQh5kfOeEfL_tsByRyZI8d_sY--4M'

    LOOKUP_CARRIER_LOCATION = 'Carrier Location'
    LOOKUP_CARRIER_BUY_ORDERS = 'Carrier Buy Orders'
    LOOKUP_CARRIER_JUMP_LOC = 'Carrier Jump Location'
    LOOKUP_SCS_SHEET_NAME = 'SCS Sheet'

    def __init__(self, auth: Auth, session: requests.Session):
        self.auth: Auth = auth
        self.requests_session: requests.Session = session
        self.sheets: dict[str, int] = {}

        self.killswitches: dict[str, str] = {}
        self.carrierTabNames: dict[str, str] = {}
        self.marketUpdatesSetBy: dict[str, dict] = {}
        self.lookupRanges: dict[str, str] = {}

        if not config.shutting_down:
            # If shutdown is called during the intial stages of auth, we won't have been initialised yet
            # So make sure we don't call config.get_str, as that blocks if config.shutting_down is true
            self.configSheetName = tk.StringVar(value=config.get_str('configSheetName', default='EDMC Plugin Settings'))
            
            self.check_and_authorise_access_to_spreadsheet()

    def check_and_authorise_access_to_spreadsheet(self) -> any:
        """Checks and (Re)Authorises access to the spreadsheet. Returns the current sheets"""
        logger.debug('Checking access to spreadsheet')
        res = self.requests_session.get(f'{self.BASE_SHEET_END_POINT}/v4/spreadsheets/{self.SPREADSHEET_ID}?fields=sheets/properties(sheetId,title)')
        sheet_list_json: any = res.json()
        logger.debug(f'{res}{sheet_list_json}')

        if res.status_code != requests.codes.ok:
            # Need to authorise this specific file
            logger.debug('404 - access not granted yet, showing picker')
            self.handler = LocalHTTPServer()
            self.handler.start()
            
            webbrowser.open(self.handler.gpickerEndpoint)
            logger.info('Waiting for auth response')
            while not self.handler.response:
                # spin
                time.sleep(1 / 10)
                
                # TODO: how does python properly handle timeouts
                
                # EDMC shutdown, bail
                if config.shutting_down:
                    logger.warning('Sheet Authorise - aborting, shutting down')
                    self.handler.close()
                    self.handler = None
                    return None
            
            self.handler.close()
            logger.debug(f'response: {self.handler.response}')
            
            # For now, lets ignore the response entirely and use our known values instead
            res = self.requests_session.get(f'{self.BASE_SHEET_END_POINT}/v4/spreadsheets/{self.SPREADSHEET_ID}?fields=sheets/properties(sheetId,title)')
            sheet_list_json = res.json()
            if res.status_code != requests.code.ok:
                res.raise_for_status()

            self.handler = None

        # {'sheets': [{'properties': {'sheetId': 944449574, 'title': 'Carrier'}}, {'properties': {'sheetId': 824956629, 'title': 'CMDR - Marasesti'}}, {'properties': {'sheetId': 1007636203, 'title': 'FC Tritons Reach'}}, {'properties': {'sheetId': 344055582, 'title': 'CMDR - T2F-7KX'}}, {'properties': {'sheetId': 1890618844, 'title': "CMDR-Roxy's Roost"}}, {'properties': {'sheetId': 684229219, 'title': 'CMDR - Galactic Bridge'}}, {'properties': {'sheetId': 1525608748, 'title': 'CMDR - Nebulous Terraforming'}}, {'properties': {'sheetId': 48909025, 'title': 'CMDR - CLB Voqooe Lagoon'}}, {'properties': {'sheetId': 1395555039, 'title': 'Buy orders'}}, {'properties': {'sheetId': 1241558540, 'title': 'EDMC Plugin Testing'}}, {'properties': {'sheetId': 943290351, 'title': 'WIP - System Info'}}, {'properties': {'sheetId': 1304500094, 'title': 'WIP - SCS Offload'}}, {'properties': {'sheetId': 480283806, 'title': 'WIP - Marasesti'}}, {'properties': {'sheetId': 584248853, 'title': 'Detail3-Steel'}}, {'properties': {'sheetId': 206284589, 'title': 'Detail2-Polymers'}}, {'properties': {'sheetId': 948337654, 'title': 'Detail1-Medical Diagnostic Equipment'}}, {'properties': {'sheetId': 1936079810, 'title': 'WIP - Data'}}, {'properties': {'sheetId': 2062075030, 'title': 'Sheet3'}}, {'properties': {'sheetId': 1653004935, 'title': 'Colonization'}}, {'properties': {'sheetId': 135970834, 'title': 'Shoppinglist'}}]}
        # Lets mangle this a bit to be more useful
        for sheet in sheet_list_json['sheets']:
            key = sheet['properties']['title']
            value = sheet['properties']['sheetId']
            self.sheets[key] = int(value)
        
    def fetch_data(self, query: str) -> any:
        """Actually send a request to Google"""
        base_url = f'{self.BASE_SHEET_END_POINT}/v4/spreadsheets/{self.SPREADSHEET_ID}/values/{query}'
        logger.debug(f'Sending request to GET {base_url}')
        try:
            token_refresh_attempted = False
            while True:
                res = self.requests_session.get(base_url)
                if res.status_code == requests.codes.ok:
                    return res.json()
                elif res.status_code == requests.codes.unauthorized:
                    if not token_refresh_attempted:
                        token_refresh_attempted = True
                        self.auth.refresh()
                        continue
                else:
                    logger.error(f'{res}{res.json()}')
                return {}
        except:
            return {}

    def insert_data(self, range: str, body: dict) -> None:
        """Add/update some data in the spreadsheet"""
        # POST https://sheets.googleapis.com/v4/spreadsheets/SPREADSHEET_ID/values/Sheet1!A1:E1:append?valueInputOption=VALUE_INPUT_OPTION
        # Append adds new rows to the end of the given range
        base_url = f'{self.BASE_SHEET_END_POINT}/v4/spreadsheets/{self.SPREADSHEET_ID}/values/{range}:append?valueInputOption=USER_ENTERED'
        logger.debug(f'Sending request to POST {base_url}')
        logger.debug(json.dumps(body))
        
        token_refresh_attempted = False
        while True:
            logger.debug('sending request...')
            logger.debug(self.requests_session.headers)
            res = self.requests_session.post(base_url, json=body)
            logger.debug(f'{res}{res.json()}')
            if res.status_code == requests.codes.ok:
                return res.json()
            elif res.status_code == requests.codes.unauthorized:
                if not token_refresh_attempted:
                    token_refresh_attempted = True
                    self.auth.refresh()
                    continue
            else:
                logger.error(f'{res}{res.json()}')
            return None

    def update_data(self, range: str, body: dict) -> None:
        """Updates existing data in the spreadsheet"""
        # PUT https://sheets.googleapis.com/v4/spreadsheets/{spreadsheetId}/values/{range}?valueInputOption=VALUE_INPUT_OPTION
        base_url = f'{self.BASE_SHEET_END_POINT}/v4/spreadsheets/{self.SPREADSHEET_ID}/values/{range}?valueInputOption=USER_ENTERED'
        logger.debug(f'Sending request to PUT {base_url}')
        logger.debug(json.dumps(body))

        token_refresh_attempted = False
        while True:
            logger.debug('sending request...')
            logger.debug(self.requests_session.headers)
            res = self.requests_session.put(base_url, json=body)
            logger.debug(f'{res}{res.json()}')
            if res.status_code == requests.codes.ok:
                return res.json()
            elif res.status_code == requests.codes.unauthorized:
                if not token_refresh_attempted:
                    token_refresh_attempted = True
                    self.auth.refresh()
                    continue
            else:
                logger.error(f'{res}{res.json()}')
            return None

    def populate_initial_settings(self) -> None:
        # Lets get everything on the settings sheet and wade through it
        # {{BASE_END_POINT}}/v4/spreadsheets/{{SPREADSHEET_ID}}/values/'EDMC Plugin Testing'!A:E
        logger.debug('Fetching latest settings')
        
        sheet = f"'{self.configSheetName.get()}'"
        query = 'A:C'
        data = self.fetch_data(f'{sheet}!{query}')
        logger.debug(data)
        
        # TODO: Error handling

        self.killswitches = {}
        self.carrierTabNames = {}
        self.marketUpdatesSetBy = {}
        self.lookupRanges = {}

        section_killswitches = False
        section_carriers = False
        section_market_updates = False
        section_lookups = False

        for row in data.get('values'):
            logger.debug(row)

            if len(row) == 0:
                # Blank line, skip
                section_killswitches = False
                section_carriers = False
                section_market_updates = False
                section_lookups = False
                continue
            elif row[0] == 'Killswitches':
                section_killswitches = True
                continue
            elif row[0] == 'Carriers':
                section_carriers = True
                continue
            elif row[0] == 'Markets':
                section_market_updates = True
                continue
            elif row[0] == 'Lookups':
                section_lookups = True
                continue

            if section_killswitches:
                self.killswitches[row[0].lower()] = row[1].lower()
                continue
            elif section_carriers:
                self.carrierTabNames[row[1]] = row[2]
                continue
            elif section_market_updates:
                self.marketUpdatesSetBy[row[0]] = {
                    'setByOwner': row[1] == 'TRUE'
                }
                continue
            elif section_lookups:
                self.lookupRanges[row[0]] = row[1]
                continue

        self.killswitches['last updated'] = time.time()
        logger.debug(self.killswitches)
        logger.debug(self.carrierTabNames)
        logger.debug(self.marketUpdatesSetBy)
        logger.debug(self.lookupRanges)

    def sheet_names(self) -> list[str]:
        if self.sheets:
            return list(self.sheets.keys())
        return []

    def commodity_type_name_to_dropdown(self, commodity: str) -> str:
        """Returns the specific commodity name that matches the one in the spreadsheet"""
        if commodity == 'ceramiccomposites':
            return 'Ceramic Composites'
        elif commodity == 'cmmcomposite':
            return 'CMM Composite'
        elif commodity == 'computercomponents':
            return 'Computer Components'
        elif commodity == 'foodcartridges':
            return 'Food Cartridges'
        elif commodity == 'fruitandvegetables':
            return 'Fruit and Vedge'
        elif commodity == 'ceramicinsulatingmembrane' or commodity == 'insulatingmembrane':
            return 'Insulating Membrane'
        elif commodity == 'liquidoxygen':
            return 'Liquid Oxygen'
        elif commodity == 'medicaldiagnosticequipment':
            return 'Medical Diagnostic Equipment'
        elif commodity == 'nonlethalweapons':
            return 'Non-Lethal Weapons'
        elif commodity == 'powergenerators':
            return 'Power Generators'
        elif commodity == 'waterpurifiers':
            return 'Water Purifiers'
        
        return commodity.title()    # Convert to Camelcase to match the spreadsheet a bit better

    def add_to_carrier_sheet(self, sheet, cmdr, commodity: str, amount: int) -> None:
        """Updates the carrier sheet with some cargo"""
        logger.debug('Building Carrier Sheet Message')
        range = f"'{sheet}'!A:A"
        body = {
            'range': range,
            'majorDimension': 'ROWS',
            'values': [
                [
                    cmdr,
                    self.commodity_type_name_to_dropdown(commodity),
                    amount
                ]
            ]
        }
        logger.debug(body)
        self.insert_data(range, body)
    
    def update_carrier_location(self, sheet, system: str) -> None:
        """Update the carrier sheet with its current location"""
        logger.debug('Building Carrier Location Message')
        range = f"'{sheet}'!{self.lookupRanges[self.LOOKUP_CARRIER_LOCATION] or 'G1'}"
        body = {
            'range': range,
            'majorDimension': 'ROWS',
            'values': [
                [
                    system
                ]
            ]
        }
        logger.debug(body)
        self.update_data(range, body)

    def update_carrier_jump_location(self, sheet: str, system, departTime: str | None) -> None:
        """Update the carrier sheet with its planned jump"""
        logger.debug("Building Carrier Jump Message")
        range = f"'{sheet}'!{self.lookupRanges[self.LOOKUP_CARRIER_JUMP_LOC] or 'G2'}"
        body = {
            'range': range,
            'majorDimension': 'ROWS',
            'values': [
                [
                    system or '',
                    departTime or ''
                ]
            ]
        }
        logger.debug(body)
        self.update_data(range, body)

    def update_carrier_market(self, sheet, marketData) -> None:
        """Update the current Buy orders if they are out of date"""

        # TODO: Finish this after basic functionality

        # First, check if the market was last set by the carrier owner via a 'CarrierTradeOrder' event

    def update_carrier_market_entry(self, sheet, station, commodity: str, amount: int) -> None:
        """Update the current Buy order for the given commodity"""
        spreadsheetCommodity = self.commodity_type_name_to_dropdown(commodity)
        logger.debug(f"Updating {spreadsheetCommodity} to {amount}")

        # Find our commodity in the list
        buyOrders = self.fetch_data(f"'{sheet}'!{self.lookupRanges[self.LOOKUP_CARRIER_BUY_ORDERS] or 'F3:H22'}")
        logger.debug(f'Old: {buyOrders}')
        for order in buyOrders['values']:
            # Make sure we don't overwrite the Demand column
            order[2] = None

            if order[0] == spreadsheetCommodity:
                if amount > 0:
                    order[1] = amount
                else:
                    order[1] = ''

        logger.debug(f'New: {buyOrders}')
        self.update_data(buyOrders['range'], buyOrders)

        # Also record that it was updated by the carrier owner
        configSheet = f"'{self.configSheetName.get()}'"
        marketSettings = self.fetch_data(f'{configSheet}!A18:B{18 + len(self.marketUpdatesSetBy)}')
        logger.debug(json.dumps(marketSettings))
        
        if self.marketUpdatesSetBy.get(station):
            for setting in marketSettings['values']:
                if setting[0] == station:
                    setting[1] = 'TRUE'

            logger.debug(f'New Markets settings: {marketSettings}')
            self.update_data(marketSettings['range'], marketSettings)
        else:
            logger.debug(f'Unknown Market settings for ({station}), adding...')
            range = f'{configSheet}!A18'
            body = {
                'range': range,
                'majorDimension': 'ROWS',
                'values': [
                    [
                        station,
                        'TRUE'
                    ]
                ]
            }
            self.insert_data(range, body)
        
    def add_to_scs_sheet(self, cmdr, system, commodity: str, amount: int) -> None:
        """Updates the SCS sheet with some cargo"""
        logger.debug('Building SCS Sheet Message')
        sheet = self.lookupRanges[self.LOOKUP_SCS_SHEET_NAME] or 'SCS Offload'
        range = f"'{sheet}'!A:A"
        body = {
            'range': range,
            'majorDimension': 'ROWS',
            'values': [
                [
                    #cmdr       # This isn't currently recorded, but needs to be
                    self.commodity_type_name_to_dropdown(commodity),
                    system.upper(),
                    amount
                ]
            ]
        }
        logger.debug(body)
        self.insert_data(range, body)