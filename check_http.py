#!/usr/bin/env python
#
# Copyright (c) Christoph Roeder <chris@brightdroid.com>
#

import argparse
import sys
import time
import re
import urllib2, socket

version = '1.0'
httpCode2Nagios = {
    200: 0,
    301: 0,
    302: 0,
    404: 1,
    403: 1
}
nagiosStatus2Text = {
    0: "OK",
    1: "WARN",
    2: "CRIT"
}


### parse args
parser = argparse.ArgumentParser(description='This plugin can check http(s) content.')
parser.add_argument('-v', '--version', action='version', version='%(prog)s ' + version)
parser.add_argument('-p', '--proxy', help='Proxy to use, e.g. http://user:pass@proxy:port')
parser.add_argument('-t', '--timeout', help='Timout in seconds')
parser.add_argument('-r', '--regex', help='Search page content for this regex')
parser.add_argument('-s', '--size', nargs=2, metavar=('MIN', 'MAX'), help='Minimum page size required (bytes), Maximum page size required (bytes)')
parser.add_argument('url', nargs='?')
args = parser.parse_args()

# valid URL given?
if not args.url or not re.match(r'^https?://', args.url):
    parser.print_help()
    sys.exit('Valid URL required!')



### use proxy?
if args.proxy:
    opener = urllib2.build_opener(
	urllib2.HTTPHandler(),
        urllib2.HTTPSHandler(),
        urllib2.ProxyHandler({'http': str(args.proxy)}),
        urllib2.ProxyHandler({'https': str(args.proxy)})
    )
    urllib2.install_opener(opener)



### do the request
responseCode = None
responseBody = ""
status = {
    'exitCode': 2,
    'summary': '',
    'size': 0,
    'time': time.clock(),
}
try:
    timeout = float(args.timeout) if args.timeout else None
    response = urllib2.urlopen(args.url, None, timeout)
    responseCode = response.getcode()
    responseBody = response.read()
    status['summary'] = "Status %d" % responseCode

except urllib2.HTTPError as e:
    responseCode = e.code
    responseBody = str(e.reason)
    status['summary'] = e

except urllib2.URLError as e:
    status['summary'] = str(e.reason)

except socket.timeout as e:
    status['summary'] = "Socket timeout"


    
### verify response status
status['size'] = len(responseBody)
status['time'] = time.clock()-status['time']
if responseCode in httpCode2Nagios:
    status['exitCode'] = httpCode2Nagios[responseCode]
    


### check body content?
if args.regex and not re.search(args.regex, responseBody, re.IGNORECASE):
    status['exitCode'] = 2
    status['summary'] = "Status %d - pattern not found" % responseCode



### check page size?
if args.size:
    args.size = map(int, args.size)
    if status['size'] < args.size[0]:
	status['exitCode'] = 2
	status['summary'] = "Status %d - pagesize to small" % responseCode
    if status['size'] > args.size[1]:
	status['exitCode'] = 2
	status['summary'] = "Status %d - pagesize to large" % responseCode




### output status and return status
status['nagiosStatus'] = nagiosStatus2Text[status['exitCode']]
print "{nagiosStatus}: {summary} - {size} bytes in {time:.3f} second response time|time={time:.4f};;;0.0000 size={size:.2f}B;;;0".format(**status)
sys.exit(status['exitCode'])
