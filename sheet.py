import logging
import requests
import time
import datetime
import webbrowser
import tkinter as tk
import json
import traceback

from config import config, appname
from auth import Auth, LocalHTTPServer, SPREADSHEET_ID
from pathlib import Path

plugin_name = Path(__file__).resolve().parent.name
logger = logging.getLogger(f'{appname}.{plugin_name}')

# TODO: This duplication is dumb
CONFIG_SHEET_NAME = 'mom_config_sheet_name'
CONFIG_ASSIGNED_CARRIER = 'mom_assigned_carrier'
CONFIG_FEAT_TRACK_DELIVERY = 'mom_feature_track_delivery'

class Sheet:
    BASE_SHEET_END_POINT = 'https://sheets.googleapis.com'
    SPREADSHEET_ID = SPREADSHEET_ID

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
        self.commodityNamesToNice: dict[str, str] = {}
        self.commodityNamesFromNice: dict[str, str] = {}
        self.sheetFunctionality: dict[str, dict[str, bool]] = {}
        
        
        """
            This ones needs a bit of explaining:
                [commodity] = (amount, A1range)
        """
        self.inTransitCommodities: dict[str, tuple[int, str]] = {}

        if config.shutting_down:
            # If shutdown is called during the intial stages of auth, we won't have been initialised yet
            # So make sure we don't call config.get_str, as that blocks if config.shutting_down is true
            return
        
        self.configSheetName = tk.StringVar(value=config.get_str(CONFIG_SHEET_NAME, default='EDMC Plugin Settings'))
        self.cmdrsAssignedCarrier = tk.StringVar(value=config.get_str(CONFIG_ASSIGNED_CARRIER))
            
        self.check_and_authorise_access_to_spreadsheet()

    def check_and_authorise_access_to_spreadsheet(self, skipReauth=False) -> any:
        """Checks and (Re)Authorises access to the spreadsheet. Returns the current sheets"""
        logger.debug('Checking access to spreadsheet')
        res = self.requests_session.get(f'{self.BASE_SHEET_END_POINT}/v4/spreadsheets/{self.SPREADSHEET_ID}?fields=sheets/properties(sheetId,title)')
        sheet_list_json: any = res.json()
        logger.debug(f'{res}{sheet_list_json}')

        if res.status_code != requests.codes.ok:
            if not skipReauth:
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
                if res.status_code != requests.codes.ok:
                    res.raise_for_status()

                self.handler = None
            else:
                logger.error("No longer authorised")
                return

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
    
    def _convert_A1_range_to_idx_range(self, a1Str: str, skipHeaderRow: bool = False) -> dict:
        # 'EDMC Plugin Settings'!E1:G4
        logger.debug('Converting A1 range to index')
        splits = a1Str.split('!')
        sheetName = splits[0][1:-1].replace("''", "'")              # 'Explorer''s Rest' -> Explorer's Rest
        ranges = splits[1].split(':')
        rangeStart = self._A1_to_index(ranges[0])                   # E1 -> col:4, row:0
        rangeEnd = self._A1_to_index(ranges[1])                     # G4 -> col:6, row:3
        
        rowOffset = 1 if skipHeaderRow else 0

        return {
                'sheetId': self.sheets[sheetName],
                'startRowIndex': rangeStart[1] + rowOffset,         # Inclusive
                'endRowIndex': rangeEnd[1] + 1,                     # Exclusive (ie, + 1 from where you want to finish)
                'startColumnIndex': rangeStart[0],                  # Inclusive
                'endColumnIndex': rangeEnd[0] + 1                   # Exclusive (ie, + 1 from where you want to finish)
            }

    def _get_datetime_string(self) -> str:
        return datetime.datetime.now(datetime.UTC).replace(microsecond=0).isoformat().replace('T',' ').replace('+00:00', '')        

    def _get_carrier_name_from_id(self, id: str) -> str:
        return self.carrierTabNames[id]
    
    def _get_carrier_id_from_name(self, name: str) -> str:
        for carrierId in self.carrierTabNames.keys():
            carrierName = self.carrierTabNames[carrierId]
            if carrierName == name:
                return carrierId
        return 'UNKNOWN'

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

    def fetch_data_bulk(self, ranges: list[str]) -> any:
        """Fetch multiple bits of data from the spreadsheet"""
        base_url = f'{self.BASE_SHEET_END_POINT}/v4/spreadsheets/{self.SPREADSHEET_ID}/values:batchGet?'
        for range in ranges:
            base_url += f'ranges={range}&'
        base_url += 'majorDimension=ROWS&valueRenderOption=FORMATTED_VALUE'
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

    def insert_data(self, range: str, body: dict, returnValues: bool = False) -> any:
        """Add/update some data in the spreadsheet"""
        # POST https://sheets.googleapis.com/v4/spreadsheets/SPREADSHEET_ID/values/Sheet1!A1:E1:append?valueInputOption=VALUE_INPUT_OPTION
        # Append adds new rows to the end of the given range
        base_url = f'{self.BASE_SHEET_END_POINT}/v4/spreadsheets/{self.SPREADSHEET_ID}/values/{range}:append?valueInputOption=USER_ENTERED'
        if returnValues:
            base_url += '&includeValuesInResponse=true'

        logger.debug(f'Sending request to POST {base_url}')
        
        # Handle single quotes in sheet names
        if body.get('range'):
            body['range'] = body['range'].replace("''", "'")
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

        # Handle single quotes in sheet names
        if body.get('range'):
            body['range'] = body['range'].replace("''", "'")
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

        # Make sure any new sheets/tabs get their ids added to the 'self.sheets' dict
        self.check_and_authorise_access_to_spreadsheet(skipReauth=True)

        if config.shutting_down:
            # If shutdown is called before we have the sheet name, make sure we bail
            # as making a call to config.get_str blocks
            return
        
        sheet = f"'{self.configSheetName.get()}'"
        if sheet == "''":
            logger.error('No EDMC Plugin Settings sheet selected')
            return

        dataRange = f'{sheet}!A:C'
        carrierRange = f'{sheet}!J:L'
        marketRange = f'{sheet}!O:P'
        featureRange = f'{sheet}!S:V'
        
        data = self.fetch_data_bulk((dataRange, carrierRange, marketRange, featureRange))

        logger.debug(data)
        
        # TODO: Error handling
        # for now, just bail, and try again later
        if not data or len(data) == 0:
            return

        self.killswitches = {}
        self.carrierTabNames = {}
        self.marketUpdatesSetBy = {}
        self.lookupRanges = {}
        self.commodityNamesToNice = {}
        self.commodityNamesFromNice = {}
        self.sheetFunctionality = {}

        section_killswitches = False
        section_lookups = False
        section_commodity_mapping = False

        # Lets not let temporary failures in these settings kill the entire plugin
        try:
            rangeIdx = 0
            for valueRange in data.get('valueRanges'):
                match rangeIdx:
                    case 0: # Data Range
                        for row in valueRange.get('values'):
                            #logger.debug(row)

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
                    case 1: # Carrier Range
                        for row in valueRange.get('values'):
                            if row[0] == 'Carriers':
                                continue
                            self.carrierTabNames[row[1]] = row[2]
                    case 2: # Market Range
                        for row in valueRange.get('values'):
                            self.marketUpdatesSetBy[row[0]] = {
                                    'setByOwner': row[1] == 'TRUE'
                                }
                    case 3: # Feature Range
                        colNames: dict[int, str] = {}
                        for row in valueRange.get('values'):
                            if row[0] == 'Sheet Functionality':
                                for idx in range(1, len(row)):
                                    logger.debug(f'Adding {row[idx]} to Column Names')
                                    colNames[idx] = row[idx]
                                continue
                                
                            settings: dict[str, bool] = {}
                            for idx in colNames.keys():
                                settings[colNames[idx]] = row[idx] == 'TRUE'

                            self.sheetFunctionality[row[0]] = settings

                rangeIdx += 1
        except Exception:
            logger.error(traceback.format_exc())

        self.killswitches['last updated'] = time.time()

    def populate_cmdr_data(self, cmdr: str) -> None:
        """Populate CMDR specific data on start up"""
        # This shouldn't be called more than once, as we just want to pre-populate some stuff after a shutdown
        try:
            systemInfoSheet = self.lookupRanges[self.LOOKUP_SYSTEMINFO_SHEET_NAME] or 'System Info'
            cmdrInfoRange = self.lookupRanges[self.LOOKUP_CMDR_INFO] or 'G:I'

            data = self.fetch_data_bulk([f'{systemInfoSheet}!{cmdrInfoRange}'])
            if not data or len(data) == 0:
                return

            # TODO: Fetch any in-transit cargo
            
            # Fetch current assigned carrier, and save it to our settings
            if self.cmdrsAssignedCarrier.get() == '':
                logger.info('#### CMDR assigned carrier currently unknown, getting from spreadhsheet... ####')
                for row in data['valueRanges'][0]['values']:
                    # Skip blank rows, and those that don't have the carrier set
                    if len(row) < 3:
                        continue
                    
                    # Also skip any rows which aren't for us
                    if row[0] != cmdr:
                        continue
                    
                    logger.info(f'found "{row[2]}"')
                    config.set(CONFIG_ASSIGNED_CARRIER, row[2])
                    config.save()
                    break

        except Exception:
            logger.error(traceback.format_exc())

    def sheet_names(self) -> list[str]:
        if self.sheets:
            return list(self.sheets.keys())
        return []

    def commodity_type_name_to_dropdown(self, commodity: str) -> str:
        """Returns the specific commodity name that matches the one in the spreadsheet"""
        return self.commodityNamesToNice.get(commodity, commodity.title())  # Convert to Camelcase to match the spreadsheet a bit better

    def dropdown_to_commodity_type_name(self, commodity: str) -> str:
        """Returns the specific commodity name thats matches the one in the spreadsheet"""
        return self.commodityNamesFromNice.get(commodity, commodity.lower())

    def add_to_carrier_sheet(self, sheet: str, cmdr: str, commodity: str, amount: int, inTransit: bool = False) -> None:
        """Updates the carrier sheet with some cargo"""
        if not sheet or sheet == '':
            logger.error('No sheet name provided')
            return
        
        logger.debug(f'Building Carrier Sheet Message (inTransit:{inTransit} commodity:{commodity} amount:{amount})')
        range = f"'{sheet}'!A:A"
        bodyValue = [
            cmdr,
            self.commodity_type_name_to_dropdown(commodity),
            amount
        ]
        update = False

        if self.sheetFunctionality.get(sheet, {}).get('Delivery', False) and config.get_bool(CONFIG_FEAT_TRACK_DELIVERY):
            if inTransit or amount > 0:
                logger.debug(f'Checking for existing row for {commodity}')
                existingValue = self.inTransitCommodities.pop(commodity, None)
                if existingValue:
                    if inTransit or (not inTransit and existingValue[1].startswith(f"'{sheet}'")):
                        logger.debug('Existing in-transit row found, updating')
                        # Buying or Selling cargo to the carrier, just update the existing in-transit row
                        range = existingValue[1]
                        if inTransit:
                            # Buying additional cargo for something thats already in-transit, just update the existing row with the additional value
                            bodyValue[2] += existingValue[0]
                        update = True
                    else:
                        # We've recorded an in-transit move for one carrier, then dropped it off at the next... err... panic?!
                        logger.warning('In-Transit row found, but for a different carrier, ignoring')
                        # Should we clear the in-transit record ... or just leave it?
                        # We might just be doing a partial delivery
                else:
                    logger.debug('Not found, creating new one')

                bodyValue.append(not inTransit)

                if amount < 0 and inTransit:
                    # We must be selling to a different station. If we don't actually know about this commodity, then there is no need to add an entry into the sheet
                    if not update:
                        logger.info('Commodity not tracked as in-transit, skipping adding new row')
                        return
            else:
                logger.debug('Not in transit, and Buying from the carrier, then mark Delivered as True')
                bodyValue.append(True)
        else:
            if not inTransit:
                logger.debug('Not in Transit, skipping setting value')
                bodyValue.append(None)
            else:
                # We're buying from a station, but delivery tracking is disabled, so just don't write anything to the sheet
                logger.info('Delivery Tracking disabled, skipping adding new row')
                return
                
        if self.sheetFunctionality.get(sheet, {}).get('Timestamp', False):
            bodyValue.append(self._get_datetime_string())
        else:
            bodyValue.append(None)

        if update and bodyValue[2] == 0:
            # Clear the row
            bodyValue = ['', '', '']
            if self.sheetFunctionality[sheet].get('Delivery', False) and config.get_bool(CONFIG_FEAT_TRACK_DELIVERY):
                bodyValue.append('')
            else:
                bodyValue.append(None)
            if self.sheetFunctionality[sheet].get('Timestamp', False):
                bodyValue.append('')
            else:
                bodyValue.append(None)

        body = {
            'range': range,
            'majorDimension': 'ROWS',
            'values': [
                bodyValue
            ]
        }
        logger.debug(body)
        if not update:
            response = self.insert_data(range, body, returnValues=True)
        else:
            response = self.update_data(range, body)
        
        # Now format the row we just created
        if self.sheetFunctionality[sheet].get('Delivery', False) and config.get_bool(CONFIG_FEAT_TRACK_DELIVERY):
            logger.debug('Formatting Delivery cell')
            updates = response.get('updates', response)
            updatedRange = updates.get('updatedRange')
            if updatedRange:
                #logger.debug('updatedRange section found')
                # Keep track of our in-transit commodities
                if inTransit:
                    self.inTransitCommodities[commodity] = (int(bodyValue[2]), updatedRange)
                    logger.debug(f'New in-transit commodity added: {self.inTransitCommodities}')

                logger.debug('Converting updatedRange to numeric indices')
                range = self._convert_A1_range_to_idx_range(updatedRange)
                logger.debug(range)
                # We just want to update Column D
                range['startColumnIndex'] += 3
                range['endColumnIndex'] = int(range['startColumnIndex']) + 1
                sheetUpdates: list = [
                    {
                        'repeatCell': {
                            'range': range,
                            'cell': {
                                'dataValidation': {
                                    'condition': {
                                        'type': 'BOOLEAN'
                                    }
                                }
                            },
                            'fields': 'dataValidation.condition'
                        }
                    }
                ]
                self.update_sheet(sheetUpdates)   
            else:
                logger.error('No updatedRange found in response')
    
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

        if self.sheetFunctionality[sheet].get('Buy Order Adjustment', False):
            logger.debug('Adjust Buy Order is set, fudging the value to include the Starting Inventory')
            # Fudge the Buy order a bit to keep the ship inventory total correct, by including any starting inventory
            startingInventory = self.fetch_data(f"{sheet}!{self.lookupRanges[self.LOOKUP_CARRIER_STARTING_INV] or 'A1:C20'}")
            logger.debug(startingInventory)
            if len(startingInventory) == 0:
                logger.error('No Starting Inventory found, bailing')
                return
            
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
        #configSheet = f"'{self.configSheetName.get()}'"
        #marketSettings = self.fetch_data(f'{configSheet}!A18:B{18 + len(self.marketUpdatesSetBy)}')
        #logger.debug(json.dumps(marketSettings))
        
        #if self.marketUpdatesSetBy.get(station):
        #    for setting in marketSettings['values']:
        #        if setting[0] == station:
        #            setting[1] = 'TRUE'

        #    logger.debug(f'New Markets settings: {marketSettings}')
        #    self.update_data(marketSettings['range'], marketSettings)
        #else:
        #    logger.debug(f'Unknown Market settings for ({station}), adding...')
        #    range = f'{configSheet}!A18'
        #    body = {
        #        'range': range,
        #        'majorDimension': 'ROWS',
        #        'values': [
        #            [
        #                station,
        #                'TRUE'
        #            ]
        #        ]
        #    }
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
            # Skip blank rows
            if len(row) == 0:
                continue

            if row[0] == cmdr:
                row[1] = version
                row[2] = self._get_datetime_string()
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
                        self._get_datetime_string()
                    ]
                ]
            }
            res = self.insert_data(range, body)
        if res:
            updates = res.get('updates', res)
            updatedRange = updates.get('updatedRange')
            range = self._convert_A1_range_to_idx_range(updatedRange, skipHeaderRow=True)
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
        range = f"'{sheet}'!{self.lookupRanges[self.LOOKUP_CMDR_INFO] or 'G:I'}"
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

    def recalculate_in_transit(self, sheet: str, cmdr: str, clear: bool = False) -> None:
        """Checks the current carrier list for any items that might still be in transit since the last time we started"""
        if not sheet:
            logger.error(f'Carrier {sheet} not known, bailing')
            return
        
        if clear:
            logger.debug("Clearing in-transit commodities")
            
            rowsToDelete: list = []
            offsets: dict[int, int] = {}
            for commodity in self.inTransitCommodities:
                amount = self.inTransitCommodities[commodity][0]
                range = self.inTransitCommodities[commodity][1]

                # Lets just double check what we think we're about to delete matches whats currently there
                data = self.fetch_data(range)
                logger.debug(data)
                if data.get('values'):
                    row = data['values'][0]
                    logger.debug(f'Comparing "{row[1]}" vs "{self.commodity_type_name_to_dropdown(commodity)}" and "{row[2]}" vs "{amount}"')
                    if row[1] == self.commodity_type_name_to_dropdown(commodity) and int(row[2]) == amount:
                        # Both Commodity name and amount match, so lets get rid of it
                        idxRange = self._convert_A1_range_to_idx_range(range)
                        offset = offsets.get(idxRange['sheetId'], 0)

                        if len(rowsToDelete) > 0:
                            # We need to offset these by the rows we're deleting
                            logger.debug(f'Offsetting range by {offset}')
                            idxRange['startRowIndex'] -= offset
                            idxRange['endRowIndex'] -= offset

                        rowsToDelete.append(
                            {
                                "deleteRange": {
                                    "range": idxRange,
                                    "shiftDimension": "ROWS"
                                }
                            }
                        )

                        offsets[idxRange['sheetId']] = offset + (idxRange['endRowIndex'] - idxRange['startRowIndex'])
                        logger.debug(offsets)
            #logger.debug(rowsToDelete)
            if len(rowsToDelete) > 0:
                self.update_sheet(rowsToDelete)
            
            logger.debug('done')
            self.inTransitCommodities = {}
            return

        if not self.sheetFunctionality[sheet].get('Delivery', False) or not config.get_bool(CONFIG_FEAT_TRACK_DELIVERY):
            logger.debug('Sheet not tracking delivery, so skipping in-transit check')
            return

        data = self.fetch_data(f"'{sheet}'!A:E")
        logger.debug(data)

        rowIdx = 0
        for row in data['values']:
            rowIdx += 1
            if len(row) < 4:
                continue    # Skip bad rows
            if row[0] != cmdr:
                continue    # Not one we care about
            if row[3] == 'FALSE':
                # Something thats in transit!
                # NB. To keep things simple, lets enforce only 1 commodity of the same type can be in transit at once
                commodity = self.dropdown_to_commodity_type_name(row[1])
                self.inTransitCommodities[commodity] = (int(row[2]), f"'{sheet}'!A{rowIdx}:E{rowIdx}")

        logger.debug(f'Commodities in transit: {self.inTransitCommodities}')

    
