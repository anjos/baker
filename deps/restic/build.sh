#/bin/sh

bzip2 -dc restic.bz2 > $PREFIX/bin/restic
chmod 755 $PREFIX/bin/restic
