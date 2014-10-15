from mass_changer import MassChanger, ListedPackageMatcher, BasicPackageChanger, ChangeInstruction

class BulkDelete(object):
    def __init__(self, ckanclient, dry_run=False, force=False):
        '''
        Delete packages
        @param ckanclient: instance of ckanclient to make the changes
        @param license_id: id of the license to change packages to
        @param force: do not stop if there is an error with one package
        '''
        self.ckanclient = ckanclient
        self.dry_run = dry_run
        self.force = force

    def delete_package_list(self, packages):
        instructions = [
            ChangeInstruction(ListedPackageMatcher(packages),
                              BasicPackageChanger('state', 'deleted'))
            ]
        self.mass_changer = MassChanger(self.ckanclient,
                                        instructions,
                                        dry_run=self.dry_run,
                                        force=self.force)
        self.mass_changer.run()
