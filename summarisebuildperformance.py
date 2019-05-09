#!/usr/bin/python3
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from collections import defaultdict
from statistics import stdev
import os
import sys

localtz = datetime(2000,1,1,tzinfo=timezone.utc).astimezone().tzinfo

#parse a variety of date formats
def myparsedt(s):
	try:
		#format used in build log names, zulu time
		result = datetime.strptime(s,'%Y-%m-%dT%H:%M:%SZ')
		result = result.replace(tzinfo=timezone.utc)
	except:
		try:
			#RFC style datetimes
			result = parsedate_to_datetime(s)
		except:
			#LS output
			result = datetime.strptime(s,'%b %d %H:%M')
	if result.tzinfo is None:
		result = result.replace(tzinfo=localtz)
	return result

starttime = myparsedt(sys.argv[1])

if len(sys.argv) >=3:
	minbuilds = int(sys.argv[2])
else:
	minbuilds = 0

results = defaultdict(list)

for fn in os.listdir('/build/buildd/logs'):
	(package,version,archandts) = fn.split('_')
	(arch,ts) = archandts.split('-',1)
	ts = myparsedt(ts)
	if ts > starttime:
		#print(fn)
		#print(ts)
		f = open('/build/buildd/logs/'+fn,'rb')
		f.seek(0,os.SEEK_END)
		filesize=f.tell()
		f.seek(max(-filesize,-2048),os.SEEK_END)
		lines = f.readlines()[1:] #first line read is likely to be partial.
		if len(lines) > 4 and (lines[-3] == b'--------------------------------------------------------------------------------\n'):
			#print(lines[-1])
			i = -4
			d = {}
			while i >= -len(lines):
				line = lines[i].strip()
				if line == b'':
					break
				#print(line)
				(key,value) = line.split(b': ',1)
				d[key] = value
				i -= 1
			if d[b'Status'] == b'successful':
				#print(fn)
				summarysplit = lines[-1].split(b' ')
				#print(summarysplit)
				#print(summarysplit[2][:-1])
				(hours,mins,secs) = summarysplit[2][:-1].split(b':')
				hours = int(hours)
				mins = int(mins)
				secs = int(secs)
				td = timedelta(hours=hours,minutes=mins,seconds=secs)
				results[package].append(td)

listforsorting = []
for (package, timedeltas) in results.items():
	if len(timedeltas) >= minbuilds:
		mean = sum(timedeltas,timedelta(0)) / len(timedeltas)
		if len(timedeltas) > 1:
			sstd = timedelta(seconds=stdev(td.total_seconds() for td in timedeltas))
		else:
			sstd = None
		listforsorting.append((package,len(timedeltas),mean,sstd))
listforsorting.sort()

for package,num,averagebuildtime,sstd in listforsorting:
	print(package+': '+str(averagebuildtime) +' (count: '+str(num)+' sstd: '+str(sstd)+'))')

