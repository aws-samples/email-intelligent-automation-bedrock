import random
import csv
from datetime import datetime, timedelta
from faker import Faker

# Initialize Faker
fake = Faker()

# Define the number of log entries to generate
num_entries = 10000

# Define the list of issue types
issue_types = [
    "Suspicious IP connection",
    "Unusual traffic pattern",
    "Security event",
    "Performance issue",
    "Configuration problem",
    "Normal activity"
]

# Generate the synthetic network log data
with open('network_logs.csv', 'w', newline='') as csvfile:
    fieldnames = [
        'timestamp', 'source_ip', 'dest_ip', 'protocol', 'source_port',
        'dest_port', 'bytes_transferred', 'issue_type', 'issue_description'
    ]
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

    writer.writeheader()

    for _ in range(num_entries):
        # Generate random network log attributes
        timestamp = fake.date_time_between(start_date='-1w', end_date='now')
        source_ip = fake.ipv4()
        dest_ip = fake.ipv4()
        protocol = random.choice(['TCP', 'UDP', 'ICMP'])
        source_port = random.randint(1024, 65535)
        dest_port = random.randint(1, 1024)
        bytes_transferred = random.randint(100, 10000)

        # Randomly assign an issue type
        issue_type = random.choice(issue_types)

        # Generate an issue description based on the issue type
        if issue_type == "Suspicious IP connection":
            issue_description = f"Suspicious connection from {source_ip} to {dest_ip}"
        elif issue_type == "Unusual traffic pattern":
            issue_description = f"Unusual traffic pattern detected with {protocol} protocol"
        elif issue_type == "Security event":
            issue_description = f"Potential security event: {source_ip} tried to connect to {dest_port}"
        elif issue_type == "Performance issue":
            issue_description = f"High latency and packet loss between {source_ip} and {dest_ip}"
        elif issue_type == "Configuration problem":
            issue_description = f"Mismatched ports: {source_port} to {dest_port}"
        else:
            issue_description = "Normal network activity"

        # Write the log entry to the CSV file
        writer.writerow({
            'timestamp': timestamp,
            'source_ip': source_ip,
            'dest_ip': dest_ip,
            'protocol': protocol,
            'source_port': source_port,
            'dest_port': dest_port,
            'bytes_transferred': bytes_transferred,
            'issue_type': issue_type,
            'issue_description': issue_description
        })

print(f"Generated {num_entries} synthetic network log entries.")