#!/usr/bin/env python
#
# Copyright (c) Christoph Roeder <chris@brightdroid.com>
#

import argparse
import sys
import time
import re
import requests

version = '2.0'



def outputResult(nagiosStatus, summary, response=None, **kwargs):
	"""Print nagios plugin output and exit with return code

	:param nagiosStatus: nagios return code
	:type nagiosStatus: int
	:param summary: error string
	:type summary: string
	:param response: Response object
	:type response: requests.Response
	:param kwargs: list of options (warn, crit, regex, minsize)
	:type kwargs: **kwargs
	"""

	nagiosStatus2Text = {
		0: "OK",
		1: "WARN",
		2: "CRIT",
		3: "UNK",
	}


	### no response
	if response is None:
		print "{nagiosStatus}: {summary}".format(
			nagiosStatus=nagiosStatus2Text[nagiosStatus],
			summary=summary
		)
		sys.exit(nagiosStatus)

	### valid response
	else:
		# summary with status code
		if response.status_code and summary:
			summary = "Status %d - %s" % (response.status_code, summary)
			
		else:
			summary = "Status %d" % (response.status_code)

		print "{nagiosStatus}: {summary} - {size} bytes in {time:.3f} second response time|time={time:.4f};{warn:.4f};{crit:.4f}; size={size:.2f}B;;;0".format(
			nagiosStatus=nagiosStatus2Text[nagiosStatus],
			summary=summary,
			size=len(response.text),
			time=float(response.elapsed.microseconds/1000)/1000,
			warn=args.warn,
			crit=args.crit,
		)

		sys.exit(nagiosStatus)





if __name__ == "__main__":
	### parse args
	parser = argparse.ArgumentParser(description='This plugin can check http(s) content.')
	parser.add_argument('-v', '--version', action='version', version='%(prog)s ' + version)
	parser.add_argument('-p', '--proxy', help='Proxy to use, e.g. http://user:pass@proxy:port')
	parser.add_argument('-t', '--timeout', type=int, default=8, help='Timout in seconds (Default: 10)')
	parser.add_argument('-r', '--regex', help='Search page content for this regex')
	parser.add_argument('-s', '--size', nargs=2, metavar=('MIN', 'MAX'), help='Minimum page size required (bytes), Maximum page size required (bytes)')
	parser.add_argument('-w', '--warning', dest='warn', type=float, default=0.0, help='Response time to result in warning status (seconds)')
	parser.add_argument('-c', '--critical', dest='crit', type=float, default=0.0, help='Response time to result in critical status (seconds)')
	parser.add_argument('url', nargs='?')
	args = parser.parse_args()

	# valid URL given?
	if not args.url or not re.match(r'^https?://', args.url):
		parser.print_help()
		sys.exit('Valid URL required!')

	# warn and crit given?
	if bool(args.warn) != bool(args.crit):
		parser.print_help()
		sys.exit('Warning and critical must both be given!')

	# warn > crit?
	if args.warn > 0.0 and args.warn >= args.crit:
		parser.print_help()
		sys.exit('Warning have to be smaller than critical!')


	### set default values
	status = 0
	summary = ""

	# use proxy?
	if args.proxy:
		proxies = {
			'http': str(args.proxy),
			'https': str(args.proxy)
		}
	else:
		proxies = {
			'http': None,
			'https': None,
		}


	### do the request
	try:
		r = requests.get(args.url, timeout=float(args.timeout), proxies=proxies)
		r.raise_for_status()

	except requests.exceptions.Timeout as e:
		outputResult(3, "Timeout reached")

	except requests.exceptions.TooManyRedirects as e:
		outputResult(2, "Too many redirects")

	except requests.exceptions.ConnectionError as e:
		outputResult(2, "Connect error")

	except requests.exceptions.HTTPError as e:
		outputResult(2, e)

	except Exception as e:
		outputResult(2, "Error %s" % e)


	### check body content?
	if args.regex and not re.search(args.regex, r.text, re.IGNORECASE):
		status = max(2, status)
		summary = "Pattern not found"


	### check page size?
	if args.size:
		args.size = map(int, args.size)
		responseSize = len(r.text)

		if responseSize < args.size[0]:
			status = max(2, status)
			summary = "Response to small"

		if responseSize > args.size[1]:
			status = max(2, status)
			summary = "Response to large"


	### check response time?
	responseTime = float(r.elapsed.microseconds/1000)/1000

	if args.crit and responseTime > float(args.crit):
		status = max(2, status)
		summary = "Response to slow"

	elif args.warn and responseTime > float(args.warn):
		status = max(1, status)
		summary = "Response to slow"


	### http status code check
	if r.status_code in [301, 302]:
		status = max(1, status)
	
	elif r.status_code != 200:
		status = max(2, status)


	### output status and return status
	outputResult(status, summary, r, regex=args.regex, warn=args.warn, crit=args.crit)
