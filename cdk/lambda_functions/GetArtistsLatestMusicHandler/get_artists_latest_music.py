from requests.exceptions import HTTPError
from botocore.exceptions import ClientError
import requests
import boto3
import json
import os

def handler(event: dict, context) -> dict:
    """
    Queries a couple of Spotify's APIs to return back the latest musical releases
    for the artist.
    """
    
    # If access token is passed in, use it. Otherwise, invoke Lambda that will return one.
    if not event['access_token']:
        access_token = request_token()
    else: 
        access_token: str = event['access_token']
    
    artist_id: str = event['artist_id']
    artist_name: str = event['artist_name']
    
    last_album_details = get_latest_album(artist_id, artist_name, access_token)
    last_single_details = get_latest_single(artist_id, artist_name, access_token)
    latest_tracks_featured_on_details = get_latest_tracks_artist_featured_on(artist_id, access_token)
    
    return {
        'status': 200,
        'payload': {
            'last_album_details': last_album_details,
            'last_single_details': last_single_details,
            'latest_tracks_featured_on_details': latest_tracks_featured_on_details
        }
    }
    
def request_token() -> str:
    """
    Invoke Lambda function that sends a POST request to Spotify `Token` 
    API to get an access token. 
    """    
    
    lambda_name = os.getenv('GET_ACCESS_TOKEN_LAMBDA')
    
    try:
        lambda_ = boto3.client('lambda')
        response: dict = lambda_.invoke(
            FunctionName=lambda_name,
            InvocationType='RequestResponse'
        )
    except ClientError as err:
        print(f'\nClient Error Message: \n\t{err.response["Error"]["Message"]}')
        print(f'Client Error Code: \n\t{err.response["Error"]["Code"]}')
    except Exception as err:
        print(f'\n\tOther error occurred: \n\t{err}')
    else:
        
        # Convert botocore.response.StreamingBody object to dict
        returned_json: dict = json.load(response['Payload'])
        
        return returned_json['payload']['access_token']

        
    return ''
        
def get_latest_album(artist_id: str, artist_name: str, access_token: str) -> dict:
    """
    Queries the Spotify API to return the last album released by the
    artist.
    """
    
    endpoint: str = f'https://api.spotify.com/v1/artists/{artist_id}/albums'
    
    try:
        print(f'Initiating GET request for the {artist_name}\'s last album...')
        
        response = requests.get(
            url=endpoint,
            params={
                'limit': 1,
                'offset': 0,
                'include_groups': 'album',
                'market': 'US'
            },
            headers={
                'Authorization': f'Bearer {access_token}'
            }
        )
        
        # Catch any HTTP errors
        response.raise_for_status()
    except HTTPError as err:
        print(f'HTTP Error occurred: {err}')
    except Exception as err:
        print(f'Other error occurred: {err}')
    else:
        print('Parsing JSON...')
        
        album_search_results: dict = response.json()
        
        # Extract out the last album's details
        last_album: dict = album_search_results['items'][0]
        last_album_artists: list[str] = [artist['name'] for artist in last_album['artists']]
        
        return {
            'last_album_name': last_album['name'],
            'last_album_release_date': last_album['release_date'],
            'last_album_artists': last_album_artists
        }
    
    return {}

def get_latest_single(artist_id: str, artist_name: str, access_token: str) -> dict:
    """
    Queries the Spotify API to return the last single released by the
    artist.
    """
    
    endpoint: str = f'https://api.spotify.com/v1/artists/{artist_id}/albums'
    
    try:
        print(f'Initiating GET request for the {artist_name}\'s last single...')
        
        response = requests.get(
            url=endpoint,
            params={
                'limit': 1,
                'offset': 0,
                'include_groups': 'single',
                'market': 'US'
            },
            headers={
                'Authorization': f'Bearer {access_token}'
            }
        )
        
        # Catch any HTTP errors
        response.raise_for_status()
    except HTTPError as err:
        print(f'HTTP Error occurred: {err}')
    except Exception as err:
        print(f'Other error occurred: {err}')
    else:
        print('Parsing JSON...')
        
        # Extract out the last single's details
        last_single: dict = response.json()['items'][0]
        last_single_artists: list[str] = [artist['name'] for artist in last_single['artists']]
        
        return {
            'last_single_name': last_single['name'],
            'last_single_release_date': last_single['release_date'],
            'last_single_artists': last_single_artists
        }
        
    return {}

def get_latest_tracks_artist_featured_on(artist_name: str, access_token: str) -> dict:
    """
    Queries the Spotify API to return the last track the artist was 
    featured on
    """
    
    endpoint: str = 'https://api.spotify.com/v1/search'
    
    try:
        print(f'Initiating GET request for the last track {artist_name} was featured on...')
        
        response = requests.get(
            url=endpoint,
            params={
                'q': f'artist:{artist_name}',
                'type': 'track',
                'limit': 20,
                'offset': 0,
                'market': 'US'
            },
            headers={
                'Authorization': f'Bearer {access_token}'
            }
        )
        
        # Catch any HTTP errors
        response.raise_for_status()
    except HTTPError as err:
        print(f'HTTP Error occurred: {err}')
    except Exception as err:
        print(f'Other error occurred: {err}')
    else:
        print('Parsing JSON...')
        
        # Extract out the last couple track's featured on details
        # First sort results by release date
        latest_tracks_list: list = response.json()['tracks']['items']
        sorted_results = sorted(latest_tracks_list[track]['release_date'] for track in latest_tracks_list)
        
        return {
            'last_2_featured_tracks': sorted_results[:2],
        }
                
    return {}