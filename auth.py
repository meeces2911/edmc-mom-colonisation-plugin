import os
import threading
import logging
import requests
import urllib
import os
import base64
import hashlib
import random
import webbrowser
import time

from urllib import parse
from config import config, appname
from pathlib import Path
from http.server import BaseHTTPRequestHandler, HTTPServer

SPREADSHEET_URL = 'https://docs.google.com/spreadsheets/d/1dB8Zty_tGoEHFjXQh5kfOeEfL_tsByRyZI8d_sY--4M/edit'

## OAuth
CLIENT_ID = os.getenv('CLIENT_ID') or '28330765453-6m8337sg9a6m7dtokamos8a30em5v8fr.apps.googleusercontent.com'
CLIENT_SECRET = os.getenv('CLIENT_SECRET') or ''
SCOPES = os.getenv('SCOPES') or 'https%3A//www.googleapis.com/auth/drive.file'
GOOGLE_AUTH_SERVER = 'https://accounts.google.com/o/oauth2/v2/auth'
GOOGLE_TOKEN_SERVER = 'https://oauth2.googleapis.com/token'

## GPicker
API_KEY = os.getenv('API_KEY') or ''
APP_ID = '28330765453'

plugin_name = Path(__file__).resolve().parent.name
logger = logging.getLogger(f'{appname}.{plugin_name}')

class This:
    def __init__(self):
        self.httpres: str | None = None
        self.access_token: str | None = None

this = This()

class Auth:
    AUTH_TIMEOUT = 30
    TOKEN_STORE_NAME = 'google_apikeys'
    
    def __init__(self, cmdr: str, session: requests.Session) -> None:
        logger.debug(f'New Auth for {cmdr}')
        self.cmdr: str = cmdr
        self.verifier: bytes | None = None
        self.state: str | None = None
        self.handler: LocalHTTPServer | None = None
        self.access_token: str | None = None
        self.requests_session: requests.Session = session
        
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
                'client_id': CLIENT_ID,
                'client_secret': CLIENT_SECRET,
                'refresh_token': tokens[idx]                
            }
            logger.debug(f'Refresh token exchange body: {body}')
            
            res = self.requests_session.post(
                GOOGLE_TOKEN_SERVER,
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
                this.access_token = self.access_token   # TODO: rationalise this

                # Add bearer token to all future requests
                self.requests_session.headers['Authorization'] = f'Bearer {this.access_token}'

                return None
        
        logger.info("Google API: New auth request")
        
        self.handler = LocalHTTPServer()
        self.handler.start()
        
        # similar to the CAPI, lets create some entropy
        v = random.SystemRandom().getrandbits(8 * 32)
        self.verifier = self.base64_url_encode(v.to_bytes(32, byteorder='big')).encode('utf-8')
        s = random.SystemRandom().getrandbits(8 * 32)
        self.state = self.base64_url_encode(s.to_bytes(32, byteorder='big'))
        challenge = self.base64_url_encode(hashlib.sha256(self.verifier).digest())
        
        authuri = (
            f'{GOOGLE_AUTH_SERVER}?response_type=code'
            f'&client_id={CLIENT_ID}'
            f'&redirect_uri={self.handler.redirect}'
            f'&scope={SCOPES}'
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
            if config.shutting_down:
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
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET,
            'code': data['code'][0],
            'code_verifier': self.verifier,
            'grant_type': 'authorization_code',
            'redirect_uri': self.handler.redirect
        }
        logger.debug(f'Token exchange body: {body}')
        
        res = self.requests_session.post(
            GOOGLE_TOKEN_SERVER,
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
        this.access_token = self.access_token

        # Add bearer token to all future requests
        self.requests_session.headers['Authorization'] = f'Bearer {this.access_token}'
    
    def clear_auth_token(self) -> None:
        cmdrs = config.get_list('cmdrs', default=[])
        idx = cmdrs.index(self.cmdr)
        tokens: dict = config.get_list(self.TOKEN_STORE_NAME, default=[])
        tokens += [''] * (len(cmdrs) - len(tokens))
        
        # Remove the entry for ths commander
        tokens.pop(idx)
        
        config.set(self.TOKEN_STORE_NAME, tokens)
        config.save()

        self.access_token = None

    def base64_url_encode(self, text: bytes) -> str:
        """Base64 encode text for URL."""
        return base64.urlsafe_b64encode(text).decode().replace('=', '')

class CredentialsError(Exception):
    """Exception Class for OAuth Credentials error"""

    def __init__(self, *args) -> None:
        self.args = args
        if not args:
            self.args = ('Error: Invalid Credentials',)

class LocalHTTPServer:
    """
    Local HTTP webserver, based of EDMCs LinuxProtocolHandler
    """

    def __init__(self) -> None:        
        self.httpd = HTTPServer(('localhost', 0), HTTPRequestHandler)
        self.redirect = f'http://localhost:{self.httpd.server_port}/auth'
        self.gpickerEndpoint = f'http://localhost:{self.httpd.server_port}/gpicker'

        if not os.getenv("EDMC_NO_UI"):
            logger.info(f'Web server listening on {self.redirect} and {self.gpickerEndpoint}')

        self.thread: threading.Thread | None = None
        self.response: str | None = None
        

    def start(self) -> None:
        """Start the HTTP server thread."""
        self.thread = threading.Thread(target=self.worker, name='Google OAuth worker')
        self.thread.daemon = True
        self.thread.start()

    def close(self) -> None:
        """Shutdown the HTTP server thread."""
        logger.info('Shutting down Httphandler')
        thread = self.thread
        if thread:
            logger.debug('Httphandler Thread')
            self.thread = None

            if self.httpd:
                logger.info('Shutting down httpd')
                #self.httpd.shutdown()  # This causes deadlocks, even though its called from another thread :\
                # TODO: Find a better way to do this, as it currently delays shutdown by a second or so
                try:
                    requests.get(self.redirect, timeout=1) # Do a dummy call to unblock handle_request if EDMC was closed midway through an auth request
                except:
                    pass

                self.http = None

            logger.info('Joining thread')
            thread.join()  # Wait for it to quit

        else:
            logger.debug('No thread')

        logger.debug('Done.')

    def worker(self) -> None:
        """HTTP Worker."""
        this.httpres = None
        while not this.httpres:
            self.httpd.handle_request()
            if config.shutting_down:
                return
        
        self.response = this.httpres
        

class HTTPRequestHandler(BaseHTTPRequestHandler):
    """Simple HTTP server to handle IPC from protocol handler."""

    def parse(self) -> bool:
        """Parse a request."""
        url = parse.unquote(self.path)
        if url.startswith('/auth'):
            self.send_response(200)
            this.httpres = url
            return True
        elif url.startswith('/gpicker'):
            self.send_response(200)
            if url.find('?') >= 0:
              this.httpres = url
            return True
        self.send_response(404)  # Not found
        return False

    def do_HEAD(self) -> None:
        """Handle HEAD Request."""
        self.parse()
        self.end_headers()

    def do_GET(self) -> None:
        """Handle GET Request."""
        url = parse.unquote(self.path)
        logger.debug(f'GET request for {url}')
        if self.parse():
            
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            
            if url.startswith('/auth'):    
                self.wfile.write(self._generate_auth_response().encode())
            elif url.startswith('/gpicker'):
                self.wfile.write(self._generate_gapi_picker_response().encode())
        else:
            self.send_response(404)
            self.end_headers()

    def log_request(self, code: int | str = '-', size: int | str = '-') -> None:
        """Override to prevent logging."""

    def _generate_auth_response(self) -> str:
        """
        Generate the authentication response HTML.

        :return: The HTML content of the authentication response.
        """
        return (
            '<html>'
            '<head>'
            '<title>Authentication successful - Elite: Dangerous</title>'
            '<style>'
            'body { background-color: #000; color: #fff; font-family: "Helvetica Neue", Arial, sans-serif; }'
            'h1 { text-align: center; margin-top: 100px; }'
            'p { text-align: center; }'
            '</style>'
            '</head>'
            '<body>'
            '<h1>Authentication successful</h1>'
            '<p>Thank you for authenticating.</p>'
            '<p>Please close this browser tab now.</p>'
            '</body>'
            '</html>'
        )
    
    def _generate_gapi_picker_response(self) -> str:
        """
        Used to authorise access to specific files via the Drive API
        """
        return f"""<!DOCTYPE html>
<html>
<head>
  <title>Elite Dangerous Spreadhseet Picker</title>
  <meta charset="utf-8" />
  <style>
    body {{ background-color: #000; color: #fff; font-family: "Helvetica Neue", Arial, sans-serif; }}
    pre {{ text-align: center; margin-top: 100px; white-space: pre-wrap; font-size: xx-large; }}
    p {{ text-align: center; }}
    .picker-dialog-bg {{ background-color: #000 !important; display: none}}
    .picker-framepane-root {{ background-color: rgb(171, 171, 171) !important }}
  </style>
</head>
<body>

<pre id="content" style="white-space: pre-wrap;">
Please authorise access to the 'MERC Expantion Needs' Spreadsheet. 
<a href="{SPREADSHEET_URL}">Click here</a> to open it if its not shown in the list below, and then refresh this page.
</pre>

<script type="text/javascript">
  let tokenClient;
  let accessToken = '{this.access_token}';

  /**
   * Callback after api.js is loaded.
   */
  function gapiLoaded() {{
    gapi.load('client:picker', initializePicker);
  }}

  /**
   * Callback after the API client is loaded. Loads the
   * discovery doc to initialize the API.
   */
  async function initializePicker() {{
    await gapi.client.load('https://www.googleapis.com/discovery/v1/apis/drive/v3/rest');
    createPicker();
  }}

  /**
   * Callback after Google Identity Services are loaded.
   */
  function gisLoaded() {{
    tokenClient = google.accounts.oauth2.initTokenClient({{
      client_id: '{CLIENT_ID}',
      scope: '{SCOPES}',
      callback: '', // defined later
    }});
  }}

  /**
   *  Create and render a Picker object for searching images.
   */
  function createPicker() {{
    const view = new google.picker.DocsView(google.picker.ViewId.SPREADSHEETS)
        .setMode(google.picker.DocsViewMode.LIST);
    const picker = new google.picker.PickerBuilder()
        .enableFeature(google.picker.Feature.NAV_HIDDEN)
        .setDeveloperKey('{API_KEY}')
        .setAppId('{APP_ID}')
        .setOAuthToken(accessToken)
        .addView(view)
        .setCallback(pickerCallback)
        .setMaxItems(1)
        .build();
    picker.setVisible(true);
  }}

  /**
   * Displays the file details of the user's selection.
   * @param {{object}} data - Containers the user selection from the picker
   */
  async function pickerCallback(data) {{
    if (data.action === google.picker.Action.PICKED) {{
      window.location = `http://${{window.location.host}}/auth?spreadsheet=${{data.docs[0].embedUrl}}`
    }}
  }}  
</script>
<script async defer src="https://apis.google.com/js/api.js" onload="gapiLoaded()"></script>
<script async defer src="https://accounts.google.com/gsi/client" onload="gisLoaded()"></script>
</body>
</html>
"""