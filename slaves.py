from buildbot.buildslave import BuildSlave


class MySlave(BuildSlave):
    # We store the passwords for the buildslaves in a separate file, so we
    # can share this one more widely.
    # Thanks https://svn.torproject.org/svn/projects/buildbot/trunk/master.cfg
    PASSWORD_FILE = "passwords.py"

    d = {}
    execfile(PASSWORD_FILE, d)
    PASSWORDS = d['PASSWORDS']
    del d

    name = ""
    is_leap = None

    def __init__(self, name, is_leap):
        self.name = name
        self.is_leap = is_leap
        BuildSlave.__init__(self, name, self.PASSWORDS[name])


slaves = [
    MySlave("localhost_slave", is_leap=True),
    MySlave("macmini_kali", is_leap=False)
]


def leap_names():
    return [slave.name for slave in slaves if slave.is_leap]


def is_leap(slave_name):
    return slave_name in leap_names()


def names():
    return [slave.name for slave in slaves]
