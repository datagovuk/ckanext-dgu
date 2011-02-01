======
curate
======

This describes the process that ultimately results in package resource links being checked and potentially tagged. 

The checking rules are written in N3 and operate on a combination of the API and the RDF descriptions of the packages. A digression into how the RDF descriptions come to be is in order here.

Daily there are a couple of scripts that run on the ``hmgqueue`` server as the ``ckanrdf`` user. The first, ``/home/ckanrdf/make_rdf.sh`` calls the ``ckanrdf`` command to crawl the API and generate descriptions of the packages and then uses ``rsync`` to copy the directory hierarchy to the ``hmgapi`` server. The second ``/home/ckanrdf/archive.sh`` makes an archive of the data and copies the resulting tar files to ``hmgapi``.

The link checker is really a specialised set of rules for the ``curate`` program. The ruleset for DGU that outputs CSV is in ckanext-dgu/curation/report.n3

The ``curate`` tool should be installed in the normal way according to the installation instructions and the ``ckanext-dgu`` package must also be installed.

The ``ckanext-dgu`` package contains an entrypoint called ``curate:report`` that outputs a line of CSV for its arguments.

The program is run as follows::

    curate \
    	   -a http://catalogue.data.gov.uk/api \
	   -b http://catalogue.data.gov.uk/doc/dataset/ \
	   -r curation/report.n3

The ``-a`` and ``-b`` arguments set the API base and the base for RDF descriptions respectively
