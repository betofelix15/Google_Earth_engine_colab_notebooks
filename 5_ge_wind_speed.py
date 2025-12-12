# This is the information for the dataset for wind speed

# Name: ECMWF_ERA5_LAND_DAILY_AGGR ERA5-Land Daily Aggregated - ECMWF Climate Reanalysis
# Link: https://developers.google.com/earth-engine/datasets/catalog/
# Citation: Muñoz Sabater, J., (2019): ERA5-Land monthly averaged data from 1981 to present. Copernicus Climate Change Service (C3S) Climate Data Store (CDS). (18 June 2025), doi:10.24381/cds.68d2bb30
# Terms of Use: Please acknowledge the use of ERA5-Land as stated in the Copernicus C3S/CAMS License agreement:
# 5.1.1 Where the Licensee communicates or distributes Copernicus Products to the public, the Licensee shall inform the recipients of the source by using the following or any similar notice: 'Generated using Copernicus Climate Change Service Information [Year]'.

# 5.1.2 Where the Licensee makes or contributes to a publication or distribution containing adapted or modified Copernicus Products, the Licensee shall provide the following or any similar notice: 'Contains modified Copernicus Climate Change Service Information [Year]';

# Any such publication or distribution covered by clauses 5.1.1 and 5.1.2 shall state that neither the European Commission nor ECMWF is responsible for any use that may be made of the Copernicus Information or Data it contains.

# cadence: 1 Month
# Pixel size: 11132 meters
# Band 1: u_component_of_wind_10m
# Band 1 Unit: m/s
# Band 1 Description: Eastward component of the 10m wind. It is the horizontal speed of air moving towards the east, at a height of ten meters above the surface of the Earth, in meters per second. Care should be taken when comparing this variable with observations, because wind observations vary on small space and time scales and are affected by the local terrain, vegetation and buildings that are represented only on average in the ECMWF Integrated Forecasting System. This variable can be combined with the V component of 10m wind to give the speed and direction of the horizontal 10m wind.
# Band 2: v_component_of_wind_10m
# Band 2 Unit: m/s
# Band 2 Description: Northward component of the 10m wind. It is the horizontal speed of air moving towards the north, at a height of ten meters above the surface of the Earth, in meters per second. Care should be taken when comparing this variable with observations, because wind observations vary on small space and time scales and are affected by the local terrain, vegetation and buildings that are represented only on average in the ECMWF Integrated Forecasting System. This variable can be combined with the U component of 10m wind to give the speed and direction of the horizontal 10m wind.


# import libraries
import ee
import geopandas as gpd
import pandas as pd
import os

# set working directory
os.chdir('C:/Users/Jesus/Box/PROPESCA/BIENPESCA')

# authenticate & initialize earth engine
ee.Authenticate()
ee.Initialize(project='ee-sst-j-felix')

# load the shapefile
office = gpd.read_file('shapefiles/office_points_latest.shp')
office.columns = [
    "state_id",  "state",    "office_id",  "office",   "locality",  "cvegeo",   "status",   "stat_abr",  "mun_id",
    "local_id",  "climate",  "latitud", "longitud",  "altitud",  "letter_id",  "population",  "male_pop",  "feml_pop",
    "opccupied_households",  "obs_id",   "municipio",  "geometry"]

# get the image collection (filter for date)
wind_collection = (
    ee.ImageCollection("ECMWF/ERA5_LAND/DAILY_AGGR")
    .filterDate('2006-01-01', '2024-12-31')
)

# Convert office into ee.FeatureCollection with 100 km buffe
def create_buffered_feature(row):
    coords = row.geometry.coords[0]
    ee_point = ee.Geometry.Point(coords)
    buffer = ee_point.buffer(100000)  # 100 km
    return ee.Feature(buffer).set({'office_id': row.office_id})


# Apply the conversion
features = [create_buffered_feature(row) for idx, row in office.iterrows()]
fc = ee.FeatureCollection(features)

# define years and months
years = list(range(2006, 2025))
months = list(range(1, 13))



def extract_monthly_stats(year, month):
    start = ee.Date.fromYMD(year, month, 1)
    end = start.advance(1, 'month')

    mean_img = wind_collection.filterDate(start, end).mean()

    def extract_for_feature(f):
        mean = mean_img.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=f.geometry(),
            scale=20000,  # You can adjust this scale as needed
            maxPixels=1e8
        )
        return f.set({
            'year': year,
            'month': month,
            'avg_east_wind_speed': mean.get('u_component_of_wind_10m'),
            'avg_north_wind_speed': mean.get('v_component_of_wind_10m')
        })

    return fc.map(extract_for_feature)

# Loop and export
for y in years:
    print(f"Processing year {y}...")

    # Merge all monthly FeatureCollections for the year
    monthly_results = [extract_monthly_stats(y, m) for m in months]

    year_fc = ee.FeatureCollection(monthly_results[0])
    for fc_month in monthly_results[1:]:
        year_fc = year_fc.merge(fc_month)

    # Set up export task
    task = ee.batch.Export.table.toDrive(
        collection=year_fc,
        description=f'wind_speed_{y}',
        driveFolder='BIENPESCA_exports',  # Replace with your actual Shared Drive folder name
        driveFileNamePrefix=f'wind_speed_{y}',
        fileFormat='CSV'
    )

    task.start()
    print(f" Export started for year {y}. Monitor at https://code.earthengine.google.com/tasks")

print("All export tasks submitted!")

