import logging
import requests
import time
import webbrowser
import urllib
import os
import base64
import hashlib
import random

from config import config, appname
from protohandler import LinuxProtocolHandler
from pathlib import Path

plugin_name = Path(__file__).resolve().parent.name
logger = logging.getLogger(f'{appname}.{plugin_name}')

class Auth:
    GOOGLE_AUTH_SERVER = 'https://accounts.google.com/o/oauth2/v2/auth'
    GOOGLE_TOKEN_SERVER = 'https://oauth2.googleapis.com/token'
    
    CLIENT_ID = os.getenv('CLIENT_ID') or '28330765453-6m8337sg9a6m7dtokamos8a30em5v8fr.apps.googleusercontent.com'
    CLIENT_SECRET = os.getenv('CLIENT_SECRET') or ''
    SCOPES = os.getenv('SCOPES') or 'https%3A//www.googleapis.com/auth/drive.file'
    
    AUTH_TIMEOUT = 30
    TOKEN_STORE_NAME = 'google_apikeys'
    
    def __init__(self, cmdr: str, session: requests.Session) -> None:
        logger.debug(f'New Auth for {cmdr}')
        self.cmdr: str = cmdr
        self.verifier: bytes | None = None
        self.state: str | None = None
        self.handler: LinuxProtocolHandler | None = None
        self.access_token: str | None = None
        self.requests_session: requests.Session = session
        self.shutting_down: bool = False
        
    def __del__(self) -> None:
        if self.handler:
            self.handler.close()
        
    def refresh(self) -> None:
        # Do some stuff with existing tokens...
        self.verifier = None
        self.state = None
        
        cmdrs = config.get_list('cmdrs', default=[])
        idx = cmdrs.index(self.cmdr)
        
        tokens = config.get_list(self.TOKEN_STORE_NAME, default=[])
        tokens += [''] * (len(cmdrs) - len(tokens))
        
        if tokens[idx]:
            # We have an existing refresh_token, lets try and use it
            logger.debug('Refresh token found for cmdr')
            
            body = {
                'grant_type': 'refresh_token',
                'client_id': self.CLIENT_ID,
                'client_secret': self.CLIENT_SECRET,
                'refresh_token': tokens[idx]                
            }
            logger.debug(f'Refresh token exchange body: {body}')
            
            res = self.requests_session.post(
                self.GOOGLE_TOKEN_SERVER,
                data=body,
                timeout=self.AUTH_TIMEOUT
            )
            resBodyJson = res.json()
            logger.debug(f'Response: {res}{resBodyJson}')
            
            if res.status_code != requests.codes.ok:
                logger.error(f'Bad token response: {res}{resBodyJson}')
            else:
                # Google doesn't seem to return new refresh tokens in their reply here :(
                # so, best we can do is just use the new access token
                
                self.access_token = resBodyJson.get('access_token')
                return None
        
        logger.info("Google API: New auth request")
        
        self.handler = LinuxProtocolHandler(logger, self.CLIENT_ID, self.SCOPES)
        self.handler.start()
        
        # similar to the CAPI, lets create some entropy
        v = random.SystemRandom().getrandbits(8 * 32)
        self.verifier = self.base64_url_encode(v.to_bytes(32, byteorder='big')).encode('utf-8')
        s = random.SystemRandom().getrandbits(8 * 32)
        self.state = self.base64_url_encode(s.to_bytes(32, byteorder='big'))
        challenge = self.base64_url_encode(hashlib.sha256(self.verifier).digest())
        
        authuri = (
            f'{self.GOOGLE_AUTH_SERVER}?response_type=code'
            f'&client_id={self.CLIENT_ID}'
            f'&redirect_uri={self.handler.redirect}'
            f'&scope={self.SCOPES}'
            f'&state={self.state}'
            f'&code_challenge={challenge}'
            f'&code_challenge_method=S256'
        )
        logger.debug(f'Browser opening {authuri}')
        
        webbrowser.open(authuri)
        while not self.handler.response:
            # spin
            time.sleep(1 / 10)
            
            # TODO: how does python properly handle timeouts
            
            # EDMC shutdown, bail
            if self.shutting_down:
                logger.warning('Auth: Refresh - aborting, shutting down')
                self.handler.close()
                self.handler = None
                return None
        
        self.handler.close()
        self.auth(self.handler.response)
        self.handler = None
        
        return None
        
    def auth(self, payload: str) -> None:
        """ Now exchange the auth token with an access_request one """
        # will come back with something like /auth?state=pOiorvXGIISkV0xXGOyKOmH4_oRqfV1ReaIXEAptVrc&code=4/0AQSTgQGARr4HjUmniyldb5X6uWI5ChkrAsE6h5xJDzmJf55xaPmDAF2UmRb0MaM-kYW3Cw&scope=https://www.googleapis.com/auth/drive.file
        logger.debug(f'auth callback called with {payload}')
        
        if '?' not in payload:
            logger.error(f'Google API returned invalid response: {payload}')
            raise CredentialsError('malformed payload')
            
        data = urllib.parse.parse_qs(payload[(payload.index('?') + 1):])
        
        # First, check our state string is valid
        if not self.state or not data.get('state') or data['state'][0] != self.state:
            logger.error(f'Bad state. Response invalid or expired.\nExpected: {self.state}\nActual: {data["state"][0]}\n{payload}')
            raise CredentialsError('bad state')
            
        # States good, ok, did we actually get a code back
        if not data.get('code'):
            logger.error(f'No Code token.\n{payload}')
            raise CredentialsError('no code token')
            
        # all good, token exchange time
        body = {
            'client_id': self.CLIENT_ID,
            'client_secret': self.CLIENT_SECRET,
            'code': data['code'][0],
            'code_verifier': self.verifier,
            'grant_type': 'authorization_code',
            'redirect_uri': self.handler.redirect
        }
        logger.debug(f'Token exchange body: {body}')
        
        res = self.requests_session.post(
            self.GOOGLE_TOKEN_SERVER,
            data=body,
            timeout=self.AUTH_TIMEOUT
        )
        resBodyJson = res.json()
        logger.debug(f'Response: {res}{resBodyJson}')
        
        if res.status_code != requests.codes.ok:
            logger.error(f'Bad token response: {res}{resBodyJson}')
            res.raise_for_status()
            
        logger.info("Google Auth: successfully got access token")
        cmdrs = config.get_list('cmdrs', default=[])
        idx = cmdrs.index(self.cmdr)
        tokens = config.get_list(self.TOKEN_STORE_NAME, default=[])
        tokens += [''] * (len(cmdrs) - len(tokens))
        tokens[idx] = resBodyJson.get('refresh_token', '')
        config.set(self.TOKEN_STORE_NAME, tokens)
        config.save()
        
        self.state = None
        self.verifier = None
        
        self.access_token = resBodyJson.get('access_token')    
    
    def base64_url_encode(self, text: bytes) -> str:
        """Base64 encode text for URL."""
        return base64.urlsafe_b64encode(text).decode().replace('=', '')

class CredentialsError(Exception):
    """Exception Class for OAuth Credentials error"""

    def __init__(self, *args) -> None:
        self.args = args
        if not args:
            self.args = ('Error: Invalid Credentials',)

class Sheet:
    BASE_SHEET_END_POINT = 'https://sheets.googleapis.com'
    SPREADSHEET_ID = '1dB8Zty_tGoEHFjXQh5kfOeEfL_tsByRyZI8d_sY--4M'

    def __init__(self, _logger: logging.Logger, auth: Auth, session: requests.Session):
        self.auth: Auth = auth
        self.logger: logging.Logger = _logger
        self.requests_session: requests.Session = session
        self.shutting_down: bool = False
        self.sheets: dict[str, int] = {}

        self.configSheetName = config.get_str('configSheetName', default='EDMC Plugin Settings')

        self.check_and_authorise_access_to_spreadsheet()

    def check_and_authorise_access_to_spreadsheet(self) -> any:
        """Checks and (Re)Authorises access to the spreadsheet. Returns the current sheets"""
        self.logger.debug('Checking access to spreadsheet')
        res = self.requests_session.get(f'{self.BASE_SHEET_END_POINT}/v4/spreadsheets/{self.SPREADSHEET_ID}?fields=sheets/properties(sheetId,title)')
        sheet_list_json: any = res.json()
        self.logger.debug(f'{res}{sheet_list_json}')

        if res.status_code != requests.codes.ok:
            # Need to authorise this specific file
            self.logger.debug('404 - access not granted yet, showing picker')
            self.handler = LinuxProtocolHandler(self.logger, self.CLIENT_ID, self.SCOPES, self.access_token)
            self.handler.start()
            
            webbrowser.open(self.handler.gpickerEndpoint)
            self.logger.info('Waiting for auth response')
            while not self.handler.response:
                # spin
                time.sleep(1 / 10)
                
                # TODO: how does python properly handle timeouts
                
                # EDMC shutdown, bail
                if self.shutting_down:
                    self.logger.warning('Sheet Authorise - aborting, shutting down')
                    self.handler.close()
                    self.handler = None
                    return None
            
            self.handler.close()
            self.logger.debug(f'response: {self.handler.response}')
            
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
        try:
            res = self.requests_session.get(base_url)
            if res.status_code == requests.codes.ok:
                return res.json()
            else:
                return {}
        except:
            return {}


    def populate_initial_settings(self) -> None:
        # Lets get everything on the settings sheet and wade through it
        # {{BASE_END_POINT}}/v4/spreadsheets/{{SPREADSHEET_ID}}/values/'EDMC Plugin Testing'!A:E
        sheet = f"'{self.configSheetName.get()}'"
        query = 'A:B'
        data = self.fetch_data(f'{sheet}!{query}')
        logger.debug(data)

    def sheet_names(self) -> list[str]:
        if self.sheets:
            return list(self.sheets.keys())
        return []

      