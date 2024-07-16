import boto3
import json

# Initialize a session using Amazon DynamoDB
session = boto3.Session(
    aws_access_key_id='YOUR_ACCESS_KEY',
    aws_secret_access_key='YOUR_SECRET_KEY',
    region_name='YOUR_REGION'
)

# Initialize DynamoDB resource
dynamodb = session.resource('dynamodb')

# Specify the table
table = dynamodb.Table('YourTableName')

def query_dynamodb(reponame, eventuuid_prefix, eventtype):
    try:
        # Query the table with conditions on reponame and eventuuid, and filter on eventtype
        response = table.query(
            KeyConditionExpression=boto3.dynamodb.conditions.Key('reponame').eq(reponame) & 
                                    boto3.dynamodb.conditions.Key('eventuuid').begins_with(eventuuid_prefix),
            FilterExpression=boto3.dynamodb.conditions.Attr('eventtype').eq(eventtype)
        )
        return response['Items']
    except Exception as e:
        print(e)
        return None

def convert_set_to_list(data):
    if isinstance(data, list):
        return [convert_set_to_list(item) for item in data]
    elif isinstance(data, dict):
        return {key: convert_set_to_list(value) for key, value in data.items()}
    elif isinstance(data, set):
        return list(data)
    else:
        return data

def write_to_json_file(data, filename='data.json'):
    try:
        # Convert sets to lists
        data = convert_set_to_list(data)
        # Write data to the file
        with open(filename, 'w') as file:
            json.dump(data, file, indent=4)
    except Exception as e:
        print(e)

# Replace 'your_reponame', 'your_eventuuid_prefix', and 'your_eventtype' with actual values
reponame = 'your_reponame'
eventuuid_prefix = 'your_eventuuid_prefix'
eventtype = 'your_eventtype'

items = query_dynamodb(reponame, eventuuid_prefix, eventtype)

if items:
    write_to_json_file(items, 'output.json')
    print(f"Written {len(items)} items to the JSON file.")
else:
    print("No items found.")