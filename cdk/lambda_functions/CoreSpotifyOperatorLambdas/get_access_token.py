from botocore.exceptions import ClientError
from requests.exceptions import HTTPError
import requests
import base64
import boto3
import json

def handler(event, context) -> dict:
    """
    Fetches an access token from the Spotify `/token/` API. 
    This access token is needed for all future Spotify API calls. 
    """
        
    try:      
        print('Attempting to pull Spotify client credentials from AWS Secrets Manager...')

        # Create a Secrets Manager client
        ssm = boto3.client('secretsmanager')
        
        response = ssm.get_secret_value(
            SecretId='SpotifySecrets'
        )
    except ClientError as err:
        print(f'Client Error Message: {err.response["Error"]["Message"]}')
        print(f'Client Error Code: {err.response["Error"]["Code"]}')
        raise
    except Exception as err:
        print(f'Other Error Occurred: {err}')
        raise
    else: 
        print('Successfully retrieved Spotify client credentials from AWS Secrets Manager')
        
        # Extract client creds from returned payload
        client_creds = json.loads(response['SecretString'])
        client_id = client_creds['SPOTIFY_CLIENT_ID']
        client_secret = client_creds['SPOTIFY_CLIENT_SECRET']
        
        # Request access token
        access_token = request_token(client_id, client_secret)
        
        return {
            'access_token': access_token
        }

def request_token(client_id: str, client_secret: str) -> str:
    """
    Sends POST request to Spotify Token API to get an access token
    """    
    
    client_creds: str = f'{client_id}:{client_secret}'
    endpoint: str = 'https://accounts.spotify.com/api/token'
    
    try:
        print("Initiating POST request for Access Token...")
        
        response = requests.post(
            url=endpoint, 
            headers={
                # Encode the client credentials to base64
                'Authorization': f'Basic {base64.b64encode(client_creds.encode()).decode()}',
                'Content-Type': 'application/x-www-form-urlencoded'
            }, 
            data={
                'grant_type': 'client_credentials'
            }
        )
        
        # Catch any HTTP errors
        response.raise_for_status()
    except HTTPError as err:
        print(f'HTTP Error occurred: {err}')
        raise
    except Exception as err:
        print(f'Other error occurred: {err}')
        raise
    else:
        print(f'Successfully received response from Spotify Token API. HTTP Status code: {response.status_code}')
        print(f'Returned Payload: {response.json()}')

        # Check if error occurred while attempting to retrieve access token. If not, return token
        if response.json().get('error'):
            print(f'Unsuccessful response from Spotify Token API. Error: {response.json()["error"]}')
            raise Exception(f'Error: {response.json()["error"]}')
        else:
            return response.json()['access_token']

