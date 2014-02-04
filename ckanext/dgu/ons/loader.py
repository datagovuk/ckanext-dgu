import re

from datautildate import date

from ckanext.importlib.loader import ResourceSeriesLoader

class OnsLoader(ResourceSeriesLoader):
    def __init__(self, ckanclient, stats):
        field_keys_to_find_pkg_by = ['title', 'owner_org', 'external_reference']
        field_keys_to_expect_invariant = [
            'geographic_coverage', 'temporal_granularity',
            'precision', 'url', 'taxonomy_url',
            'license_id']
        extras_to_not_overwrite = ['theme-primary', 'themes-secondary']
        super(OnsLoader, self).__init__(
            ckanclient,
            field_keys_to_find_pkg_by,
            field_keys_to_expect_invariant=field_keys_to_expect_invariant,
            extras_to_not_overwrite=extras_to_not_overwrite,
            stats=stats
            )

    def _get_search_options(self, field_keys, pkg_dict):
        search_options_list = super(OnsLoader, self)._get_search_options(field_keys, pkg_dict)
        return search_options_list

    def _get_hub_id(self, resource):
        '''For a given resource, returns its hub id
        e.g. "April 2009 data: Experimental Statistics | hub/id/119-46440"
              gives "119-46440"

        If the resource has no hub id then it returns None (this is the case
        for resources that were manually created during the period in 2012
        when it was possible).
        '''
        try:
            return resource['hub-id']
        except KeyError, e:
            return None
            

    def _choose_date(self, pkg1, date2_str, earlier_or_later, extra_field):
        '''From two packages, look in an extra field and return the value
        of the one which is earlier (or later).'''
        assert earlier_or_later in ('earlier', 'later')
        dates = [pkg1['extras'].get(extra_field), date2_str]
        parsed_dates = [(date.FlexiDate.from_str(date_str).as_datetime() if date_str else None) for date_str in dates]
        non_none_parsed_dates = [d for d in parsed_dates if d]
        if not non_none_parsed_dates:
            return None
        cmp_func = min if earlier_or_later == 'earlier' else max
        picked_parsed_date = cmp_func(non_none_parsed_dates)
        return dates[parsed_dates.index(picked_parsed_date)]
    
    def _merge_resources(self, existing_pkg, pkg):
        # merge date_released and date_updated fields
        pub_date = pkg['extras']['date_released']
        pkg['extras']['date_released'] = self._choose_date(existing_pkg, pub_date, 'earlier', 'date_released')
        pkg['extras']['date_updated'] = self._choose_date(existing_pkg, pub_date, 'later', 'date_updated')        
        merged_dict = super(OnsLoader, self)._merge_resources(existing_pkg, pkg)
        # sort resources by publish-date
        cmp_hub_id = lambda res1, res2: cmp(res1.get('publish-date'),
                                            res2.get('publish-date'))
        merged_dict['resources'] = sorted(merged_dict['resources'], cmp=cmp_hub_id)
        return merged_dict

    def _get_resource_id(self, res):
        return res.get('hub-id')
