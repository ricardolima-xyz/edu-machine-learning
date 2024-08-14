import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import re
import nltk
from nltk.corpus import stopwords
from nltk.stem.snowball import SnowballStemmer
import sys
import warnings
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
import warnings
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.metrics import f1_score
from sklearn.metrics import roc_auc_score
from sklearn.metrics import precision_score
from sklearn.metrics import recall_score
from sklearn.metrics import accuracy_score
from sklearn.multiclass import OneVsRestClassifier
import joblib

# reading products
f = open('examples/products.json')
data = json.load(f) # returns JSON object as a dictionary

# creating dataframe with three rows (name,description,categories)
column_names = ['name','description','categories']
df = pd.DataFrame(columns = column_names)

names,descriptions,categories = [],[],[]
for product in data:
  names.append(product['name'])
  descriptions.append(product['description'])
  productCategories = []
  for cat in product['category']:
    productCategories.append(cat['name'])
  categories.append(productCategories)

df = pd.DataFrame(list(zip(names,descriptions,categories)) ,columns = column_names)

cat = pd.DataFrame(df['categories'].to_list()) # listing the categories seperately

# finding total unique categories/classes from which our prediction will belong too
category_0 = cat[0].unique()
category_1 = cat[1].unique()
category_2 = cat[2].unique()
category_3 = cat[3].unique()
category_4 = cat[4].unique()
category_5 = cat[5].unique()
category_6 = cat[6].unique()
cates = np.concatenate([category_0, category_1, category_2,category_3,category_4,category_5,category_6])
cates = list(dict.fromkeys(cates))
cates = [x for x in cates if x is not None] # remove None


cat = pd.concat([cat,pd.DataFrame(columns = list(cates))]) # concatnate categories/classes to original dataframe

##cat.fillna(0, inplace = True) # fill with zero
cat.infer_objects(copy=False) ###

# filling attendence for all the categories/classes
for i in range(7):
  row = 0
  for category in cat[i]:
    if category!= 0:
      cat.loc[row,category] = 1 # loc is label-based, which means that you have to specify rows and columns based on their row and column labels.
    row = row + 1
# iloc is integer position-based, so you have to specify rows and columns by their integer position values (0-based integer position)
    
df2 = pd.concat([df['name'],df['description'],cat.loc[:,"2-Channel Amps":]],axis=1) # creating new dataframe which contains name of product,description and categories it belong to

bar_plot = pd.DataFrame()
bar_plot['category'] = df2.columns[2:] # column name, which are categories
bar_plot['count'] = df2.iloc[:,2:].sum().values
bar_plot.sort_values(['count'], inplace=True, ascending=False)
bar_plot.reset_index(inplace=True, drop=True)

print(bar_plot.head()) # Top 5 most occuring categories

######
######
##### https://github.com/prakhargurawa/Product-Category-Prediction/blob/main/Product_Category_Prediction.ipynb
