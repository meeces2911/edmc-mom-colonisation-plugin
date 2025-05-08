import sheet as plugin

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