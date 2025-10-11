# Change Log

## 1.6.0

### What's Changed
* Added a timeout to the shutdown code so that if a HTTP call is part way through when closing EDMC, we don't wait forever for it to finish
* On that note, also added a whole bunch more checks to see if we're in the middle of a shut down before doing a (potentially) long running operation
* Added additional status bar update when fetching the initial settings - as if google is going a bit slow that can take a minute and its nice to know the plugin is indeed still doing something
* First go at changing the Carrier and Sheet dropdowns to a searchable Combobox. For now, this has only been done for the ones on the plugin options sheet, not the one that appears on the main screen - as these Comboboxes do not respect the selected theme (at least on Windows).
  * (and for those of us that use the Transparent theme, it makes a _noticable_ difference if something isn't using the theme!)

### Fixed
* Fixed default config values not working correctly if the initial settings can't be fetched. This resulted in the plugin options sheet not being able to be displayed correctly, and the user effectively stuck with no way of fixing the issue.
* Fixed - hopefully (or at least prevented) - occurrences of blank CMDRs ending up being added to the spreadsheet. Still not 100% sure what scenario is the actual cause of this

## 1.5.0

### What's Changed
* Made a few small tweaks to better support Squadron Carriers
* Changed CarrierDepositFuel events (donating Tritium) to use the timestamp provided in the event, rather than the current time when adding to the sheet
* (Finally) Show a dialog message box advising a plugin upgrade is required when a new minimum version is detected

## 1.4.1

### Fixed
* Fixed another instance of Delivery Tracking on the SCS Offload sheet not working due to checking user preferences (and missed from the previous update)

## 1.4.0

### What's Changed
* Changed how in-transit cargo is checked on start-up. Both the (last) assigned carrier and the currently docked one will be checked, and erroneous cargo cleared
* The last 50 completed systems are kept track of. This allows for the SCS Offload sheet to be correctly updated with in-transit cargo when buying from carriers in previously completed systems

### Fixed
* Any entry added to the SCS Offload sheet will now always have the Delivered checkbox field set, regardless of the users preference
  * Delivery Tracking is still (currently) optional for carrier deliveries. This will be removed in a future release

## 1.3.5

### Fixed
* Fixed an issue preventing CMDRs who did not depoy the beacon from updating the System Info sheet if they were the first ones to dock
* Fixed an error being raise when looking for in-progress systems and not finding any

## 1.3.4

### Fixed
* In-Transit cargo not getting cleared correctly when deliverying them to a different fleet carrier than expected

## 1.3.3

### Fixed
* Fixed a typo in the lookup key used to check in-transit cargo while doing SCS Reconciliations

## 1.3.2

### Fixed
* Fixed SCS Reconcile not taking into account in-transit cargo if the reconcile was triggered before selling

## 1.3.1

### What's Changed
* Increased the default timeout of any sheet updates to 30 seconds
  * This should reduce the chance of double (or tripple) ups being created as part of the retry logic, until I have a chance to fix that properly

## 1.3.0

### What's Changed
* Added support for the new colonisation journal entries. This means its a LOT easier to keep the spreadsheet up to date when doing SCS dropoffs and not all CMDRs are using the tracker
  * `ColonisationBeaconDeployed` When a new Beacon is deployed, an entry is automatically added to the System Info sheet.
    > **Note:** CMDRs still need to manually fill in the Station/Building type, as that information is not recorded in the journals :(
  * `ColonisationConstructionDepot` When docked at a System Colonisation Ship:
    *  For the first time, a check is done to see if the information on the Data sheet has been filled out. If not, this is done automatically
    * Every 60 seconds (this might change later) a check of the current SCS offload data is done. If any discrepancies are found, then corrections are automatically added.
  * `ColonisationContribution` Uses this journal entry to determine what has been sold/transferred to the SCS, rather than guessing what cargo is no longer on the ship
  * `ColonisationSystemClaim` is ignored, as it doesn't actually contain any useful information, sadly.
  * `ColonisationSystemClaimRelease` same as claim, this is ignored
* Added some retry logic for sheet updates. Hopefully this should result in less `TRUE` values being let in places where checkboxes should be
  * Due to the nature of this, its pretty difficult to test, so feel free to send any feedback my way if you notice this still happening
* Tweaked the way carrier jumps are handled. Hopefully this should mean less scheduled jumps being left in the cell after the carrier has finished jumpiing

### Fixed
* (Finally) Fixed timestamps being entered in the wrong cell if Delivery Tracking was disabled

## 1.2.5

### Fixed
* Changed SCS station name check to cope with new ship names

## 1.2.4

### Fixed
* Fixed CarrierTradeOrders not using the correct carrier id when updating the spreadsheet
* Fixed In-Transit cargo being 'remembered' after they'd been dropped off to a SCS ship

## 1.2.3

### Fixed
* Fix for the fix that fixes the In-Transit ... you get the idea. (This fixes the In-transit checkmark not getting updated correctly)

## 1.2.2

### Fixed
* Fixed the fix for In-Transit items across multiple carriers not being correctly recorded. Sorry.

## 1.2.1

### Fixed
* Fixed In-Transit items across multiple carriers not being correctly recorded after being dropped off, resulting in duplicate entries
* Fixed carriers/sheet names _without_ spaces in their names not updating the spreadsheet correctly

## 1.2.0

### What's Changed
* Added In-Transit Commodity tracking. If you're hauling something to a carrier, and that carrier has `Delivery` tracking enabled, then a new entry will appear on the Carrier tab with the **Delivered** checkbox unticked. Once the cargo has been sold to the Carrier the checkbox will be ticked. (in theory)
  * In-Transit Commodity tracker requires both the spreadsheet settings to be updated and the CMDRs plugin to have the setting enabled to enable this for a given carrier
* Added new setting **Assume Carrier Buy is for Unloading to SCS** which controls whether to enable delivery tracking for the SCS Offload sheet separately. Set this to **False** to disable the delivery tracking
* Added Status Indicator widget to EDMCs display. This will change to red if the spreadsheet hasn't been connected to successfully
* Added 'Carrier' widget to EDMCs display. This is used by the In-Transit delivery tracker to know which carrier you are working on.
  * It will default to the carrier you were assigned to initially (ie, the one mentioned on the System Info sheet)
* Added new settings options to hide both widgets
* Handle **CarrierLocation** Journal Events - this means that after the carrier jumps, and the owner is still on line, the spreadsheet will automatically clear the scheduled jump field if they are not on the carrier
* All saved settings can now be cleared by pressing the **Clear all settings** button. (Hopefully only i'll need to use it, but its there in case anyone else needs it too)
* Made initial start up slightly (only slightly) faster by batching some of the intial spreadsheet calls
* Handle **CarrierDepositFuel** Journal Events - this means that 'dontating' fuel to a carrier now counts as a delivery
* Automatically add an entry to the System Info sheet, if docking to an Unknwon SCS for the first time

### Fixed
* Fixed wrong carrier sheet being updated on carrier jump if you'd docked to another carrier since setting the jump
* Re-enable early event queuing prior to Google authentication is complete. This means we don't miss out on the start-up events
* Settings are now saved correctly and should persist between restarts
* New carriers/sheets not being correctly added to all the places needed when updates to the spreadsheet were detected

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