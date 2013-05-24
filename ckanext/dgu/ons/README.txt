Maintenance
===========

Occasionally ONS add new source publishers, and their names often do not correspond with the names in DGU. You can check the list ONS use on their website: http://www.statistics.gov.uk/hub/statistics-producers/index.html Ensure this list is pasted into ckanext/dgu/bin/ons_test_publishers.py and then run it against a server's list of publishers::

  (pyenv) $ python ../ckanext-dgu/ckanext/dgu/bin/ons_test_publishers.py http://data.gov.uk/api

If any are missing then add the new publisher to data.gov.uk or a mapping to their name (organisation_name_mapping in schema.py), and rerun until there are no errors.
