#!/bin/bash

base_dir=`pwd`
virtualenv_directory=$base_dir/sandbox
if [[ ! -d $virtualenv_directory ]]; then
    virtualenv --python=python2 $virtualenv_directory
fi

virtualenv_bin=$virtualenv_directory/bin
PATH=$virtualenv_directory/bin:$PATH

buildbot_sources=buildbot-sources
if [[ ! -d buildbot-sources/.git ]]; then
    git clone --depth 1 git://github.com/buildbot/buildbot.git $buildbot_sources
else
    cd $buildbot_sources
    git pull
    cd -
fi

cd $buildbot_sources
pip install -e master
pip install -e slave
make prebuild_frontend
cd -

buildbot stop master
buildbot upgrade-master master
buildbot start master
