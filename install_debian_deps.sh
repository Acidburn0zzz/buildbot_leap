#!/bin/bash
JESSIE_PACKAGES=(git
		 libffi-dev
		 libsqlite3-dev
		 libzmq-dev
		 python-virtualenv
		 python2.7
		 make,
		 gcc
		)

if [[ $EUID -ne 0 ]]; then
    echo "You need to be root to install packages"
    exit 1
fi

for package in ${JESSIE_PACKAGES[@]}; do
    apt-get install $package
done
