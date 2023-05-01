from exceptions.error_handling import FailedToRetrieveToken
from ui.colors import Colors, print_colors, colorfy
from botocore.exceptions import ClientError
import boto3
import sys
import json

# Local memory storage of the current artists I am monitoring
ARTIST_CACHE: list[dict] = []

def request_token() -> str:
    """
    Invoke Lambda function that sends a POST request to Spotify `Token` 
    API to get an access token. Then returns it back to the CLI client
    """    
    
    lambda_name = 'GetAccessTokenHandler'
    
    try:
        lambda_ = boto3.client('lambda')
        response: dict = lambda_.invoke(
            FunctionName=lambda_name,
            InvocationType='RequestResponse'
        )
    except ClientError as err:
        print(f'\nClient Error Message: \n\t{err.response["Error"]["Message"]}')
        print(f'Client Error Code: \n\t{err.response["Error"]["Code"]}')
        sys.exit()
    except Exception as err:
        print(f'\n\tOther error occurred: \n\t{err}')
    else:
        
        # Convert botocore.response.StreamingBody object to dict
        returned_json: dict = json.load(response['Payload'])
        
        # Raise exception if payload is None, otherwise return access token
        if returned_json['payload']['access_token'] is not None:
            return returned_json['payload']['access_token']
        else:
            raise FailedToRetrieveToken
        
    return ''


def list_artists(continue_prompt=False) -> None:
    """
    Prints out a list of the current artists that are being monitored
    """

    global ARTIST_CACHE
    lambda_name = 'GetArtistsHandler'

    # Use cached list of artists, otherwise, invoke lambda to get fresh data
    if len(ARTIST_CACHE) > 0:
        for i in range(len(ARTIST_CACHE)):
            current_iteration_num = str(i + 1)
            print(f'\n\t[{colorfy(Colors.LIGHT_GREEN, current_iteration_num)}] {ARTIST_CACHE[i]["artist_name"]}')
    else: 
        try:
            lambda_ = boto3.client('lambda')
            response = lambda_.invoke(
                FunctionName=lambda_name,
                InvocationType='RequestResponse'
            )    
        except ClientError as err:
            print(f'\nClient Error Message: \n\t{err.response["Error"]["Message"]}')
            print(f'Client Error Code: \n\t{err.response["Error"]["Code"]}')
            sys.exit()
        except Exception as err:
            print(f'\n\tOther error occurred: \n\t{err}')
        else:

            # Convert botocore.response.StreamingBody object to dict
            returned_payload: dict = json.load(response['Payload'])
            
            print('\nCurrent monitored artists:')
            list_of_names: list[str] = returned_payload['payload']['artists']['current_artists_names']
            for i in range(len(list_of_names)):
                current_iteration_num = str(i + 1)
                print(f'\n\t[{colorfy(Colors.LIGHT_GREEN, current_iteration_num)}] {list_of_names[i]}')

            # Update cache with current artists 
            ARTIST_CACHE = returned_payload['payload']['artists']['current_artists_with_id']

    menu_loop_prompt(continue_prompt)


def fetch_artist_id(artist_name: str, access_token: str) -> tuple[str, str]:
    """
    Queries the Spotify `Search` API for the artist's Spotify ID. 
    Returns a tuple of the artist's Spotify ID and name. 
    """

    lambda_name = 'GetArtist-IDHandler'
    payload = json.dumps({
        'artist_name': artist_name,
        'access_token': access_token    
    })
    
    try:
        lambda_ = boto3.client('lambda')
        response = lambda_.invoke(
            FunctionName=lambda_name,
            InvocationType='RequestResponse',
            Payload=payload.encode()
        )    
    except ClientError as err:
        print(f'\nClient Error Message: \n\t{err.response["Error"]["Message"]}')
        print(f'Client Error Code: \n\t{err.response["Error"]["Code"]}')
        sys.exit()
    except Exception as err:
        print(f'\n\tOther error occurred: \n\t{err}')
    else:
        
        # Convert botocore.response.StreamingBody object to dict
        returned_payload: dict = json.load(response['Payload'])
        results = returned_payload['payload']

        # Give user the most likely artist they were looking for 
        first_artist_guess = results['firstArtistGuess']

        # Fetch user choice. Check to make sure it is a proper selection
        while True:
            try:
                answer = input(f'\nIs {colorfy(Colors.LIGHT_GREEN, first_artist_guess["artist_name"])} the artist you were looking for? (`y` for yes or `n` for no)\n> ')
                if 'y' in answer.lower() and len(answer) <= 3:
                    return first_artist_guess["artist_id"], first_artist_guess["artist_name"]
                elif 'n' in answer.lower() and len(answer) <=4:

                    # Give them a list of the other most likely choices and have them choose
                    for i in range(len(results['artistSearchResultsList'])):
                        current_iteration_str = str(i + 1)
                        print(f'\n[{colorfy(Colors.LIGHT_GREEN, current_iteration_str)}]')
                        print(f'\tArtist: {results["artistSearchResultsList"][i]["name"]}')
                        
                    # Prompt user for artist choice again
                    user_choice = input(f'\nWhich artist were you looking for? Select the number.\n> ')
                    
                    # Return selected artist's Spotify ID and name
                    for i in range(len(results['artistSearchResultsList'])):
                        if int(user_choice) == i + 1:
                            return results['artistSearchResultsList'][i]['id'], results['artistSearchResultsList'][i]['name']      
                else:
                    raise ValueError
            except ValueError:
                print_colors(Colors.YELLOW, '\n\tPlease enter a valid selection.')

    return '', ''


def add_artist(access_token: str, continue_prompt=False) -> None:
    """
    Prompts user for which artist they want to add to be monitored. 
    Then invokes a lambda function that performs a PUT request against a DynamoDB table.
    """
    
    global ARTIST_CACHE

    while True:
        
        # Ask user for which artist they want to search for 
        list_artists()
        user_artist_choice = input("\nWhich artist would you like to add to your monitor list?\n> ")

        # Queries the Spotify Search API for the artist ID.
        artist_id, artist_name = fetch_artist_id(user_artist_choice, access_token)
        artist = {'artist_id': artist_id, 'artist_name': artist_name}
        
        # Find out if artist is already in list. If not, add the artist
        if artist in ARTIST_CACHE:
            print(f'\nYou\'re already monitoring {colorfy(Colors.LIGHT_GREEN, artist_name)}!')
        else:
            lambda_name = 'AddArtistsHandler'
            payload = json.dumps({
                'artist_id': artist_id,
                'artist_name': artist_name  
            })
            
            try:
                lambda_ = boto3.client('lambda')
                response = lambda_.invoke(
                    FunctionName=lambda_name,
                    InvocationType='RequestResponse',
                    Payload=payload.encode()
                )    
            except ClientError as err:
                print(f'\nClient Error Message: \n\t{err.response["Error"]["Message"]}')
                print(f'Client Error Code: \n\t{err.response["Error"]["Code"]}')
                sys.exit()
            except Exception as err:
                print(f'\n\tOther error occurred: \n\t{err}')
            else:

                # Convert botocore.response.StreamingBody object to dict
                returned_payload: dict = json.load(response['Payload'])

                if returned_payload['statusCode'] != 200:
                    print('Something went wrong. Please try again.')
                    break
                else: 
                    
                    # Update cache with new addition
                    ARTIST_CACHE.append(artist)
                
                    print(f'\n\tYou are now monitoring for {colorfy(Colors.LIGHT_GREEN, artist_name)}\'s new music!')
                    break
                
    menu_loop_prompt(continue_prompt)


def remove_artist(continue_prompt=False) -> None:
    """
    Removes an artist from the monitored list
    """
    
    global ARTIST_CACHE

    # Ask which artist the user would like to remove
    list_artists()
    while True:
        try:
            choice = int((input("\nWhich artist would you like to remove? Make a selection:\n> ")))
            if choice in list(range(1, len(ARTIST_CACHE) + 1)):
                break
            else:
                raise ValueError
        except ValueError:
            print_colors(Colors.YELLOW, "\n\tPlease enter a valid selection.")

    # Invoke a lambda function that performs a DELETE request against a DynamoDB table.
    lambda_name = 'RemoveArtistsHandler'
    payload = json.dumps({
        'artist_id': ARTIST_CACHE[choice - 1]['artist_id'],
        'artist_name': ARTIST_CACHE[choice - 1]['artist_name']
    })

    try:
        lambda_ = boto3.client('lambda')
        response = lambda_.invoke(
            FunctionName=lambda_name,
            InvocationType='RequestResponse',
            Payload=payload.encode()
            )
    except ClientError as err:
                print(f'\nClient Error Message: \n\t{err.response["Error"]["Message"]}')
                print(f'Client Error Code: \n\t{err.response["Error"]["Code"]}')
                sys.exit()
    except Exception as err:
        print(f'\n\tOther error occurred: \n\t{err}')
    else:
        
        # Convert botocore.response.StreamingBody object to dict
        returned_payload: dict = json.load(response['Payload'])
        
        if returned_payload['statusCode'] != 200:
            print('Something went wrong. Please try again.')
        else:
            
            # Update cache by removing artist
            print(f"\n\tRemoved {colorfy(Colors.LIGHT_GREEN, ARTIST_CACHE[choice - 1]['artist_name'])} from list!")
            ARTIST_CACHE.pop(choice - 1)
            
    menu_loop_prompt(continue_prompt)


def quit() -> None:
    """
    Quits the application.
    """
    
    print(f"\n\t{colorfy(Colors.RED, 'Quitting App!')}")
    sys.exit()


def menu_loop_prompt(continue_prompt: bool) -> None:
    """
    If True is passed in, user will be prompted to press ENTER to get back to main menu
    """
    
    if continue_prompt:
        choice = input(f"\nPress {colorfy(Colors.LIGHT_GREEN, '[ENTER]')} to go back to main menu... (Or {colorfy(Colors.YELLOW, 'q')} to quit app)\n> ")
        if choice.lower() == 'q':
            quit() 