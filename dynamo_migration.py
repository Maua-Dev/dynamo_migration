import boto3
from botocore.exceptions import ClientError
import os
import sys

AWS_SOURCE_REGION = os.environ.get('AWS_SOURCE_REGION')
AWS_DESTINATION_REGION = os.environ.get('AWS_DESTINATION_REGION')
SOURCE_TABLE = os.environ.get('SOURCE_TABLE')
DESTINATION_TABLE = os.environ.get('DESTINATION_TABLE')
SOURCE_ROLE_ARN = os.environ.get('SOURCE_ROLE_ARN') 

def main():
    
    if not all([AWS_SOURCE_REGION, AWS_DESTINATION_REGION, SOURCE_TABLE, DESTINATION_TABLE, SOURCE_ROLE_ARN]):
        print("Error: One or more environment variables are not set.")
        sys.exit(1)

    sts_client = boto3.client('sts')
    try:
        response = sts_client.assume_role(
            RoleArn=SOURCE_ROLE_ARN,
            RoleSessionName="GitHubActions-DynamoMigration"
        )
        credentials = response['Credentials']
        print(f"Successfully assumed role {SOURCE_ROLE_ARN} in the source account.")
        
        source_dynamodb = boto3.resource(
            'dynamodb',
            aws_access_key_id=credentials['AccessKeyId'],
            aws_secret_access_key=credentials['SecretAccessKey'],
            aws_session_token=credentials['SessionToken'],
            region_name=AWS_SOURCE_REGION
        )
    except ClientError as e:
        print(f"Fatal error assuming source role: {e}")
        sys.exit(1)
    
    destination_dynamodb = boto3.resource('dynamodb', region_name=AWS_DESTINATION_REGION)
    
    source_table_obj = source_dynamodb.Table(SOURCE_TABLE)
    destination_table_obj = destination_dynamodb.Table(DESTINATION_TABLE)
    
    print(f"Starting migration from table '{SOURCE_TABLE}' to '{DESTINATION_TABLE}'...")
    
   
    paginator = source_dynamodb.meta.client.get_paginator('scan')
    processed_items = 0
    try:

        with destination_table_obj.batch_writer() as batch:
            for page in paginator.paginate(TableName=SOURCE_TABLE):
                for item in page.get('Items', []):
                    batch.put_item(Item=item)
                    processed_items += 1
                    if processed_items % 200 == 0:
                        print(f"{processed_items} items processed...")
    except ClientError as e:
        print(f"Error during the DynamoDB write operation: {e}")
        sys.exit(1)

    print(f"\nMigration complete! Total of {processed_items} items transferred.")

if __name__ == '__main__':
    main()