import requests
import time
import re
from getpass import getpass
from pymongo import MongoClient


# MongoDB connection
def connect_mongodb(mongodb_user, mongodb_pass, app_name):
    #validate inputs
    if not re.match("^[A-Za-z0-9_]+$", mongodb_user):
        print("Error Invalid MongoDB username. ")
        return None, None
    if not re.match("^[A-Za-z0-9_]+$", app_name):
        print("Error Invalid MongoDB app name. ")
        return None, None
    mongodb_uri = f'mongodb+srv://{mongodb_user}:{mongodb_pass}@riotapi.tkwuexp.mongodb.net/?retryWrites=true&w=majority&appName={app_name}'
    mongo_client = MongoClient(mongodb_uri)
    db = mongo_client.get_database(input("Enter desired database name to store match IDs: "))
    #Collection name where match IDs will be stored
    match_collection = db.match_IDs
    return match_collection, db


# Gets summoner information
def get_puuid(summoner_name, tagline, api_key):
    api_url = f'https://americas.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{summoner_name}/{tagline}?api_key={api_key}'
    resp = requests.get(api_url)
    if resp.status_code == 200:
        summoner_information = resp.json()
        puuid = summoner_information['puuid']
        return puuid

    else:
        print(f"Error: {resp.status_code} - {resp.text}")
        if resp.status_code == 400:
            print(f"No player found for {summoner_name}")
        if resp.status_code == 429:
            print("Rate limit exceeded, try again in 2 minutes.")
            time.sleep(120)
            return
        return None


# Stores match IDs into desired database, handling duplicates and various potential errors
def store_match_ids(puuid, num_matches, api_key, gamemode, match_collection):
    api_url = f'https://americas.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?type={gamemode}&count={num_matches}&api_key={api_key}'
    match_list_resp = requests.get(api_url)
    count_new_matches = 0
    count_duplicate_matches = 0
    if match_list_resp.status_code != 200:
        print(f"Error getting match list: {match_list_resp.status_code} - {match_list_resp.text}")
        return None
    else:
        match_ids = match_list_resp.json()
        for match_id in match_ids:
            if match_collection.find_one({"match_id": match_id}):
                #print("Match already registered")
                count_duplicate_matches += 1
                continue
            else:
                match_collection.insert_one({"match_id": match_id})
                count_new_matches += 1
        print(f"{count_duplicate_matches} duplicate match IDs found. ")
        print(f"{count_new_matches} new match IDs inserted into the {match_collection.name} collection. ")


# Clears collection based on user inputs, handling exceptions
def clear_collection(puuid, num_matches, api_key, gamemode, match_collection):
    clear_input = input("Enter 'y' or 'n' to clear chosen collection: ")
    match clear_input:
        case 'y':
            if match_collection.count_documents({}) == 0:
                store_match_ids(puuid, num_matches, api_key, gamemode, match_collection)
            else:
                match_collection.delete_many({})
                store_match_ids(puuid, num_matches, api_key, gamemode, match_collection)
        case 'n':
            if clear_input == 'n':
                print("Storing match IDs in MongoDB...")
                store_match_ids(puuid, num_matches, api_key, gamemode, match_collection)
        case _:
            print("Invalid input, please try again.")
            clear_collection(puuid, num_matches, api_key, gamemode, match_collection)

def get_average_match_duration(api_key, match_collection):
    match_ids = match_collection.distinct('match_id')

    total_duration_seconds = 0
    valid_matches_count = 0

    for match_id in match_ids:
        api_url = f'https://americas.api.riotgames.com/lol/match/v5/matches/{match_id}?api_key={api_key}'
        match_resp = requests.get(api_url)

        time.sleep(1)

        if match_resp.status_code == 429:
            print("Rate limit exceeded, try again in 2 minutes.")
            time.sleep(120)
            return

        if match_resp.status_code != 200:
            print(f"Error getting match details for {match_id}: {match_resp.status_code} - {match_resp.text}")
            continue
        match_data = match_resp.json()
        match_duration_seconds = match_data['info']['gameDuration']
        total_duration_seconds += match_duration_seconds
        valid_matches_count += 1

    if valid_matches_count > 0:
        average_duration_seconds = total_duration_seconds / valid_matches_count
        return average_duration_seconds
    else:
        print("No valid matches found.")
        return None


def main():
    start_time = time.time()
    api_key = getpass("Enter your Riot API key: ")


    #MongoDB connection
    mongodb_user = input("Enter your MongoDB username: ")
    mongodb_pass = getpass("Enter your MongoDB password: ")
    app_name = input("Enter your MongoDB app name: ")
    match_collection, db = connect_mongodb(mongodb_user, mongodb_pass, app_name)  # assigns db and collection where match IDs will be stored

    # Summoner info
    summoner_info = input("Enter the summoner information: ")
    summoner_name = summoner_info.split("#", 1)[0]
    tagline = summoner_info.split("#", 1)[1]

    #print(summoner_name + " " + tagline)

    puuid = get_puuid(summoner_name, tagline, api_key)
    if not puuid:
        return

    num_matches = 100
    gamemode = input("Enter desired gamemode (ranked, normal, tourney, or tutorial): ")
    gamemode_list = ['ranked', 'normal', 'tourney', 'tutorial']
    while gamemode not in gamemode_list and not isinstance(gamemode, str):
        gamemode = input("Invalid input, please enter desired gamemode (ranked, normal, tourney, or tutorial): ")
    clear_collection(puuid, num_matches, api_key, gamemode, match_collection)

    print("Calculating average match duration...")
    avg_duration = get_average_match_duration(api_key, match_collection)
    if avg_duration:
        print(f"Average match duration in {gamemode} mode: {avg_duration} seconds")

    end_time = time.time()  # Record the end time
    runtime = end_time - start_time  # Calculate the runtime
    print(f"Total Runtime: {runtime:.2f} seconds")


if __name__ == '__main__':
    main() # run in terminal
