#!/bin/sh
rsync -ahP ~/Projects/Capture /Volumes/BlackBox/Backups/  --exclude=.DS_Store --exclude=*_Proxy* --exclude=*_Rendered*.mxf*
