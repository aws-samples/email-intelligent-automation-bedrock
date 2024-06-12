import boto3
import os
import time
from botocore.exceptions import ClientError


client = boto3.client('workmail')

def handler(event, context):
  org_name = os.environ['work_org_name']
  user_name = os.environ['user_name']
  user_password = os.environ['password']
  
  request_type = event['RequestType']
  if request_type == 'Create': 
      return on_create(event, org_name, user_name, user_password)
  if request_type == 'Update': 
      return on_update(event, context)
  if request_type == 'Delete': 
      return on_delete(event, context)
  raise Exception("Invalid request type: %s" % request_type)

def on_create(event, org_name, user_name, user_password):
    props = event["ResourceProperties"]
    print("create new resource with props %s" % props)

    try:
        # Create the WorkMail organization
        workmail_response = client.create_organization(Alias=org_name)
        org_id = workmail_response["OrganizationId"]
        print(f"Created WorkMail organization with ID: {org_id}")

        # Wait for the organization to become active
        _wait_for_organization_state(org_id, "Active")

        # Try to create the WorkMail user
        try:
            print("creating user")
            user_response = client.create_user(
                OrganizationId=org_id,
                Name=user_name,
                DisplayName=user_name,
                Password=user_password
            )
            user_id = user_response["UserId"]
            print(f"Created WorkMail user with ID: {user_id}")
        except client.exceptions.NameAvailabilityException:
            # User already exists, get the existing user ID
            user_details = client.list_users(OrganizationId=org_id, MaxResults=1)
            print(f"User {user_name} already exists with ID: {user_id}")

        # Register the user to the WorkMail organization
        print("register user to workmail org")
        register_response = client.register_to_work_mail(
            OrganizationId=org_id,
            EntityId=user_id,
            Email=f"{user_name}@{org_name}.awsapps.com"
        )
        print(f"Registered user to WorkMail organization: {register_response}")

        # Set the physical resource ID to the organization ID and user ID
        physical_resource_id = f"{org_id}/{user_id}"

        response = {"PhysicalResourceId": physical_resource_id}
        return response

    except ClientError as e:
        print(f"Error creating WorkMail organization or user: {e}")
        raise

def _wait_for_organization_state(org_id, desired_state):
    print ("Checking weather Org is Active")
    while True:
        org_details = client.describe_organization(OrganizationId=org_id)
        current_state = org_details["State"]
        print("Current State is "+ current_state)
        if current_state == desired_state:
            break
        time.sleep(5)
    #time.sleep(60)

def on_update(event, context):
    physical_id = event["PhysicalResourceId"]
    props = event["ResourceProperties"]
    print(f"Updating resource with PhysicalResourceId: {physical_id} and props: {props}")

    # There's nothing to update for this custom resource
    # since the organization and user are immutable
    return {
        "PhysicalResourceId": physical_id
    }

def on_delete(event, context):
    physical_id = event["PhysicalResourceId"]
    print(f"Deleting resource with PhysicalResourceId: {physical_id}")

    try:
        # Extract the organization ID and user ID from the physical resource ID
        org_id, user_id = physical_id.split("/")

        # Deregister the user from the WorkMail organization
        client.deregister_from_work_mail(
            OrganizationId=org_id,
            EntityId=user_id
        )
        print(f"Deregistered user with ID {user_id} from WorkMail organization {org_id}")

        # Delete the user
        client.delete_user(
            OrganizationId=org_id,
            UserId=user_id
        )
        print(f"Deleted user with ID {user_id} from WorkMail organization {org_id}")

        # Delete the organization
        client.delete_organization(
            OrganizationId=org_id,
            DeleteDirectory=True  # Assuming you want to delete the associated directory
        )
        print(f"Deleted WorkMail organization with ID {org_id}")

    except ClientError as e:
        print(f"Error deleting WorkMail organization or user: {e}")
        raise

    return {
        "PhysicalResourceId": physical_id
    }