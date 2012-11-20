Maintenance
===========

Occasionally ONS add new source publishers, and their names often do not correspond with the names in DGU. You can check the list ONS use on their website: http://www.statistics.gov.uk/hub/statistics-producers/index.html Ensure this list is pasted into ckanext/dgu/bin/ons_test_publishers.py and then run it using a configuration that contains the DGU publishers::

  paster --plugin=ckanext-dgu ons_publisher_test --config=dgu2.ini

If any are missing then add them or a mapping to their name (organisation_name_mapping in schema.py) and rerun until there are no errors.
