import psycopg2 as psql
import sqlalchemy as sqla
import sshtunnel as ssht
import geopandas as gpd
import pandas as pd 

class Database:

    # Init of the database for psycopg2 and sqlalchemy
    def __init__(self, db_name, host, port, db_user, db_psw = None, tunneling = False, ssh_user = None, ssh_psw = None, ssh_key = None):

        if tunneling:
            self.server = ssht.SSHTunnelForwarder((host, 22),
                                                   ssh_username = ssh_user,
                                                   ssh_password = ssh_psw,
                                                   remote_bind_address = ('localhost', port))
            self.server.start()
            print(f"Server connected via SSH on port {self.server.local_bind_port}")

            self.conn = psql.connect(database = db_name,
                                     host = 'localhost',
                                     port = self.server.local_bind_port,
                                     user = db_user,
                                     password = db_psw)
            
            self.engine = sqla.create_engine(f"postgresql://{db_user}:{db_psw}@localhost:{self.server.local_bind_port}/{db_name}")

        else:
            self.conn = psql.connect(database = db_name,
                                     host = host,
                                     port = port,
                                     user = db_user,
                                     password = db_psw)
        
            self.engine = sqla.create_engine(f"postgresql://{db_user}:{db_psw}@{host}:{port}/{db_name}")
    
    # Return all instances of the database based on a query
    def query(self, query: str) -> pd.DataFrame:
        return pd.read_sql(query, self.conn)

    # Return all the panoids from an specific municipality and certain h3 code
    def get_panoids_from_municipality(self, 
                                      municipality_name: str,
                                      h3_code: str) -> gpd.GeoDataFrame:

        query = lambda mun_name, h3: f"""SELECT
                                             p.panoid, 
                                             p.year, 
                                             p.month, 
                                             p.im_front,
                                             p.im_back, 
                                             p.im_side_a, 
                                             p.im_side_b, 
                                             g.density,
                                             g.h3,
                                             p.geometry
                                         FROM
                                             panoids as p, 
                                             (SELECT
                                                  panoid, 
                                                  {h3} as h3, 
                                                  density 
                                              FROM 
                                                  geodata 
                                              WHERE 
                                                  gm_naam = '{mun_name}'
                                             ) as g 
                                         WHERE 
                                             p.panoid = g.panoid AND 
                                             p.zone = '{municipality_name}_NL'"""
        
        sql_query = query(municipality_name, h3_code)
        gdf = gpd.read_postgis(sql_query, con = self.engine, geom_col = 'geometry', crs = 4326)

        return gdf
    
    def get_image_paths_from_h3(self, h3: str, h3_res: int) -> pd.DataFrame:
        query = f"""SELECT 
                        p.panoid, 
                        p.zone, 
                        im_front, 
                        im_back, 
                        im_side_a, 
                        im_side_b 
                    FROM 
                        geodata as g, 
                        panoids as p 
                    WHERE  
                        g.panoid = p.panoid AND 
                        h3_{h3_res} = '{h3}'"""
        return self.query(query)
    
