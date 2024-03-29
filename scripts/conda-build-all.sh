#!/usr/bin/env bash

# Script to build all conda packages on the current system
script_dir="$( cd "$(dirname "$0")" ; pwd -P )"

python_versions=()
python_versions+=('3.9')

python_pkgs=()
python_pkgs+=('conda') #baker itself

echo -e "#!/usr/bin/env bash\n"

for pyver in "${python_versions[@]}"; do
  for p in "${python_pkgs[@]}"; do
    echo "## To build '${p}', issue the following:"
    echo conda build --python=$pyver $p
    echo ${script_dir}/conda-build-docker.sh --python=$pyver /work/$p
    echo ""
  done
done
