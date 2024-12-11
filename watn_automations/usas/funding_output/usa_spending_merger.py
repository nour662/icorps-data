import os
import pandas as pd
import zipfile

"""
This program is intended to be used to go thorugh the USA Spending Records and merge all similiar files together. After downloading
all indetified companies award records from the USA Spending database, move all outputted folders together into a seperate folder. 
This script will go through that folder and merge together all Assistance Prime Award Summaries, Assistance Sub Awards, 
Contract Prime Award Summaries, and Contract Sub Awards, for all companies, into their own 4 seperate .csv files. 

The 4 .csv file output will be located within this master folder and they will be cleaned through the removal of all empty columns.
"""
#Locates the path to the USA Spending .zip folders
folder_path = (r'C:\Users\sluca\Downloads\USA_Spending')

os.chdir(folder_path)

#Creates empty lists to store record in
assistance_prime_award_list =  []
assistance_sub_award_list =  []
contract_prime_award_list = [] 
contract_sub_award_list =  []

#Sorts through the saved .zip files from the USA spending website
for zip_file in os.listdir(folder_path):
    if zip_file.endswith('.zip'):
        zip_path = os.path.join(folder_path, zip_file)

        # Gets the list of files in the .zip folders and sort them
        with zipfile.ZipFile(zip_path, 'r') as zips:
            csv_files = [file for file in zips.namelist() if file.endswith('.csv')]
            csv_files.sort() 

            for index, csv_file in enumerate(csv_files):
                with zips.open(csv_file) as placement:
                    df = pd.read_csv(placement)
                    
                    # Drop all-NaN columns before appending
                    df = df.dropna(axis=1, how='all')  # Removes columns that are completely NaN
                    
                    if index == 0:
                        assistance_prime_award_list.append(df)
                    elif index == 1:
                        assistance_sub_award_list.append(df)
                    elif index == 2:
                        contract_prime_award_list.append(df)
                    elif index == 3:
                        contract_sub_award_list.append(df)

# Concatenate all the lists into single DataFrames
assistance_prime_award = pd.concat(assistance_prime_award_list, ignore_index=True, sort=False)
assistance_sub_award = pd.concat(assistance_sub_award_list, ignore_index=True, sort=False)
contract_prime_award = pd.concat(contract_prime_award_list, ignore_index=True, sort=False)
contract_sub_award = pd.concat(contract_sub_award_list, ignore_index=True, sort=False)

# Save the merged DataFrames to separate CSV files
assistance_prime_award.to_csv('assistance_prime_award.csv', index=False)
assistance_sub_award.to_csv('assistance_sub_award.csv', index=False)
contract_prime_award.to_csv('contract_prime_award.csv', index=False)
contract_sub_award.to_csv('contract_sub_award.csv', index=False)