import os
import threading
import logging
import requests
from urllib import parse

from http.server import BaseHTTPRequestHandler, HTTPServer

SPREADSHEET_URL = 'https://docs.google.com/spreadsheets/d/1dB8Zty_tGoEHFjXQh5kfOeEfL_tsByRyZI8d_sY--4M/edit'
API_KEY = ''
APP_ID = '28330765453'

class This:
    def __init__(self):
        self.client_id: str | None = None
        self.scopes: str | None = None
        self.access_token: str | None = None
        self.httpres: str | None = None

this = This()

class LinuxProtocolHandler:
    """
    Implementation of GenericProtocolHandler.

    This implementation uses a localhost HTTP server
    """

    def __init__(self, _logger: logging.Logger, client_id: str, scope: str, access_token: str | None) -> None:
        global logger
        logger = _logger
        this.client_id = client_id
        this.scopes = scope
        this.access_token = access_token
        
        self.httpd = HTTPServer(('localhost', 0), HTTPRequestHandler)
        self.redirect = f'http://localhost:{self.httpd.server_port}/auth'
        self.gpickerEndpoint = f'http://localhost:{self.httpd.server_port}/gpicker'

        if not os.getenv("EDMC_NO_UI"):
            logger.info(f'Web server listening on {self.redirect} and {self.gpickerEndpoint}')

        self.thread: threading.Thread | None = None
        self.response: str | None = None
        self.shutting_down: bool = False
        

    def start(self) -> None:
        """Start the HTTP server thread."""
        self.thread = threading.Thread(target=self.worker, name='Google OAuth worker')
        self.thread.daemon = True
        self.thread.start()

    def close(self) -> None:
        """Shutdown the HTTP server thread."""
        logger.info('Shutting down Httphandler')
        self.shutting_down = True
        thread = self.thread
        if thread:
            logger.debug('Httphandler Thread')
            self.thread = None

            if self.httpd:
                logger.info('Shutting down httpd')
                #self.httpd.shutdown()  # This causes deadlocks, even though its called from another thread :\
                # TODO: Find a better way to do this, as it currently delays shutdown by a second or so
                requests.get(self.redirect) # Do a dummy call to unblock handle_request
                self.http = None

            logger.info('Joining thread')
            thread.join()  # Wait for it to quit

        else:
            logger.debug('No thread')

        logger.debug('Done.')

    def worker(self) -> None:
        """HTTP Worker."""
        while not this.httpres:
            self.httpd.handle_request()
            if self.shutting_down:
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
      client_id: '{this.client_id}',
      scope: '{this.scopes}',
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