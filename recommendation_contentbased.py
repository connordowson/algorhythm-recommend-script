from sklearn import preprocessing
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns; sns.set()  # for plot styling
import psycopg2

import matplotlib.pyplot as plt

connection = psycopg2.connect(user = "admin",
                              password = "***REMOVED***",
                              host = "connordowson.com",
                              port = "5432",
                              database = "algorhythm")
cur = connection.cursor()

#select all user ids
cur.execute("SELECT id FROM recommend_user;")
user_id_nested = cur.fetchall()
user_ids = []
for user in user_id_nested:
    user_ids.append(user[0])
    
print(user_ids)        
    
for user_id in user_ids:
    #select a users top tracks
    cur.execute("SELECT song_id_id FROM recommend_usertoptracks WHERE user_id_id = '{0}';".format(user_id))
    users_top_tracks = cur.fetchall()

    users_top_track_ids = []
    for track in users_top_tracks:
        users_top_track_ids.append(track[0])

    cur.execute("SELECT song_id, title, artist, acousticness, danceability, energy, instrumentalness, liveness, loudness, speechiness, valence FROM recommend_song;")
    songs_result = cur.fetchall()
    most_similar_songs = []

    songs_to_compare = []
    for song in songs_result:
        if (song[0] not in users_top_track_ids) and (song not in songs_to_compare):
            songs_to_compare.append(song)

    for track in users_top_track_ids:
        cur.execute("SELECT song_id, title, artist, acousticness, danceability, energy, instrumentalness, liveness, loudness, speechiness, valence FROM recommend_song WHERE song_id = '{0}';".format(track))
        this_song = cur.fetchall()[0]

        for song in songs_to_compare:
            song_values = []
            value = 0
            for x in range(3,10):
                value = value + (abs(this_song[x] - song[x]))
                song_values.append([song[0], song[1], song[2], value])
            if len(most_similar_songs) <= 20:
                most_similar_songs.append([song[0], song[1], song[2], value])
            else:
                most_similar_songs = sorted(most_similar_songs, key = lambda value: float(value[3]))
                least_similar = most_similar_songs[19][3]
                if (value < least_similar) and ([song[0], song[1], song[2], value] not in most_similar_songs):
                    most_similar_songs.pop(19)
                    most_similar_songs.append([song[0], song[1], song[2], value])


    for song in most_similar_songs:
    #     print("{0} - {1}".format(song[1], song[2]))
        cur.execute("INSERT into recommend_recommendation (song_id_id, user_id_id) VALUES ('{0}', {1}) ON CONFLICT DO NOTHING;".format(song[0], user_id))
        connection.commit()
        
    print("Uploaded recommendations for user: {0}".format(user_id))