from sklearn import preprocessing
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns; sns.set()  # for plot styling
import psycopg2

import recommendations

connection = psycopg2.connect(user = "admin",
                              password = "***REMOVED***",
                              host = "connordowson.com",
                              port = "5432",
                              database = "algorhythm")
cur = connection.cursor()


cur.execute("SELECT id from recommend_user;")
all_user_ids = cur.fetchall()

for user in all_user_ids:
    rec = recommendations.Recommender(user[0])
    rec.get_user_songs()
