import os
import time
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA

# Internal imports
import general_tools.tools as tools
from general_tools.database import Database
from general_tools.img2vec import Img2Vec

# Choose one municipality and its resolution
municipality = 'Rotterdam'
resolution = 'h3_10'
images_folder_path = '../stv_database'

# Algorithm settings

img2vec_model = [
    'resnet18',
    'resnet34',
    'resnet50',
    'resnet101',
    'resnet152'][4]

k = 5
seed = 2102
outdim_PCA = 5

img2vec = Img2Vec(gpu = False, model = img2vec_model)
vec_length = Img2Vec.RESNET_OUTPUT_SIZES[img2vec_model]

NAME = 'street-level-views'
HOST = 'localhost'
PORT = 2222
USER = 'postgres'
db = Database(NAME, HOST, PORT, USER, db_psw = 'postgres')
panoids_gdf = db.get_panoids_from_municipality(municipality, resolution)

# Defining the paths
municipality_folder_path = f'{images_folder_path}/{municipality}_NL/imagedb'
print(f"Getting images from: TUD_Project_Folder -> {municipality_folder_path}")

# Creating destination folder for the city
destination_folder = f'municipalities/{municipality}_{resolution}'
destination_images_folder = f'{destination_folder}/spatial_units'
if not os.path.exists(destination_folder):
    os.makedirs(destination_folder)
    os.makedirs(destination_images_folder)
print(f"Saving municipality to: {destination_folder}")
print(f"Saving images to: {destination_images_folder}")

# Identifying spatial units
spatial_units = panoids_gdf['h3'].unique()
spatial_units.sort()

# testing for one spatial unit
total_h3s = len(spatial_units)
all_h3s = []
for i, h3 in enumerate(spatial_units):
    print(f"Getting images from spatial unit: {h3} ({i}/{total_h3s})")
    imgs_su = tools.get_images_from_h3(h3, municipality, panoids_gdf)
    imgs_su['slv_path'] = imgs_su.apply(lambda x: f"{municipality_folder_path}/{x['im']}", axis=1)
    imgs_su['new_path'] = imgs_su.apply(lambda x: f"{destination_images_folder}/{h3}/PANO_{x['panoid']}_{x['side']}.png", axis=1)

    # Getting the images that greater than 60kb
    imgs = []
    new_paths = []
    max_attempts = 5
    for img_file, new_path in zip(imgs_su['slv_path'], imgs_su['new_path']):
        attempt = 0
        img_kb = 0
        while attempt < max_attempts:
            try:
                img_kb = os.path.getsize(img_file) / 1024
                if img_kb > 60:
                    imgs.append(img_file)
                    new_paths.append(new_path)
                break  # Exit the loop if getsize succeeds
            except OSError as e:
                print(f"Attempt {attempt + 1} failed for {img_file}: {e}")
                time.sleep(1)  # Wait for 1 second before retrying
                attempt += 1
        if attempt == max_attempts:
            print(f"Failed to get size for {img_file} after {max_attempts} attempts.")
        
    # Checking if the spatial unit is usable
    if len(imgs) < 5:
        print(f"WARNING HEX:{h3} -> Unusable as it has less than 5 images")
        continue

    # Getting the image vectors    
    matrix = img2vec.get_vec_matrix(imgs)

    # Reducing the dimensionality of the embeddings
    reduced_matrix = PCA(n_components = outdim_PCA).fit_transform(matrix)

    # Clustering the reduced embeddings using k-means
    kmeans = KMeans(init='k-means++', n_clusters = k, n_init = 1000, random_state = seed)
    kmeans.fit(reduced_matrix)
    cluster_kmeans = kmeans.predict(reduced_matrix)

    # Sampling the k most representative images from the clusters
    df = pd.DataFrame({'slv_path': imgs, 'image_path': new_paths, 'kmeans': cluster_kmeans, 'h3': h3})
    df_embs = pd.DataFrame(matrix, columns=[f'x{i}' for i in range(matrix.shape[1])])
    df = pd.concat([df, df_embs], axis=1)
    df = df.sample(len(df)).groupby(['kmeans']).first()

    # storing the pickle file
    all_h3s.append(df)
    pd.concat(all_h3s).to_pickle(f'{destination_folder}/spatial_units.pkl')

    # Saving the images
    for j, row in df.iterrows():
        spatial_unit_folder = f'{destination_images_folder}/{h3}'
        if not os.path.exists(spatial_unit_folder):
            os.makedirs(spatial_unit_folder)
        os.system(f'cp "{row["slv_path"]}" "{row["image_path"]}"')
    
    

