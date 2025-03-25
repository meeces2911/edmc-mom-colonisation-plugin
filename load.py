#
# Mercs of Mikunn - Colonisation Tracker
# Created by meeces2911
#

import logging
import threading
import tkinter as tk
import requests
import traceback

from tkinter import ttk
from threading import Lock, Thread
from monitor import monitor
from pathlib import Path
from queue import SimpleQueue

import semantic_version
import time
import json

import myNotebook as nb
from config import config, appname, appversion, user_agent
from companion import CAPIData, SERVER_LIVE, capi_fleetcarrier_query_cooldown, session as csession
from ttkHyperlinkLabel import HyperlinkLabel
from prefs import AutoInc

from sheet import Sheet
from auth import Auth, SPREADSHEET_ID

plugin_name = Path(__file__).resolve().parent.name
logger = logging.getLogger(f'{appname}.{plugin_name}')

VERSION = '1.2.0-beta1'
_CAPI_RESPONSE_TK_EVENT_NAME = '<<CAPIResponse>>'

KILLSWITCH_CMDR_UPDATE = 'cmdr info update'
KILLSWITCH_CARRIER_BUYSELL_ORDER = 'carrier buysell order'
KILLSWITCH_CARRIER_LOC = 'carrier location'
KILLSWITCH_CARRIER_JUMP = 'carrier jump'
KILLSWITCH_CARRIER_MARKET = 'carrier market full'
KILLSWITCH_SCS_SELL = 'scs sell commodity'
KILLSWITCH_CMDR_BUYSELL = 'cmdr buysell commodity'
KILLSWITCH_CARRIER_TRANSFER = 'carrier transfer'
KILLSWITCH_CARRIER_RECONCILE = 'carrier reconcile'

# Probably overkill, but lets start with a sensible framework like how the EDSM plugin does it
class This:
    """Holds module globals."""
    
    def __init__(self):
        self.thread: threading.Thread | None = None
        
        self.auth: Auth | None = None
        self.queue: SimpleQueue[PushRequest] = SimpleQueue()
        
        self.enabled: bool = True
        self.killswitches: dict[str, str] = {}
        
        self.requests_session : requests.Session = requests.Session()
        self.requests_session.headers['User-Agent'] = user_agent

        self.sheet: Sheet | None = None
        self.configSheetName: tk.StringVar

        self.currentCargo: dict | None = None
        self.carrierCallsign: str | None = None
        self.cargoCapacity: int = 0
        self.cmdrsAssignedCarrier: str | None = 'X7H-9KW'

        self.clearAuthButton: tk.Button | None = None
        self.settingsClosed: bool = False

        self.carrierAPIEnabled: tk.BooleanVar = tk.BooleanVar(value=config.get_bool('capi_fleetcarrier', default=False))  # Don't change this name, its used by EDMC
        self.lastCarrierQueryTime: tk.IntVar = tk.IntVar(value=config.get_int('fleetcarrierquerytime', default=0))  # Don't change this name, its used by EDMC
        self.nextUpdateCarrierTime: int = int(time.time())
        self.capiMutex: threading.Semaphore = threading.Semaphore()

    def __del__(self):
        if self.requests_session:
            self.requests_session.close()

this = This()

class PushRequest:
    """Holds info about things to send to the Google Sheet"""
    TYPE_CMDR_SELL: int = 1
    TYPE_CARRIER_LOC_UPDATE: int = 2
    TYPE_CARRIER_MARKET_UPDATE: int = 3
    TYPE_CARRIER_CMDR_BUY: int = 4
    TYPE_CARRIER_BUY_SELL_ORDER_UPDATE: int = 5
    TYPE_CARRIER_JUMP: int = 6
    TYPE_SCS_SELL: int = 7
    TYPE_CMDR_UPDATE: int = 8
    TYPE_CARRIER_TRANSFER: int = 9
    TYPE_CARRIER_RECONCILE: int = 10
    TYPE_CMDR_BUY: int = 11
    TYPE_CARRIER_INTRANSIT_RECALC: int = 12

    def __init__(self, cmdr, station: str, reqType: int, data: dict):
        self.cmdr = cmdr
        self.station = station
        self.type = reqType
        self.data = data

def plugin_prefs(parent: ttk.Notebook, cmdr: str | None, is_beta: bool) -> nb.Frame:
    """
    Return a TK Frame for adding to the EDMC settings dialog.
    """
    PADX = 10
    BUTTONX = 12
    PADY = 1
    BOXY = 2
    SEPY = 10

    this.settingsClosed = False
    this.configSheetName = tk.StringVar(value=config.get_str('configSheetName', default='EDMC Plugin Settings'))

    frame = nb.Frame(parent)
    frame.columnconfigure(1, weight=1)

    row = AutoInc(start=0)

    with row as cur_row:
        HyperlinkLabel(
            frame, text='MERC Expedition Needs', background=nb.Label().cget('background'), url=f'https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit',
            underline=True
        ).grid(row=cur_row, columnspan=2, padx=PADX, pady=PADY+4, sticky=tk.W)    
        nb.Label(frame, text='Version %s' % VERSION).grid(row=cur_row, column=3, padx=PADX, pady=PADY+4, sticky=tk.W)

    ttk.Separator(frame, orient=tk.HORIZONTAL).grid(row=row.get(), columnspan=4, padx=PADX, pady=PADY, sticky=tk.EW)

    if this.sheet:
        sheetNames: list[str] = this.sheet.sheet_names()
    else:
        sheetNames: list[str] = ('ERROR',)
        
    with row as cur_row:
        nb.Label(frame, text='Settings Sheet').grid(row=cur_row, column=0, padx=PADX, pady=PADY, sticky=tk.W)
        nb.OptionMenu(
            frame, this.configSheetName, this.configSheetName.get(), *sheetNames
        ).grid(row=cur_row, column=1, columnspan=2, padx=PADX, pady=BOXY, sticky=tk.W)

    this.clearAuthButton = ttk.Button(
        frame,
        text='Clear Google Authentication',
        command=lambda: clear_token_and_disable_button(),
        state=tk.ACTIVE if this.auth.access_token else tk.DISABLED
    )
    this.clearAuthButton.grid(row=row.get(), padx=BUTTONX, pady=PADY, sticky=tk.W)

    ttk.Separator(frame, orient=tk.HORIZONTAL).grid(row=row.get(), columnspan=4, padx=PADX, pady=PADY+4, sticky=tk.EW)

    with row as cur_row:
        nb.Label(frame, text='Currently Assigned Carrier').grid(row=cur_row, column=0, padx=PADX, pady=PADY, sticky=tk.W)
        nb.OptionMenu(
            frame, this.configSheetName, this.configSheetName.get(), *sheetNames
        ).grid(row=cur_row, column=1, columnspan=2, padx=PADX, pady=BOXY, sticky=tk.W)

    return frame

def clear_token_and_disable_button() -> None:
    logger.info('Clearing Google Authentication token')
    this.auth.clear_auth_token()
    this.clearAuthButton.configure(state=tk.DISABLED)

def prefs_changed(cmdr: str | None, is_beta: bool) -> None:
    """
    Reload settings for new CMDR
    """
    this.settingsClosed = True

    initial_startup()

def plugin_start3(plugin_dir: str) -> str:
    """
    Only allow the plugin to run in version 5 and above
    """
    if isinstance(appversion, str):
        core_version = semantic_version.Version(appversion)

    elif callable(appversion):
        core_version = appversion()
    
    logger.info(f'Core EDMC version: {core_version}')
    if core_version < semantic_version.Version('5.0.0-beta1'):
        raise ValueError('Unable to run before EDMC version 5.0.0-beta1. Please upgrade EDMC')
    
    logger.debug('Starting worker thread...')
    this.thread = Thread(target=worker, name='MoMCT worker')
    this.thread.daemon = True
    this.thread.start()
    logger.debug('Done.')
    
    return 'MoM: Colonisation Tracker'

def plugin_stop() -> None:
    """Stop the plugin"""
    logger.debug('Shutting down...')
    
    this.thread.join()
    this.thread = None
    
    logger.debug('done')

def worker() -> None:
    """Main worker thread to send/get tracking data"""
    logger.debug('Worker starting')

    if not this.enabled:
        logging.info('Plugin Disbaled, exiting')
        return
    
    # Wait until we know what cmdr we're working with
    logger.debug('Waiting for current cmdr to be identified...')
    while not monitor.cmdr:
        time.sleep(1 / 10)
        if config.shutting_down:
            logger.debug("Main: Shutting down, existing thread")
            return None
    
    while True:
        try:
            initial_startup()
            break
        except Exception:
            logger.error(traceback.format_exc())
            # wait 30 seconds and try again
            for i in range(1, 30):
                time.sleep(1)
                if config.shutting_down:
                    logger.debug('Main: Shutting down, exiting thread')
                    return None

    # Then start the main loop
    logger.debug("Startup complete, entering main loop")
    while True:
        # Do some stuff
        try:
        
            # Auth token has been cleared via the button in settings
            if not this.auth.access_token:
                while not this.settingsClosed:
                    if config.shutting_down:
                        logger.debug("Main: Shutting down, exiting thread")
                        return None
                    # Spin
                    time.sleep(1 / 10)
            
                time.sleep(1)   # Give the settings window a second to actually close before we stall the UI
                this.auth.refresh()

            while process_kill_siwtches():
                logger.warning('Killsiwtch Active, reporting paused... [retrying in 60 seconds]')
                for i in range(1, 60):
                    ## Don't sleep for the full 60 seconds here, in case shutdown is called, we need to quit ASAP
                    time.sleep(1)
                    if config.shutting_down:
                        logger.debug('Main: Shutting down, exiting thread')
                        return None

            ##logger.debug('Checking for next item in the queue... [Queue Empty: ' + str(this.queue.empty()) + ']')
            try:
                item: PushRequest = this.queue.get(timeout=1)
                process_item(item)
            except:
                # Empty, all good, lets go around again
                pass

            if config.shutting_down:
                logger.debug('Main: Shutting down, exiting thread')
                this.auth = None
                return None
        
        except Exception:
            logger.error(traceback.format_exc())
            # wait 30 seconds and try again
            for i in range(1, 30):
                time.sleep(1)
                if config.shutting_down:
                    logger.debug('Main: Shutting down, exiting thread')
                    return None

def initial_startup() -> None:
    """'First' startup code. Also called after settings have changed"""
    # Get auth token first
    this.auth = Auth(monitor.cmdr, this.requests_session)
    this.auth.refresh()

    # Ok, now make sure we can access the spreadsheet
    this.sheet = Sheet(this.auth, this.requests_session)
    
    # Request some initial settings
    this.sheet.populate_initial_settings()
    this.killswitches = this.sheet.killswitches
    
    # Record the fact that we're using the plugin
    this.sheet.record_plugin_usage(monitor.cmdr, VERSION)

def process_kill_siwtches() -> bool:
    """Go through all the killswitches and if any match, return True to suspend the plugin"""
    
    if len(this.killswitches) == 0:
        return False
    
    if 'last updated' in this.killswitches:
        #logger.debug('Checking if update required')
        if time.localtime() > time.localtime(float(this.killswitches.get('last updated')) + 59):
            this.sheet.populate_initial_settings()
            this.killswitches = this.sheet.killswitches

    if 'enabled' in this.killswitches:
        if not this.killswitches.get('enabled') == 'true':
            logger.warning('Killswitch: Enabled = False')
            this.enabled = False
            return True
        else:
            this.enabled = True
        
    if 'minimum version' in this.killswitches:
        if semantic_version.Version(VERSION) < semantic_version.Version(this.killswitches.get('minimum version')):
            logger.warning(f'Killswitch: Minimum Version ({this.killswitches.get("minimum version")}) is higher than us')
            return True
        
    return False

def process_item(item: PushRequest) -> None:
    # Don't let one failed update kill the entire plugin
    try:
        logger.debug(f'Processing item: [{item.type}] {item.data}')
        sheetName = this.sheet.carrierTabNames.get(item.station)
        
        match item.type:
            case PushRequest.TYPE_CMDR_SELL:
                logger.info('Processing CMDR Sell request')
                if this.killswitches.get(KILLSWITCH_CMDR_BUYSELL, 'true') != 'true':
                    logger.warning('DISABLED by killswitch, ignoring')
                    return
                
                inTransit = False
                commodity = item.data['Type']
                amount = int(item.data['Count'])

                if not sheetName:
                    sheetName = this.sheet.carrierTabNames.get(this.cmdrsAssignedCarrier)
                    logger.info(f'Carrier not known, assuming in-transit for {sheetName}')
                    inTransit = True
                    amount = amount * -1    # Selling, so carrier should 'loose' this amount (even, if it never really gained it)
                
                this.sheet.add_to_carrier_sheet(sheetName, item.cmdr, commodity, amount, inTransit=inTransit)
            case PushRequest.TYPE_CARRIER_LOC_UPDATE:
                logger.info('Processing Carrier Location update')
                if this.killswitches.get(KILLSWITCH_CARRIER_LOC, 'true') != 'true':
                    logger.warning('DISABLED by killswitch, ignoring')
                    return
                this.sheet.update_carrier_location(sheetName, item.data)
            case PushRequest.TYPE_CARRIER_MARKET_UPDATE:
                logger.info('Processing Carrier Market update')
                if this.killswitches.get(KILLSWITCH_CARRIER_MARKET, 'true') != 'true':
                    logger.warning('DISABLED by killswitch, ignoring')
                    return
                this.sheet.update_carrier_market(sheetName, item.data)
            case PushRequest.TYPE_CARRIER_CMDR_BUY:
                logger.info('Processing Carrier CMDR Buy request')
                if this.killswitches.get(KILLSWITCH_CMDR_BUYSELL, 'true') != 'true':
                    logger.warning('DISABLED by killswitch, ignoring')
                    return
                commodity = item.data['Type']
                amount = int(item.data['Count']) * -1   # We're removing from the carrier
                this.sheet.add_to_carrier_sheet(sheetName, item.cmdr, commodity, amount)
            case PushRequest.TYPE_CARRIER_BUY_SELL_ORDER_UPDATE:
                logger.info('Processing Carrier Buy/Sell Order update')
                logger.debug(this.killswitches)
                if this.killswitches.get(KILLSWITCH_CARRIER_BUYSELL_ORDER, 'true') != 'true':
                    logger.warning('DISABLED by killswitch, ignoring')
                    return
                commodity = item.data['Commodity']
                amount = 0
                # Currently, only track Buy orders
                if item.data.get('PurchaseOrder'):
                    amount = int(item.data['PurchaseOrder'])
                this.sheet.update_carrier_market_entry(sheetName, item.station, commodity, amount)
            case PushRequest.TYPE_CARRIER_JUMP:
                logger.info('Processing Carrier Jump update')
                if this.killswitches.get(KILLSWITCH_CARRIER_JUMP, 'true') != 'true':
                    logger.warning('DISABLED by killswitch, ignoring')
                    return
                destination = item.data.get('Body')
                departTime = item.data.get('DepartureTime')
                this.sheet.update_carrier_jump_location(sheetName, destination, departTime)
            case PushRequest.TYPE_SCS_SELL:
                logger.info('Processing SCS Sell request')
                if this.killswitches.get(KILLSWITCH_SCS_SELL, 'true') != 'true':
                    logger.warning('DISABLED by killswitch, ignoring')
                    return
                process_scs_market_updates(item.cmdr, item.station, item.data)
            case PushRequest.TYPE_CMDR_UPDATE:
                logger.info('Processing CMDR Update')
                if this.killswitches.get(KILLSWITCH_CMDR_UPDATE, 'true') != 'true':
                    logger.warning('DISABLED by killswitch, ignoring')
                    return
                this.sheet.update_cmdr_attributes(item.cmdr, this.cargoCapacity)
            case PushRequest.TYPE_CARRIER_TRANSFER:
                logger.info('Processing Carrier Transfer request')
                if this.killswitches.get(KILLSWITCH_CARRIER_TRANSFER, 'true') != 'true':
                    logger.warning('DISABLED by killswitch, ignoring')
                    return
                process_carrier_transfer(sheetName, item.cmdr, item.data)
            case PushRequest.TYPE_CARRIER_RECONCILE:
                logger.info('Processing Carrier Reconcile request')
                if this.killswitches.get(KILLSWITCH_CARRIER_RECONCILE, 'true') != 'true':
                    logger.warning('DISABLED by killswitch, ignoring')
                    return
                this.sheet.reconcile_carrier_market(item.data)
            case PushRequest.TYPE_CMDR_BUY:
                # This is really only split from the carrier one in case we want to do different things... but could always be merged
                logger.info(f'Processing CMDR Buy Request, assuming in-transit for {sheetName}')
                if this.killswitches.get(KILLSWITCH_CMDR_BUYSELL, 'true') != 'true':
                    logger.warning('DISABLED by killswitch, ignoring')
                    return
                commodity = item.data['Type']
                amount = int(item.data['Count'])
                this.sheet.add_to_carrier_sheet(sheetName, item.cmdr, commodity, amount, inTransit=True)
            case PushRequest.TYPE_CARRIER_INTRANSIT_RECALC:
                logger.info('Processing Carrier In-Transit Recalculate request')
                resetCargo = False
                if item.data:
                    resetCargo = bool(item.data.get('clear', False))
                this.sheet.recalculate_in_transit(sheetName, item.cmdr, clear=resetCargo)
            case _:
                raise "Unknown PushRequest"
    except Exception:
        logger.error(traceback.format_exc())

def process_scs_market_updates(cmdr: str, station: str, data: dict) -> None:
    """Because SCS transfers don't provide the same journal info, we'll have to get a bit more creative"""
    # Its most likely that the current cargo will be empty, but that might not be the case
    for cargoItem in data['oldCargo']:
        logger.debug(f"Checking for difference in {cargoItem}")
        if not cargoItem in data['newCargo']:
            logger.debug('All Transferred')
            amount = int(data['oldCargo'][cargoItem])
            this.sheet.add_to_scs_sheet(cmdr, station, cargoItem, amount)
        else:
            logger.debug('Partial transfer (or none)')
            oldAmount = int(data['oldCargo'][cargoItem])
            newAmount = int(data['newCargo'][cargoItem])
            if oldAmount == newAmount:
                # Skip, nothing was actually transferred
                logger.debug('none, skipping')
                continue
            else:
                this.sheet.add_to_scs_sheet(cmdr, station, cargoItem, oldAmount - newAmount)    # Yes, this is backwards, but we want a positive amount

def process_carrier_transfer(sheetName: str, cmdr: str, data:dict) -> None:
    """Handle direct carrier transfers, so totals still line up"""
    for transfer in data['Transfers']:
        commodity = transfer['Type']
        amount = int(transfer['Count'])
        
        if transfer['Direction'] == 'tocarrier':
            # Count this as a 'Sell'
            this.sheet.add_to_carrier_sheet(sheetName, cmdr, commodity, amount)
        else:
            # Count this as a 'Buy'
            amount = amount * -1
            this.sheet.add_to_carrier_sheet(sheetName, cmdr, commodity, amount)

def journal_entry(cmdr, is_beta, system, station, entry, state):
    if not this.sheet:
        logger.error('Journal entry before finished authenticating to Google, ignored')
        return

    
    location = station
    if not location and entry.get('CarrierID'): # Event must be carrier based
        location = this.carrierCallsign
    logger.debug(entry['event'] + ' at ' + (location or '<unknown>'))
    logger.debug(f'Entry: {entry}')
    logger.debug(f'State: {state}')
    

    if this.carrierAPIEnabled.get():
        this.capiMutex.acquire()
        
        # Stick to the 15 minute cooldown that EDMC uses
        if int(time.time()) > (this.lastCarrierQueryTime.get() + capi_fleetcarrier_query_cooldown):
            # Request info from the Carrier API.
            # This seems to run on the same server that calculates jump slots, so when its busy the API takes *ages* to respond
            query_time = int(time.time())
            this.lastCarrierQueryTime.set(query_time)
            logger.debug('Calling FC API...')
            csession.fleetcarrier(
                query_time=query_time, tk_response_event=_CAPI_RESPONSE_TK_EVENT_NAME
            )
            logger.debug('Done')

        this.capiMutex.release()
        

    if entry['event'] == 'StartUp':
        """
        {
            'timestamp': '2025-03-01T23:22:53Z',
            'event': 'StartUp',
            'StarSystem': 'Zlotrimi',
            'StarPos': [-16.0, -23.21875, 139.5625],
            'SystemAddress': 3618249902459,
            'Population': 930301705,
            'Docked': True,
            'MarketID': 3231007232,
            'StationName': 'Hieb Terminal',
            'StationType': 'Orbis'
        }
        """
        logger.info(f'StartUp: In system {system}')
        if station is None:
            logger.info('StartUp: Flying in normal space')
        else:
            logger.info(f'StartUp: Docked at {station}')
        this.currentCargo = state['Cargo']
        this.cargoCapacity = state['CargoCapacity']
        this.queue.put(PushRequest(cmdr, station, PushRequest.TYPE_CMDR_UPDATE, None))

        if entry.get('StationType') == 'FleetCarrier':
            this.carrierCallsign = station
            this.queue.put(PushRequest(cmdr, station, PushRequest.TYPE_CARRIER_INTRANSIT_RECALC, None))
        else:
            this.queue.put(PushRequest(cmdr, this.cmdrsAssignedCarrier, PushRequest.TYPE_CARRIER_INTRANSIT_RECALC, None))

    elif entry['event'] == 'Location':
        logger.info(f'Location: In system {system}')
        if station is None:
            logger.info('Location: Flying in normal space')
        else:
            logger.info(f'Location: Docked at {station}')
    elif entry['event'] == 'FSDJump':
        logger.info(f'FSDJump: Arrived In system {system}')
    elif entry['event'] == 'Docked':
        # Keep track of current cargo
        this.currentCargo = state['Cargo']
        
         # Update the carrier location
        if station in this.sheet.carrierTabNames.keys():
            this.queue.put(PushRequest(cmdr, station, PushRequest.TYPE_CARRIER_LOC_UPDATE, system))
            this.carrierCallsign = station

        # Update cargo capacity if its changed (There might be a better event for this)
        if this.cargoCapacity != state['CargoCapacity']:
            this.queue.put(PushRequest(cmdr, station, PushRequest.TYPE_CMDR_UPDATE, None))
        this.cargoCapacity = state['CargoCapacity']

    elif entry['event'] == 'Undocked':
         this.currentCargo = None
    elif entry['event'] == 'Cargo':
        # SCS don't do MarketSell, but there are Cargo events, so lets just track what we started with and do a diff
        if station == 'System Colonisation Ship' or station == '$EXT_PANEL_ColonisationShip:#index=1;':
            data = {
                'oldCargo': this.currentCargo,
                'newCargo': state['Cargo']
            }
            this.queue.put(PushRequest(cmdr, system, PushRequest.TYPE_SCS_SELL, data))
            this.currentCargo = state['Cargo']
        # No more cago, lets make sure any in-transit stuff we might have been tracking is cleared
        if int(entry.get('Count', 0)) == 0:
            this.queue.put(PushRequest(cmdr, system, PushRequest.TYPE_CARRIER_INTRANSIT_RECALC, {'clear': True}))
    elif entry['event'] == 'Market':
        # Actual market data is in the market.json file
        if station in this.sheet.carrierTabNames.keys():
            logger.debug(f'Station ({station}) known, checking market data')
            journaldir = config.get_str('journaldir')
            if journaldir is None or journaldir == '':
                journaldir = config.default_journal_dir

            path = Path(journaldir) / f'{entry["event"]}.json'
            logger.debug(path)
            try:
                with path.open('rb') as dataFile:
                    marketData = json.load(dataFile)
                    this.queue.put(PushRequest(cmdr, station, PushRequest.TYPE_CARRIER_MARKET_UPDATE, marketData))
            except Exception:
                logger.error(traceback.format_exc())
    elif entry['event'] == 'MarketSell':
        """
        {
            'timestamp': '2025-03-01T23:18:21Z',
            'event': 'MarketSell',
            'MarketID': 3231007232,
            'Type': 'liquidoxygen',
            'Type_Localised': 'Liquid oxygen',
            'Count': 1,
            'SellPrice': 572,
            'TotalSale': 572,
            'AvgPricePaid': 650
        }
        """
        logger.debug(f'MarketSell: CMDR {cmdr} sold {entry["Count"]} {entry["Type"]} to {station}')
        if station in this.sheet.carrierTabNames.keys():
            logger.debug('Station known, creating queue entry')
            # Something for us to do, lets queue it
            this.queue.put(PushRequest(cmdr, station, PushRequest.TYPE_CMDR_SELL, entry))
        else:
            logger.debug(f'Station ({station}) unknown, assuming transfer to carrier')
            # This will get messy
            this.queue.put(PushRequest(cmdr, station, PushRequest.TYPE_CMDR_SELL, entry))
    elif entry['event'] == 'MarketBuy':
        """
        {
            "timestamp": "2025-03-08T07:09:11Z",
            "event": "MarketBuy",
            "MarketID": 3231007232,
            "Type": "superconductors",
            "Count": 124,
            "BuyPrice": 5862,
            "TotalCost": 726888
        }
        """
        logger.debug(f'MarketBuy: CMDR {cmdr} bought {entry["Count"]} {entry["Type"]} from {station}')
        if station in this.sheet.carrierTabNames.keys():
            logger.debug('Station known, creating queue entry')
            # Something for us to do, lets queue it
            this.queue.put(PushRequest(cmdr, station, PushRequest.TYPE_CARRIER_CMDR_BUY, entry))
        else:
            logger.debug(f'Station ({station}) unknown, assuming transfer to carrier')
            # This will get messy
            this.queue.put(PushRequest(cmdr, this.cmdrsAssignedCarrier, PushRequest.TYPE_CMDR_BUY, entry))
    elif entry['event'] == 'CarrierTradeOrder':
        """
        // BUY Order
        {
            "timestamp": "2025-03-08T05:39:13Z",
            "event": "CarrierTradeOrder",
            "CarrierID": 3707348992,
            "BlackMarket": false,
            "Commodity": "copper",
            "PurchaseOrder": 252,
            "Price": 1267
        }
        // SELL Order
        {
            "timestamp": "2025-03-08T23:57:41Z",
            "event": "CarrierTradeOrder",
            "CarrierID": 3707348992,
            "BlackMarket": false,
            "Commodity": "steel",
            "SaleOrder": 70,
            "Price": 4186
        }
        // CANCEL Order
        {
            "timestamp": "2025-03-09T00:06:29Z",
            "event": "CarrierTradeOrder",
            "CarrierID": 3707348992,
            "BlackMarket": false,
            "Commodity": "insulatingmembrane",
            "Commodity_Localised": "Insulating Membrane",
            "CancelTrade": true
        }
        """
        if this.carrierCallsign and this.carrierCallsign in this.sheet.carrierTabNames.keys():
            logger.debug(f'Carrier "{this.carrierCallsign}" known, creating queue entry')
            this.queue.put(PushRequest(cmdr, this.carrierCallsign, PushRequest.TYPE_CARRIER_BUY_SELL_ORDER_UPDATE, entry))
        else:
            logger.debug(f'Carrier "{this.carrierCallsign}" not known, skipping market update')
    elif entry['event'] == 'CarrierJumpRequest' or entry['event'] == 'CarrierJumpCancelled':
        """
        {
            "timestamp": "2025-03-09T02:44:36Z",
            "event": "CarrierJumpRequest",
            "CarrierID": 3707348992,
            "SystemName": "LTT 8001",
            "Body": "LTT 8001 A 2",
            "SystemAddress": 3107442365154,
            "BodyID": 6,
            "DepartureTime": "2025-03-09T03:36:10Z"
        }
        """
        if this.carrierCallsign and this.carrierCallsign in this.sheet.carrierTabNames.keys():
            logger.debug(f'Carrier "{this.carrierCallsign}" known, creating queue entry')
            this.queue.put(PushRequest(cmdr, this.carrierCallsign, PushRequest.TYPE_CARRIER_JUMP, entry))
    elif entry['event'] == 'CarrierJump':
        """
        {
            "timestamp": "2025-03-14T07:11:01Z",
            "event": "CarrierJump",
            "Docked": false,
            "OnFoot": true,
            "StarSystem": "Katuri",
            "SystemAddress": 3309012257139,
            "StarPos": [-19.68750, -6.06250, 81.56250],
            "SystemAllegiance": "Federation",
            "SystemEconomy": "$economy_Agri;",
            "SystemEconomy_Localised": "Agriculture",
            "SystemSecondEconomy": "$economy_Refinery;",
            "SystemSecondEconomy_Localised": "Refinery",
            "SystemGovernment": "$government_Democracy;",
            "SystemGovernment_Localised": "Democracy",
            "SystemSecurity": "$SYSTEM_SECURITY_high;",
            "SystemSecurity_Localised": "High Security",
            "Population": 2841893384,
            "Body": "Katuri A 1",
            "BodyID": 7,
            "BodyType": "Planet",
            "ControllingPower": "Yuri Grom",
            "Powers": ["Edmund Mahon", "Yuri Grom"],
            "PowerplayState": "Stronghold",
            "Factions": [{
                    "Name": "Independents of Katuri",
                    "FactionState": "None",
                    "Government": "Democracy",
                    "Influence": 0.009911,
                    "Allegiance": "Independent",
                    "Happiness": "$Faction_HappinessBand2;",
                    "Happiness_Localised": "Happy",
                    "MyReputation": 0.000000
                }, {
                    "Name": "Katuri Jet Advanced Inc",
                    "FactionState": "None",
                    "Government": "Corporate",
                    "Influence": 0.014866,
                    "Allegiance": "Federation",
                    "Happiness": "$Faction_HappinessBand2;",
                    "Happiness_Localised": "Happy",
                    "MyReputation": 0.000000
                }, {
                    "Name": "Defence Force of Katuri",
                    "FactionState": "None",
                    "Government": "Dictatorship",
                    "Influence": 0.016848,
                    "Allegiance": "Independent",
                    "Happiness": "$Faction_HappinessBand2;",
                    "Happiness_Localised": "Happy",
                    "MyReputation": 0.000000
                }, {
                    "Name": "Katuri Legal Company",
                    "FactionState": "None",
                    "Government": "Corporate",
                    "Influence": 0.025768,
                    "Allegiance": "Federation",
                    "Happiness": "$Faction_HappinessBand2;",
                    "Happiness_Localised": "Happy",
                    "MyReputation": 0.000000
                }, {
                    "Name": "Katuri Jet Boys",
                    "FactionState": "None",
                    "Government": "Anarchy",
                    "Influence": 0.018831,
                    "Allegiance": "Independent",
                    "Happiness": "$Faction_HappinessBand2;",
                    "Happiness_Localised": "Happy",
                    "MyReputation": 0.000000
                }, {
                    "Name": "Section 31",
                    "FactionState": "None",
                    "Government": "Corporate",
                    "Influence": 0.009911,
                    "Allegiance": "Federation",
                    "Happiness": "$Faction_HappinessBand2;",
                    "Happiness_Localised": "Happy",
                    "MyReputation": 0.000000
                }, {
                    "Name": "Intergalactic Nova Republic",
                    "FactionState": "None",
                    "Government": "Democracy",
                    "Influence": 0.903865,
                    "Allegiance": "Federation",
                    "Happiness": "$Faction_HappinessBand2;",
                    "Happiness_Localised": "Happy",
                    "MyReputation": 0.000000,
                    "PendingStates": [{
                            "State": "Expansion",
                            "Trend": 0
                        }
                    ]
                }
            ],
            "SystemFaction": {
                "Name": "Intergalactic Nova Republic"
            }
        }
        """
        if this.carrierCallsign and this.carrierCallsign in this.sheet.carrierTabNames.keys():
            logger.debug(f'Carrier "{this.carrierCallsign}" known, creating queue entry')
            this.queue.put(PushRequest(cmdr, this.carrierCallsign, PushRequest.TYPE_CARRIER_JUMP, entry))
    elif entry['event'] == 'CarrierStats':
        """
        {
            'timestamp': '2025-03-09T05:07:21Z',
            'event': 'CarrierStats',
            'CarrierID': 3707348992,
            'Callsign': 'X7H-9KW',
            'Name': 'THE LAST RESORT',
            'DockingAccess': 'all',
            'AllowNotorious': True,
            'FuelLevel': 456,
            'JumpRangeCurr': 500.0,
            'JumpRangeMax': 500.0,
            'PendingDecommission': False,
            'SpaceUsage': {
                'TotalCapacity': 25000,
                'Crew': 680,
                'Cargo': 715,
                'CargoSpaceReserved': 21941,
                'ShipPacks': 0,
                'ModulePacks': 0,
                'FreeSpace': 1664
            },
            'Finance': {
                'CarrierBalance': 1997048445,
                'ReserveBalance': 0,
                'AvailableBalance': 1824985690,
                'ReservePercent': 0,
                'TaxRate_refuel': 8,
                'TaxRate_repair': 10
            },
            'Crew': [{
                    'CrewRole': 'BlackMarket',
                    'Activated': False
                }, {
                    'CrewRole': 'Captain',
                    'Activated': True,
                    'Enabled': True,
                    'CrewName': 'Loren Mcdowell'
                }, {
                    'CrewRole': 'Refuel',
                    'Activated': True,
                    'Enabled': True,
                    'CrewName': 'Marlin Cain'
                }, {
                    'CrewRole': 'Repair',
                    'Activated': True,
                    'Enabled': True,
                    'CrewName': 'Jemma Short'
                }, {
                    'CrewRole': 'Rearm',
                    'Activated': False
                }, {
                    'CrewRole': 'Commodities',
                    'Activated': True,
                    'Enabled': True,
                    'CrewName': 'Jennifer Cardenas'
                }, {
                    'CrewRole': 'VoucherRedemption',
                    'Activated': False
                }, {
                    'CrewRole': 'Exploration',
                    'Activated': False
                }, {
                    'CrewRole': 'Shipyard',
                    'Activated': False
                }, {
                    'CrewRole': 'Outfitting',
                    'Activated': False
                }, {
                    'CrewRole': 'CarrierFuel',
                    'Activated': True,
                    'Enabled': True,
                    'CrewName': 'Jorge Dale'
                }, {
                    'CrewRole': 'VistaGenomics',
                    'Activated': False
                }, {
                    'CrewRole': 'PioneerSupplies',
                    'Activated': False
                }, {
                    'CrewRole': 'Bartender',
                    'Activated': False
                }
            ],
            'ShipPacks': [],
            'ModulePacks': []
        }
        """
        # Keep track of the call sign for easy lookups later
        this.carrierCallsign = entry['Callsign']
        logger.debug(f'Carrier ID updated to {this.carrierCallsign}')
    elif entry['event'] == 'CargoTransfer':
        """
        {
            "timestamp": "2025-03-14T10:26:51Z",
            "event": "CargoTransfer",
            "Transfers": [{
                    "Type": "steel",
                    "Count": 76,
                    "Direction": "tocarrier"
                }, {
                    "Type": "steel",
                    "Count": 644,
                    "Direction": "tocarrier"
                }
            ]
        }
        """
        if this.carrierCallsign and this.carrierCallsign in this.sheet.carrierTabNames.keys():
            logger.debug(f'Carrier "{this.carrierCallsign}" known, creating queue entry')
            this.queue.put(PushRequest(cmdr, this.carrierCallsign, PushRequest.TYPE_CARRIER_TRANSFER, entry))
    elif entry['event'] == 'CarrierDepositFuel':
        """
        {
            "timestamp": "2025-03-25T08:06:16Z",
            "event": "CarrierDepositFuel",
            "CarrierID": 3707348992,
            "Amount": 1,
            "Total": 245
        }
        """
        if station in this.sheet.carrierTabNames.keys():
            logger.debug(f'Carrier "{station}" known, creating queue entry')
            # Lets make a synthic entry, to mimick a MarketSell request
            sellEntry = {
                'Type': 'tritium',
                'Count': int(entry['Amount'])
            }
            this.queue.put(PushRequest(cmdr, station, PushRequest.TYPE_CMDR_SELL, sellEntry))

def cmdr_data(data, is_beta):
    if data.source_host == SERVER_LIVE:
        logger.debug(f'CAPI: {data}')
        
def capi_fleetcarrier(data):
    """ Fleetcarrier data is not updated often, so calling this more than once every 15 minutes is pointless"""
    if data.source_host == SERVER_LIVE:
        logger.debug(f'FC: {data}')

        # Reconcile Fleet Carrier orders
        # TODO: Change from overwriting starting inv, and use descrepency instead
        # TODO: This is so far behind current tracking that its useless when actively being filled :(
        # Just ignore it then ?
        #this.queue.put(PushRequest(None, None, PushRequest.TYPE_CARRIER_RECONCILE, data))

        # Update current location

    
