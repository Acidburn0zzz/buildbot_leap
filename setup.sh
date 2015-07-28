#!/bin/bash

# Requirements:
## virtualenv
## buildbot

base_dir=`pwd`
virtualenv --python=python2 sandbox

source sandbox/bin/activate

buildbot create-master master
ln -s $base_dir/master.cfg master/
ln -s $base_dir/passwords.py master/
ln -s $base_dir/conf.cfg master/

slave_name="localhost_slave"
slave_password=`python2 -c "from passwords import *; print PASSWORDS['$slave_name']"`
echo $slave_password
buildslave create-slave slave localhost:9989 $slave_name $slave_password
