import os
import boto3
import random
import string

table_name = os.environ['TABLE_NAME']

print(table_name)

def lambda_handler(event, context):
    # Create a DynamoDB client
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(table_name)
    
        # Define transfer status values
    transfer_statuses = ["Pending", "InProgress", "Cancelled", "Sent"]

    # Populate the table with 10 records
    for i in range(50):
        transfer_id = f"MTN{''.join(random.choices(string.digits, k=7))}"
        transfer_status = random.choice(transfer_statuses)
        #table.put_item(item={"transferID": transfer_id, "transferStatus": transfer_status})
        item = {"transferID": transfer_id, "transferStatus": transfer_status}
        table.put_item(Item=item)
        print(f"Inserted item: {item}")

    return {
        'statusCode': 200,
        'body': 'Data uploaded successfully!'
    }