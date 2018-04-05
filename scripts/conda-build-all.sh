#!/usr/bin/env bash

# Script to build all conda packages on the current system
script_dir="$( cd "$(dirname "$0")" ; pwd -P )"

simple_pkgs=()
#simple_pkgs+=('deps/restic')

python_versions=()
python_versions+=('2.7')
python_versions+=('3.6')

python_pkgs=()
#python_pkgs+=('deps/yapf')
#python_pkgs+=('deps/logfury')
#python_pkgs+=('deps/b2')
#python_pkgs+=('deps/schedule')
python_pkgs+=('conda') #baker itself

for p in "${simple_pkgs[@]}"; do
  conda build --build-only ${p}
  ${script_dir}/conda-build-docker.sh /work/$p
done

for pyver in "${python_versions[@]}"; do
  for p in "${python_pkgs[@]}"; do
    conda build --python=$pyver $p
    ${script_dir}/conda-build-docker.sh --build-only --python=$pyver /work/$p
  done
done
