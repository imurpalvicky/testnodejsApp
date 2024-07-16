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

def query_dynamodb(reponame, eventuuid):
    try:
        # Query the table
        response = table.query(
            KeyConditionExpression=boto3.dynamodb.conditions.Key('reponame').eq(reponame) & 
                                    boto3.dynamodb.conditions.Key('eventuuid').eq(eventuuid)
        )
        return response['Items']
    except Exception as e:
        print(e)
        return None

def write_to_json_file(data, filename='data.json'):
    try:
        # Write data to the file
        with open(filename, 'w') as file:
            json.dump(data, file, indent=4)
    except Exception as e:
        print(e)

# Replace 'your_reponame' and 'your_eventuuid' with actual values
reponame = 'your_reponame'
eventuuid = 'your_eventuuid'

items = query_dynamodb(reponame, eventuuid)

if items:
    write_to_json_file(items, 'output.json')
    print(f"Written {len(items)} items to the JSON file.")
else:
    print("No items found.")