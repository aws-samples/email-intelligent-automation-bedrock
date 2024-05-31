import json
import boto3
from botocore.exceptions import ClientError
event ='123'
context = 'abc'

def get_status(event, context):
    # Get the transfer ID from the event payload
    #transfer_id = event['payload']['transferID']
    #print(event)
    transfer_id = 'MTN0000123'
    # Create a DynamoDB client
    dynamodb = boto3.client('dynamodb')

    try:
        # Query the moneyTransferStatus table with the transfer ID
        response = dynamodb.query(
            TableName='moneyTransferStatus',
            KeyConditionExpression='transferID = :transfer_id',
            ExpressionAttributeValues={
                ':transfer_id': {'S': transfer_id}
            }
        )

        # Check if the query returned any items
        if 'Items' in response and len(response['Items']) > 0:
            item = response['Items'][0]
            transfer_status = item['transferStatus']['S']
            return {
                'status': 'success',
                'transferStatus': transfer_status
            }
        else:
            return {
                'status': 'error',
                'message': 'Transfer not found'
            }

    except ClientError as e:
        error_message = e.response['Error']['Message']
        return {
            'status': 'error',
            'message': error_message
        }
status = get_status(event,context)
print (status)