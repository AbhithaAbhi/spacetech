import sgp4
from sgp4.earth_gravity import wgs72
from sgp4.io import twoline2rv
import pyproj
from datetime import datetime, timedelta
import concurrent.futures

# Step 1: Get Satellite Location
def get_satellite_positions(tle_lines, num_minutes=1440):
    positions = []
    tle_sets = [tle_lines[i:i + 3] for i in range(0, len(tle_lines), 3)]

    for tle_set in tle_sets:
        satellite = twoline2rv(tle_set[1], tle_set[2], wgs72)
        current_time = datetime.utcnow()

        for i in range(num_minutes):
            time = current_time + timedelta(minutes=i)
            position, _ = satellite.propagate(
                time.year, time.month, time.day, time.hour,
                time.minute, time.second + time.microsecond / 1e6
            )
            positions.append((time, position))

    return positions

# Read TLE data from the file
with open('30000sats.txt', 'r') as file:
    tle_data = file.readlines()

# Step 1: Get Satellite Location
positions = get_satellite_positions(tle_data)

# Print out some positions for debugging
for position in positions[:10]:
    print("Position:", position)

# Extract position coordinates
pos_x = [pos[0] for _, pos in positions]
pos_y = [pos[1] for _, pos in positions]
pos_z = [pos[2] for _, pos in positions]

# Step 2: Convert data to Lat-Long-Alt format
ecef = pyproj.CRS("EPSG:4978")
lla = pyproj.CRS("EPSG:4326")
transformer = pyproj.Transformer.from_crs(ecef, lla, always_xy=True)
lons, lats, alts = transformer.transform(pos_x, pos_y, pos_z)

# Step 3: Find when it is going over a certain lat-long region
user_coordinates = [
    (16.56673, 103.48196, 16.76673, 103.68196),  # Bounding box around the point
    # Add more bounding boxes if needed
]

def is_in_bounding_box(coord, box):
    lat, lon = coord
    lat_min, lon_min, lat_max, lon_max = box
    return lat_min <= lat <= lat_max and lon_min <= lon <= lon_max

filtered_data = []
for (time, position), (lat_min, lon_min, lat_max, lon_max) in zip(positions, user_coordinates):
    lat, lon, _ = position  # Unpack the position tuple (x, y, z)
    print("Checking position:", time, lat, lon)
    if is_in_bounding_box((lat, lon), (lat_min, lon_min, lat_max, lon_max)):
        filtered_data.append((time, (lat, lon)))

# Step 4: Optimize code using concurrent.futures
def process_satellite(args):
    time, coord, box = args
    if is_in_bounding_box(coord, box):
        lat, lon = coord
        return f"Time: {time}, Latitude: {lat}, Longitude: {lon}"
    return None

filtered_data_optimized = []
with concurrent.futures.ProcessPoolExecutor() as executor:
    args_list = [
        (time, coord, box) for (time, coord), box in zip(filtered_data, user_coordinates)
    ]
    results = executor.map(process_satellite, args_list)
    filtered_data_optimized = [result for result in results if result]

# Print or process the filtered data
for result in filtered_data_optimized:
    print(result, flush=True)
