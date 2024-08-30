# WebPKI Certificate Transparency Thesis

Repository to house scripts and code related to my ongoing WekPKI and CT Thesis Research @ OSU

## Descriptions

### domains.py
This script connects to a websocket server [Certstream Server Go](https://github.com/d-Rickyy-b/certstream-server-go) (which is ran as a docker container) to continuously receive a stream of domains from CT Logs, saves the received data into a JSON file, and performs [ZDNS](https://github.com/zmap/zdns) scans to collect TXT records for the _validation-contactemail and _validation-contactphone subdomains. Addional ZDNS scans for CAA records are also performed on the primary domains collected from CT logs. The results of the ZDNS scans are saved into separate JSON files for CAA and TXT records.

### app.py & websocket.py
This application identifies disposable email addresses used as contact methods in WHOIS records. Domains are collected using [Certstream Server Go](https://github.com/d-Rickyy-b/certstream-server-go) which streams Certificate Transparency logs continuously to a websocket connection. Domains are extracted from the data stream and whois queries are subsequently made to identify contact email addresses which are compared against a list of known disposable domains. If a disposable email address is found, the domain is flagged as vulnerable and the data is stored to a mysql database. The total number of vulnerable domains found is served to a [Flask app](http://162.213.248.87:81/)

### CA_DCV_METHODS.ipynb
This Jupyter notebook uses pandas and matplotlib to visualize chrome root store data related to my certificate transparency research in the form or bar graphs. The first bar graph is a visualization of how many root CA's in the chrome root store allow each DCV method. The second bar graph is a visualization of how many parent CA's allow each DCV method.