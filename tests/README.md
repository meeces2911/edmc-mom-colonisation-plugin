# Tests (yay!)

## Prereqs
To run these tests locally, you should do the following:
* Change directory to `tests` 
* Create a new Python Virtual Environment. eg `python -m venv .venv`
* Activate the environment. eg, for Powershell `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser` then `. ".venv\Scripts\Activate.ps1" -verbose`
* Install EDMCs basic dependencies `pip install -r requirements.txt`

## Running the tests
>Make sure you are running these tests from the python virtual environment created during the Prereqs
* Change directory to `tests` if not already there
* Change into the python venv `.venv\scripts\Activate.ps1`
* Then just run pytest `pytest`

## Debugging tests
>Code Coverage cannot be enabled at the same time as debugging a test!
* Edit `pytest.ini` and comment out any relevant `addopts` 
