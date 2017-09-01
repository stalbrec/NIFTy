#!/bin/bash

git clone https://gitlab.mpcdf.mpg.de/ift/pyHealpix.git
(cd pyHealpix && autoreconf -i && ./configure --enable-openmp --prefix=${HOME}/.local && make -j4 install)
(cd pyHealpix && autoreconf -i && PYTHON=python3 PYTHON_CONFIG=python3-config ./configure --enable-openmp --prefix=${HOME}/.local && make -j4 install)
rm -rf pyHealpix
