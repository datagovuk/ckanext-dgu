'''
Takes a list of package names.
For each package:
 * double-checks it has a URL but no resources
 * creates a new resource with download url according to the resource
'''
from mass_changer import *
from common import ScriptError

log = __import__("logging").getLogger(__name__)

pkg_name_list = '''anti-social-behaviour-orders-1999-2007
asylum-applications-jan-mar-2009
control-of-immigration-quarterly-statistical-summary-united-kingdom-2009-october-december
coroners-statistics-england-and-wales
courts-statistics-user-survey-england-and-wales
court-statistics-company-insolvency-and-bankruptcy-england-and-wales
court-statistics-england-and-wales
court-statistics-mortages-and-landlord-possession-england-and-wales
crime-in-england-and-wales
crime-statistics-local-reoffending-england-and-wales
crime-statistics-prison-and-probation-england-and-wales
crime-statistics-reoffending-of-adults-england-and-wales
crime-statistics-reoffending-of-juvenilles-england-and-wales
data_gov_uk-datasets
digest-uk-energy-statistics-2008
directgov-central-hottest-pages-monthly
directgov-central-internal-search-terms-monthly
directgov-section-visits-monthly
electricity-consumption-2007
electricity-gas-consumption-2007
energy-consumption-uk-2008
final-energy-consumption-2007
foi-statistics-uk-central-government
fuel-poverty-statistics-2007
gas-consumption-2007
gb-reported-bicycling-accidents
gb-road-traffic-counts
gb-traffic-matrix
greenhouse-gas-emissions-2008
high-level-indicators-energy-use-2006
judicial-and-court-statistics-england-and-wales
laboratory-tests-and-prices
local-authority-carbon-dioxide-emissions-2007
magistrates-courts-statistics-survey-england-and-wales
monthly-energy-prices
monthly-energy-trends
ni_012_refused_and_deferred_houses_in_multiple_occupation_hmos_licence_applications_leading_to_immig
ni_013_migrants_english_language_skills_and_knowledge
ni_023_perceptions_that_people_in_the_area_treat_one_another_with_respect_and_consideration
ni_024_satisfaction_with_the_way_the_police_and_local_council_dealt_with_anti-social_behaviour
ni_025_satisfaction_of_different_groups_with_the_way_the_police_and_local_council_dealt_with_anti-so
ni_026_specialist_support_to_victims_of_a_serious_sexual_offence
ni_029_gun_crime_rate
ni_031_re-offending_rate_of_registered_sex_offenders
ni_032_repeat_incidents_of_domestic_violence
ni_034_domestic_violence_-_murder
ni_036_protection_against_terrorist_attack
ni_038_drug_related_class_a_offending_rate
ni_078_reduction_in_number_of_schools_where_fewer_than_30_of_pupils_achieve_5_or_more_a-_c_grades_at
ni_101_looked_after_children_achieving_5_a-c_gcses_or_equivalent_at_key_stage_4_including_english_an
ni_109_delivery_of_sure_start_childrens_centres
ni_126_early_access_for_women_to_maternity_services
ni_127_self_reported_experience_of_social_care_users
ni_128_user_reported_measure_of_respect_and_dignity_in_their_treatment
ni_181_time_taken_to_process_housing_benefit-council_tax_benefit_new_claims_and_change_events
ni_184_food_establishments_in_the_area_which_are_broadly_compliant_with_food_hygiene_law
ni_185_co2_reduction_from_local_authority_operations
ni_190_achievement_in_meeting_standards_for_the_control_system_for_animal_health
ni_194_air_quality_-_reduction_in_nox_and_primary_pm10_emissions_through_local_authorities_estate_an
other-fuels-consumption-2006
police-use-firearms-england-wales-2007-2008
prison-end-of-custody-licence-releases-and-recalls-england-and-wales
prison-population-england-and-wales
probation-offender-management-caseload-statistics-england-and-wales
probation-statistics-quarterly-brief-england-and-wales
quality-indicators-energy-data-2007
quarterly-energy-prices
quarterly-energy-trends
road-transport-energy-consumption-2007
sentencing-statistics-england-and-wales
statistics-terrorism-arrests-outcomes-2001-2008
ukba-control-of-immigration-statistics-2008
ukba-control-of-immigration-statistics-2008-supplementary-tables
uk-energy-in-brief-2008
uk-energy-sector-indicators-background-2008
uk-energy-sector-indicators-key-supporting-2008
uk-exportcontrollists
uk-exportcontrol-sanctions
uk-export-control-statistics
uk-glossary-exportcontrol
uk-ipo-offences
weekly-fuel-prices
'''.split()
pkg_name_list = [name for name in pkg_name_list if name]

class TransferUrl(object):
    def __init__(self, ckanclient, dry_run=False, force=False):
        '''
        Changes licenses of packages.
        @param ckanclient: instance of ckanclient to make the changes
        @param license_id: id of the license to change packages to
        @param force: do not stop if there is an error with one package
        '''
        self.ckanclient = ckanclient
        self.dry_run = dry_run
        self.force = force

    def transfer_url(self):
        instructions = [
            ChangeInstruction(
                [
                    TransferUrlMatcher(),
                    ],
                CreateResource(url='%(url)s'))
            ]
        self.mass_changer = MassChangerNamedPackages(self.ckanclient,
                                        instructions,
                                        dry_run=self.dry_run,
                                        force=self.force)
        self.mass_changer.pkg_name_list = pkg_name_list
        self.mass_changer.run()
        
class TransferUrlMatcher(PackageMatcher):
    def match(self, pkg):
        if not (pkg['url'] or '').strip():
            log.warn('Ignoring package with no URL: %r', pkg['name'])
            return False
##        if not pkg['url'].lower().endswith('.pdf'):
##            log.warn('Ignoring package URL not ending in ".PDF": %r %r',
##                     pkg['name'], pkg['url'])
##            return False
        if pkg['resources']:
            log.warn('Ignoring package with resources already: %r', pkg['name'])
            return False        
        return True
