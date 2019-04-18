from sklearn import preprocessing
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns; sns.set()  # for plot styling
import psycopg2

connection = psycopg2.connect(user = "admin",
                        password = "***REMOVED***",
                        host = "connordowson.com",
                        port = "5432",
                        database = "algorhythm")
cur = connection.cursor()


class Recommender(object):

    def __init__(self, user_id):

        self.user_id = user_id


    def get_user_songs(self):

        user_id = self.user_id

        cur.execute("SELECT song_id_id FROM recommend_usertoptracks WHERE user_id_id = {0};".format(user_id))
        this_user_songs_temp = cur.fetchall()
        this_user_songs = []
        for song in this_user_songs_temp:
            this_user_songs.append(song[0])

        cur.execute("SELECT user_id_id, song_id_id, time_range FROM recommend_usertoptracks WHERE NOT user_id_id = {0};".format(user_id))
        all_other_songs = list(cur.fetchall())

        cur.execute("SELECT id FROM recommend_user WHERE NOT id = {0};".format(user_id))
        all_other_users = cur.fetchall()

        grouped_by_user = [[song for song in all_other_songs if song[0] == user[0]] for user in all_other_users]

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

        matches = []
        for playlist in grouped_by_playlist:
            playlist = set(playlist)
            if len(playlist.intersection(this_user_songs)) > 1:
                matches.append(playlist.difference(this_user_songs))
                        
        potential_recommendations = []      
        for playlist in matches:
            temp_playlist = []
            for song in playlist:
                cur.execute("SELECT song_id from recommend_song WHERE song_id = '{0}';".format(song))
                this_data = list(cur.fetchone())
                temp_playlist.append(this_data[0])
            potential_recommendations.append(temp_playlist)
            

        this_user_song_data = []
        this_user_song_ids = []
        for song in this_user_songs:
            cur.execute("SELECT song_id, title, artist, acousticness, danceability, energy, instrumentalness, key, liveness, mode, speechiness, tempo, valence from recommend_song WHERE song_id = '{0}'".format(song))
            this_data = list(cur.fetchone())
            # Add song title and artist to titles list
            this_user_song_ids.append(this_data[0])
            #Remove title and artist and add audio features to song data list
            this_data.pop(0)
            this_data.pop(0)
            this_data.pop(0)
            this_user_song_data.append(this_data)
            
        potential_recommendations_song_data = []
        potential_recommendations_song_ids = []
        for playlist in potential_recommendations:
            temp_playlist = []
            temp_ids = []
            for song in playlist:
                cur.execute("SELECT song_id, title, artist, acousticness, danceability, energy, instrumentalness, key, liveness, mode, speechiness, tempo, valence from recommend_song WHERE song_id = '{0}'".format(song))
                this_data = list(cur.fetchone())
                # Add song title and artist to titles list
                temp_ids.append(this_data[0])
                #Remove title and artist and add audio features to song data list
                this_data.pop(0)
                this_data.pop(0)
                this_data.pop(0)
                temp_playlist.append(this_data)
            potential_recommendations_song_data.append(temp_playlist)
            potential_recommendations_song_ids.append(temp_ids)


            pca_values_user_songs_df, cluster_centers, furthest_from_center = self.get_pca_df(this_user_song_ids, this_user_song_data)
            x = this_user_song_ids + potential_recommendations_song_ids[0]
            y = this_user_song_data + potential_recommendations_song_data[0]

            pca_values_user_songs_df, cluster_centers, furthest_from_center = self.get_pca_df(x, y)

            recommendations = []
            for index, playlist in enumerate(potential_recommendations_song_ids):
                recommendation_coords = self.recommendation_pca_values(this_user_song_ids, playlist, this_user_song_data, potential_recommendations_song_data[index])
                recommended_songs = self.filter_recommendations(recommendation_coords, cluster_centers, furthest_from_center)
                if recommendations:
                    for song in recommended_songs:
                        if not song in recommendations:
                            recommendations.append(song)
                else:
                    if recommended_songs:
                        for song in recommended_songs:
                            recommendations.append(song)

            for song in recommendations:
                cur.execute("INSERT into recommend_recommendation (song_id_id, user_id_id) VALUES ('{0}', {1}) ON CONFLICT DO NOTHING;".format(song, user_id))
                connection.commit()

            print("Uploaded recommendations ({0}) for user: ".format(len(recommendations)), user_id)
                

    def get_pca_df(self, song_ids, song_data):
        fieldnames = ['acousticness', 'danceability', 'energy', 'instrumentalness', 'key', 'liveness', 'mode', 'speechiness', 'tempo', 'valence']
        playlist_df = pd.DataFrame(columns=fieldnames, index=song_ids)
        scaled_song_data = preprocessing.scale(song_data)
                    
        for index, song in enumerate(playlist_df.index):
            playlist_df.loc[song, 'acousticness'] = scaled_song_data[index][0]
            playlist_df.loc[song, 'danceability'] = scaled_song_data[index][1]
            playlist_df.loc[song, 'energy'] = scaled_song_data[index][2]
            playlist_df.loc[song, 'instrumentalness'] = scaled_song_data[index][3]
            playlist_df.loc[song, 'key'] = scaled_song_data[index][4]
            playlist_df.loc[song, 'liveness'] = scaled_song_data[index][5]
            playlist_df.loc[song, 'mode'] = scaled_song_data[index][6]
            playlist_df.loc[song, 'speechiness'] = scaled_song_data[index][7]
            playlist_df.loc[song, 'tempo'] = scaled_song_data[index][8]
            playlist_df.loc[song, 'valence'] = scaled_song_data[index][9]
                            
        pca_playlist = PCA()
        pca_playlist.fit(playlist_df)
        pca_playlist_data = pca_playlist.transform(playlist_df)
        
        per_var = np.round(pca_playlist.explained_variance_ratio_*100, decimals=1)
        labels = ['PC' + str(x) for x in range(1, len(per_var) + 1)]

        plt.bar(x=range(1, len(per_var)+1), height=per_var, tick_label=labels)
        plt.ylabel('Percentage of explained variance')
        plt.xlabel('Principal component')
        plt.title('Scree Plot')
        plt.clf()
        
        # Plot graph of PCA analysis for each song
        
        pca_df = pd.DataFrame(pca_playlist_data, index=song_ids, columns=labels)
        plt.scatter(pca_df.PC1, pca_df.PC2, s=50)
        plt.title('PCA analysis of songs')
        plt.xlabel('PC1 - {0}%'.format(per_var[0]))
        plt.ylabel('PC2 - {0}%'.format(per_var[1]))

        # Add title of each song to its point on the scatter graph
        for song_id in pca_df.index:
            plt.annotate(song_id,(pca_df.PC1.loc[song_id], pca_df.PC2.loc[song_id]))

        from sklearn.cluster import KMeans
        clusters = 2
        kmeans = KMeans(n_clusters = clusters)
        kmeans.fit(pca_df)
        y_kmeans = kmeans.predict(pca_df)

        plt.scatter(pca_df.PC1, pca_df.PC2, c=y_kmeans, s=50, cmap='plasma')
        centers = kmeans.cluster_centers_

        coordinates = list(zip(pca_df.PC1, pca_df.PC2))
        
        pca_values_df = pd.DataFrame(coordinates, index=song_ids, columns=['PC1', 'PC2'])
        
        centers_coords = []
        centers_coords.append(np.array(centers[:, 0]))
        centers_coords.append(np.array(centers[:, 1]))
        
        furthest_from_center = []
        for cluster in centers_coords:
            temp_distance = 0
            for point in coordinates:
                this_point = np.array((point[0], point[1]))
                this_distance = np.linalg.norm(this_point - cluster)
                if this_distance > temp_distance:
                    temp_distance = this_distance
            furthest_from_center.append(temp_distance)
            
        pca_values_df = pd.DataFrame(coordinates, index=song_ids, columns=['PC1', 'PC2'])

        
        plt.scatter(centers[:, 0], centers[:, 1], c='black', s=200, alpha=0.5)

        plt.clf()
            
        return pca_values_df, centers_coords, furthest_from_center

    def recommendation_pca_values(self, song_ids_user, song_ids_recommend, song_data_user, song_data_recommend):
        song_ids = song_ids_user + song_ids_recommend
        song_data = song_data_user + song_data_recommend
        
        fieldnames = ['acousticness', 'danceability', 'energy', 'instrumentalness', 'key', 'liveness', 'mode', 'speechiness', 'tempo', 'valence']
        playlist_df = pd.DataFrame(columns=fieldnames, index=song_ids)
        scaled_song_data = preprocessing.scale(song_data)
                    
        for index, song in enumerate(playlist_df.index):
            playlist_df.loc[song, 'acousticness'] = scaled_song_data[index][0]
            playlist_df.loc[song, 'danceability'] = scaled_song_data[index][1]
            playlist_df.loc[song, 'energy'] = scaled_song_data[index][2]
            playlist_df.loc[song, 'instrumentalness'] = scaled_song_data[index][3]
            playlist_df.loc[song, 'key'] = scaled_song_data[index][4]
            playlist_df.loc[song, 'liveness'] = scaled_song_data[index][5]
            playlist_df.loc[song, 'mode'] = scaled_song_data[index][6]
            playlist_df.loc[song, 'speechiness'] = scaled_song_data[index][7]
            playlist_df.loc[song, 'tempo'] = scaled_song_data[index][8]
            playlist_df.loc[song, 'valence'] = scaled_song_data[index][9]
                            
        pca_playlist = PCA()
        pca_playlist.fit(playlist_df)
        pca_playlist_data = pca_playlist.transform(playlist_df)
            
        # Plot graph of PCA analysis for each song
        per_var = np.round(pca_playlist.explained_variance_ratio_*100, decimals=1)
        labels = ['PC' + str(x) for x in range(1, len(per_var) + 1)]
        
        pca_df = pd.DataFrame(pca_playlist_data, index=song_ids, columns=labels)

        coordinates = list(zip(pca_df.PC1, pca_df.PC2))
        
        pca_values_df = pd.DataFrame(coordinates, index=song_ids, columns=['PC1', 'PC2'])
            
        for song_id in song_ids_user:
            if song_id in pca_values_df.index:
                pca_values_df = pca_values_df.drop(song_id)
        
        return pca_values_df

    def filter_recommendations(self, song_df, centers, furthest_values):

        coordinates = list(zip(song_df.PC1, song_df.PC2))
                
        songs_to_recommend = []
        
        for index, row in song_df.iterrows():
            for index, cluster_center in enumerate(centers):
                coordinates = np.array(row.PC1, row.PC2)
                distance_from_cluster = np.linalg.norm(coordinates - cluster_center)
                if(distance_from_cluster >= furthest_values[index]) and not any(row.name in s for s in songs_to_recommend):
                    songs_to_recommend.append(row.name)
                    
        return songs_to_recommend