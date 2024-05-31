import boto3
import os
from botocore.exceptions import ClientError


client = boto3.client('workmail')

def handler(event, context):
  print(event)
  org_name = os.environ['work_org_name']
  user_name = os.environ['user_name']
  
  request_type = event['RequestType']
  if request_type == 'Create': return on_create(event, org_name)
  if request_type == 'Update': return on_update(event)
  if request_type == 'Delete': return on_delete(event,user_name,org_name)
  raise Exception("Invalid request type: %s" % request_type)

def on_create(event,orgName):
    props = event["ResourceProperties"]
    print("create new resource with props %s" % props)
    # call workmail organization api
    try:
        workmail_response = client.create_organization(
        Alias = orgName
        )
        print (workmail_response)
        response = {'PhysicalResourceId' : workmail_response['OrganizationId']}
        return response
    except ClientError as q:
        print("Error while creating the organization: %s" % q)


def on_update(event):
    physical_id = event["PhysicalResourceId"]
    props = event["ResourceProperties"]
    request_type = event["RequestType"]
    print("Nothing to do as an update event : update resource %s with props %s" %
        (physical_id, props))
    response = {
      'PhysicalResourceId': physical_id
    }
    return response

def on_delete(event,user_name,org_name):
    physical_id = event["PhysicalResourceId"]
    print("delete resource %s" % physical_id)
    
    list_orgs = client.list_organizations()
    for orgs in list_orgs['OrganizationSummaries']:
        if orgs['Alias'] == org_name:
           org_id = orgs['OrganizationId']
    
    user_avail = client.list_users(
                            OrganizationId=org_id
                                            )
    for x in user_avail['Users']:
        print('start deleting users')
        if x['Name'] == user_name:
            del_dereg_from_workmail(org_id,x['Id'])
            response = {
                        'PhysicalResourceId' : physical_id,
                        'OrganizationID' : org_id
                            }        
    try:
        del_org_response = client.delete_organization(
                    OrganizationId=org_id,
                    DeleteDirectory=True
                    )
        print(del_org_response)
        response = {
                        'PhysicalResourceId' : physical_id,
                        'OrganizationID' : org_id
                    }
        return response
    except ClientError as m:
                print("Error while deleting the organization: %s" % m)
                raise m
                
            
def del_dereg_from_workmail(org_id,ent_id):
    try:
        dereg_response = client.deregister_from_work_mail(
                        OrganizationId=org_id,
                        EntityId=ent_id
                                )
        print(dereg_response)               
    except ClientError as k:
        print("Error while deregistering the users: %s" % k)
        raise k
    
    try:
        del_user_response = client.delete_user(
                                OrganizationId=org_id,
                                UserId=ent_id
                                )
        print(del_user_response)
    except ClientError as l:
            print("Error while deleting the users: %s" % l)
            raise l



# the workmail user creation and assign user to workmail domain has depndancies on below resources
# organization and domain - both should be in active state

def is_complete(event, context):
    org_name = os.environ['work_org_name']
    user_name = os.environ['user_name']
    password = os.environ['password']
    physical_id = event["PhysicalResourceId"]
    request_type = event["RequestType"]

    if request_type == 'Create':
    # check if resource is stable based on request_type
        is_response = client.list_organizations()
        #print(is_response)
        is_ready = False
        for i in is_response['OrganizationSummaries']:
            #checking the status of the organization created
            if i['State'] == "Active" and i['Alias'] == org_name:
                print ('user getting created.....')
                #if yes creating the user and registering the user is done. if not goes to exception block
                try:
                    user_response = client.create_user(
                                        OrganizationId=i['OrganizationId'],
                                        Name=user_name,
                                        DisplayName=user_name,
                                        Password=password)
                    print(user_response)
                    reg_user_response = client.register_to_work_mail(
                                        OrganizationId=i['OrganizationId'],
                                        EntityId=user_response['UserId'],
                                        Email=user_name+'@'+org_name+'.awsapps.com')
                    print(reg_user_response)
                    is_ready = True
                except ClientError as e:
                    print(e.response)
                    # if the error is NameAvailabilityException, it will go for user registeration for email
                    if e.response['Error']['Code'] == 'NameAvailabilityException':
                        print("User already exists..registering user to the domain")
                        try:
                            user_avail = client.list_users(
                                                OrganizationId=i['OrganizationId'],
                                                MaxResults=1
                                                )
                            for x in user_avail['Users']:
                                print('start registering users')
                                if x['Name'] == user_name:
                                    print(x['Id'])
                                    try:    
                                        reg_user_response = client.register_to_work_mail(
                                                    OrganizationId=i['OrganizationId'],
                                                    EntityId=x['Id'],
                                                    Email=user_name+'@'+org_name+'.awsapps.com')
                                        is_ready = True
                                        print (reg_user_response)
                                    except ClientError as g:
                                        print(g.response)
                                        if g.response['Error']['Code'] == 'MailDomainStateException':
                                            print('Domain is still getting created..please wait')
                                            is_ready = False
                                        else:                                       
                                            print("Unexpected error: %s" % g) 
                                            #is_ready = True 
                                            raise g
                        except ClientError as f:
                            print(f.response)
                            # if the error is NameAvailabilityException (means user already exist) and should go to user registration
                            if f.response['Error']['Code'] == 'NameAvailabilityException':
                                is_ready = False
                                print ('Domain is still getting created..please wait')
                            else:
                                print("Unexpected error on listing users: %s" % f)
                                #is_ready = True
                                raise f
                    elif e.response['Error']['Code'] == 'MailDomainStateException':
                        print('Domain is still getting created..please wait')
                        is_ready = False
                    else:
                        print("Unexpected error: %s" % e)     
                        #is_ready = True
                        raise e
        return { 'IsComplete': is_ready }
    elif request_type == 'Delete':
        is_ready = True
        return { 'IsComplete': is_ready }