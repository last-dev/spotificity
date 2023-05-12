from botocore.exceptions import ClientError
import boto3
import os

def handler(event, context) -> dict:
    """
    Updates artist table with the latest music released by all of the artists being monitored.
    If there are any changes in the music, craft a list of all artists with changes and return it.
    If there are no changes, return an empty list.
    """
    
    print(f'Passed in event: {event}')
    artists_with_changes: list = []
    
    # Create a DynamoDB client
    ddb = boto3.client('dynamodb')
    table = os.getenv('ARTIST_TABLE_NAME')
    
    print('Initiating iteration through artists to update the music table...')
    for artist in event:
        artist_id: str = artist['artist_id']
        artist_name: str = artist['artist_name']
        last_album_details: dict = artist['last_album_details']
        last_single_details: dict = artist['last_single_details']

        # Update DynamoDB with latest musical releases
        try:
            print(f'Initiating PUT request to update {table} with {artist_name}\'s latest releases...')
            
            # Convert the last_album_details and last_single_details to DynamoDB format
            converted_last_album_details: dict = {
                'M': {
                    'last_album_name': {
                        'S': last_album_details['last_album_name']
                    },
                    'last_album_release_date': {
                        'S': last_album_details['last_album_release_date']
                    },
                    'last_album_artists': {
                        'L': [{'S': artist} for artist in last_album_details['last_album_artists']]
                    }
                }
            }
            converted_last_single_details: dict = {
                'M': {
                    'last_single_name': {
                        'S': last_single_details['last_single_name']
                    },
                    'last_single_release_date': {
                        'S': last_single_details['last_single_release_date']
                    },
                    'last_single_artists': {
                        'L': [{'S': artist} for artist in last_single_details['last_single_artists']]
                    }
                }
            }
            
            response = ddb.update_item(
                TableName=table,
                Key={
                    'artist_id': {
                        'S': artist_id
                    }       
                },
                UpdateExpression='SET last_album_details = :last_album_details, last_single_details = :last_single_details',
                ExpressionAttributeValues={
                    ':last_album_details': converted_last_album_details,
                    ':last_single_details': converted_last_single_details
                },
                ReturnConsumedCapacity='TOTAL',
                ReturnValues='UPDATED_OLD'
            )
        except ClientError as err:
            print(f'Client Error Message: {err.response["Error"]["Message"]}')
            print(f'Client Error Code: {err.response["Error"]["Code"]}')
            raise
        except Exception as err:
            print(f'Other Error Occurred: {err}')
            raise
        else:
            print(f'PUT request successful. {artist_name}\'s latest releases have been updated in {table}.')
            
            # Check if there are any changes in the music. If so, add artist to list of artists with changes.
            print('Checking if there are any changes in the music...')
            if response['Attributes']['last_album_details']['M']['last_album_name']['S'] != converted_last_album_details['M']['last_album_name']['S']:
                print(f'{artist_name} dropped a new album! Adding {artist_name} to list of artists with changes...')
                artists_with_changes.append({
                    'artist_name': artist_name,
                    'last_album_details': last_album_details,
                })
            elif response['Attributes']['last_single_details']['M']['last_single_name']['S'] != converted_last_single_details['M']['last_single_name']['S']:
                print(f'{artist_name} dropped a new single! Adding {artist_name} to list of artists with changes...')
                artists_with_changes.append({
                    'artist_name': artist_name,
                    'last_single_details': last_single_details
                })
            else:
                print(f'No changes in {artist_name}\'s music.')
            
        
    if len(artists_with_changes) == 0:
        print('No changes in music from all artists. Returning empty list...')
        return {
            'new_music': artists_with_changes
        }
    else:
        print('There were some changes in music! Returning list of artists with the updates...')
        return {
            'new_music': artists_with_changes
        }