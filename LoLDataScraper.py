import requests
import random
import matplotlib.pyplot as plt
import numpy as np
from scipy import stats
import pandas as pd

#insert API key
API_KEY = 'YOUR-API-KEY-GOES-HERE'

def get_summoner_info(summoner_name):
    api_url = f'https://na1.api.riotgames.com/lol/summoner/v4/summoners/by-name/{summoner_name}?api_key={API_KEY}'
    resp = requests.get(api_url)
    if resp.status_code == 200:
        return resp.json()
    else:
        print(f"Error: {resp.status_code} - {resp.text}")
        return None


def get_match_history(puuid, count: int, type):
    api_url = f'https://americas.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?type={type}&start=0&count={count}&api_key={API_KEY}'
    resp = requests.get(api_url)
    if resp.status_code == 200:
        return resp.json()
    else:
        print(f"Error: {resp.status_code} - {resp.text}")
        return None


def get_match_details(match_id):
    api_url = f'https://americas.api.riotgames.com/lol/match/v5/matches/{match_id}?api_key={API_KEY}'
    resp = requests.get(api_url)
    if resp.status_code == 200:
        return resp.json()
    else:
        print(f"Error: {resp.status_code} - {resp.text}")
        return None


def format_match_duration(duration_seconds):
    match_duration_minutes = duration_seconds // 60
    match_duration_seconds = duration_seconds % 60
    return f"{match_duration_minutes} minutes {match_duration_seconds:.3f} seconds"


def hypothesis_test(match_durations, mu):
    # Define null and alternative hypotheses
    mu_formatted = format_match_duration(mu)
    null_hypothesis = f"Null Hypothesis (H0): μ = {mu_formatted} ({mu} seconds)"
    alt_hypothesis = f"Alternative Hypothesis (H1): μ ≠ {mu_formatted} ({mu} seconds)"
    print(null_hypothesis)
    print(alt_hypothesis)

    # Compute test statistic (t-value)
    t_stat, _ = stats.ttest_1samp(match_durations, mu)
    print(f"T-statistic: {t_stat:.4f}")

    # Determine the p-value
    p_value = stats.t.sf(np.abs(t_stat), len(match_durations) - 1) * 2
    print(f"P-value: {p_value:.4f}")

    # Draw conclusions
    alpha = 0.05
    print(f"Reject the null only if p-value is less than alpha, {alpha}.")
    print("Outcome:")
    if p_value < alpha:
        print(f"{p_value} < {alpha} ∴ reject the null hypothesis.")
    else:
        print(f"{p_value} > {alpha} ∴ fail to reject the null hypothesis.")
    print()

    return p_value


def get_average_stats(summoner_name, sample_size, count, type, mu):
    player_info = get_summoner_info(summoner_name)
    if player_info:
        puuid = player_info['puuid']
        matches = get_match_history(puuid, count, type)
        if matches:
            try:
                random_matches = random.sample(matches, int(sample_size))
            except ValueError as e:
                print("Error:", e)
                print("Number of matches inputted exceeds the number of available matches.")
                return None

            match_durations = []
            match_ids = []
            total_kills = 0
            total_deaths = 0
            total_assists = 0
            total_gold_earned = 0
            for match_id in random_matches:
                match_data = get_match_details(match_id)
                if match_data:
                    match_duration_totalSeconds = match_data['info']['gameDuration']
                    match_durations.append(match_duration_totalSeconds)
                    match_ids.append(match_id)
                    participant_stats = next((p for p in match_data['info']['participants'] if p['puuid'] == puuid),
                                             None)
                    if participant_stats:
                        total_kills += participant_stats['kills']
                        total_deaths += participant_stats['deaths']
                        total_assists += participant_stats['assists']
                        total_gold_earned += participant_stats['goldEarned']
            avg_duration = sum(match_durations) // int(sample_size)
            avg_kda = (total_kills + total_assists) / total_deaths if total_deaths > 0 else (
                        total_kills + total_assists)
            avg_gold_earned = total_gold_earned / int(sample_size)
            print()
            print("Data gathered: ")
            print(f"Average Game Duration: {format_match_duration(avg_duration)} ({avg_duration} seconds)")
            print(f"Average KDA: {avg_kda:.2f}")
            print(f"Average Gold Earned: {avg_gold_earned:.0f}")
            plot_match_durations(match_durations, avg_duration, int(sample_size))
            create_table(match_ids, match_durations, summoner_name)
            print()
            print("Hypothesis Testing:")
            p_value = hypothesis_test(match_durations, float(mu))
            return p_value
        else:
            print("No match data available.")
    else:
        print("Failed to retrieve summoner information.")




def plot_match_durations(match_durations, avg_duration, sample_size):
    plt.figure(figsize=(10, 6))
    plt.bar(range(len(match_durations)), match_durations)
    plt.axhline(y=avg_duration, color='r', linestyle='--',
                label=f'Average Duration: {format_match_duration(avg_duration)}')
    plt.xlabel('Match Index')
    plt.ylabel('Game Duration (seconds)')
    plt.title(f'Game Durations for {sample_size} Random Matches')
    plt.legend()
    plt.show()


def create_table(match_ids, match_durations, summoner_name):
    df = pd.DataFrame({'Match ID': match_ids, 'Match Index': range(1, len(match_durations) + 1),
                       'Game Duration (seconds)': match_durations})
    excel_filename = f'{summoner_name}_match_durations.xlsx'
    df.to_excel(excel_filename, index=False)
    print(f"Excel file '{excel_filename}' created for summoner '{summoner_name}'.")


def main():
    summoner_name = input("Enter the summoner name: ")
    type = input("Enter desired gamemode (ranked, normal, tourney, or tutorial): ")
    typeList = ['ranked', 'normal', 'tourney', 'tutorial']
    if type not in typeList:
        type = input("Invalid input, please enter desired gamemode (ranked, normal, tourney, or tutorial): ")
    count = int(input("Enter number of matches (max 100): "))
    if count > 100 or count <= 0:
        count = int(input("Invalid input, please enter a number less than 101 and greater than 0: "))
    sample_size = int(input("Enter sample size: "))
    if sample_size > count:
        sample_size = int(input("Invalid input, please enter a number less than the number of matches: "))
    mu = float(input("Enter average game duration in seconds, μ, desired: "))
    if mu is not float or int:
        mu = float(input("Invalid input, please enter average game duration in seconds, μ, desired: "))

    print("Gathering information, please wait...")
    p_value = get_average_stats(summoner_name, sample_size, count, type, mu)


if __name__ == "__main__":
    main()
