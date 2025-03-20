import logging
import requests
import time
import datetime
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
    LOOKUP_CARRIER_SUM_CARGO = 'Carrier Sum Cargo'
    LOOKUP_CARRIER_STARTING_INV = 'Carrier Starting Inventory'
    LOOKUP_SCS_SHEET_NAME = 'SCS Sheet'
    LOOKUP_SYSTEMINFO_SHEET_NAME = 'System Info Sheet'
    LOOKUP_CMDR_INFO = 'CMDR Info'

    def __init__(self, auth: Auth, session: requests.Session):
        self.auth: Auth = auth
        self.requests_session: requests.Session = session
        self.sheets: dict[str, int] = {}

        self.killswitches: dict[str, str] = {}
        self.carrierTabNames: dict[str, str] = {}
        self.marketUpdatesSetBy: dict[str, dict] = {}
        self.lookupRanges: dict[str, str] = {}
        self.buyOrdersIveSet: dict[str, int] = {}

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

    def _A1_to_index(self, colStr: str) -> list[int]:
        """Converts an A1 range column into a numeric index, starting from A = 0"""
        colIdx = 0
        rowStr = ''
        for char in colStr:
            charInt = ord(char)
            if charInt >= 65:  # ord('A') = 65
                colIdx += charInt - 65
            else:
                rowStr += char
        return [colIdx, int(rowStr)-1]
    
    def _convert_A1_range_to_idx_range(self, a1Str: str, skipHeaderRow: bool) -> dict:
        # 'EDMC Plugin Settings'!E1:G4
        splits = a1Str.split('!')
        sheetName = splits[0].replace("'", '')                      # 'EDMC Plugin Settings'
        ranges = splits[1].split(':')
        rangeStart = self._A1_to_index(ranges[0])                   # E1 -> col:4, row:0
        rangeEnd = self._A1_to_index(ranges[1])                     # G4 -> col:6, row:3
        
        rowOffset = 1 if skipHeaderRow else 0

        return {
                'sheetId': self.sheets[sheetName],
                'startRowIndex': rangeStart[1] + rowOffset,         # Inclusive
                'endRowIndex': rangeEnd[1] + 1,                     # Exclusive (ie, + 1 from where you want to finish)
                'startColumnIndex': rangeStart[0],                  # Inclusive
                'endColumnIndex': rangeEnd[0]                       # Exclusive (ie, + 1 from where you want to finish)
            }
        

    def fetch_data(self, query: str) -> any:
        """Actually send a request to Google"""
        base_url = f'{self.BASE_SHEET_END_POINT}/v4/spreadsheets/{self.SPREADSHEET_ID}/values/{query}'
        logger.debug(f'Sending request to GET {base_url}')
        try:
            token_refresh_attempted = False
            while True:
                res = self.requests_session.get(base_url, timeout=10)
                if res.status_code == requests.codes.ok:
                    return res.json()
                elif res.status_code == requests.codes.unauthorized:
                    logger.error(f'{res}{res.json()}')
                    if not token_refresh_attempted:
                        token_refresh_attempted = True
                        self.auth.refresh()
                        continue
                else:
                    logger.error(f'{res}{res.json()}')
                return {}
        except:
            return {}

    def insert_data(self, range: str, body: dict) -> any:
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
            res = self.requests_session.post(base_url, json=body, timeout=10)
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

    def update_data(self, range: str, body: dict) -> any:
        """Updates existing data in the spreadsheet"""
        # PUT https://sheets.googleapis.com/v4/spreadsheets/{spreadsheetId}/values/{range}?valueInputOption=VALUE_INPUT_OPTION
        base_url = f'{self.BASE_SHEET_END_POINT}/v4/spreadsheets/{self.SPREADSHEET_ID}/values/{range}?valueInputOption=USER_ENTERED'
        logger.debug(f'Sending request to PUT {base_url}')
        logger.debug(json.dumps(body))

        token_refresh_attempted = False
        while True:
            logger.debug('sending request...')
            logger.debug(self.requests_session.headers)
            res = self.requests_session.put(base_url, json=body, timeout=10)
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

    def update_sheet(self, sheetUpdates: list) -> any:
        """Updates an existing sheet, copying cells, setting display formats...etc"""
        # POST https://sheets.googleapis.com/v4/spreadsheets/SPREADSHEET_ID:batchUpdate
        base_url = f'{self.BASE_SHEET_END_POINT}/v4/spreadsheets/{self.SPREADSHEET_ID}:batchUpdate'
        logger.debug(f'Sending request to POST {base_url}')
        
        body = {
            'requests': sheetUpdates
        }
        logger.debug(json.dumps(body))

        token_refresh_attempted = False
        while True:
            logger.debug('sending request...')
            logger.debug(self.requests_session.headers)
            res = self.requests_session.post(base_url, json=body, timeout=10)
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
        data = self.fetch_data(f'{sheet}!A:C')
        carriers = self.fetch_data(f'{sheet}!J:L')
        markets = self.fetch_data(f'{sheet}!O:P')
        #logger.debug(data)
        #logger.debug(carriers)
        #logger.debug(markets)
        
        # TODO: Error handling
        # for now, just bail, and try again later
        if not data or not carriers or not markets:
            return

        self.killswitches = {}
        self.carrierTabNames = {}
        self.marketUpdatesSetBy = {}
        self.lookupRanges = {}
        self.commodityNamesToNice = {}
        self.commodityNamesFromNice = {}

        section_killswitches = False
        section_lookups = False
        section_commodity_mapping = False

        # Lets not let temporary failures in these settings kill the entire plugin
        try:

            for row in data.get('values'):
                logger.debug(row)

                if len(row) == 0:
                    # Blank line, skip
                    section_killswitches = False
                    section_lookups = False
                    section_commodity_mapping = False
                    continue
                elif row[0] == 'Killswitches':
                    section_killswitches = True
                    continue
                elif row[0] == 'Lookups':
                    section_lookups = True
                    continue
                elif row[0] == 'Commodity Mapping':
                    section_commodity_mapping = True
                    continue

                if section_killswitches:
                    self.killswitches[row[0].lower()] = row[1].lower()
                    continue
                elif section_lookups:
                    self.lookupRanges[row[0]] = row[1]
                    continue
                elif section_commodity_mapping:
                    self.commodityNamesToNice[row[0]] = row[1]
                    self.commodityNamesFromNice[row[1]] = row[0]    # TODO: How do we handle double ups here ? Do we care ?

            for row in carriers.get('values'):
                if row[0] == 'Carriers':
                    continue
                self.carrierTabNames[row[1]] = row[2]

            for row in markets.get('values'):
                self.marketUpdatesSetBy[row[0]] = {
                        'setByOwner': row[1] == 'TRUE'
                    }
        except Exception as ex:
            logger.error(ex)

        self.killswitches['last updated'] = time.time()
        #logger.debug(self.killswitches)
        #logger.debug(self.carrierTabNames)
        #logger.debug(self.marketUpdatesSetBy)
        #logger.debug(self.lookupRanges)
        logger.debug(self.commodityNamesToNice)
        logger.debug(self.commodityNamesFromNice)

    def sheet_names(self) -> list[str]:
        if self.sheets:
            return list(self.sheets.keys())
        return []

    def commodity_type_name_to_dropdown(self, commodity: str) -> str:
        """Returns the specific commodity name that matches the one in the spreadsheet"""
        return self.commodityNamesToNice.get(commodity, commodity.title())  # Convert to Camelcase to match the spreadsheet a bit better

    def dropdown_to_commodity_type_name(self, commodity: str) -> str:
        """Returns the specific commodity name thats matches the one in the spreadsheet"""
        return self.commodityNamesFromNice.get(commodity, commodity)

    def add_to_carrier_sheet(self, sheet: str, cmdr: str, commodity: str, amount: int) -> None:
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
    
    def update_carrier_location(self, sheet: str, system: str) -> None:
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

    def update_carrier_jump_location(self, sheet: str, system: str, departTime: str | None) -> None:
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

    def update_carrier_market(self, sheet: str, marketData: dict) -> None:
        """Update the current Buy orders if they are out of date"""

        # TODO: Finish this after basic functionality

        # First, check if the market was last set by the carrier owner via a 'CarrierTradeOrder' event

    def update_carrier_market_entry(self, sheet: str, station: str, commodity: str, amount: int) -> None:
        """Update the current Buy order for the given commodity"""
        spreadsheetCommodity = self.commodity_type_name_to_dropdown(commodity)
        logger.debug(f"Updating {spreadsheetCommodity} to {amount}")

        startingInventory = self.fetch_data(f"{sheet}!{self.lookupRanges[self.LOOKUP_CARRIER_STARTING_INV] or 'A1:C20'}")
        logger.debug(startingInventory)
        if len(startingInventory) == 0:
            logger.error('No Starting Inventory found, bailing')
            return
        
        # Fudge the Buy order a bit to keep the ship inventory total correct, by including any starting inventory
        for row in startingInventory['values']:
            if row[1] == spreadsheetCommodity and len(row) == 3:
                amount += int(row[2])

        # Find our commodity in the list
        buyOrders = self.fetch_data(f"'{sheet}'!{self.lookupRanges[self.LOOKUP_CARRIER_BUY_ORDERS] or 'F3:H22'}")
        logger.debug(f'Old: {buyOrders}')
        if len(buyOrders) == 0:
            logger.error('No Buy Order table found, bailing')
            return

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

        self.buyOrdersIveSet[commodity.lower()] = int(time.time())

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
            #self.insert_data(range, body)
        
    def add_to_scs_sheet(self, cmdr: str, system: str, commodity: str, amount: int) -> None:
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
                    system,
                    amount
                ]
            ]
        }
        logger.debug(body)
        self.insert_data(range, body)

    def record_plugin_usage(self, cmdr: str, version: str) -> None:
        """Updates the Plugin sheet with usage info"""
        logger.debug('Building Plugin Usage Message')
        sheet = f"'{self.configSheetName.get()}'"
        range = f'{sheet}!E:G'
        data = self.fetch_data(range)
        logger.debug(data)
        
        setRow = False
        for row in data['values']:
            if row[0] == cmdr:
                row[1] = version
                row[2] = datetime.datetime.now(datetime.UTC).replace(microsecond=0).isoformat().replace('T',' ').replace('+00:00', '')
                setRow = True
                break
        
        if setRow:
            logger.debug(f'New Plugin Usage: {data}')
            res = self.update_data(data['range'], data)
        else:
            body = {
                'range': range,
                'majorDimension': 'ROWS',
                'values': [
                    [
                        cmdr,
                        version,
                        datetime.datetime.now(datetime.UTC).replace(microsecond=0).isoformat().replace('T', ' ').replace('+00:00', '')
                    ]
                ]
            }
            res = self.insert_data(range, body)
        if res:
            range = self._convert_A1_range_to_idx_range(res['updatedRange'], skipHeaderRow=True)
            # We just want to update Column G
            range['startColumnIndex'] += 2
            range['endColumnIndex'] = int(range['startColumnIndex']) + 1

            sheetUpdates: list = [
                {
                    'repeatCell': {
                        'range': range,
                        'cell': {
                            'userEnteredFormat': {
                                'numberFormat': {
                                    'type': 'DATE',
                                    'pattern': 'yyyy-MM-dd HH:mm:ss'
                                }
                            }
                        },
                        'fields': 'userEnteredFormat.numberFormat'
                    }
                }
            ]
            self.update_sheet(sheetUpdates)

    

    def update_cmdr_attributes(self, cmdr: str, cargoCapacity: int) -> None:
        """Updates anything we wnat to track about the current CMDR"""
        logger.debug('Building CMDR Update Message')
        sheet = self.lookupRanges[self.LOOKUP_SYSTEMINFO_SHEET_NAME] or 'System Info'
        range = f"'{sheet}'!{self.lookupRanges[self.LOOKUP_CMDR_INFO] or 'G1'}"
        data = self.fetch_data(range)
        logger.debug(data)

        setRow = False
        for row in data['values']:
            # Skip blank rows
            if len(row) == 0:
                continue

            if row[0] == cmdr:
                row[1] = cargoCapacity
                setRow = True
                break

        if setRow:
            self.update_data(data['range'], data)
        else:
            logger.debug('CMDR not found, adding to table')
            body = {
                'range': range,
                'majorDimension': 'ROWS',
                'values': [
                    [
                        cmdr,
                        cargoCapacity,
                        None # Cap Ship
                    ]
                ]
            }
            self.insert_data(range, body)

    def reconcile_carrier_market(self, carrierData: dict) -> None:
        """
        After the CAPI call has come back, we know (within the last 15 or so minutes) the current state of the carrier.
        So, lets make sure the Buy orders and inventory match up.
        """
        carrier: str = carrierData['name']['callsign']
        if not carrier in self.carrierTabNames.keys():
            logger.debug(f'Carrier {carrier} unknown, ignoring')
            return
        
        logger.debug('Building Reconcile Carrier message')
        sheet = f"'{self.carrierTabNames[carrier]}'"
        
        buyOrders = self.fetch_data(f"{sheet}!{self.lookupRanges[self.LOOKUP_CARRIER_BUY_ORDERS] or 'F3:H22'}")
        logger.debug(buyOrders)
        if len(buyOrders) == 0:
            logger.error('No Buy Order data found, bailing')
            return
        
        startingInventory = self.fetch_data(f"{sheet}!{self.lookupRanges[self.LOOKUP_CARRIER_STARTING_INV] or 'A1:C20'}")
        logger.debug(startingInventory)
        if len(startingInventory) == 0:
            logger.error('No Starting Inventory found, bailing')
            return
        
        startingInventoryAmounts: dict[str, int] = {}
        for row in startingInventory['values']:
            if row[0] == 'CMDR':
                continue
            if len(row) == 3:
                startingInventoryAmounts[row[1]] = int(row[2])
            else:
                startingInventoryAmounts[row[1]] = 0
        logger.debug(startingInventoryAmounts)

        # Clear out all buy orders and start from scratch
        for row in buyOrders['values']:
            if row[0] == 'Commodity':
                continue    # Skip the table header
            
            # Only blank them out if we haven't explicitly set them in the last 30 minutes
            commodity = self.dropdown_to_commodity_type_name(row[0])
            if not self.buyOrdersIveSet.get(commodity) or (self.buyOrdersIveSet[commodity.lower()] + 60 * 30) < int(time.time()):
                logger.debug(f'{row[0]} is old, replacing ({row[1]}) with CAPI value')
                row[1] = startingInventoryAmounts.get(commodity, '')
                logger.debug(f'Resetting to starting value {row[1]}')
            row[2] = None   # Don't overwrite the computed cells

        # Now go through all the current orders and set them
        for order in carrierData['orders']['commodities']['purchases']:
            commodityName = self.commodity_type_name_to_dropdown(order['name'])
            if not self.buyOrdersIveSet.get(commodity) or (self.buyOrdersIveSet[commodity.lower()] + 60 * 30) < int(time.time()):
                for row in buyOrders['values']:
                    if row[0] == commodityName:
                        row[1] = int(order['total']) + startingInventoryAmounts.get(commodityName, 0)

        # Work out how much the spreadsheet thinks is on the ship
        sumCargo = self.fetch_data(f"{sheet}!{self.lookupRanges[self.LOOKUP_CARRIER_SUM_CARGO] or 'AE:AF'}")
        logger.debug(sumCargo)
        if len(sumCargo) == 0:
            logger.error('No Sum Cargo data found, bailing')
            return
        
        for cargo in sumCargo['values']:
            if len(cargo) == 0 or cargo[0] == 'Commodity':
                continue    # Skip blank rows and headers

            cargoNiceName = cargo[0]
            logger.debug(f'Checking {cargoNiceName}')
            commodityName = self.dropdown_to_commodity_type_name(cargoNiceName).lower()
            if cargoNiceName != commodityName:
                logger.debug(f'(Converting to {commodityName})')

            commodityTotal: int = 0
            for carrierCargo in carrierData['cargo']:
                # Unhelpfully, there can be multiple entries of the same cargo in this array, so we have to go through it all and add it up
                if carrierCargo['commodity'].lower() == commodityName:
                    commodityTotal += int(carrierCargo['qty'])

            if commodityTotal != int(cargo[1]):
                logger.debug(f'Descrepency found! Correcting [Actual:{commodityTotal} vs Estimated:{cargo[1]}]')
                # Ok, lets now update the Starting Inventory
                for invRow in startingInventory['values']:
                    if invRow[1] == cargoNiceName:
                        if len(invRow) == 3:
                            invRow[2] = int(invRow[2]) + (commodityTotal - int(cargo[1]))
                        else:
                            invRow.append(int(commodityTotal - int(cargo[1])))


        logger.debug(buyOrders)
        logger.debug(startingInventory)
        self.update_data(buyOrders['range'], buyOrders)
        self.update_data(startingInventory['range'], startingInventory)