import sys

from ckanext.command import Command

class MassChangerCommand(Command):
    def __init__(self, commands=None):
        usage = "%%prog [options]"
        if commands:
            usage += " {%s}" % '|'.join(commands)
        else:
            commands = []
        self.parser = Command.StandardParser(usage=usage)
        self.parser.add_option("-H", "--host",
                          dest="api_url",
                          default="http://test.ckan.net/api",
                          help="API URL (default: http://test.ckan.net/api)")
        self.parser.add_option("-k", "--key",
                          dest="api_key",
                          help="API Key (required)")
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
        self.parser.add_option("-u", "--username",
                          dest="username",
                          help="Username for HTTP Basic Authentication")
        self.parser.add_option("-p", "--password",
                          dest="password",
                          help="Password for HTTP Basic Authentication")
        self.add_additional_options()
        super(MassChangerCommand, self).__init__()

    def assert_args_valid(self):
        assert self.dry_run or (self.options.api_key is not None), "Please specify an API Key"

    def command(self):
        try:
            self.assert_args_valid
        except AssertionError, e:
            print 'ERROR', e.args
            self.parser.print_help()
            sys.exit(1)
        # now do command

def command():
    MassChangerCommand().command()

