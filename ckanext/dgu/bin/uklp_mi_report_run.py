#! /usr/bin/python 

from sqlalchemy import create_engine
from sqlalchemy import Table, MetaData, types, Column
from datetime import datetime, date
from sqlalchemy.sql import text
import grp
import os
import sys
import logging

# Install:
# sudo apt-get install ckan python-mysqldb
# sudo chown www-data:ckandguos /var/lib/ckan/dguos/static/report
# okfn@dgu-uat:~$ sudo chmod +x /var/lib/ckan/dguos
# okfn@dgu-uat:~$ sudo chmod +r /var/lib/ckan/dguos
# okfn@dgu-uat:~$ sudo chmod +r /var/lib/ckan/dguos/static
# okfn@dgu-uat:~$ sudo chmod +x /var/lib/ckan/dguos/static

# Potential problems:
# [*] No geo data on service records
# [+] Not picking the correct resource locators
# [+] Provider role
#     -> Are any of them empty?
#     -> What are the implications?
# [+] Error reporting
# [ ] Need to alter table to support series and other on the summary
# [ ] Report C doesn't have series or other_type (table needs altering)
# [ ] What happens in duplicate runs?
# [ ] Running on dev, not on live
# [X] Geographic coverage not pulled in correctly
# [X] Extent vs bounding box

# Config options

if len(sys.argv) <= 3:
    print >> sys.stderr, "Not enough arguments. Please run:"
    print >> sys.stderr, "%s POSTGRESQL_DSN MYSQL_DSN REPORT_DIR"%sys.argv[0]
elif len(sys.argv) > 4:
    print >> sys.stderr, "Too many arguments. Please run:"
    print >> sys.stderr, "%s POSTGRESQL_DSN MYSQL_DSN REPORT_DIR"%sys.argv[0]
POSTGRESQL_DSN, MYSQL_DSN, REPORT_DIR = sys.argv[1:]
REPORT_PREPEND = ''

if not os.path.exists(REPORT_DIR):
    os.mkdir(REPORT_DIR)
www_data_gid = grp.getgrnam('www-data')[2]
engine = create_engine(POSTGRESQL_DSN)
engine_mysql = create_engine(MYSQL_DSN)

logging.basicConfig(filename='%s/error.log' % REPORT_DIR, level=logging.ERROR)

metadata = MetaData(engine)

tmp_publisher_info = Table(
    'tmp_publisher_info', metadata,
    Column('nid', types.Integer),
    Column('title', types.Text),
    Column('timestamp', types.DateTime)
)

#tmp_owner_info = Table(
#    'tmp_owner_info', metadata,
#    Column('nid', types.Text),
#    Column('title', types.Text),
#    Column('timestamp', types.DateTime)
#)

report_uklp_report_c_history = Table(
    'report_uklp_report_c_history', metadata,
     Column('report_date', types.DateTime),
     Column('nid', types.Integer),
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
)

report_uklp_report_e_history_by_owner = Table(
    'report_uklp_report_e_history_by_owner', metadata,
     Column('report_date', types.DateTime),
     Column('nid', types.Text),
     #Column('title', types.Text),
     #Column('date_registered', types.DateTime),
     Column('dataset', types.Integer),
     Column('series', types.Integer),
     Column('other_type', types.Integer),
     Column('view', types.Integer),
     Column('download', types.Integer),
     Column('transformation', types.Integer),
     Column('invoke', types.Integer),
     Column('other', types.Integer),
)


metadata.create_all(engine)

def run_report():
    delete=False
    if len(sys.argv) > 1 and sys.argv[1] == 'delete':
        delete = True
        print "Will delete today's record from the history afterwards"
    datenow = date.today().isoformat()
    conn = engine.connect()
    update_publisher_table(conn)
    #update_owner_table(conn)

    trans = conn.begin()

    conn.execute(package_extra_pivot_query)
    cur = conn.connection.connection.cursor()
    dataset_report = '%s/%s%s-Report-A-DGUK-Datasets.csv' % (REPORT_DIR, REPORT_PREPEND, datenow)
    file_to_export = file(dataset_report, 'w+')
    cur.copy_expert(reporta_query, file_to_export)
    os.chown(dataset_report, -1, www_data_gid)

    cur = conn.connection.connection.cursor()
    services_report = '%s/%s%s-Report-B-DGUK-Services.csv' % (REPORT_DIR, REPORT_PREPEND, datenow)
    file_to_export = file(services_report, 'w+')
    cur.copy_expert(reportb_query, file_to_export)
    os.chown(services_report, -1, www_data_gid)

    cur = conn.connection.connection.cursor()
    services_report = '%s/%s%s-Report-D-DGUK-Series.csv' % (REPORT_DIR, REPORT_PREPEND, datenow)
    file_to_export = file(services_report, 'w+')
    cur.copy_expert(reportd_query, file_to_export)
    os.chown(services_report, -1, www_data_gid)

    cur = conn.connection.connection.cursor()
    services_report = '%s/%s%s-Report-F-DGUK-Other.csv' % (REPORT_DIR, REPORT_PREPEND, datenow)
    file_to_export = file(services_report, 'w+')
    cur.copy_expert(reportf_query, file_to_export)
    os.chown(services_report, -1, www_data_gid)

    conn.execute(reportc_insert % dict(date = datenow))
    cur = conn.connection.connection.cursor()
    summary_report = '%s/%s%s-Report-C-DGUK-Org-Summary.csv' % (REPORT_DIR, REPORT_PREPEND, datenow)
    file_to_export = file(summary_report, 'w+')
    cur.copy_expert(reportc_query % dict(date = datenow), file_to_export)
    os.chown(summary_report, -1, www_data_gid)

    #conn.execute(reporte_insert % dict(date = datenow))
    #cur = conn.connection.connection.cursor()
    #summary_report = '%s/%s%s-Report-E-DGUK-Repsonsible-Party-Summary.csv' % (REPORT_DIR, REPORT_PREPEND, datenow)
    #file_to_export = file(summary_report, 'w+')
    #cur.copy_expert(reporte_query % dict(date = datenow), file_to_export)
    #os.chown(summary_report, -1, www_data_gid)

    if delete:
        conn.execute(history_delete % dict(date = datenow))
    trans.commit()

def update_publisher_table(conn):

    publisher_table = Table('tmp_publisher_info', metadata, autoload=True)
    conn.execute(publisher_table.delete())
    conn_mysql = engine_mysql.connect()
    results = conn_mysql.execute(publisher_info_query)
    result_list = []
    for result in results:
        result_list.append({'nid': result['nid'],
                            'title': result['title'],
                            'timestamp': datetime.fromtimestamp(result['timestamp'])
                           }
                          )
    conn.execute(publisher_table.insert(), result_list)
    conn_mysql.close()


publisher_info_query = '''
select node.nid, node.title, min(timestamp) timestamp 
from node join node_revisions using(nid) 
where node.type = 'publisher' 
group by 1,2;'''

#def update_owner_table(conn):
#
#    owner_table = Table('tmp_owner_info', metadata, autoload=True)
#    conn.execute(owner_table.delete())
#    results = conn.execute(owner_info_query)
#    result_list = []
#    now = datetime.now()
#    for result in results:
#        result_list.append({'nid': result[0],
#                            'title': result[1],
#                            'timestamp': result[2],
#                           }
#                          )
#    conn.execute(owner_table.insert(), result_list)
#
#owner_info_query = '''
#select DISTINCT "responsible-party", "responsible-party", '2011-11-09'
#from tmp_package_extra_pivot
#'''

package_extra_pivot_query = '''
drop table if exists tmp_package_extra_pivot;
select
package_id,
max(case when key = 'access_constraints' then value else '""' end)                    "access_constraints",
max(case when key = 'agency' then value else '""' end)                                "agency",
max(case when key = 'bbox-east-long' then value else '""' end)                        "bbox-east-long",
max(case when key = 'bbox-north-lat' then value else '""' end)                        "bbox-north-lat",
max(case when key = 'bbox-south-lat' then value else '""' end)                        "bbox-south-lat",
max(case when key = 'bbox-west-long' then value else '""' end)                        "bbox-west-long",
max(case when key = 'categories' then value else '""' end)                            "categories",
max(case when key = 'contact-email' then value else '""' end)                         "contact-email",
max(case when key = 'coupled-resource' then value else '""' end)                      "coupled-resource",
max(case when key = 'dataset-reference-date' then value else '""' end)                "dataset-reference-date",
max(case when key = 'date_released' then value else '""' end)                         "date_released",
max(case when key = 'date_updated' then value else '""' end)                          "date_updated",
max(case when key = 'date_update_future' then value else '""' end)                    "date_update_future",
max(case when key = 'department' then value else '""' end)                            "department",
max(case when key = 'external_reference' then value else '""' end)                    "external_reference",
max(case when key = 'frequency-of-update' then value else '""' end)                   "frequency-of-update",
-- This just looks like a typo -- max(case when key = 'geographical_granularity' then value else '""' end)              "geographical_granularity",
max(case when key = 'geographic_coverage' then value else '""' end)                   "geographic_coverage",
max(case when key = 'geographic_granularity' then value else '""' end)                "geographic_granularity",
max(case when key = 'guid' then value else '""' end)                                  "guid",
max(case when key = 'import_source' then value else '""' end)                         "import_source",
max(case when key = 'INSPIRE' then value else '""' end)                               "INSPIRE",
max(case when key = 'licence' then value else '""' end)                               "licence",
max(case when key = 'licence_url' then value else '""' end)                           "licence_url",
max(case when key = 'mandate' then value else '""' end)                               "mandate",
max(case when key = 'metadata-date' then value else '""' end)                         "metadata-date",
max(case when key = 'metadata-language' then value else '""' end)                     "metadata-language",
max(case when key = 'national_statistic' then value else '""' end)                    "national_statistic",
max(case when key = 'openness_score' then value else '""' end)                        "openness_score",
max(case when key = 'openness_score_last_checked' then value else '""' end)           "openness_score_last_checked",
max(case when key = 'precision' then value else '""' end)                             "precision",
max(case when key = 'published_by' then value else '""' end)                          "published_by",
max(case when key = 'published_via' then value else '""' end)                         "published_via",
max(case when key = 'resource-type' then value else '""' end)                         "resource-type",
max(case when key = 'responsible-party' then value else '""' end)                     "responsible-party",
max(case when key = 'series' then value else '""' end)                                "series",
max(case when key = 'spatial-data-service-type' then value else '""' end)             "spatial-data-service-type",
max(case when key = 'spatial-reference-system' then value else '""' end)              "spatial-reference-system",
max(case when key = 'taxonomy_url' then value else '""' end)                          "taxonomy_url",
max(case when key = 'temporal_coverage_from' then value else '""' end)                "temporal_coverage_from",
max(case when key = 'temporal_coverage-from' then value else '""' end)                "temporal_coverage-from",
max(case when key = 'temporal_coverage_to' then value else '""' end)                  "temporal_coverage_to",
max(case when key = 'temporal_coverage-to' then value else '""' end)                  "temporal_coverage-to",
max(case when key = 'temporal_granularity' then value else '""' end)                  "temporal_granularity",
max(case when key = 'update_frequency' then value else '""' end)                      "update_frequency",
max(case when key = 'harvest_object_id' then value else '""' end)                     "harvest_object_id"
into tmp_package_extra_pivot
from package_extra
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
(select max(url) from resource r join resource_group rg on rg.id = r.resource_group_id where rg.package_id = package.id and r.state = 'active') "Rescource locator",
array_to_string(ARRAY[btrim("bbox-west-long", '"'),btrim("bbox-south-lat", '"'),btrim("bbox-east-long", '"'), btrim("bbox-north-lat", '"')], ',') "Geographic location",
array_to_string(ARRAY[btrim("bbox-west-long", '"'),btrim("bbox-south-lat", '"'),btrim("bbox-east-long", '"'), btrim("bbox-north-lat", '"')], ',') "Geographic Extent",
access_constraints "Constraints",
(select array_to_string(array_agg(tag.name), ',') 
   from package_tag join tag on tag.id = package_tag.tag_id where package_tag.package_id = package.id) "Keywords",
notes "Abstract"
from package 
join tmp_package_extra_pivot on package.id = tmp_package_extra_pivot.package_id
left join tmp_publisher_info on published_by = tmp_publisher_info.nid::text

where "resource-type" = '"dataset"' and package.state = 'active'
) to STDOUT with csv header
'''

reportd_query = '\n'.join(reporta_query.strip().split('\n')[:-2]) + '''
where "resource-type" = '"series"' and package.state = 'active'
) to STDOUT with csv header
'''

reportf_query = '\n'.join(reporta_query.strip().split('\n')[:-2]) + '''
where (not ("resource-type" = '""' or "resource-type" is NULL or "resource-type" = '"dataset"' or "resource-type" = '"series"' or "resource-type" = '"service"')) and package.state = 'active'
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
left join tmp_publisher_info on published_by = tmp_publisher_info.nid::text
where "resource-type" = '"service"' and package.state = 'active'
) to STDOUT with csv header;
'''

reportc_insert = '''
delete from report_uklp_report_c_history where report_date = '%(date)s';
insert into report_uklp_report_c_history
select '%(date)s'::timestamp as timestamp, nid, pub.title, pub.timestamp
,sum(case when "resource-type" = '"dataset"' then 1 else 0 end)
,sum(case when "resource-type" = '"series"' then 1 else 0 end)
,sum(case when "resource-type" != '"series"' and "resource-type" != '"dataset"' and "resource-type" != '"service"' then 1 else 0 end)
,sum(case when "resource-type" = '"service"' and "spatial-data-service-type" = '"view"' then 1 else 0 end)
,sum(case when "resource-type" = '"service"' and "spatial-data-service-type" = '"download"' then 1 else 0 end)
,sum(case when "resource-type" = '"service"' and "spatial-data-service-type" = '"transformation"' then 1 else 0 end)
,sum(case when "resource-type" = '"service"' and "spatial-data-service-type" = '"invoke"' then 1 else 0 end)
-- ,sum(case when "resource-type" = '"service"' and "spatial-data-service-type" = '"other"' then 1 else 0 end)
,sum(case when "resource-type" = '"service"' and ("spatial-data-service-type" not in ('"view"', '"download"', '"transformation"', '"invoke"')) then 1 else 0 end)
from package join tmp_package_extra_pivot on package.id = tmp_package_extra_pivot.package_id
left join tmp_publisher_info pub on cast(nid as text) = published_by 
where package.state = 'active' and "resource-type" <> '""'
group by 1,2,3,4;
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
cur.other - coalesce("old".other, 0) "Other Services change"
from
report_uklp_report_c_history cur 
left join 
(select 
    distinct on (nid) report_uklp_report_c_history.* 
 from 
    report_uklp_report_c_history  
 where 
    report_date < '%(date)s'
 order by nid, report_date desc
) "old" on "old".nid = cur.nid
where cur.report_date = '%(date)s'
) to STDOUT with csv header;
'''


reporte_insert = '''
delete from report_uklp_report_e_history_by_owner where report_date = '%(date)s';
insert into report_uklp_report_e_history_by_owner
select '%(date)s'::timestamp as timestamp, "responsible-party"
,sum(case when "resource-type" = '"dataset"' then 1 else 0 end)
,sum(case when "resource-type" = '"series"' then 1 else 0 end)
,sum(case when "resource-type" != '"series"' and "resource-type" != '"dataset"' and "resource-type" != '"service"' then 1 else 0 end)
,sum(case when "resource-type" = '"service"' and "spatial-data-service-type" = '"view"' then 1 else 0 end)
,sum(case when "resource-type" = '"service"' and "spatial-data-service-type" = '"download"' then 1 else 0 end)
,sum(case when "resource-type" = '"service"' and "spatial-data-service-type" = '"transformation"' then 1 else 0 end)
,sum(case when "resource-type" = '"service"' and "spatial-data-service-type" = '"invoke"' then 1 else 0 end)
-- ,sum(case when "resource-type" = '"service"' and "spatial-data-service-type" = '"other"' then 1 else 0 end)
,sum(case when "resource-type" = '"service"' and ("spatial-data-service-type" not in ('"view"', '"download"', '"transformation"', '"invoke"')) then 1 else 0 end)
from package join tmp_package_extra_pivot on package.id = tmp_package_extra_pivot.package_id
where package.state = 'active' and "resource-type" <> '""'
group by 1,2;
'''

reporte_query = '''
copy(
select 
-- We use cur.nid rather than the cur.title in this case
cur.nid "Responsible Party",
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
cur.other - coalesce("old".other, 0) "Other Services change"
from
report_uklp_report_e_history_by_owner cur 
left join 
(select 
    distinct on (nid) report_uklp_report_e_history_by_owner.* 
 from 
    report_uklp_report_e_history_by_owner
 where 
    report_date < '%(date)s'
 order by nid, report_date desc
) "old" on "old".nid = cur.nid
where cur.report_date = '%(date)s'
) to STDOUT with csv header;
'''

history_delete = '''
delete from report_uklp_report_e_history_by_owner where report_date = '%(date)s';
delete from report_uklp_report_c_history where report_date = '%(date)s';
'''

if __name__ == '__main__':
    try:
        run_report()
    except:
	import traceback
        logging.error(traceback.format_exc())
        raise

