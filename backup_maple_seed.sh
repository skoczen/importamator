#!/bin/sh
rsync -ahP /Volumes/Maple\ Seed/Projects /Volumes/BlackBox/Backups/ --exclude=.DS_Store --exclude=*_Proxy* --exclude=*_Rendered*.mxf*
rsync -ahP /Volumes/Maple\ Seed/Audio /Volumes/BlackBox/Backups/ --exclude=.DS_Store --exclude=*_Proxy* --exclude=*_Rendered*.mxf*
