import json
import boto3
from botocore.exceptions import ClientError

def get_transfer_status(parameters):
    # Create a DynamoDB client
    dynamodb = boto3.client('dynamodb')
    
    for parameter in parameters:
        transfer_id = parameter.get("value", None)

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

def lambda_handler(event, context):
    action = event['actionGroup']
    api_path = event['apiPath']

    if api_path == '/transferStatus/{transferID}':
        parameters = event['parameters']
        body = get_transfer_status(parameters)
    else:
        body = {"{}::{} is not a valid api, try another one.".format(action, api_path)}

    response_body = {
        'application/json': {
            'body': str(body)
        }
    }

    action_response = {
        'actionGroup': event['actionGroup'],
        'apiPath': event['apiPath'],
        'httpMethod': event['httpMethod'],
        'httpStatusCode': 200,
        'responseBody': response_body
        }

    response = {'response': action_response}
    return response