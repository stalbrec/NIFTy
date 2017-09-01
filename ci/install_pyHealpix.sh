#!/bin/bash

git clone https://gitlab.mpcdf.mpg.de/ift/pyHealpix.git
(cd pyHealpix && autoreconf -i && ./configure --enable-openmp && make -j4 install)
(cd pyHealpix && autoreconf -i && PYTHON=python3 ./configure --enable-openmp && make -j4 install)
rm -rf pyHealpix
