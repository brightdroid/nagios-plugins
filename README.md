# nagios-plugins


Alternative Nagios Plugins written in Python


## check_http

This plugin can check http(s) content, even behind a proxy with https!

Example:
```
./check_http.py -p http://proxy:port http://www.google.com
```

## check_ssl

This plugin can check ssl certificates, even behind a proxy!

Example:
```
./check_ssl.py -p http://proxy:port google.com
```
