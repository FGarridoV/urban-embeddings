import pandas as pd

def get_images_from_h3(h3, municipality, panoids_gdf):
    panoids_h3 = panoids_gdf.loc[panoids_gdf['h3'] == h3]
    df_f = panoids_h3.rename(columns={'im_front': 'im'}).drop(columns=['im_side_a', 'im_back', 'im_side_b'])
    df_s = panoids_h3.rename(columns={'im_side_a': 'im'}).drop(columns=['im_front', 'im_back', 'im_side_b'])
    df_b = panoids_h3.rename(columns={'im_back': 'im'}).drop(columns=['im_front', 'im_side_a', 'im_side_b'])
    df_a = panoids_h3.rename(columns={'im_side_b': 'im'}).drop(columns=['im_front', 'im_side_a', 'im_back'])
    df_f['side'] = 'f'
    df_s['side'] = 'a'
    df_b['side'] = 'r'
    df_a['side'] = 'b'
    panoids_h3 = pd.concat([df_f, df_s, df_b, df_a], axis=0).reset_index(drop=True)
    #panoids_h3['url'] = panoids_h3.apply(lambda row: image_url(f'{municipality}_NL', row['im']), axis=1)
    return panoids_h3