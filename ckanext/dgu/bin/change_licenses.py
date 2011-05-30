from mass_changer import *
from common import ScriptError

class ChangeLicenses(object):
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

    def change_all_packages(self, license_id):
        instructions = [
            ChangeInstruction(AnyPackageMatcher(),
                              BasicPackageChanger('license_id', license_id))
            ]
        self.mass_changer = MassChanger(self.ckanclient,
                                        instructions,
                                        dry_run=self.dry_run,
                                        force=self.force)
        self.mass_changer.run()

    def change_oct_2010(self, license_id):
        instructions = [
            ChangeInstruction(
                [
                    BasicPackageMatcher('license_id', 'localauth-withrights'),
                    BasicPackageMatcher('name', 'spotlightonspend-transactions-download'),
                    BasicPackageMatcher('name', 'better-connected-2010-council-website-performance-survey-results'),
                    ],
                NoopPackageChanger()),
            ChangeInstruction(
                AnyPackageMatcher(),
                BasicPackageChanger('license_id', self.license_id)),
            ]
        self.mass_changer = MassChanger(self.ckanclient,
                                        instructions,
                                        dry_run=self.dry_run,
                                        force=self.force)
        self.mass_changer.run()
