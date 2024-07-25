# WebPKI Certificate Transparency Thesis

Repository to house scripts and code related to my ongoing WekPKI and CT Thesis Research @ OSU

## Description

This script connects to a websocket server [Certstream Server Go](https://github.com/d-Rickyy-b/certstream-server-go) (which is ran as a docker container) to continuously receive a stream of domains from CT Logs, saves the received data into a JSON file, and performs [ZDNS](https://github.com/zmap/zdns) scans to collect TXT records for the _validation-contactemail and _validation-contactphone subdomains. Addional ZDNS scans for CAA records are also performed on the primary domains collected from CT logs. The results of the ZDNS scans are saved into separate JSON files for CAA and TXT records.
