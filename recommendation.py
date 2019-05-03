import psycopg2

# Connect to database
connection = psycopg2.connect(user = "admin",
                              password = "",
                              host = "connordowson.com",
                              port = "5432",
                              database = "algorhythm")
cur = connection.cursor()

# Get all user ids
cur.execute("SELECT id FROM recommend_user;")
temp = cur.fetchall()
user_ids = []
for user_id in temp:
    user_ids.append(user_id[0])
print(user_ids)

# Create collaborative fitlering function
def collaborative_filtering(user_id, potential_recommendations, users_top_track_ids):

    # Combine the playlists of potential songs
    potential_songs = []
    for playlist in potential_recommendations:
        potential_songs = potential_songs + playlist

    # Use sets to remove any duplicates
    potential_songs = set(potential_songs)
    potential_songs = list(potential_songs)   
        
    most_similar_songs = []

    print("Finding recommendations...")
    # For each song in the users top tracks, fetch the audio features on the song
    for user_song_id in users_top_track_ids:
        cur.execute("SELECT song_id, title, artist, acousticness, danceability, energy, instrumentalness, liveness, loudness, speechiness, valence FROM recommend_song WHERE song_id = '{0}';".format(user_song_id))
        this_song = cur.fetchall()[0]
        
        # For each song in the potential recommendations, fetch the audio features on the song
        for potential_song_id in potential_songs:
            cur.execute("SELECT song_id, title, artist, acousticness, danceability, energy, instrumentalness, liveness, loudness, speechiness, valence FROM recommend_song WHERE song_id = '{0}';".format(potential_song_id))
            potential_song = cur.fetchall()[0]

            # Find the delta for each audio feature belonging to the current user song, and the potential recommendation song, then find the sum of it
            delta = 0
            for x in range(3,10):
                delta = delta + (abs(this_song[x] - potential_song[x]))
            # If the most similar songs list has less than 20 songs, add this song, along with its title, artist, and delta
            if len(most_similar_songs) < 20:
                most_similar_songs.append([potential_song[0], potential_song[1], potential_song[2], delta])
            # If the most similar songs list has 20 songs, see if this song is more similar than the least similar song inside the list
            else:
                # Sort the list so that the least similar song is at the end (19th index)
                most_similar_songs = sorted(most_similar_songs, key = lambda delta: float(delta[3]))
                least_similar = most_similar_songs[19][3]
                # If the song is more similar, and isn't already in the list, add it
                if (delta < least_similar) and ([potential_song[0], potential_song[1], potential_song[2], delta] not in most_similar_songs):
                    most_similar_songs.pop(19)
                    most_similar_songs.append([potential_song[0], potential_song[1], potential_song[2], delta])

    # Once all songs have been considered, delete a users current recommendations, and then upload the new ones
    print("Recommendations finished!")
    cur.execute("DELETE from recommend_recommendation WHERE user_id_id = {0};".format(user_id))
    connection.commit()
    for song in most_similar_songs:
        print("{0} - {1}".format(song[1], song[2]))
        cur.execute("INSERT into recommend_recommendation (song_id_id, user_id_id) VALUES ('{0}', {1}) ON CONFLICT DO NOTHING;".format(song[0], user_id))
        connection.commit()
    print("Uploaded recommendations for user: {0}".format(user_id))


def content_based_recommendation(user_id):
    # Select the users top tracks
    cur.execute("SELECT song_id_id FROM recommend_usertoptracks WHERE user_id_id = '{0}';".format(user_id))
    users_top_tracks = cur.fetchall()

    # Song ids are nested in lists, extract them from the list
    users_top_track_ids = []
    for track in users_top_tracks:
        users_top_track_ids.append(track[0])

    # For each song in the database, fetch the audio features on the song
    cur.execute("SELECT song_id, title, artist, acousticness, danceability, energy, instrumentalness, liveness, loudness, speechiness, valence FROM recommend_song;")
    songs_result = cur.fetchall()
    
    most_similar_songs = []

    # For each song in the database, add to potential list of recommendations if it isn't in the users top tracks
    songs_to_compare = []
    for song in songs_result:
        if (song[0] not in users_top_track_ids) and (song not in songs_to_compare):
            songs_to_compare.append(song)

    # For each song in the users top tracks, fetch the audio features on the song
    for track in users_top_track_ids:
        cur.execute("SELECT song_id, title, artist, acousticness, danceability, energy, instrumentalness, liveness, loudness, speechiness, valence FROM recommend_song WHERE song_id = '{0}';".format(track))
        this_song = cur.fetchall()[0]

        # Find the delta for each audio feature belonging to the current user song, and the potential recommendation song, then find the sum of it
        for song in songs_to_compare:
            delta = 0
            for x in range(3,10):
                delta = delta + (abs(this_song[x] - song[x]))
            # If the most similar songs list has less than 20 songs, add this song, along with its title, artist, and delta
            if len(most_similar_songs) < 20:
                most_similar_songs.append([song[0], song[1], song[2], delta])
            # If the most similar songs list has 20 songs, see if this song is more similar than the least similar song inside the list
            else:
                # Sort the list so that the least similar song is at the end (19th index)
                most_similar_songs = sorted(most_similar_songs, key = lambda delta: float(delta[3]))
                least_similar = most_similar_songs[19][3]
                # If the song is more similar, and isn't already in the list, add it
                if (delta < least_similar) and ([song[0], song[1], song[2], delta] not in most_similar_songs):
                    most_similar_songs.pop(19)
                    most_similar_songs.append([song[0], song[1], song[2], delta])


    # Once all songs have been considered, delete a users current recommendations, and then upload the new ones
    print("Recommendations finished!")
    cur.execute("DELETE from recommend_recommendation WHERE user_id_id = {0};".format(user_id))
    connection.commit()
    for song in most_similar_songs:
        print("{0} - {1}".format(song[1], song[2]))
        cur.execute("INSERT into recommend_recommendation (song_id_id, user_id_id) VALUES ('{0}', {1}) ON CONFLICT DO NOTHING;".format(song[0], user_id))
        connection.commit()
        
    print("Uploaded recommendations for user: {0}".format(user_id))

# For each user in the database
for user_id in user_ids:

    # Select all of their top tracks in the database (for all time ranges)
    cur.execute("SELECT song_id_id FROM recommend_usertoptracks WHERE user_id_id = {0};".format(user_id))
    this_user_songs_temp = cur.fetchall()
    # Song ids are nested inside a list, extract them
    users_top_track_ids = []
    for song in this_user_songs_temp:
        users_top_track_ids.append(song[0])
        
    # Select all top tracks for the rest of the users
    cur.execute("SELECT user_id_id, song_id_id, time_range FROM recommend_usertoptracks WHERE NOT user_id_id = {0};".format(user_id))
    all_other_songs = list(cur.fetchall())

    # Select the user ids except the current user
    cur.execute("SELECT id FROM recommend_user WHERE NOT id = {0};".format(user_id))
    all_other_users = cur.fetchall()

    # Group the top tracks entries into lists. Each list contains all of a single users top tracks 
    grouped_by_user = [[song for song in all_other_songs if song[0] == user[0]] for user in all_other_users]

    # Group the user playlists into seperate ones for each time range
    time_ranges = ['short_term', 'medium_term', 'long_term']
    grouped_by_playlist_nested = []
    for user in grouped_by_user:
        new_group = [[song for song in user if song[2] == time_range] for time_range in time_ranges]
        grouped_by_playlist_nested.append(new_group)

    grouped_by_playlist = []
    for group in grouped_by_playlist_nested:
        for playlist in group:
            if playlist:
                temp = []
                for song in playlist:
                    temp.append(song[1])
                grouped_by_playlist.append(temp)

    # Find if any user top tracks playlists contain at least 5 songs the same as the current user
    matches = []
    for playlist in grouped_by_playlist:
        playlist = set(playlist)
        if len(playlist.intersection(users_top_track_ids)) >= 5:
            matches.append(playlist.difference(users_top_track_ids))

    # Get song ids for potential matches
    potential_recommendations = []      
    for playlist in matches:
        temp_playlist = []
        for song in playlist:
            cur.execute("SELECT song_id from recommend_song WHERE song_id = '{0}';".format(song))
            this_data = list(cur.fetchone())
            temp_playlist.append(this_data[0])
        potential_recommendations.append(temp_playlist)

    print("Number of playlists with at least 5 common songs for user {0}: ".format(user_id) ,len(potential_recommendations))

    # If there are at least 2 other playlists with at least 5 matching songs, run the collaborative filtering
    if(len(potential_recommendations) >= 2):
        collaborative_filtering(user_id, potential_recommendations, users_top_track_ids)
    # If not, run content based filtering
    else:
        content_based_recommendation(user_id)

print("Recommendations finished.")

