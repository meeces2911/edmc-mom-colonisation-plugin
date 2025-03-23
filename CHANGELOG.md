# Change Log

## 1.2.0

### What's Changed
* Added In-Transit Commodity tracking. If you're hauling something to a carrier, and that carrier has `Delivery` tracking enabled, then a new entry will appear on the Carrier tab with the **Delivered** checkbox unticked. Once the cargo has been sold to the Carrier the checkbox will be ticked. (in theory)
  >Additional quirks with this are, it relies on the CMDR selecting the carrier they are currently filling. If they then choose to sell the cargo elsewhere, the spreadsheet will need manually correcting to remove this. #TODO Can this be solved?

### Known Issues
* Buy Order table will be updated even when setting a Buy order to something we don't track. No values are changed though
* Even though the spreadsheet is chosen at authorisation time, its still hardcoded in the plugin to use a specific one.

## 1.1.2

### Fixed
* A silent crash for new CMDRs using the plugin for the first time and it trying to record usage stats. (Restarting EDMC would have fixed the problem, but there is currently no way for CMDRs to know something has gone wrong)

## 1.1.1

### Fixed
* Carrier Sheets with ' in them failed to update the carrier sheet correctly when buying or selling from the Carrier

## 1.1.0

### What's Changed
* Switched to a new Spreadsheet URL

### Known Issues
* Buy Order table will be updated even when setting a Buy order to something we don't track. No values are changed though
* Even though the spreadsheet is chosen at authorisation time, its still hardcoded in the plugin to use a specific one.

## 1.0.2

### What's Changed
* Added Cargo capacity tracker for CMDRs

## 1.0.1

### Fixed
* Fixed handling a startup logging issue where 'station' wasn't known yet (oops!)

## 1.0.0

### What's Changed
* Initil release!
* Global killswitch to disable updating the spreadsheet if something goes horribly wrong
* Minimum version checking
* Selling to a Carrier
* Buying from a Carrier
* Docking at a carrier updates its current location
* Updating Buy orders when set by carrier owner (requires the owner specifically to be running the plugin)
* Selling to a SCS
* Tracking Carrier jump requests
* Auto update a list of which cmdrs are using this
* Update cmdrs cargo capacity when docked