# This is the information for the dataset for precipitation
# Name: ERA5-Land Daily Aggregated - ECMWF Climate Reanalysis ERA5-Land Daily Aggregated - ECMWF Climate Reanalysis
# Link: https://developers.google.com/earth-engine/datasets/catalog/ECMWF_ERA5_LAND_DAILY_AGGR#bands
# Citation: Muñoz Sabater, J., (2019): ERA5-Land monthly averaged data from 1981 to present. Copernicus Climate Change Service (C3S) Climate Data Store (CDS). (18 June 2025), doi:10.24381/cds.68d2bb30
# Terms of Use: See Copernicus C3S/CAMS License agreement
# cadence: 1 month
# Pixel size: 11132 meters
# Band 1: total_precipitation_sum

# import libraries
import ee
import geopandas as gpd
import pandas as pd
import time
import os

# set working directory
os.chdir('C:/Users/Jesus/Box/PROPESCA/BIENPESCA')

# authenticate & initialize earth engine
ee.Authenticate()
ee.Initialize(project='ee-sst-j-felix')

# load the shapefile
office = gpd.read_file('shapefiles/coastal_sf_20km_land_only.shp')
office.columns = [
    "state_id", "state", "office_id", "office", "locality", "cvegeo",
    "status", "stat_abr", "mun_id", "local_id", "climate", "latitud",
    "longitud", "altitud", "letter_id", "population", "male_pop",
    "feml_pop", "opccupied_households", "obs_id", "municipio",
    "long", "lat", "geometry"
]

# get the image collection
prec_collection = (
    ee.ImageCollection("ECMWF/ERA5_LAND/DAILY_AGGR")
    .filterDate('2006-01-01', '2024-12-31')
    .select('total_precipitation_sum')
)

def create_geom_feature(row):
    area = row.geometry
    ee_area = ee.Geometry(area.__geo_interface__)
    return ee.Feature(ee_area).set({'office_id': row.office_id})


# apply the conversion
features = [create_geom_feature(row) for idx, row in office.iterrows()]
fc = ee.FeatureCollection(features)

# define years and months
years = list(range(2006, 2025))
months = list(range(1, 13))

# define the prec extraction function
def extract_monthly_stats(year, month):
    start = ee.Date.fromYMD(year, month, 1)
    end = start.advance(1, 'month')
    mean_img = prec_collection.filterDate(start, end).mean()

    def extract_for_feature(f):
        mean = mean_img.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=f.geometry(),
            scale=1000,
            maxPixels=1e8
        )
        std = mean_img.reduceRegion(
            reducer=ee.Reducer.stdDev(),
            geometry=f.geometry(),
            scale=1000,
            maxPixels=1e8
        )
        return f.set({
            'year': year,
            'month': month,
            'avg_prec': mean.get('total_precipitation_sum'),
            'sd_prec': std.get('total_precipitation_sum'),
        })

    return fc.map(extract_for_feature)

all_years_dfs = []
for y in years:
    print(f"Processing year {y}...")
    monthly_results = []
    for m in months:
        monthly_results.append(extract_monthly_stats(y, m))
    year_fc = ee.FeatureCollection(monthly_results).flatten()

    # get year data locally
    year_data = year_fc.getInfo()
    features = year_data['features']
    rows = [f['properties'] for f in features]
    df_year = pd.DataFrame(rows)
    all_years_dfs.append(df_year)

    # save yearly CSV immediately (optional)
    # df_year.to_csv(f"C:/Users/Jesus/Box/PROPESCA/BIENPESCA/data/clean data/coastal_precip_{y}.csv", index=False)

    print(f"Saved year {y} data with {len(df_year)} rows.")

# optional: combine all years into one DataFrame and save
final_df = pd.concat(all_years_dfs, ignore_index=True)
final_df.to_csv("C:/Users/Jesus/Box/PROPESCA/BIENPESCA/data/clean data/coastal_precip_2006_2024_all.csv", index=False)
print("Saved combined CSV for all years.")

# End of script
# Note: The script processes each year and month, extracting the mean and standard deviation of precipitation.
