import os
import subprocess
import time
import math
import random

# init to logo image
IMAGE_DIRECTORY = "/home/smahtSticker/imgs/"
IMAGE = subprocess.Popen(["feh", "--hide-pointer", "-x", "-q", "-B", "black", "-g", "1920x480", IMAGE_DIRECTORY + "blank.png"])

# SETUP GPS:
import serial
import adafruit_gps
UART = serial.Serial("/dev/ttyS0", baudrate=9600, timeout=10)
GPS = adafruit_gps.GPS(UART)
UPDATE_DISTANCE = 25 # feet
LAST_UPDATE_LOCATION = 90, 135 #brrr
SLEEP_TIME = 5 # seconds
CURRENT_ZIP_CODE = 0

# SETUP OPENAI:
from dotenv import load_dotenv
from openai import OpenAI
load_dotenv()
CLIENT = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
)

# SETUP GEOPY
import geopy
from geopy.geocoders import Nominatim
LOCATOR = geopy.Nominatim(user_agent='smahtSticker')

# start open minded
CURRENT_POLITICAL_VIEWS = ""

# images - add more bumper stickers here
L_STICKERS = ["l1.png", "l2.png", "l3.png", "l4.png", "l5.png", "l6.png"]
C_STICKERS = ["c1.png", "c2.png", "c3.png", "c4.png", "c5.png", "c6.png"]

LAST_CHECK = time.monotonic()

def communicateWithOverlord(msg):
    chat_completion = CLIENT.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": "You are an expert on political views."
            },
            {
                "role": "user",
                "content": msg,
            }
        ],
        temperature=0,
        model="gpt-3.5-turbo",
    )
    return chat_completion.choices[0].message.content 

def calculateDistanceFromLastGpsUpdate(lat, lon):
    print(f"DEBUG: Calculating distance using Lat: {lat}  Lon: {lon}")
    # Radius of the Earth in kilometers
    R_km = 6371.0
    
    # Convert latitude and longitude from degrees to radians
    previous_lat = math.radians(LAST_UPDATE_LOCATION[0])
    previous_lon = math.radians(LAST_UPDATE_LOCATION[1])
    new_lat = math.radians(lat)
    new_lon = math.radians(lon)
    
    # Haversine formula
    dlon = new_lon - previous_lon
    dlat = new_lat - previous_lat
    a = math.sin(dlat / 2)**2 + math.cos(previous_lat) * math.cos(new_lat) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance_km = R_km * c
    
    # Convert distance from kilometers to feet
    R_ft = 6371.0 * 3280.84  # Radius of the Earth in feet
    distance_ft = distance_km * R_ft / R_km
    
    print(f"DEBUG: Distance from last update: {distance_ft}ft")
    return distance_ft

def getZipCode(latitude, longitude):
    print(f"DEBUG: Getting zip code for lat: {latitude}, long: {longitude}")
    location = LOCATOR.reverse((latitude,longitude))
    if 'address' in location.raw.keys():
      if 'postcode' in location.raw['address'].keys():
        return location.raw['address']['postcode']
    else:
      False

def updatePoliticalViews(zipcode):
    print(f"DEBUG: Zip code: {zipcode}")
    global CURRENT_POLITICAL_VIEWS
    global IMAGE

    msg = f"What is the most likely political view of the zip code {zipcode}? Responding with only one word, either 'Liberal' or 'Conservative'."
    update_required = True # setting to always update even if view hasn't changed.
    reply = communicateWithOverlord(msg)
    bumper_sticker = "blank.png"

    print(reply)
    
    if reply.lower().replace(".","") == "liberal":
        bumper_sticker =  random.choice(L_STICKERS)
        if CURRENT_POLITICAL_VIEWS != "L":
            CURRENT_POLITICAL_VIEWS = "L"
            update_required = True
    elif reply.lower().replace(".","") == "conservative":
        bumper_sticker =  random.choice(C_STICKERS)
        if CURRENT_POLITICAL_VIEWS != "C":
            CURRENT_POLITICAL_VIEWS = "C"
            update_required = True
    else:
        print("Error")
        return

    if update_required:
        print(bumper_sticker)
        IMAGE.kill()
        IMAGE = subprocess.Popen(["feh", "--hide-pointer", "-x", "-q", "-B", "black", "-g", "1920x480", IMAGE_DIRECTORY + bumper_sticker])


while True:
    GPS.update()

    current = time.monotonic()
    if current - LAST_CHECK >= 1.0:
        LAST_CHECK = current
        if not GPS.has_fix:
            print('Waiting for fix...')
            time.sleep(1)
            continue
        
        if calculateDistanceFromLastGpsUpdate(GPS.latitude, GPS.longitude) > UPDATE_DISTANCE:
            LAST_UPDATE_LOCATION = GPS.latitude, GPS.longitude
            zip_code = getZipCode(GPS.latitude, GPS.longitude)
            print(f"DEBUG: Last update location changed: {LAST_UPDATE_LOCATION}")
            if zip_code != False and zip_code != CURRENT_ZIP_CODE:
                print("DEBUG: Calling an update.")
                updatePoliticalViews(zip_code)
                CURRENT_ZIP_CODE = zip_code
            else:
                print("DEBUG: Still in the same area")
        else:
            print(f"DEBUG: Haven't move more than {UPDATE_DISTANCE}ft since last gps update")