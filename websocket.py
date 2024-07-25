import asyncio
import json
import subprocess
import websockets

def clean_domain(domain):
    if domain.startswith("www."):
        domain = domain[4:]  # Remove "www."
    if domain.startswith("*."):
        domain = domain[1:]  # Remove "*."
    return domain

def run_zdns_command(domain, record_type):
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

async def keep_alive(websocket):
    try:
        while True:
            await asyncio.sleep(30)
            await websocket.ping()
    except asyncio.CancelledError:
        pass

async def connect_to_server(uri):
    domains_output_file = "domains.json"
    caa_output_file = "CAA.json"
    txt_output_file = "TXT.json"

    while True:
        try:
            async with websockets.connect(uri) as websocket:
                print("Connected to server")
                keep_alive_task = asyncio.create_task(keep_alive(websocket))

                while True:
                    message = await websocket.recv()
                    data = json.loads(message)
                    print(f"Received: {data['data']}")

                    try:
                        if "data" in data:
                            with open(domains_output_file, "a") as domains_file:
                                with open(caa_output_file, "a") as caa_file, open(txt_output_file, "a") as txt_file:
                                    for domain in data["data"]:
                                        clean_domain_name = clean_domain(domain)
                                        clean_domain_name = clean_domain_name.lstrip('.')
                                        domains_file.write(f"{clean_domain_name}\n")
                                        clean_domain_for_caa = clean_domain_name
                                        caa_results = run_zdns_command(clean_domain_for_caa, 'CAA')
                                        for result in caa_results:
                                            caa_file.write(json.dumps(result) + "\n")
                                        email_domain = f"_validation-contactemail.{clean_domain_name}"
                                        phone_domain = f"_validation-contactphone.{clean_domain_name}"
                                        txt_results_email = run_zdns_command(email_domain, 'TXT')
                                        txt_results_phone = run_zdns_command(phone_domain, 'TXT')
                                        for result in txt_results_email:
                                            txt_file.write(json.dumps(result) + "\n")
                                        for result in txt_results_phone:
                                            txt_file.write(json.dumps(result) + "\n")
                    except Exception as e:
                        print(f"Error processing domains: {e}")

        except websockets.exceptions.ConnectionClosedError as e:
            print(f"Connection closed: {e}")
            await asyncio.sleep(5)
        except Exception as e:
            print(f"Error: {e}")
            await asyncio.sleep(5)

async def main():
    uri = "ws://localhost:8080/domains-only"
    await connect_to_server(uri)

if __name__ == "__main__":
    asyncio.run(main())
