#!/usr/bin/env python

import argparse
import sys
import re
from OpenSSL import SSL, crypto
import socket
import datetime

version = '1.0'



### print status and exit with return code
def printCert(cert):
	# type check
	if not isinstance(cert, crypto.X509):
		print "CRIT: Certificate is invalid"
		sys.exit(2)

	nagiosStatus2Text = {
		0: "OK",
		1: "WARN",
		2: "CRIT"
	}

	# format expire times
	nbefore = datetime.datetime.strptime(cert.get_notBefore(), '%Y%m%d%H%M%SZ')
	nafter = datetime.datetime.strptime(cert.get_notAfter(), '%Y%m%d%H%M%SZ')

	# calculate time diff between now and "not after"
	now = datetime.datetime.utcnow()
	if now > nafter:
		diff = now - nafter
	else:
		diff = nafter - now

	certInfo = {
		'subject': cert.get_subject().commonName,
		'days': int(diff.days),
		'minutes': int(diff.seconds/60),
		'hours': int(diff.seconds/60/60),
		'expired': nafter < now,
		'date': nafter,
	}
	exitCode = 2

	# invalid
	if nbefore > now:
		summary = "Certificate is invalid"

	# expired
	elif certInfo['expired']:
		summary = "Certificate '{subject}' expired {days} days ago".format(**certInfo)

	# crit...
	elif args.crit and args.crit > certInfo['days']:
		if certInfo['days'] > 0:
			summary = "Certificate '{subject}' expires in {days} days".format(**certInfo)
		elif certInfo['hours'] > 1:
			summary = "Certificate '{subject}' expires in {hours} hours".format(**certInfo)
		else:
			summary = "Certificate '{subject}' expires in {minutes} minutes".format(**certInfo)

	# warn...
	elif args.warn and args.warn > certInfo['days']:
		summary = "Certificate '{subject}' expires in {days} days".format(**certInfo)
		exitCode = 1
	
	# ok	
	else:
		summary = "Certificate '{subject}' valid until {date:%Y-%m-%d, %H:%M} UTC".format(**certInfo)
		exitCode = 0

	# output and exit
	print "{nagiosStatus}: {summary}|days={days:d};{warn:d};{crit:d};0".format(
		nagiosStatus=nagiosStatus2Text[exitCode],
		summary=summary,
		warn=args.warn,
		crit=args.crit,
		**certInfo
	)

	sys.exit(exitCode)



### parse args
parser = argparse.ArgumentParser(description='This plugin can check ssl certificates.')
parser.add_argument('-v', '--version', action='version', version='%(prog)s ' + version)
parser.add_argument('-p', '--proxy', help='Proxy to use, e.g. proxy:port or user:pass@proxy:port')
parser.add_argument('-t', '--timeout', type=int, default=10, help='Timout in seconds (Default: 10)')
parser.add_argument('-w', '--warning', dest='warn', type=int, default=30, help='Days until certificate expires to be in warning-state. (Default: 30)')
parser.add_argument('-c', '--critical', dest='crit', type=int, default=0, help='Days until certificate expires to be in critical-state. (Default: 0)')
parser.add_argument('-P', '--port', type=int, default=443, help='Port to connect to (Default: 443)')
parser.add_argument('domain', nargs='?')
args = parser.parse_args()

# domain given?
if not args.domain:
	parser.print_help()
	sys.exit('Domain required!')



### create socket
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)



try:
	### use proxy?
	if args.proxy:
		proxy = re.search(r'^(?:([^:]+):([^:]*)@)?([^:]+):(.*)$', args.proxy).groups()
		s.connect((proxy[2], int(proxy[3])))
		CONNECT = "CONNECT %s HTTP/1.0\r\nConnection: close\r\n\r\n" % (args.domain)
		s.send(CONNECT)
		s.recv(4096)      
	else:
		s.connect((args.domain, args.port))

	### send request
	ctx = SSL.Context(SSL.SSLv23_METHOD)
	ctx.set_timeout(args.timeout)
	ss = SSL.Connection(ctx, s)
	ss.set_connect_state()
	ss.do_handshake()

except Exception as e:
	print "CRIT: connect error"
	sys.exit(2)



### parse cert
cert = ss.get_peer_certificate()
printCert(cert)



### close socket
ss.shutdown()
ss.close()
