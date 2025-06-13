#
# Mercs of Mikunn - Colonisation Tracker
# Created by meeces2911
#

import logging
import threading
import tkinter as tk
import requests
import traceback
import sys

from tkinter import ttk
from threading import Lock, Thread
from pathlib import Path
from queue import SimpleQueue

import semantic_version
import time
import json

import plug
import myNotebook as nb
from monitor import monitor
from config import config, appname, appversion, user_agent
from companion import CAPIData, SERVER_LIVE, capi_fleetcarrier_query_cooldown, session as csession
from ttkHyperlinkLabel import HyperlinkLabel
from prefs import AutoInc
from theme import theme

from sheet import Sheet
from auth import Auth, SPREADSHEET_ID

plugin_name = Path(__file__).resolve().parent.name
logger = logging.getLogger(f'{appname}.{plugin_name}')

VERSION = '1.3.4'
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
KILLSWITCH_SCS_RECONCILE = 'scs reconcile'
KILLSWITCH_SCS_RECONCILE_DELAY = 'scs reconcile delay in seconds'
KILLSWITCH_SCS_DATA_POPULATE = 'scs data populate'

CONFIG_SHEET_NAME = 'mom_config_sheet_name'
CONFIG_ASSIGNED_CARRIER = 'mom_assigned_carrier'
CONFIG_UI_PLUGIN_STATUS = 'mom_show_plugin_status'
CONFIG_UI_SHOW_CARRIER = 'mom_show_assigned_carrier'
CONFIG_FEAT_TRACK_DELIVERY = 'mom_feature_track_delivery'
CONFIG_FEAT_ASSUME_CARRIER_UNLOAD_SCS = 'mom_feature_assume_carrier_unload_scs'

# Use the same 'icons' as the EDSM plugin
IMG_KNOWN_B64 = 'R0lGODlhEAAQAMIEAFWjVVWkVWS/ZGfFZ////////////////yH5BAEKAAQALAAAAAAQABAAAAMvSLrc/lAFIUIkYOgNXt5g14Dk0AQlaC1CuglM6w7wgs7rMpvNV4q932VSuRiPjQQAOw=='
IMG_UNKNOWN_B64 = 'R0lGODlhEAAQAKEDAGVLJ+ddWO5fW////yH5BAEKAAMALAAAAAAQABAAAAItnI+pywYRQBtA2CtVvTwjDgrJFlreEJRXgKSqwB5keQ6vOKq1E+7IE5kIh4kCADs='

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
        self.configSheetName: tk.StringVar = tk.StringVar(value=config.get_str(CONFIG_SHEET_NAME, default='EDMC Plugin Settings'))

        self.latestCarrierCallsign: str | None = None
        self.myCarrierCallsign: str | None = None
        self.cargoCapacity: int = 0
        self.cmdrsAssignedCarrier: tk.StringVar = tk.StringVar(value=config.get_str(CONFIG_ASSIGNED_CARRIER))
        self.nextSCSReconcileTime: int = int(time.time())
        self.dataPopulatedForSystems: list[str] = []

        self.clearAuthButton: tk.Button | None = None
        self.pauseWork: bool = False

        self.carrierAPIEnabled: tk.BooleanVar = tk.BooleanVar(value=config.get_bool('capi_fleetcarrier', default=False))  # Don't change this name, its used by EDMC
        self.lastCarrierQueryTime: tk.IntVar = tk.IntVar(value=config.get_int('fleetcarrierquerytime', default=0))  # Don't change this name, its used by EDMC
        self.nextUpdateCarrierTime: int = int(time.time())
        self.capiMutex: threading.Semaphore = threading.Semaphore()

        self.uiFrame: tk.Frame | None = None
        self.uiFrameRows: AutoInc = AutoInc(start=0)
        self._IMG_KNOWN = tk.PhotoImage(data=IMG_KNOWN_B64)
        self._IMG_UNKNOWN = tk.PhotoImage(data=IMG_UNKNOWN_B64)
        self.pluginStatusIcon: tk.Label | None = None
        self.showPluginStatus: tk.BooleanVar = tk.BooleanVar(value=config.get_bool(CONFIG_UI_PLUGIN_STATUS, default=True))
        self.showAssignedCarrier: tk.BooleanVar = tk.BooleanVar(value=config.get_bool(CONFIG_UI_SHOW_CARRIER, default=True))
        self.featureTrackDelivery: tk.BooleanVar = tk.BooleanVar(value=config.get_bool(CONFIG_FEAT_TRACK_DELIVERY, default=True))
        self.featureAssumeCarrierUnloadToSCS: tk.BooleanVar = tk.BooleanVar(value=config.get_bool(CONFIG_FEAT_ASSUME_CARRIER_UNLOAD_SCS, default=True))

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
    TYPE_SCS_SYSTEM_ADD: int = 13
    TYPE_SCS_PROGRESS_UPDATE: int = 14
    TYPE_SCS_DATA_POPULATE: int = 15

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

    logger.info('Settings opened, pausing worker thread')
    this.pauseWork = True
    this.cmdrsAssignedCarrier.set(config.get_str(CONFIG_ASSIGNED_CARRIER))   # Refetch this from the config db, in case its changed since start up

    frame: tk.Frame = nb.Frame(parent)
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
    
    with row as cur_row:
        this.clearAuthButton = ttk.Button(
            frame,
            text='Clear Google Authentication',
            command=lambda: clear_token_and_disable_button(),
            state=tk.ACTIVE if this.auth.access_token else tk.DISABLED
        )
        this.clearAuthButton.grid(row=cur_row, padx=BUTTONX, pady=PADY, sticky=tk.W)

        ttk.Button(
            frame, text='Clear all settings', command=lambda: clear_saved_settings(parent)
        ).grid(row=cur_row, column=3, columnspan=1, padx=BUTTONX, pady=PADY, sticky=tk.W)

    ttk.Separator(frame, orient=tk.HORIZONTAL).grid(row=row.get(), columnspan=4, padx=PADX, pady=PADY+4, sticky=tk.EW)

    nb.Checkbutton(frame, text='Show Connection Status', variable=this.showPluginStatus).grid(row=row.get(), column=0, padx=PADX, pady=PADY, sticky=tk.W)
    nb.Checkbutton(frame, text='Show Currently Assigned Carrier', variable=this.showAssignedCarrier).grid(row=row.get(), column=0, padx=PADX, pady=PADY, sticky=tk.W)

    with row as cur_row:
        nb.Label(frame, text='Currently Assigned Carrier').grid(row=cur_row, column=0, padx=PADX, pady=PADY, sticky=tk.W)
        nb.OptionMenu(
            frame, this.cmdrsAssignedCarrier, '', *this.sheet.carrierTabNames.values()
        ).grid(row=cur_row, column=1, columnspan=2, padx=PADX, pady=BOXY, sticky=tk.W)

    ttk.Separator(frame, orient=tk.HORIZONTAL).grid(row=row.get(), columnspan=4, padx=PADX, pady=PADY, sticky=tk.EW)

    nb.Checkbutton(frame, text='Delivery Tracking', variable=this.featureTrackDelivery).grid(row=row.get(), column=0, padx=PADX, pady=PADY, sticky=tk.W)
    nb.Checkbutton(frame, text='Assume Carrier Buy is for Unloading to SCS', variable=this.featureAssumeCarrierUnloadToSCS).grid(row=row.get(), column=0, padx=PADX, pady=PADY, sticky=tk.W)

    # If the dialog is closed without the user clicking ok, make sure we resume the worker
    frame.bind('<Destroy>', lambda event: prefs_changed_cancelled())

    return frame

def clear_token_and_disable_button() -> None:
    logger.info('Clearing Google Authentication token')
    this.auth.clear_auth_token()
    this.clearAuthButton.configure(state=tk.DISABLED)

def clear_saved_settings(parent) -> None:
    response = tk.messagebox.showinfo(
        'Warning',
        'This will clear all your EDMC specific settings related to this plugin. It will not change the spreadsheet in any way.\r\n\r\nAre you sure you wish to continue?',
        parent=parent,
        type='yesno'        # TODO: Can we work out what constant should be used here
    )
    if response == 'yes':   # TODO: Can we work out what constant should be used here
        logger.warning('Clearing settings')
        logger.debug('  Clearing Config Sheet Name')
        config.delete(CONFIG_SHEET_NAME, suppress=True)
        logger.debug('  Clearing CMDR Assigned Carrier')
        config.delete(CONFIG_ASSIGNED_CARRIER, suppress=True)
        logger.debug('  UI Show Plugin Status')
        config.delete(CONFIG_UI_PLUGIN_STATUS, suppress=True)
        logger.debug('  UI Show Assigned Carrier')
        config.delete(CONFIG_UI_SHOW_CARRIER, suppress=True)
        logger.debug('  Feature Delivery Tracking')
        config.delete(CONFIG_FEAT_TRACK_DELIVERY, suppress=True)
        logger.debug('  Feature Assume Carrier Unload To SCS')
        config.delete(CONFIG_FEAT_ASSUME_CARRIER_UNLOAD_SCS, suppress=True)

        config.save()

        # Reset the checkboxes to something sensible
        this.showPluginStatus.set(True)
        this.showAssignedCarrier.set(True)
        this.featureTrackDelivery.set(True)
        this.featureAssumeCarrierUnloadToSCS.set(True)

def prefs_changed_cancelled() -> None:
    """Settings dialog has been closed without clicking ok"""
    logger.info('Settings closed, resuming worker thread')
    this.pauseWork = False

def prefs_changed(cmdr: str | None, is_beta: bool) -> None:
    """
    Reload settings for new CMDR
    """
    logger.debug('Saving settings')

    # Save settings to DB
    config.set(CONFIG_SHEET_NAME, this.configSheetName.get())
    config.set(CONFIG_ASSIGNED_CARRIER, this.cmdrsAssignedCarrier.get())
    config.set(CONFIG_UI_PLUGIN_STATUS, this.showPluginStatus.get())
    config.set(CONFIG_UI_SHOW_CARRIER, this.showAssignedCarrier.get())
    config.set(CONFIG_FEAT_TRACK_DELIVERY, this.featureTrackDelivery.get())
    config.set(CONFIG_FEAT_ASSUME_CARRIER_UNLOAD_SCS, this.featureAssumeCarrierUnloadToSCS.get())

    # Update the widgets
    this.uiFrameRows = AutoInc(start=0)
    for widget in this.uiFrame.winfo_children():
        widget.destroy()
    this.uiFrame.grid(row=0)
    this.uiFrame.configure(height=1)
    
    _add_status_widget()
    _add_carrier_widget()

    theme.update(this.uiFrame)

    # Ok, now we can continue our worker thread
    logger.info('Settings closed, resuming worker thread')
    this.pauseWork = False

def plugin_app(parent: tk.Frame) -> tk.Frame:
    """Add our UI widgets here"""    
    this.uiFrame = tk.Frame(parent)
    this.uiFrameRows = AutoInc(start=0)

    _add_status_widget()
    _add_carrier_widget()

    theme.update(this.uiFrame)
    return this.uiFrame

def _add_status_widget() -> None:
    frame = this.uiFrame
    row = this.uiFrameRows

    if this.showPluginStatus.get():
        with row as cur_row:
            tk.Label(frame, text='Status:', ).grid(row=cur_row, column=0, sticky=tk.W)
            this.pluginStatusIcon = tk.Label(frame, image=this._IMG_UNKNOWN)
            this.pluginStatusIcon.grid(row=cur_row, column=1, sticky=tk.W)    

def _add_carrier_widget() -> None:
    frame = this.uiFrame
    row = this.uiFrameRows

    if this.showAssignedCarrier.get() and this.sheet:
        with row as cur_row:
            tk.Label(frame, text="Carrier:").grid(row=cur_row, column=0, sticky=tk.W)
            dropdown = tk.OptionMenu(
                frame, this.cmdrsAssignedCarrier, '', *this.sheet.carrierTabNames.values(), command=lambda value: config.set(CONFIG_ASSIGNED_CARRIER, value)
            )
            dropdown.grid(row=cur_row, column=1, sticky=tk.W)
            dropdown.configure(background=ttk.Style().lookup('TMenu', 'background'), highlightthickness=0, borderwidth=0)
            dropdown['menu'].configure(background=ttk.Style().lookup('TMenu', 'background'))        # TODO: Come back later and continue bashing this until it works

def _update_status_icon(newIcon: tk.PhotoImage) -> None:
    """Updates the Plugin Status icon if its currently viewable"""
    if this.showPluginStatus.get() and this.pluginStatusIcon:
        this.pluginStatusIcon['image'] = newIcon

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

    this._IMG_KNOWN = this._IMG_UNKNOWN = None
    
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

    # Add any of our UI widgets that require sheet data
    _add_carrier_widget()
    theme.update(this.uiFrame)

    # Then start the main loop
    logger.debug("Startup complete, entering main loop")
    while True:
        # Do some stuff
        try:
            # Settings have been opened, lets pause for a sec
            if this.pauseWork:
                while this.pauseWork:
                    if config.shutting_down:
                        logger.debug("Main: Shutting down, existing thread")
                        return
                    # Spin
                    time.sleep(1 / 10)
                
                # Auth token has been cleared via the button in settings
                if not this.auth.access_token:
                    this.auth.refresh()

                # Settings change, fetch everything from scratch    
                initial_startup()

            while process_kill_siwtches():
                logger.warning('Killsiwtch Active, reporting paused... [retrying in 60 seconds]')
                for i in range(1, 60):
                    ## Don't sleep for the full 60 seconds here, in case shutdown is called, we need to quit ASAP
                    time.sleep(1)
                    if config.shutting_down:
                        logger.debug('Main: Shutting down, exiting thread')
                        return None

            # Need to check if we're shutting down before updating the status icon, which checks some settings and hangs
            if config.shutting_down:
                logger.debug('Main: Shutting down, exiting thread')
                return None

            # Update the status indicator to show that we're all good to go
            _update_status_icon(this._IMG_KNOWN)

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
            _update_status_icon(this._IMG_UNKNOWN)
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
    this.sheet.populate_cmdr_data(monitor.cmdr)
    this.cmdrsAssignedCarrier.set(config.get_str(CONFIG_ASSIGNED_CARRIER))
    
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
            plug.show_error('MoM: Plugin Disabled by Killswitch')
            return True
        else:
            this.enabled = True
        
    if 'minimum version' in this.killswitches:
        if semantic_version.Version(VERSION) < semantic_version.Version(this.killswitches.get('minimum version')):
            logger.warning(f'Killswitch: Minimum Version ({this.killswitches.get("minimum version")}) is higher than us')
            plug.show_error('MoM: Upgrade Required')
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

                assignedCarrier = this.cmdrsAssignedCarrier.get()
                if not sheetName and assignedCarrier:
                    sheetName = this.sheet.carrierTabNames.get(this.sheet._get_carrier_id_from_name(assignedCarrier))
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
                if this.featureAssumeCarrierUnloadToSCS.get():
                    sheetName = this.sheet.lookupRanges[this.sheet.LOOKUP_SCS_SHEET_NAME]
                    system = item.data['System']
                    if system in this.sheet.systemsInProgress:
                        this.sheet.add_to_carrier_sheet(sheetName, item.cmdr, commodity, amount*-1, inTransit=True, system=system)
                    else:
                        logger.debug(f'{system} not in list of Systems In Progress, not adding in-transit delivery to SCS sheet')
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
                destination = item.data.get('Body', item.data.get('SystemName'))
                departTime = item.data.get('DepartureTime')
                this.sheet.update_carrier_jump_location(sheetName, destination, departTime)
            case PushRequest.TYPE_SCS_SELL:
                logger.info('Processing SCS Sell request')
                if this.killswitches.get(KILLSWITCH_SCS_SELL, 'true') != 'true':
                    logger.warning('DISABLED by killswitch, ignoring')
                    return
                timestamp = item.data['timestamp']
                for transfer in item.data['Contributions']:
                    commodity = transfer['Name'][1:-6].lower()  # Convert $<name>_name; to just <name>
                    amount = int(transfer['Amount'])
                    this.sheet.add_to_scs_sheet(item.cmdr, item.station, commodity, amount, timestamp)
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
                assignedCarrier = this.cmdrsAssignedCarrier.get()
                if not assignedCarrier:
                    logger.info('No assigned carrier, ignoring')
                    return

                sheetName = this.sheet.carrierTabNames.get(this.sheet._get_carrier_id_from_name(assignedCarrier))
                logger.info(f'Processing CMDR Buy Request, assuming in-transit for {sheetName}')
                if this.killswitches.get(KILLSWITCH_CMDR_BUYSELL, 'true') != 'true':
                    logger.warning('DISABLED by killswitch, ignoring')
                    return

                commodity = item.data['Type']
                amount = int(item.data['Count'])
                
                this.sheet.add_to_carrier_sheet(sheetName, item.cmdr, commodity, amount, inTransit=True)
            case PushRequest.TYPE_CARRIER_INTRANSIT_RECALC:
                assignedCarrier = this.cmdrsAssignedCarrier.get()
                resetCargo = False
                logger.info(f'Processing Carrier In-Transit Recalculate request for {item.station or assignedCarrier}')
                
                if item.data:
                    resetCargo = bool(item.data.get('clear', False))
                if not sheetName and assignedCarrier:
                    sheetName = this.sheet.carrierTabNames.get(this.sheet._get_carrier_id_from_name(assignedCarrier))
                if not sheetName:
                    logger.info('No assigned carrier, ignoring')
                    return
                this.sheet.recalculate_in_transit(sheetName, item.cmdr, clear=resetCargo)
            case PushRequest.TYPE_SCS_SYSTEM_ADD:
                logger.info('Processing SCS System Add request')
                # Keep in mind 'station' here is actually system ;)
                if item.data['event'] == 'ColonisationBeaconDeployed':
                    cmdr = item.cmdr
                this.sheet.add_in_progress_scs_system(item.station, cmdr=cmdr)
            case PushRequest.TYPE_SCS_PROGRESS_UPDATE:
                logger.info('Processing SCS Progress update')
                if this.killswitches.get(KILLSWITCH_SCS_RECONCILE, 'true') != 'true':
                    logger.warning('DISABLED by killswitch, ignoring')
                    return
                this.sheet.reconcile_scs_entries(item.cmdr, item.station, item.data['ResourcesRequired'], item.data['timestamp'])
            case PushRequest.TYPE_SCS_DATA_POPULATE:
                logger.info('Processing SCS Data Populate update')
                if this.killswitches.get(KILLSWITCH_SCS_DATA_POPULATE, 'true') != 'true':
                    logger.warning('DISABLED by killswitch, ignoring')
                    return
                this.sheet.populate_scs_data(item.station, item.data['ResourcesRequired'])
            case _:
                raise "Unknown PushRequest"
    except Exception:
        logger.error(traceback.format_exc())

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
    location = station
    if not location and entry.get('CarrierID'): # Event must be carrier based
        location = this.latestCarrierCallsign
    
    if entry['event'] in ('FSSSignalDiscovered', 'Friends', 'Music', 'ReceiveText', 'ReservoirReplenished'):
        # Suppress some events that we don't care about/don't want to log
        return
    
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
        
    match entry['event']:
        case 'StartUp' | 'LoadGame':
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
            this.cargoCapacity = state['CargoCapacity']
            this.queue.put(PushRequest(cmdr, station, PushRequest.TYPE_CMDR_UPDATE, None))

            # Check for any in-transit cargo for our assigned carrier
            this.queue.put(PushRequest(cmdr, None, PushRequest.TYPE_CARRIER_INTRANSIT_RECALC, None))
            if len(state.get('Cargo', {})) == 0:
                logger.debug('No cargo, queuing in-transit clear')
                this.queue.put(PushRequest(cmdr, None, PushRequest.TYPE_CARRIER_INTRANSIT_RECALC, {'clear': True}))

            if entry.get('StationType') == 'FleetCarrier':
                logger.debug('Docked at FleetCarrier, also checking for additional in-transit cargo')
                this.latestCarrierCallsign = station
                
                assignedCarrierId = this.sheet._get_carrier_id_from_name(this.cmdrsAssignedCarrier.get())
                if station != assignedCarrierId:
                
                    # Check for any in-transit cargo listed on the sheet
                    # We may have had to log out to work around the FC cargo bug
                    this.queue.put(PushRequest(cmdr, station, PushRequest.TYPE_CARRIER_INTRANSIT_RECALC, None))
                    if len(state.get('Cargo', {})) == 0:
                        logger.debug('No cargo, queuing in-transit clear')
                        this.queue.put(PushRequest(cmdr, station, PushRequest.TYPE_CARRIER_INTRANSIT_RECALC, {'clear': True}))  # Currently docked carrier
                
        case 'Location':
            logger.info(f'Location: In system {system}')
            if station is None:
                logger.info('Location: Flying in normal space')
            else:
                logger.info(f'Location: Docked at {station}')
        case 'FSDJump':
            logger.info(f'FSDJump: Arrived In system {system}')
        case 'Docked':
            # Update the carrier location
            if this.sheet and station in this.sheet.carrierTabNames.keys():
                this.queue.put(PushRequest(cmdr, station, PushRequest.TYPE_CARRIER_LOC_UPDATE, system))
                this.queue.put(PushRequest(cmdr, station, PushRequest.TYPE_CARRIER_JUMP, {}))
                this.latestCarrierCallsign = station

            # Update cargo capacity if its changed (There might be a better event for this)
            if this.cargoCapacity != state['CargoCapacity']:
                this.queue.put(PushRequest(cmdr, station, PushRequest.TYPE_CMDR_UPDATE, None))
            this.cargoCapacity = state['CargoCapacity']

            # Add SCS to spreadsheet if missing
            if this.sheet and not system in this.sheet.systemsInProgress and (station == 'System Colonisation Ship' or station.startswith('$EXT_PANEL_ColonisationShip')):
                this.queue.put(PushRequest(cmdr, system, PushRequest.TYPE_SCS_SYSTEM_ADD, entry))
        case 'Cargo':
            # No more cago, lets make sure any in-transit stuff we might have been tracking is cleared
            if int(entry.get('Count', 0)) == 0:
                this.queue.put(PushRequest(cmdr, station, PushRequest.TYPE_CARRIER_INTRANSIT_RECALC, {'clear': True}))
        case 'Market':
            # Actual market data is in the market.json file
            if this.sheet and station in this.sheet.carrierTabNames.keys():
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
        case 'MarketSell':
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
            # Something for us to do, lets queue it
            this.queue.put(PushRequest(cmdr, station, PushRequest.TYPE_CMDR_SELL, entry))
        case 'MarketBuy':
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
            # Something for us to do, lets queue it
            requestType = PushRequest.TYPE_CARRIER_CMDR_BUY if this.sheet.carrierTabNames.get(station) else PushRequest.TYPE_CMDR_BUY
            entry['System'] = system
            this.queue.put(PushRequest(cmdr, station, requestType, entry))
        case 'CarrierTradeOrder':
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
            if this.myCarrierCallsign and this.sheet and this.myCarrierCallsign in this.sheet.carrierTabNames.keys():
                logger.debug(f'Carrier "{this.myCarrierCallsign}" known, creating queue entry')
                this.queue.put(PushRequest(cmdr, this.myCarrierCallsign, PushRequest.TYPE_CARRIER_BUY_SELL_ORDER_UPDATE, entry))
            else:
                logger.debug(f'Carrier "{this.myCarrierCallsign}" not known, skipping market update')
        case 'CarrierJumpRequest' | 'CarrierJumpCancelled':
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
            if this.myCarrierCallsign and this.sheet and this.myCarrierCallsign in this.sheet.carrierTabNames.keys():
                logger.debug(f'Carrier "{this.myCarrierCallsign}" known, creating queue entry')
                this.queue.put(PushRequest(cmdr, this.myCarrierCallsign, PushRequest.TYPE_CARRIER_JUMP, entry))
        case 'CarrierJump':
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
            if this.myCarrierCallsign and this.sheet and this.myCarrierCallsign in this.sheet.carrierTabNames.keys():
                logger.debug(f'Carrier "{this.myCarrierCallsign}" known, creating queue entry')
                this.queue.put(PushRequest(cmdr, this.myCarrierCallsign, PushRequest.TYPE_CARRIER_LOC_UPDATE, entry['StarSystem']))
                this.queue.put(PushRequest(cmdr, this.myCarrierCallsign, PushRequest.TYPE_CARRIER_JUMP, {}))
        case 'CarrierStats':
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
            this.myCarrierCallsign = entry['Callsign']
            logger.debug(f'Carrier ID updated to {this.latestCarrierCallsign}')
        case 'CarrierLocation':
            """
            {
                'timestamp': '2025-03-29T07:31:11Z',
                'event': 'CarrierLocation',
                'CarrierID': 3707348992,
                'StarSystem': 'Orgen',
                'SystemAddress': 3657533756130,
                'BodyID': 15
            }
            """
            if this.myCarrierCallsign and this.sheet and this.myCarrierCallsign in this.sheet.carrierTabNames.keys():
                logger.debug(f'Carrier "{this.myCarrierCallsign}" known, creating queue entry')
                this.queue.put(PushRequest(cmdr, this.myCarrierCallsign, PushRequest.TYPE_CARRIER_LOC_UPDATE, entry['StarSystem']))
                this.queue.put(PushRequest(cmdr, this.myCarrierCallsign, PushRequest.TYPE_CARRIER_JUMP, {}))
        case 'CargoTransfer':
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
            if this.latestCarrierCallsign and this.sheet and this.latestCarrierCallsign in this.sheet.carrierTabNames.keys():
                logger.debug(f'Carrier "{this.latestCarrierCallsign}" known, creating queue entry')
                this.queue.put(PushRequest(cmdr, this.latestCarrierCallsign, PushRequest.TYPE_CARRIER_TRANSFER, entry))
        case 'CarrierDepositFuel':
            """
            {
                "timestamp": "2025-03-25T08:06:16Z",
                "event": "CarrierDepositFuel",
                "CarrierID": 3707348992,
                "Amount": 1,
                "Total": 245
            }
            """
            if this.sheet and station in this.sheet.carrierTabNames.keys():
                logger.debug(f'Carrier "{station}" known, creating queue entry')
                # Lets make a synthic entry, to mimick a MarketSell request
                sellEntry = {
                    'Type': 'tritium',
                    'Count': int(entry['Amount'])
                }
                this.queue.put(PushRequest(cmdr, station, PushRequest.TYPE_CMDR_SELL, sellEntry))
        case 'ColonisationConstructionDepot':
            """
            {
                'timestamp': '2025-04-13T04:17:39Z',
                'event': 'ColonisationConstructionDepot',
                'MarketID': 3956667650,
                'ConstructionProgress': 0.0,
                'ConstructionComplete': False,
                'ConstructionFailed': False,
                'ResourcesRequired': [{
                        'Name': '$aluminium_name;',
                        'Name_Localised': 'Aluminium',
                        'RequiredAmount': 510,
                        'ProvidedAmount': 0,
                        'Payment': 3239
                    }, {
                        'Name': '$ceramiccomposites_name;',
                        'Name_Localised': 'Ceramic Composites',
                        'RequiredAmount': 515,
                        'ProvidedAmount': 0,
                        'Payment': 724
                    }, {
                        'Name': '$cmmcomposite_name;',
                        'Name_Localised': 'CMM Composite',
                        'RequiredAmount': 4319,
                        'ProvidedAmount': 0,
                        'Payment': 6788
                    }, {
                        'Name': '$computercomponents_name;',
                        'Name_Localised': 'Computer Components',
                        'RequiredAmount': 61,
                        'ProvidedAmount': 0,
                        'Payment': 1112
                    }, {
                        'Name': '$copper_name;',
                        'Name_Localised': 'Copper',
                        'RequiredAmount': 247,
                        'ProvidedAmount': 0,
                        'Payment': 1050
                    }, {
                        'Name': '$foodcartridges_name;',
                        'Name_Localised': 'Food Cartridges',
                        'RequiredAmount': 96,
                        'ProvidedAmount': 0,
                        'Payment': 673
                    }, {
                        'Name': '$fruitandvegetables_name;',
                        'Name_Localised': 'Fruit and Vegetables',
                        'RequiredAmount': 52,
                        'ProvidedAmount': 0,
                        'Payment': 865
                    }, {
                        'Name': '$insulatingmembrane_name;',
                        'Name_Localised': 'Insulating Membrane',
                        'RequiredAmount': 353,
                        'ProvidedAmount': 0,
                        'Payment': 11788
                    }, {
                        'Name': '$liquidoxygen_name;',
                        'Name_Localised': 'Liquid oxygen',
                        'RequiredAmount': 1745,
                        'ProvidedAmount': 0,
                        'Payment': 2260
                    }, {
                        'Name': '$medicaldiagnosticequipment_name;',
                        'Name_Localised': 'Medical Diagnostic Equipment',
                        'RequiredAmount': 12,
                        'ProvidedAmount': 0,
                        'Payment': 3609
                    }, {
                        'Name': '$nonlethalweapons_name;',
                        'Name_Localised': 'Non-Lethal Weapons',
                        'RequiredAmount': 13,
                        'ProvidedAmount': 0,
                        'Payment': 2503
                    }, {
                        'Name': '$polymers_name;',
                        'Name_Localised': 'Polymers',
                        'RequiredAmount': 517,
                        'ProvidedAmount': 0,
                        'Payment': 682
                    }, {
                        'Name': '$powergenerators_name;',
                        'Name_Localised': 'Power Generators',
                        'RequiredAmount': 19,
                        'ProvidedAmount': 0,
                        'Payment': 3072
                    }, {
                        'Name': '$semiconductors_name;',
                        'Name_Localised': 'Semiconductors',
                        'RequiredAmount': 67,
                        'ProvidedAmount': 0,
                        'Payment': 1526
                    }, {
                        'Name': '$steel_name;',
                        'Name_Localised': 'Steel',
                        'RequiredAmount': 6749,
                        'ProvidedAmount': 0,
                        'Payment': 5057
                    }, {
                        'Name': '$superconductors_name;',
                        'Name_Localised': 'Superconductors',
                        'RequiredAmount': 113,
                        'ProvidedAmount': 0,
                        'Payment': 7657
                    }, {
                        'Name': '$titanium_name;',
                        'Name_Localised': 'Titanium',
                        'RequiredAmount': 5415,
                        'ProvidedAmount': 0,
                        'Payment': 5360
                    }, {
                        'Name': '$water_name;',
                        'Name_Localised': 'Water',
                        'RequiredAmount': 709,
                        'ProvidedAmount': 0,
                        'Payment': 662
                    }, {
                        'Name': '$waterpurifiers_name;',
                        'Name_Localised': 'Water Purifiers',
                        'RequiredAmount': 38,
                        'ProvidedAmount': 0,
                        'Payment': 849
                    }
                ]
            }
            """
            if this.sheet and system in this.sheet.systemsInProgress:
                # This journal entry happens every 15 seconds... so lets just to 1 a minute and go from there
                if this.nextSCSReconcileTime > time.time():
                    logger.debug(f'SCS in known system {system}, but update too recent, skipping')
                    return
                
                logger.debug(f'SCS in known system {system}, creating queue entry')
                if not system in this.dataPopulatedForSystems:
                    this.queue.put(PushRequest(cmdr, system, PushRequest.TYPE_SCS_DATA_POPULATE, entry))
                    this.dataPopulatedForSystems.append(system)
                this.queue.put(PushRequest(cmdr, system, PushRequest.TYPE_SCS_PROGRESS_UPDATE, entry))
                this.nextSCSReconcileTime = int(time.time()) + int(this.killswitches[KILLSWITCH_SCS_RECONCILE_DELAY])
        case 'ColonisationContribution':
            """
            {
                'timestamp': '2025-04-13T08:36:25Z',
                'event': 'ColonisationContribution',
                'MarketID': 3956737026,
                'Contributions': [{
                        'Name': '$Aluminium_name;',
                        'Name_Localised': 'Aluminium',
                        'Amount': 102
                    }, {
                        'Name': '$CeramicComposites_name;',
                        'Name_Localised': 'Ceramic Composites',
                        'Amount': 503
                    }, {
                        'Name': '$ComputerComponents_name;',
                        'Name_Localised': 'Computer Components',
                        'Amount': 52
                    }, {
                        'Name': '$FoodCartridges_name;',
                        'Name_Localised': 'Food Cartridges',
                        'Amount': 20
                    }, {
                        'Name': '$MedicalDiagnosticEquipment_name;',
                        'Name_Localised': 'Medical Diagnostic Equipment',
                        'Amount': 13
                    }, {
                        'Name': '$NonLethalWeapons_name;',
                        'Name_Localised': 'Non-Lethal Weapons',
                        'Amount': 11
                    }, {
                        'Name': '$PowerGenerators_name;',
                        'Name_Localised': 'Power Generators',
                        'Amount': 17
                    }, {
                        'Name': '$WaterPurifiers_name;',
                        'Name_Localised': 'Water Purifiers',
                        'Amount': 34
                    }
                ]
            }
            """
            if this.sheet and system in this.sheet.systemsInProgress:
                logger.debug(f'SCS in known system {system}, creating queue entry')
                this.queue.put(PushRequest(cmdr, system, PushRequest.TYPE_SCS_SELL, entry))
        case 'ColonisationBeaconDeployed':
            """
            {
                "timestamp": "2025-04-14T06:47:06Z",
                "event": "ColonisationBeaconDeployed"
            }
            """
            logger.debug('Ccreating queue entry')
            this.queue.put(PushRequest(cmdr, system, PushRequest.TYPE_SCS_SYSTEM_ADD, entry))

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

    
