import sys

from ckanext.importlib.api_command import ApiCommand

class MassChangerCommand(ApiCommand):
    def __init__(self, commands=None):
        usage = "% %prog [options]"
        if commands:
            usage += " {%s}" % '|'.join(commands)
        super(MassChangerCommand, self).__init__(usage=usage)

    def add_options(self):
        super(MassChangerCommand, self).add_options()
        self.parser.add_option("-d", "--dry-run",
                          dest="dry_run",
                          action="store_true",
                          default=False,
                          help="Write no changes")
        self.parser.add_option("-f", "--force",
                          dest="force",
                          action="store_true",
                          default=False,
                          help="Don't abort rest of packages on an error")

    def command(self):
        super(MassChangerCommand, self).command()

        # now do command

def command():
    MassChangerCommand().command()

