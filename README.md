# WebPKI
## Author: Derek Greene
Date: 6/27/2024 

Description: This script connects to a websocket server [Certstream Server Go](https://github.com/d-Rickyy-b/certstream-server-go) (which is ran as a docker container) to continuously receive domain data from CT Logs, saves the received data into a JSON file, and performs [ZDNS](https://github.com/zmap/zdns) scans on the received domains. The results of the ZDNS scans are saved into separate JSON files for CAA and TXT records.