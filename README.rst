Dependencies
------------
See `Bitmask Client documentation <https://leap.se/en/docs/client/dev-environment#install-dependencies>`_

- xvfb
- qmake-qt4
- cmake

Setting up a slave
------------------

- Please send an email to buildbot-master@leap.se requesting a
  password, and stating which OS are you running (GNU/Linux, Mac OS X,
  Windows) and which version.
- In a nutshell:
  - If you are going to run the slave in a GNU/Linux or a Mac
    operating system, then what you need to do is `this
    <http://trac.buildbot.net/wiki/DownloadInstall#SlaveinVirtualenv>`_
  - If you're going to run it in a Microsft Windows system, then `go
    here <http://trac.buildbot.net/wiki/RunningBuildbotOnWindows>`_

- For more information, and since we're using the latest version of
  Buildbot, please read `creating a slave
  <http://docs.buildbot.net/latest/manual/installation.html#creating-a-buildslave>`_

Local slaves
-------------
slaves are run as a different user.
to start them::
  source env/bin/activate
  buildslave start worker

Workflow
--------

- Set up a feature branch and push modifications to it.
- Fetch your feature branch in lizard:/home/buildbot/buildbot-bitmask.
- Restart the buildbot master and slaves in the virtualenv::

    buildbot@lizard:~/buildbot-bitmask$ source sandbox/bin/activate
    (sandbox)buildbot@lizard:~/buildbot-bitmask$ buildbot restart master
    (sandbox)buildslave@lizard:~$ buildslave restart worker

- Once the code is tested in the feature branch it should be rebased/squashed and
  merged into the master branch.
- With the code merged into the master branch restart the buildbot using this branch.
