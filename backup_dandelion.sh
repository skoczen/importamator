#!/bin/sh
rsync -ahP /Volumes/Dandelion/Capture /Volumes/BlackBox/Backups/  --exclude=.DS_Store --exclude=*_Proxy* --exclude=*_Rendered*.mxf*
