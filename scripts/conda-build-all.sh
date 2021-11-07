#!/usr/bin/env bash

# Script to build all conda packages on the current system
script_dir="$( cd "$(dirname "$0")" ; pwd -P )"

python_versions=()
python_versions+=('3.8')
python_versions+=('3.9')
python_versions+=('3.10')

python_pkgs=()
python_pkgs+=('conda') #baker itself

noarch_pkgs=()
noarch_pkgs+=('deps/logfury')
noarch_pkgs+=('deps/phx-class-registry')
noarch_pkgs+=('deps/b2sdk')
noarch_pkgs+=('deps/b2')

echo -e "#!/usr/bin/env bash\n"

for p in "${noarch_pkgs[@]}"; do
  echo "## To build '${p}', issue the following:"
  echo conda build -c anjos $p
  echo ""
done

for pyver in "${python_versions[@]}"; do
  for p in "${python_pkgs[@]}"; do
    echo "## To build '${p}', issue the following:"
    echo conda build -c anjos --python=$pyver $p
    echo ${script_dir}/conda-build-docker.sh --python=$pyver /work/$p
    echo ""
  done
done
