"""
Custom construct for core resources that will interact with
the Spotify API. 
"""

from constructs import Construct
from aws_cdk import (
    aws_lambda as lambda_,
    aws_lambda_event_sources as lambda_event_sources,
    aws_secretsmanager as ssm, 
    aws_dynamodb as ddb,
    Fn
)

class CoreSpotifyOperatorsConstruct(Construct):
    def __init__(self, scope: Construct, id: str, 
                 artist_table_arn: str, 
                 artist_table_stream_arn: str, 
                 update_table_music_lambda: lambda_.Function, 
                 **kwargs) -> None:
        super().__init__(scope, id, **kwargs)
        
        # Lambda layer that bundles `requests` module 
        _requests_layer = lambda_.LayerVersion(
            self, 'RequestsLayer',
            code=lambda_.Code.from_asset('lambda_layers/requests_v2-28-2.zip'),
            layer_version_name='Requests_v2-28-2',
            description='Bundles the "requests" module.',
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_10]
        )
        
        # Spotify access token 'getter' Lambda Function
        _get_access_token_lambda = lambda_.Function(
            self, 'GetAccessToken',
            runtime=lambda_.Runtime.PYTHON_3_10,
            code=lambda_.Code.from_asset('lambda_functions/GetAccessTokenHandler'),
            handler='get_access_token.handler',
            function_name='GetAccessTokenHandler',
            description=f'Calls Spotify\'s "/token/" API endpoint to get an access token.',
            layers=[_requests_layer]
        )
        
        # Spotify artist_id 'getter' Lambda Function
        _get_artist_id_lambda = lambda_.Function(
            self, 'GetArtistID',
            runtime=lambda_.Runtime.PYTHON_3_10,
            code=lambda_.Code.from_asset('lambda_functions/GetArtist-IDHandler'),
            handler='get_artist_id.handler',
            function_name='GetArtist-IDHandler',
            description=f'Queries the Spotify "/search" API endpoint for the artist ID.',
            layers=[_requests_layer]
        )
        
        # Spotify artist's latest music 'getter' Lambda Function
        _get_latest_music_lambda = lambda_.Function(
            self, 'GetLatestMusic',
            runtime=lambda_.Runtime.PYTHON_3_10,
            code=lambda_.Code.from_asset('lambda_functions/GetLatestMusicHandler'),
            handler='get_latest_music.handler',
            function_name='GetLatestMusicHandler',
            description='Queries a series of Spotify API endpoints for the artist\'s latest music.',
            layers=[_requests_layer],
            environment={
                'GET_ACCESS_TOKEN_LAMBDA': _get_access_token_lambda.function_name,
                'UPDATE_TABLE_MUSIC_LAMBDA': update_table_music_lambda.function_name
            }
        )     
        
        # Add DynamoDB Stream as an event source to trigger 'GetLatestMusicHandler'
        # More info: https://docs.aws.amazon.com/cdk/api/v1/python/aws_cdk.aws_lambda_event_sources/DynamoEventSource.html
        _get_latest_music_lambda.add_event_source(
            lambda_event_sources.DynamoEventSource(
                table=ddb.Table.from_table_attributes(
                    self, 'MonitoredArtistTable',
                    table_arn=artist_table_arn,
                    table_stream_arn=artist_table_stream_arn
                ),
                starting_position=lambda_.StartingPosition.LATEST,
                retry_attempts=3,
                bisect_batch_on_error=True, 
            )
        ) 
        
        # Import existent Spotify Secret to grant `GetAccessTokenHandler` Lambda permissions to pull secrets  
        __spotify_secrets = ssm.Secret.from_secret_name_v2(
            self, 'ImportedSpotifySecrets',
            secret_name='SpotifySecrets'
        )
        
        # Give 'GetLatestMusicHandler' permission to invoke 'GetAccessTokenHandler'
        _get_access_token_lambda.grant_invoke(_get_latest_music_lambda)  
        
        # Give 'GetAccessTokenHandler' Lambda permissions to read secret
        __spotify_secrets.grant_read(_get_access_token_lambda)
        
        # Give 'LatestMusicGetter' Lambda permissions to invoke 'UpdateTableMusicLambda'
        update_table_music_lambda.grant_invoke(_get_latest_music_lambda)