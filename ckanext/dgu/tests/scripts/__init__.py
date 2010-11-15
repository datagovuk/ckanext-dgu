from ckan.lib.create_test_data import CreateTestData

def teardown_module():
    assert not CreateTestData.get_all_data(), 'A test in module %r forgot to clean-up its data: %r' % (__name__, CreateTestData.get_all_data())
