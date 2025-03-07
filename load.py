#
# Mercs of Mikunn - Colonisation Tracker
# Created by meeces2911
#

import logging
import threading
import tkinter as tk
import requests

from tkinter import ttk
from threading import Lock, Thread
from monitor import monitor
from pathlib import Path
from queue import Queue

import semantic_version
import time

import myNotebook as nb
from config import config, appname, appversion, user_agent
from companion import CAPIData, SERVER_LIVE
from ttkHyperlinkLabel import HyperlinkLabel
from prefs import AutoInc

from sheet import Sheet, Auth

plugin_name = Path(__file__).resolve().parent.name
logger = logging.getLogger(f'{appname}.{plugin_name}')

VERSION = '1.0.0'

# Probably overkill, but lets start with a sensible framework like how the EDSM plugin does it
class This:
    """Holds module globals."""
    
    def __init__(self):
        self.thread: threading.Thread | None = None
        self.shutting_down: bool = False
        
        self.auth: Auth | None = None
        self.queue: Queue[PushRequest] = Queue()
        
        self.enabled: bool = True
        
        self.requests_session : requests.Session = requests.Session()
        self.requests_session.headers['User-Agent'] = user_agent

        self.sheet: Sheet | None = None
        self.configSheetName: str = ''

    def __del__(self):
        if self.requests_session:
            self.requests_session.close()

this = This()

class PushRequest:
    """Holds info about things to send to the Google Sheet"""
    
    def __init__(self):
        """ TODO """

def plugin_prefs(parent: ttk.Notebook, cmdr: str | None, is_beta: bool) -> nb.Frame:
    """
    Return a TK Frame for adding to the EDMC settings dialog.
    """
    PADX = 10
    BUTTONX = 12
    PADY = 1
    BOXY = 2
    SEPY = 10

    this.configSheetName = tk.StringVar(value=config.get_str('configSheetName', default='EDMC Plugin Settings'))

    frame = nb.Frame(parent)
    frame.columnconfigure(1, weight=1)

    row = AutoInc(start=0)

    with row as cur_row:
        HyperlinkLabel(
            frame, text='MERC Expedition Needs', background=nb.Label().cget('background'), url='https://docs.google.com/spreadsheets/d/1dB8Zty_tGoEHFjXQh5kfOeEfL_tsByRyZI8d_sY--4M/edit',
            underline=True
        ).grid(row=cur_row, columnspan=2, padx=PADX, pady=PADY, sticky=tk.W)    
        nb.Label(frame, text='Version %s' % VERSION).grid(row=cur_row, column=3, padx=PADX, pady=PADY, sticky=tk.W)

    ttk.Separator(frame, orient=tk.HORIZONTAL).grid(row=row.get(), columnspan=4, padx=PADX, pady=PADY, sticky=tk.EW)

    if this.sheet:
        sheetNames: list[str] = this.sheet.sheet_names()
    else:
        sheetNames: list[str] = ('ERROR')
        
    with row as cur_row:
        nb.Label(frame, text='Settings Sheet').grid(row=cur_row, column=1, padx=PADX, pady=PADY, sticky=tk.W)
        nb.OptionMenu(
            frame, this.configSheetName, this.configSheetName.get(), *sheetNames
        ).grid(row=cur_row, column=2, columnspan=1, padx=PADX, pady=BOXY, sticky=tk.W)

    return frame

def prefs_cmdr_changed(cmdr: str | None, is_beta: bool) -> None:
    """
    Save settings.
    """

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
    this.shutting_down = True
    this.auth.shutting_down = True
    
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
        if this.shutting_down:
            return None
    
    # Get auth token first
    this.auth = Auth(monitor.cmdr, this.requests_session)
    this.auth.refresh()

    # Add bearer token to all future requests
    this.requests_session.headers['Authorization'] = f'Bearer {this.auth.access_token}'

    # Ok, now make sure we can access the spreadsheet
    this.sheet = Sheet(logger, this.auth, this.requests_session)
    
    # Request some initial settings
    this.sheet.populate_initial_settings()
    
    # Then start the main loop
    while True:
        # Do some stuff
        time.sleep(1 / 10)
            
        if this.shutting_down:
            logger.debug('Main: Shutting down, exiting thread')
            this.auth = None
            return None

def journal_entry(cmdr, is_beta, system, station, entry, state):
    logger.info(entry['event'])
    logger.info(f'Entry: {entry}')
    logger.info(f'State: {state}')
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
        logger.info(f'StartUp: Cargo {state["Cargo"]}')
        logger.info(f'StartUp: CargoJSON {state["CargoJSON"]}')
    elif entry['event'] == 'Location':
        logger.info(f'Location: In system {system}')
        if station is None:
            logger.info('Location: Flying in normal space')
        else:
            logger.info(f'Location: Docked at {station}')
    elif entry['event'] == 'FSDJump':
        logger.info(f'FSDJump: Arrived In system {system}')
    elif entry['event'] == 'Docked':
        logger.info(f'Docked: In system {system}')
        logger.info(f'Docked: Docked at {station}')
        logger.info(f'Docked: Cargo {state["Cargo"]}')
        logger.info(f'Docked: CargoJSON {state["CargoJSON"]}')
    elif entry['event'] == 'Undocked':
        logger.info(f'Undocked: In system {system}')
        logger.info(f'Undocked: Undocked at {station}')
        logger.info(f'Undocked: Cargo {state["Cargo"]}')
        logger.info(f'Undocked: CargoJSON {state["CargoJSON"]}')
    elif entry['event'] == 'Cargo':
        logger.info(f'Cargo: Cargo {state["Cargo"]}')
        logger.info(f'Cargo: CargoJSON {state["CargoJSON"]}')
    elif entry['event'] == 'Market':
        logger.info(f'Market: Cargo {state["Cargo"]}')
        logger.info(f'Market: CargoJSON {state["CargoJSON"]}')
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
        logger.info(f'MarketSell: CMDR {cmdr} sold {entry["Count"]} {entry["Type_Localised"]} to {station}')
        
        
def cmdr_data(data, is_beta):
    if data.source_host == SERVER_LIVE:
        logger.info(f'CAPI: {data}')
        
def capi_fleetcarrier(data):
    if data.source_host == SERVER_LIVE:
        logger.info(f'FC: {data}')
    
