from sqlalchemy import (engine_from_config, Table,
                        MetaData, types, Column)
from pylons import config
import ckan.model as model
from ckan.logic import get_action
from ckan.lib.cli import CkanCommand
from datetime import date
import grp
import os
import sys
import re
import getpass
import logging
import zipfile

# To force debug (where www-data doesn't exist, i.e. OSX) export MI_REPORT_TEST=True locally

TERRITORIES = {
    "UK & Territorial Waters": "20.48,48.79,3.11,62.66",
    "UK, Territorial Waters and Continental Shelf": "63.887067,-23.956667,48.166667,3.398547",
    "Gilbraltar": "36.158625,-5.407807,36.084108,-5.291815",
    # Would be nice to constrain this to ones with an extent
    "All": "SELECT id FROM package where state='active'"
}

# Maximum number of rows to return from searches.
MAX_ROW_COUNT = 10000

class UKLPReports(CkanCommand):
    """
    Generates MI Reports

    By both searching (for bounding boxes) and using the primary db (for all
    other data) this report generates reports for MI.

    This command requires the name of the output directory where files will
    be written, either individual CSV files, or if -z (--zip) is provided a
    single zip file containing the reports.

    The reports use bounding boxes so that reports are constrained to one
    of the following:

      - UK & Territorial Waters
      - UK, Territorial Waters and Continental Shelf
      - Gilbraltar

    As well as these territories the reports be generated for all datasets.

    It is possible to also specify which reports can be used by specifying
    the letter names of the reports after the folder:

        paster uklpreports /tmp 'ABC'
    """
    summary = __doc__.split('\n')[0]
    usage = __doc__
    max_args = 3
    min_args = 1

    def __init__(self, name):
        super(UKLPReports, self).__init__(name)
        self.parser.add_option('-z', '--zip',
                               action='store_true',
                               default=False,
                               dest='zip_output',
                               help='Compress the reports into a single file')

    def command(self):
        self._load_config()
        self._setup_app()

        model.Session.remove()
        model.Session.configure(bind=model.meta.engine)

        self.log = logging.getLogger(__name__)
        self.log.debug("Running command")

        self.REPORT_DIR, self.LETTERS = self.args if len(self.args) == 2 else (self.args[0],'ABCDEF',)
        self.log.debug("Compressing report output: %s" % self.options.zip_output)
        self.log.info("Writing to %s" % self.REPORT_DIR)
        self.log.info("Running reports %s" % ','.join([x for x in self.LETTERS]))

        if not os.path.exists(self.REPORT_DIR):
            os.mkdir(self.REPORT_DIR)

        try:
            self.www_data_gid = grp.getgrnam( os.getenv('MI_REPORT_TEST') or 'www-data')[2]
        except KeyError:
            self.log.error('Could not find group www-data, if you wish to run locally '
                'then "export MI_REPORT_TEST=<GROUP_NAME>"')
            sys.exit(1)

        self.engine = engine_from_config(config, 'sqlalchemy.')
        self.metadata = MetaData(self.engine)
        self.setup_tables()  # Make sure the DB tables exist.
        self.metadata.create_all(self.engine)

        self.datenow = date.today().isoformat()
        report_files = self.run_report()
        if self.options.zip_output:
            output_file = os.path.join(self.REPORT_DIR, "%s-MI-Report-DGUK.zip" % self.datenow)
            self.log.info("Writing ZIP file to %s" % output_file)

            zf = zipfile.ZipFile(output_file, mode='w')
            try:
                for f in report_files:
                    filename = os.path.basename(f)
                    zf.write(f, compress_type=zipfile.ZIP_DEFLATED, arcname=filename)
            finally:
                zf.close()

            # No need to chownership if running as www-data already
            if getpass.getuser() != 'www-data':
                os.chown(output_file, -1, self.www_data_gid)

            # Cleanup
            for f in report_files:
                os.remove(f)

    def find_datasets(self, bbox):
        '''
        Find datasets within the specified bounding box.
        '''
        q = ''
        fq = ''
        params = {"ext_bbox": bbox}
        search_extras = {}

        for (param, value) in params.items():
            if not param.startswith('ext_'):
                fq += ' %s:"%s"' % (param, value)
            else:
                search_extras[param] = value

        context = {'model': model, 'session': model.Session,
                   'user': '', 'for_view': True}

        # Not very happy about the hard-coded rows value, would prefer if there
        # was a way to tell it 'no limit'.
        data_dict = {
            'q': q,
            'fq': fq,
            'rows': MAX_ROW_COUNT,
            'start': 0,
            'extras': search_extras
        }

        query = get_action('package_search')(context,data_dict)
        return [q['id'] for q in query['results']]

    def run_report(self):
        report_files = []

        conn = self.engine.connect()
        self.update_publisher_table(conn)

        # Clean the pivot table
        self.log.info("Cleaning up pivot table")
        conn.execute(package_extra_pivot_clean)
        self.log.info("Table cleaned")

        trans = conn.begin()

        for territory,bbox in TERRITORIES.iteritems():
            # Search to get package IDs from search using the bbox
            if territory == 'All':
                pkgs = bbox
                self.log.info('All items for All territories')
            else:
                pkgs = ["'%s'" % q for q in self.find_datasets(bbox)]
                self.log.info('%d items for %s' % (len(pkgs), territory))
                pkgs = ",".join(pkgs)

            conn.execute(package_extra_pivot_query % dict(territory=territory, packages=pkgs))

        trans.commit()
        trans = conn.begin()

        def _build_file_name(root, territory):
            return os.path.join(self.REPORT_DIR,'%s-%s_%s.csv' % \
                    (self.datenow, root, slugify(territory)))

        for territory, bbox in TERRITORIES.iteritems():
            if 'A' in self.LETTERS:
                self.log.info('Generating report A for %s' % territory)
                cur = conn.connection.connection.cursor()
                dataset_report = _build_file_name('Report-A-DGUK-Datasets', territory)
                file_to_export = file(dataset_report, 'w+')
                cur.copy_expert(reporta_query % dict(territory=territory), file_to_export)
                report_files.append(dataset_report)

            if 'B' in self.LETTERS:
                self.log.info('Generating report B for %s' % territory)
                cur = conn.connection.connection.cursor()
                services_report = _build_file_name('Report-B-DGUK-Services', territory)
                file_to_export = file(services_report, 'w+')
                cur.copy_expert(reportb_query % dict(territory=territory), file_to_export)
                report_files.append(services_report)

            if 'D' in self.LETTERS:
                self.log.info('Generating report D for %s' % territory)
                cur = conn.connection.connection.cursor()
                services_report = _build_file_name('Report-D-DGUK-Series', territory)
                file_to_export = file(services_report, 'w+')
                cur.copy_expert(reportd_query % dict(territory=territory), file_to_export)
                report_files.append(services_report)

            if 'F' in self.LETTERS:
                self.log.info('Generating report F for %s' % territory)
                cur = conn.connection.connection.cursor()
                services_report = _build_file_name('Report-F-DGUK-Other', territory)
                file_to_export = file(services_report, 'w+')
                cur.copy_expert(reportf_query % dict(territory=territory), file_to_export)
                report_files.append(services_report)

            if 'C' in self.LETTERS:
                self.log.info('Generating report C for %s' % territory)
                conn.execute(reportc_insert % dict(date=self.datenow))
                cur = conn.connection.connection.cursor()
                summary_report = _build_file_name('Report-C-DGUK-Org-Summary', territory)
                file_to_export = file(summary_report, 'w+')
                cur.copy_expert(reportc_query % dict(date=self.datenow, territory=territory), file_to_export)
                report_files.append(summary_report)

            if 'E' in self.LETTERS:
                self.log.info('Generating report E for %s' % territory)
                conn.execute(reporte_insert % dict(date=self.datenow))
                cur = conn.connection.connection.cursor()
                summary_report = _build_file_name('Report-E-DGUK-Repsonsible-Party-Summary', territory)
                file_to_export = file(summary_report, 'w+')
                cur.copy_expert(reporte_query % dict(date=self.datenow, territory=territory), file_to_export)
                report_files.append(summary_report)

        trans.commit()
        return report_files


    def update_publisher_table(self, conn):

        publisher_table = Table('tmp_publisher_info', self.metadata, autoload=True)
        conn.execute(publisher_table.delete())

        results = conn.execute(publisher_info_query)
        result_list = []
        for result in results:
            result_list.append({'id': result['id'],
                                'title': result['title'],
                                'timestamp': result['timestamp']})
        conn.execute(publisher_table.insert(), result_list)

    def setup_tables(self):
        tmp_publisher_info = Table(
            'tmp_publisher_info', self.metadata,
            Column('id', types.Text),
            Column('title', types.Text),
            Column('timestamp', types.DateTime)
        )

        report_uklp_report_c_history = Table(
            'report_uklp_report_c_history', self.metadata,
             Column('report_date', types.DateTime),
             Column('id', types.Text),
             Column('title', types.Text),
             Column('date_registered', types.DateTime),
             Column('dataset', types.Integer),
             Column('series', types.Integer),
             Column('other_type', types.Integer),
             Column('view', types.Integer),
             Column('download', types.Integer),
             Column('transformation', types.Integer),
             Column('invoke', types.Integer),
             Column('other', types.Integer),
             Column('territory', types.Text),
        )

        report_uklp_report_e_history_by_owner = Table(
            'report_uklp_report_e_history_by_owner', self.metadata,
             Column('report_date', types.DateTime),
             Column('id', types.Text),
             Column('dataset', types.Integer),
             Column('series', types.Integer),
             Column('other_type', types.Integer),
             Column('view', types.Integer),
             Column('download', types.Integer),
             Column('transformation', types.Integer),
             Column('invoke', types.Integer),
             Column('other', types.Integer),
             Column('territory', types.Text),
        )

        tmp_package_extra_pivot = Table(
            'tmp_package_extra_pivot', self.metadata,
             Column('package_id', types.Text),
             Column('access_constraints', types.Text),
             Column('agency', types.Text),
             Column('bbox-east-long', types.Text),
             Column('bbox-north-lat', types.Text),
             Column('bbox-south-lat', types.Text),
             Column('bbox-west-long', types.Text),
             Column('categories', types.Text),
             Column('contact-email', types.Text),
             Column('coupled-resource', types.Text),
             Column('dataset-reference-date', types.Text),
             Column('date_released', types.Text),
             Column('date_updated', types.Text),
             Column('date_update_future', types.Text),
             Column('department', types.Text),
             Column('external_reference', types.Text),
             Column('frequency-of-update', types.Text),
             Column('geographic_coverage', types.Text),
             Column('geographic_granularity', types.Text),
             Column('guid', types.Text),
             Column('import_source', types.Text),
             Column('UKLP', types.Text),
             Column('licence', types.Text),
             Column('licence_url', types.Text),
             Column('mandate', types.Text),
             Column('metadata-date', types.Text),
             Column('metadata-language', types.Text),
             Column('national_statistic', types.Text),
             Column('openness_score', types.Text),
             Column('openness_score_last_checked', types.Text),
             Column('precision', types.Text),
             Column('published_by', types.Text),
             Column('published_via', types.Text),
             Column('resource-type', types.Text),
             Column('responsible-party', types.Text),
             Column('series', types.Text),
             Column('spatial-data-service-type', types.Text),
             Column('spatial-reference-system', types.Text),
             Column('taxonomy_url', types.Text),
             Column('temporal_coverage_from', types.Text),
             Column('temporal_coverage-from', types.Text),
             Column('temporal_coverage_to', types.Text),
             Column('temporal_coverage-to', types.Text),
             Column('temporal_granularity', types.Text),
             Column('update_frequency', types.Text),
             Column('harvest_object_id', types.Text),
             Column('territory', types.Text),
        )


_punct_re = re.compile(r'[\t !"#$%&\'()*\-/<=>?@\[\\\]^_`{|},.]+')


def slugify(name):
    result = [w for w in _punct_re.split(name.lower())]
    return unicode('_'.join(result))


publisher_info_query = '''
select "group".id, "group".title, now() as timestamp
from "group" where "group".type = 'organization'
group by 1,2;'''

package_extra_pivot_clean = '''
    delete from tmp_package_extra_pivot;
'''

# These fields MUST be inserted in this order, don't move them around unless you also
# change the way the table is laid out.
package_extra_pivot_query = '''
insert into tmp_package_extra_pivot select package_id,
max(case when key = 'access_constraints' then value else '' end)                    "access_constraints",
max(case when key = 'agency' then value else '' end)                                "agency",
max(case when key = 'bbox-east-long' then value else '' end)                        "bbox-east-long",
max(case when key = 'bbox-north-lat' then value else '' end)                        "bbox-north-lat",
max(case when key = 'bbox-south-lat' then value else '' end)                        "bbox-south-lat",
max(case when key = 'bbox-west-long' then value else '' end)                        "bbox-west-long",
max(case when key = 'categories' then value else '' end)                            "categories",
max(case when key = 'contact-email' then value else '' end)                         "contact-email",
max(case when key = 'coupled-resource' then value else '' end)                      "coupled-resource",
max(case when key = 'dataset-reference-date' then value else '' end)                "dataset-reference-date",
max(case when key = 'date_released' then value else '' end)                         "date_released",
max(case when key = 'date_updated' then value else '' end)                          "date_updated",
max(case when key = 'date_update_future' then value else '' end)                    "date_update_future",
max(case when key = 'department' then value else '' end)                            "department",
max(case when key = 'external_reference' then value else '' end)                    "external_reference",
max(case when key = 'frequency-of-update' then value else '' end)                   "frequency-of-update",
-- This just looks like a typo -- max(case when key = 'geographical_granularity' then value else '' end)              "geographical_granularity",
max(case when key = 'geographic_coverage' then value else '' end)                   "geographic_coverage",
max(case when key = 'geographic_granularity' then value else '' end)                "geographic_granularity",
max(case when key = 'guid' then value else '' end)                                  "guid",
max(case when key = 'import_source' then value else '' end)                         "import_source",
max(case when key = 'UKLP' then value else '' end)                                  "UKLP",
max(case when key = 'licence' then value else '' end)                               "licence",
max(case when key = 'licence_url' then value else '' end)                           "licence_url",
max(case when key = 'mandate' then value else '' end)                               "mandate",
max(case when key = 'metadata-date' then value else '' end)                         "metadata-date",
max(case when key = 'metadata-language' then value else '' end)                     "metadata-language",
max(case when key = 'national_statistic' then value else '' end)                    "national_statistic",
max(case when key = 'openness_score' then value else '' end)                        "openness_score",
max(case when key = 'openness_score_last_checked' then value else '' end)           "openness_score_last_checked",
max(case when key = 'precision' then value else '' end)                             "precision",
(select title from "group" WHERE id=(select owner_org from package where id=package_id)) as "published_by",
max(case when key = 'published_via' then value else '' end)                         "published_via",
max(case when key = 'resource-type' then value else '' end)                         "resource-type",
max(case when key = 'responsible-party' then value else '' end)                     "responsible-party",
max(case when key = 'series' then value else '' end)                                "series",
max(case when key = 'spatial-data-service-type' then value else '' end)             "spatial-data-service-type",
max(case when key = 'spatial-reference-system' then value else '' end)              "spatial-reference-system",
max(case when key = 'taxonomy_url' then value else '' end)                          "taxonomy_url",
max(case when key = 'temporal_coverage_from' then value else '' end)                "temporal_coverage_from",
max(case when key = 'temporal_coverage-from' then value else '' end)                "temporal_coverage-from",
max(case when key = 'temporal_coverage_to' then value else '' end)                  "temporal_coverage_to",
max(case when key = 'temporal_coverage-to' then value else '' end)                  "temporal_coverage-to",
max(case when key = 'temporal_granularity' then value else '' end)                  "temporal_granularity",
max(case when key = 'update_frequency' then value else '' end)                      "update_frequency",
max(case when key = 'harvest_object_id' then value else '' end)                     "harvest_object_id",
cast('%(territory)s' as text) "territory"
from package_extra where package_id in (%(packages)s) and state='active'
group by package_id
'''

reporta_query = '''
copy(
SELECT
btrim("responsible-party", '"') "Record Owner",
tmp_publisher_info.title "Record Publisher",
btrim("resource-type", '"') "Resource Type",
btrim("contact-email", '"') "Contact",
package.id "CKAN ID",
package.title "Record Title",
btrim("metadata-date", '"') "Date record revised or updated",
btrim("frequency-of-update", '"') "Update schedule (if any)",
btrim(guid, '"') "Unique resource identifier",
(select max(url) from resource r join resource_group rg on rg.id = r.resource_group_id where rg.package_id = package.id and r.state = 'active') "Resource locator",
array_to_string(ARRAY[btrim("bbox-west-long", '"'),btrim("bbox-south-lat", '"'),btrim("bbox-east-long", '"'), btrim("bbox-north-lat", '"')], ',') "Geographic location",
array_to_string(ARRAY[btrim("bbox-west-long", '"'),btrim("bbox-south-lat", '"'),btrim("bbox-east-long", '"'), btrim("bbox-north-lat", '"')], ',') "Geographic Extent",
access_constraints "Constraints",
(select array_to_string(array_agg(tag.name), ',')
   from package_tag join tag on tag.id = package_tag.tag_id where package_tag.package_id = package.id) "Keywords",
notes "Abstract"
from package
join tmp_package_extra_pivot on package.id = tmp_package_extra_pivot.package_id
left join tmp_publisher_info on published_by = tmp_publisher_info.title

where "resource-type" = 'dataset' and package.state = 'active' and tmp_package_extra_pivot.territory='%(territory)s'
) to STDOUT with csv header
'''

reportd_query = '\n'.join(reporta_query.strip().split('\n')[:-2]) + '''
where "resource-type" = 'series' and package.state = 'active' and tmp_package_extra_pivot.territory='%(territory)s'
) to STDOUT with csv header
'''

reportf_query = '\n'.join(reporta_query.strip().split('\n')[:-2]) + '''
where (not ("resource-type" = '' or "resource-type" is NULL or "resource-type" = 'dataset' or "resource-type" = 'series' or "resource-type" = 'service')) and package.state = 'active' and tmp_package_extra_pivot.territory='%(territory)s'
) to STDOUT with csv header
'''

reportb_query = '''
copy(
SELECT
btrim("responsible-party", '"') "Record Owner",
tmp_publisher_info.title "Record Publisher",
btrim("resource-type", '"') "Resource Type",
btrim("contact-email", '"') "Contact",
(select min(revision_timestamp) from package_revision pr where pr.id = package.id) "Date record Registered",
btrim("metadata-date", '"') "Date record revised or updated",
btrim("frequency-of-update", '"') "Update schedule (if any)",
package.id "CKAN ID",
package.title "Record Title",
btrim(guid, '"') "Unique resource identifier",
btrim("spatial-data-service-type", '"') "Resource type",
(select max(url) from resource r join resource_group rg on rg.id = r.resource_group_id where rg.package_id = package.id and r.state = 'active') "Resource Locator",
array_to_string(ARRAY[btrim("bbox-west-long", '"'),btrim("bbox-south-lat", '"'),btrim("bbox-east-long", '"'), btrim("bbox-north-lat", '"')], ',') "Geographic Extent",
btrim("coupled-resource", '"') "Coupled Resource",
access_constraints "Constraints",
(select array_to_string(array_agg(tag.name), ',')
   from package_tag join tag on tag.id = package_tag.tag_id where package_tag.package_id = package.id) "Keywords",
notes "Abstract"
from package
join tmp_package_extra_pivot on package.id = tmp_package_extra_pivot.package_id
left join tmp_publisher_info on published_by = tmp_publisher_info.title
where "resource-type" = 'service' and package.state = 'active' and tmp_package_extra_pivot.territory='%(territory)s'
) to STDOUT with csv header;
'''


# It appears that the facetting for the 'Service' type is based solely on the resource-type
# and not the spatial-data-service-type.  There also appear to be one or two resource-type =
# 'service' that do not have a spatial-data-service-type attached particularly for
# scottish-government-spatial-data-infrastructure
reportc_insert = '''
delete from report_uklp_report_c_history where report_date = '%(date)s';
insert into report_uklp_report_c_history
select '%(date)s'::timestamp as timestamp, pub.id, pub.title, pub.timestamp
,sum(case when "resource-type" = 'dataset' then 1 else 0 end)
,sum(case when "resource-type" = 'series' then 1 else 0 end)
,sum(case when "resource-type" != 'series' and "resource-type" != 'dataset' and "resource-type" != 'service' then 1 else 0 end)
,sum(case when "resource-type" = 'service' then 1 else 0 end)
--,sum(case when "resource-type" = 'service' and "spatial-data-service-type" in ('view','discovery', 'OGC:WMS', 'other') then 1 else 0 end)
,sum(case when "resource-type" = 'service' and "spatial-data-service-type" = 'download' then 1 else 0 end)
,sum(case when "resource-type" = 'service' and "spatial-data-service-type" = 'transformation' then 1 else 0 end)
,sum(case when "resource-type" = 'service' and "spatial-data-service-type" = 'invoke' then 1 else 0 end)
,sum(case when "resource-type" = 'service' and "spatial-data-service-type" = 'other' then 1 else 0 end)
,tmp_package_extra_pivot.territory
 from package join tmp_package_extra_pivot on package.id = tmp_package_extra_pivot.package_id
left join tmp_publisher_info pub on published_by = pub.title
where package.state = 'active' and "resource-type" <> ''
group by 1,2,3,4,tmp_package_extra_pivot.territory;
'''

reportc_query = '''
copy(
select
cur.title "Organisation Name",
cur.date_registered "Date Registered",
cur.dataset "Number of datasets",
cur.series "Number of series",
cur.other_type "Number of other resource types",
cur.view "Number of View Services",
cur.download "Number of Download Services",
cur.transformation "Number of Transformation Services",
cur.invoke "Number of Invoke Services",
cur.other "Number of Other Services",
cur.dataset - coalesce("old".dataset, 0) "Dataset change",
cur.view - coalesce("old".view, 0) "View Services change",
cur.download - coalesce("old".download, 0) "Download Services change",
cur.transformation - coalesce("old".transformation, 0) "Transformation Services change",
cur.invoke - coalesce("old".invoke, 0) "Invoke Services change",
cur.other - coalesce("old".other, 0) "Other Services change",
cur.territory "Territory"
 from
report_uklp_report_c_history cur
left join
(select
    distinct on (id) report_uklp_report_c_history.*
 from
    report_uklp_report_c_history
 where
    report_date < '%(date)s'
 order by id, report_date desc
) "old" on "old".id = cur.id
where cur.report_date = '%(date)s' and cur.territory = '%(territory)s'
) to STDOUT with csv header;
'''


reporte_insert = '''
delete from report_uklp_report_e_history_by_owner where report_date = '%(date)s';
insert into report_uklp_report_e_history_by_owner
select '%(date)s'::timestamp as timestamp, "responsible-party"
,sum(case when "resource-type" = 'dataset"' then 1 else 0 end)
,sum(case when "resource-type" = 'series' then 1 else 0 end)
,sum(case when "resource-type" != 'series' and "resource-type" != 'dataset' and "resource-type" != 'service' then 1 else 0 end)
,sum(case when "resource-type" = 'service' and "spatial-data-service-type" = 'view' then 1 else 0 end)
,sum(case when "resource-type" = 'service' and "spatial-data-service-type" = 'download' then 1 else 0 end)
,sum(case when "resource-type" = 'service' and "spatial-data-service-type" = 'transformation' then 1 else 0 end)
,sum(case when "resource-type" = 'service' and "spatial-data-service-type" = 'invoke' then 1 else 0 end)
,sum(case when "resource-type" = 'service' and "spatial-data-service-type" = 'other' then 1 else 0 end)
--,sum(case when ("resource-type" = 'service' and not "spatial-data-service-type" = 'view' and not "spatial-data-service-type" = 'download' and not "spatial-data-service-type" =  'transformation' and not "spatial-data-service-type" =  'invoke') then 1 else 0 end)
,tmp_package_extra_pivot.territory
from package join tmp_package_extra_pivot on package.id = tmp_package_extra_pivot.package_id
where package.state = 'active' and "resource-type" <> ''
group by 1,2,tmp_package_extra_pivot.territory;
'''

reporte_query = '''
copy(
select
-- We use cur.id rather than the cur.title in this case
cur.id "Responsible Party",
-- This makes no sense in the context of responsible party -- cur.date_registered "Date Registered",
cur.dataset "Number of datasets",
cur.series "Number of series",
cur.other_type "Number of other resource types",
cur.view "Number of View Services",
cur.download "Number of Download Services",
cur.transformation "Number of Transformation Services",
cur.invoke "Number of Invoke Services",
cur.other "Number of Other Services",
cur.dataset - coalesce("old".dataset, 0) "Dataset change",
cur.view - coalesce("old".view, 0) "View Services change",
cur.download - coalesce("old".download, 0) "Download Services change",
cur.transformation - coalesce("old".transformation, 0) "Transformation Services change",
cur.invoke - coalesce("old".invoke, 0) "Invoke Services change",
cur.other - coalesce("old".other, 0) "Other Services change",
cur.territory "Terriroty"
from
 report_uklp_report_e_history_by_owner cur
left join
(select
    distinct on (id) report_uklp_report_e_history_by_owner.*
 from
    report_uklp_report_e_history_by_owner
 where
    report_date < '%(date)s'
 order by id, report_date desc
) "old" on "old".id = cur.id
where cur.report_date = '%(date)s' and cur.territory='%(territory)s'
) to STDOUT with csv header;
'''

history_delete = '''
delete from report_uklp_report_e_history_by_owner where report_date = '%(date)s';
delete from report_uklp_report_c_history where report_date = '%(date)s';
'''
