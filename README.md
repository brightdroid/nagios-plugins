# nagios-plugins


Alternative Nagios Plugins written in Python


## check_http

This plugin can check http(s) content, even behind a proxy with https!

Example:
```
./check_http.py -p http://proxy:port http://www.google.de
```
