import asyncio
import json
import os
import re
import time
import pymysql.cursors
import websockets
import whois
from datetime import datetime
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

host = os.environ.get("DB_HOST")
user = os.environ.get("DB_USER")
passwd = os.environ.get("DB_PASSWD")
db = os.environ.get("DB_NAME")

def clean_domain(domain):
    """Clean up domain names by removing 'www.' and '*.' prefixes."""
    if domain.startswith("www."):
        domain = domain[4:]  # Remove "www."
    if domain.startswith("*."):
        domain = domain[1:]  # Remove "*."
    return domain

def load_allowed_domains(filename):
    """Load allowed domains from a file."""
    with open(filename, 'r') as file:
        return set(line.strip().lower() for line in file)

def extract_emails(whois_data):
    """Extract email addresses from a WHOIS record."""
    emails = []
    if isinstance(whois_data, dict):
        for key in ['emails', 'admin_email', 'tech_email', 'registrant_email']:
            if key in whois_data:
                if isinstance(whois_data[key], list):
                    emails.extend(whois_data[key])
                elif isinstance(whois_data[key], str):
                    emails.append(whois_data[key])
    return emails

def domain_from_email(email):
    """Extract domain from email address."""
    match = re.search(r'@([^\s]+)$', email)
    return match.group(1).lower() if match else None

def query_whois(domain):
    """Query WHOIS data for a domain."""
    try:
        whois_info = whois.whois(domain)
        return whois_info
    except Exception as e:
        print(f"Error querying WHOIS for domain {domain}: {e}")
        return None

def convert_to_serializable(obj):
    """Convert objects to a JSON serializable format."""
    if isinstance(obj, datetime):
        return obj.isoformat()  # Convert datetime to ISO 8601 string
    if isinstance(obj, dict):
        return {k: convert_to_serializable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [convert_to_serializable(i) for i in obj]
    return obj

async def keep_alive(websocket):
    """Send ping every 30 seconds to keep the WebSocket connection alive."""
    try:
        while True:
            await asyncio.sleep(30)
            await websocket.ping()
    except asyncio.CancelledError:
        print("Keep-alive task cancelled.")
    except Exception as e:
        print(f"Error in keep_alive task: {e}")

async def connect_to_server(uri, duration=30):
    """Connect to the WebSocket server and process received messages for a given duration."""
    domains_output_file = "domains.json"
    start_time = time.time()

    async with websockets.connect(uri) as websocket:
        print("Connected to server")

        # Start keep_alive in the background
        keep_alive_task = asyncio.ensure_future(keep_alive(websocket))

        try:
            while True:
                if time.time() - start_time > duration:
                    break
                try:
                    message = await websocket.recv()
                    data = json.loads(message)
                    print(f"Received: {data.get('data')}")

                    if "data" in data:
                        with open(domains_output_file, "a") as domains_file:
                            for domain in data["data"]:
                                clean_domain_name = clean_domain(domain)
                                clean_domain_name = clean_domain_name.lstrip('.')
                                domains_file.write(f"{clean_domain_name}\n")

                except Exception as e:
                    print(f"Error processing domains: {e}")

        finally:
            keep_alive_task.cancel()  # Cancel the keep-alive task when done
            try:
                await keep_alive_task
            except asyncio.CancelledError:
                pass
            except Exception as e:
                print(f"Error awaiting keep-alive task: {e}")

async def process_domains_file(allowed_domains, db_connection):
    """Process the domains.json file, perform WHOIS lookups, and save results to the database."""
    domains_output_file = "domains.json"

    if os.path.isfile(domains_output_file):
        print(f"Processing file: {domains_output_file}")
        with open(domains_output_file, "r") as domains_file:
            domains = domains_file.readlines()

        domains = set(clean_domain(domain.strip()) for domain in domains)
        cursor = db_connection.cursor()

        for domain in domains:
            print(f"Processing domain: {domain}")
            whois_data = query_whois(domain)
            if whois_data:
                # Extract each attribute
                registrar = whois_data.get('registrar', None)
                creation_date = whois_data.get('creation_date', None)
                expiration_date = whois_data.get('expiration_date', None)
                updated_date = whois_data.get('updated_date', None)
                emails = extract_emails(whois_data)
                admin_email = whois_data.get('admin_email', None)
                tech_email = whois_data.get('tech_email', None)
                registrant_email = whois_data.get('registrant_email', None)

                # Convert dates to strings if they are in datetime format
                if isinstance(creation_date, list):
                    creation_date = creation_date[0]
                if isinstance(expiration_date, list):
                    expiration_date = expiration_date[0]
                if isinstance(updated_date, list):
                    updated_date = updated_date[0]

                creation_date = creation_date.isoformat() if isinstance(creation_date, datetime) else creation_date
                expiration_date = expiration_date.isoformat() if isinstance(expiration_date, datetime) else expiration_date
                updated_date = updated_date.isoformat() if isinstance(updated_date, datetime) else updated_date

                # Check if any email domain matches the allowed domains
                email_domains = {domain_from_email(email) for email in emails if domain_from_email(email)}
                if email_domains & allowed_domains:
                    # Insert data into the database
                    try:
                        cursor.execute(
                            """
                            INSERT INTO domains_data (domain, registrar, creation_date, expiration_date, updated_date, emails, admin_email, tech_email, registrant_email)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ON DUPLICATE KEY UPDATE
                                registrar=VALUES(registrar),
                                creation_date=VALUES(creation_date),
                                expiration_date=VALUES(expiration_date),
                                updated_date=VALUES(updated_date),
                                emails=VALUES(emails),
                                admin_email=VALUES(admin_email),
                                tech_email=VALUES(tech_email),
                                registrant_email=VALUES(registrant_email)
                            """,
                            (
                                domain,
                                registrar,
                                creation_date,
                                expiration_date,
                                updated_date,
                                json.dumps(emails),
                                admin_email,
                                tech_email,
                                registrant_email
                            )
                        )
                        db_connection.commit()
                        print(f"Domain data saved: {domain}")
                    except Exception as e:
                        print(f"Error inserting data into database for domain {domain}: {e}")

        os.remove(domains_output_file)
    else:
        print(f"{domains_output_file} not found.")

async def run_cycle(uri, allowed_domains, db_connection, duration=30):
    """Run the WebSocket client for a period, then process the file, and repeat."""
    while True:
        await connect_to_server(uri, duration)
        await process_domains_file(allowed_domains, db_connection)
        await asyncio.sleep(duration)

def connect_to_database(host=host, user=user, passwd=passwd, db=db):
    """Connect to the database using pymysql."""
    db_connection = pymysql.connect(host=host, user=user, password=passwd, database=db, cursorclass=pymysql.cursors.DictCursor)
    print("Connected to SQL database")
    return db_connection

def main():
    """Main function to run the WebSocket client and process domains."""
    uri = "ws://localhost:8080/domains-only"
    allowed_domains = load_allowed_domains('domains.txt')
    db_connection = connect_to_database()
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(run_cycle(uri, allowed_domains, db_connection))
    finally:
        loop.close()

if __name__ == '__main__':
    main()
