from mass_changer import MassChanger, ChangeInstruction
from common import ScriptError

class ChangeLicenses(object):
    def __init__(self, ckanclient, license_id, dry_run=False):
        '''
        Changes licenses of packages.
        @param ckanclient: instance of ckanclient to make the changes
        @param license_id: id of the license to change packages to
        '''
        instructions = [ChangeInstruction('*', '', 'license_id', license_id)]
        self.mass_changer = MassChanger(ckanclient, instructions, dry_run=dry_run)

    def change_all_packages(self):
        self.mass_changer.run()
