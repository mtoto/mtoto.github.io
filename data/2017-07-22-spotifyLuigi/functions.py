import requests
import datetime
import json
import collections
import os
import boto3
import math
from spotify_creds_pl import *
import pandas as pd

# Get access token
def access_token():
    
    body_params = {'grant_type' : 'refresh_token',
                'refresh_token' : refresh_token}

    url = 'https://accounts.spotify.com/api/token'
    response = requests.post(url, 
                             data = body_params, 
                             auth = (client_id, client_secret))
    
    response_dict = json.loads(response.content)
    accessToken = response_dict.get('access_token')

    return accessToken
    
# Get most recent songs and append the response
# to a new json file every day
def download_data():

    current_time = datetime.datetime.now().strftime('%Y-%m-%d')
    filename = '/spotify/json/spotify_tracks_%s.json' % current_time
    
    accesToken = access_token()
    headers = {'Authorization': 'Bearer ' + accesToken }
    payload = {'limit': 50}

    url = 'https://api.spotify.com/v1/me/player/recently-played'
    response = requests.get(url, headers = headers,
                            params = payload)
    data = response.json()

    with open(filename, 'a') as f:
        json.dump(data['items'], f)
        f.write('\n')
        
# This function takes a list of track uri's 
# to replace songs in my morning playlist
# and returns the status code of the put request.
def replace_tracks(tracks):
    
    url = 'https://api.spotify.com/v1/users/1170891844/playlists/6a2QBfOgCqFQLN08FUxpj3/tracks'
    accesToken = access_token()
    headers = {'Authorization': 'Bearer ' + accesToken,
               'Content-Type':'application/json'}
    data = {"uris": ','.join(tracks)}

    response = requests.put(url, headers = headers,
                            params = data)
                            
    return response.status_code
        
# Cleaner function to get rid of redundancy
def deduplicate(file):
    result =[]
    
    for line in file:
        data = json.loads(line)
        result.extend(data)
    
    result = {i['played_at']:i for i in result}.values()
    return result

#Parse json so it can easily be converted to a dataframe
def parse_json(file): 
    results = []
    track_cols = ['name','uri','explicit','duration_ms','type','id']

    for item in file:
        
        d_time = {'played_at' : item['played_at']}
        
        for key in item.keys(): 
            if (key == 'track'):
                track = item[key]
                d_arts = collections.defaultdict(list)
                
                for i in track['artists']: 
                    for k, v in i.items(): 
                        if (k in ['id','name']):
                            d_arts['artist_' + k].append(v)
                            
                track_sub = { k: track[k] for k in track_cols }
                
                for k,v in track_sub.items():
                    if (k in ['id','name']):
                        track_sub['track_' + k] = track_sub.pop(k)
            
        d = dict(track_sub, **d_arts)
        d.update(d_time)

        results.append(d)
                     
    return results

# This function reads in the weekly dataset 
# as a pandas dataframe, outputs the list of 
# top ten tracks and feeds them to replace_tracks()
def create_playlist(dataset, date):
    
    data = pd.read_json(dataset)          
    data['played_at'] = pd.to_datetime(data['played_at'])
    
    data = data.set_index('played_at') \
               .between_time('7:00','12:00')
        
    data = data[data.index > str(date)]
    # aggregate data
    songs = data['uri'].value_counts()\
                       .nlargest(10) \
                       .index \
                       .get_values() \
                       .tolist()
    # make api call
    res_code = replace_tracks(songs)
    
    return res_code


