#!/usr/bin/python3
import asyncio, asyncssh, sys
import io
import gzip
import deb822
import urllib.request
import time
from random import randrange,seed
import sys
import subprocess
from numpy.random import choice
import time

print('downloading package list')
delay = 10
df = None
while df is None:
    try:
        with urllib.request.urlopen('https://archive.raspbian.org/raspbian/dists/buster-staging/main/source/Sources.gz') as response:
            cf = io.BytesIO()
            cf.write(response.read())
        cf.seek(0)
        df = gzip.GzipFile(fileobj=cf, mode='rb')
    except Exception as e:
        print('failed to download source package list with exception '+str(e)+', will retry in '+str(delay)+' seconds')
        time.sleep(delay)
        delay = min(delay*2,300)

seed()
print('parsing package list')
fakeresponses = []
weights = []
i = 0;
for entry in deb822.Sources.iter_paragraphs(df):
    #print(repr(entry))
    arch = entry['architecture']
    if ('any' in arch) or ('armhf' in arch):
        size = 0
        for file in entry['Files']:
            size += int(file['size'])
        fakeresponses.append(entry['Section']+'/'+entry['Package']+'_'+entry['Version']+' ['+entry['Priority']+':uncompiled:calprio{18}:days{0}]')
        weights.append(size*size)
        i += 1
        if (i%100) == 0:
            print('processed '+str(i)+' packages')
        #if i > 200:
        #    break
    
df.close()

totalweight = 0
for weight in weights:
    totalweight += weight

for i in range(len(weights)):
    weights[i] /= totalweight

#print(weights)

print('processed package list, starting server')

class MySSHServerSession(asyncssh.SSHServerSession):
    def __init__(self):
        self._input = ''

    def connection_made(self, chan):
        self._chan = chan

    def shell_requested(self):
        return True

    def exec_requested(self,command):
        print(repr(command))
        self._command = command
        return True

    def session_started(self):
        print('in session_started')
        commandsplit = self._command.strip().split(' ')
        if commandsplit[-1] == '--list=needs-build':
            print('sending package list to client')
            time.sleep(1)
            for i in range(0,10):
                #r = randrange(0,len(fakeresponses))
                #print('about to call choice')
                r = choice(len(fakeresponses),1,p=weights)[0]
                #print('choice returned')
                #print(r)
                self._chan.write(fakeresponses[r]+'\n')
            self._chan.write('Total 10 package(s)\n')
        #self._chan.write_eof()
        if '_' in commandsplit[-1]:
            package = commandsplit[-1][0]
            self._chan.write('- '+package+':\n')
            self._chan.write('    - status: ok\n')
            self._chan.write('    - pkg-ver: '+commandsplit[-1]+'\n')
            self._chan.write('    - suite: buster-staging\n')
            self._chan.write('    - arch: armhf\n')

        self._chan.exit(0)
        pass

    def data_received(self, data, datatype):
        self._input += data

        lines = self._input.split('\n')
        for line in lines[:-1]:
            print(line)
        self._input = lines[-1]

    def eof_received(self):
        self._chan.exit(0)

    def break_received(self, msec):
        self.eof_received()

class MySSHServer(asyncssh.SSHServer):
    def session_requested(self):
        return MySSHServerSession()

async def start_server():
    await asyncssh.create_server(MySSHServer, '', 8022,
                                 #server_host_keys=['ssh_host_key'],
                                 server_host_keys=['/etc/ssh/ssh_host_rsa_key'],
                                 authorized_client_keys='/build/buildd/.ssh/id_rsa.pub')

loop = asyncio.get_event_loop()

try:
    loop.run_until_complete(start_server())
except (OSError, asyncssh.Error) as exc:
    sys.exit('Error starting server: ' + str(exc))

print('server running')
if (len(sys.argv) > 1) and (sys.argv[1] == "restartbuildd"):
	subprocess.call(['service','buildd','restart'])

#r = choice(len(fakeresponses),1,p=weights)[0]
#print(r)

loop.run_forever()
