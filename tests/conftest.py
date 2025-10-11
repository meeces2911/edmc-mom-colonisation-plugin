# Python file used to mock/stub EDMC libraries when running tests

import sys
import contextlib

##
## plug.py
##

def plug_show_error(msg: str):
    pass

module = type(sys)('plug')
module.show_error = plug_show_error
sys.modules['plug'] = module

##
## myNotebook.py
##

module = type(sys)('myNotebook')
module.Frame = {}
sys.modules['myNotebook'] = module

##
## monitor.py
##

class StubMonitor:
    cmdr: str = "cmdr_name"

module = type(sys)('monitor')
module.monitor = StubMonitor
sys.modules['monitor'] = module

##
## config.py
##

class StubConfig:
    shutting_down: bool = False

    def get_str(key: str, default: str = None):
        return default
    
    def get_bool(key: str, default: bool = False):
        print(f'StubConfig::get_bool for {key}')
        if key == 'mom_feature_track_delivery':
            # For now, just return true, and control this via the sheet features
            return True
        return default
    
    def get_int(key: str, default: int = 0):
        return default
    
    def get_list(key: str, default: list = []):
        if key == 'cmdrs':
            return [StubMonitor.cmdr]
        return default

module = type(sys)('config')
module.config = StubConfig
module.appname = 'EDMC'
module.appversion = '5.12.5'
module.user_agent = 'EDCD-EDMC-5.12.5'
sys.modules['config'] = module

##
## companion.py
##

class StubSession:
    STATE_OK:int = 3
    state: int = STATE_OK

module = type(sys)('companion')
module.CAPIData = {}
module.SERVER_LIVE = 'http://localhost'
module.capi_fleetcarrier_query_cooldown = 60 * 15
module.session = StubSession
sys.modules['companion'] = module

##
## ttkHyperlinkLabel.py
##

module = type(sys)('ttkHyperlinkLabel')
module.HyperlinkLabel = {}
sys.modules['ttkHyperlinkLabel'] = module

##
## prefs.py
##

class StubAutoInc(contextlib.AbstractContextManager):
    def __init__(self, start: int = 0, step: int = 1):
        pass

    def get(self, increment=True) -> int:
        pass

    def __enter__(self):
        pass

    def __exit__(self, *args, **kwargs) -> bool:
        return True

module = type(sys)('prefs')
module.AutoInc = StubAutoInc
sys.modules['prefs'] = module

##
## theme.py
##

class StubTheme():
    def update(self, *args, **kwargs):
        pass

module = type(sys)('theme')
module.theme = StubTheme
sys.modules['theme'] = module

##
## tkinter
##

class StubVar:
    _var: any = None
    def __init__(self, val):
        self._var = val
    def set(self, val):
        print(f'Variable SET called with {val}')
        self._var = val
    def get(self, *args, **kwargs):
        print(f'Varbale GET called with {args} or {kwargs}')
        return self._var

class StubWidget:    
    def __init__(self, *args, **kwargs):
        pass

    def __getitem__(self, key):
        return StubWidget(self)

    def grid(self, *args, **kwargs):
        pass

    def configure(self, *args, **kwargs):
        pass

class StubStyle:
    def __init__(self):
        pass

    def lookup(self, *args, **kwargs):
        pass

class StubTTK:
    def __init__(self):
        pass

    def Style():
        return StubStyle

    Notebook: object = StubWidget
    Frame: object = StubWidget
    Combobox: object = StubWidget
    Label: object = StubWidget
    OptionMenu: object = StubWidget

def tkinter_stringvar(value):
    return StubVar(value)

def tkinter_booleanvar(value):
    return StubVar(value)

def tkinter_intvar(value):
    return StubVar(value)

def tkinter_photoimage(data):
    return StubVar(data)

module = type(sys)('tkinter')
module.ttk = StubTTK
module.StringVar = tkinter_stringvar
module.BooleanVar = tkinter_booleanvar
module.IntVar = tkinter_intvar
module.PhotoImage = tkinter_photoimage
module.Frame = StubTTK.Frame
module.Label = StubTTK.Label
module.N = module.E = module.S = module.W = 0
module.OptionMenu = StubTTK.OptionMenu
sys.modules['tkinter'] = module
