import logging
import re

import sheet as plugin

logger = logging.getLogger()

def test__A1_to_index():
    sheet = plugin.Sheet(None, None)
    
    [col, row] = sheet._A1_to_index('A59')
    assert col == 0
    assert row == 58

    [col, row] = sheet._A1_to_index('BD')
    assert col == 55
    assert row == -1

    [col, row] = sheet._A1_to_index('AAA')
    assert col == 702
    assert row == -1

    [col, row] = sheet._A1_to_index('ACZ')
    assert col == 779
    assert row == -1

def test__get_datetime_string():
    sheet = plugin.Sheet(None, None)

    ts = sheet._get_datetime_string()
    assert ts
    assert re.search('\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}', ts)

    ts = sheet._get_datetime_string('2025-05-10T06:52:59Z')
    assert ts
    assert re.search('\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}', ts)
    assert ts == '2025-05-10 06:52:59'