# Author: Derek Greene
# Date: 6/27/2024
# Description: This script connects to a websocket server 'Certstream Server Go-
# 'https://github.com/d-Rickyy-b/certstream-server-go' (which is ran as a docker container)
# to continuously receive domain data from CT Logs, saves the received data into a JSON 
# file, and performs ZDNS-'https://github.com/zmap/zdns' scans on the received domains. 
# The results of the ZDNS scans are saved into separate JSON files for CAA and TXT records.

import asyncio
import json
import subprocess
import websockets

async def run_zdns_command(domain, record_type):
    command = f'./zdns {record_type} --conf-file etc/resolv.conf'
    try:
        process = subprocess.Popen(command, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd='zdns')
        stdout, stderr = process.communicate(input=domain)
        if process.returncode != 0:
            print(f"Error running command '{command}': {stderr}")
            return []

        data = [json.loads(line) for line in stdout.splitlines()]
        return data
    except subprocess.CalledProcessError as e:
        print(f"Error running command '{command}': {e}")
        return []
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON '{command}': {e}")
        return []

async def run_zdns_commands(domains, caa_results, txt_results):
    try:
        for domain in domains:
            print(f"Processing domain: {domain}")
            caa_results.extend(await run_zdns_command(domain, 'CAA'))
            txt_results.extend(await run_zdns_command(domain, 'TXT'))

        with open('zdns_results_CAA.json', 'w') as f:
            json.dump(caa_results, f, indent=4)

        with open('zdns_results_TXT.json', 'w') as f:
            json.dump(txt_results, f, indent=4)

        print("zdns scan completed successfully.")
    except Exception as e:
        print(f"Error running zdns scan: {e}")

async def connect_to_server(uri, domains):
    try:
        async with websockets.connect(uri) as websocket:
            output_file = "cert_data.json"

            with open(output_file, "w") as output_json_file:
                output_json_file.write("[")  

                first_entry = True 
                while True:
                    message = await websocket.recv()
                    data = json.loads(message)
                    print(f"Saved: {data['data']}")

                    try:
                        with open(output_file, "a") as file:
                            if not first_entry:
                                file.write(",\n") 
                            else:
                                first_entry = False
                            json.dump(data, file, indent=4)

                        if "data" in data:
                            for domain in data["data"]:
                                domains.append(domain)
                    except Exception as e:
                        print(f"Error saving to file: {e}")

    except websockets.exceptions.ConnectionClosedError as e:
        print(f"Connection closed: {e}")
    except Exception as e:
        print(f"Error: {e}")

    finally:
        with open(output_file, "a") as file:
            file.write("\n]")  

async def keep_alive(websocket):
    try:
        while True:
            await asyncio.sleep(30)
            await websocket.ping()
    except asyncio.CancelledError:
        pass

async def main():
    uri = "ws://localhost:8080/domains-only"
    domains = []
    caa_results = []
    txt_results = []

    try:
        async with websockets.connect(uri) as websocket:
            asyncio.create_task(connect_to_server(uri, domains))
            keep_alive_task = asyncio.create_task(keep_alive(websocket))

            while True:
                if domains:
                    await run_zdns_commands(domains, caa_results, txt_results)
                    domains.clear()
                await asyncio.sleep(1)
    except websockets.exceptions.ConnectionClosedError as e:
        print(f"Connection closed: {e}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        keep_alive_task.cancel()

if __name__ == "__main__":
    asyncio.run(main())