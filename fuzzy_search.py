import pandas as pd
from fuzzywuzzy import process, fuzz
from difflib import SequenceMatcher
from pyproj import Transformer


transformer = Transformer.from_crs("EPSG:3067", "EPSG:4326", always_xy=True)

def transform_coordinates(x, y):
    lon, lat = transformer.transform(x, y)
    return lat, lon

def advanced_hybrid_scorer(query, choice):
    ratio_score = fuzz.ratio(query, choice)  # General similarity
    partial_score = fuzz.partial_ratio(query, choice)  # Strong substring matching
    token_score = fuzz.token_set_ratio(query, choice)  # Handles extra/missing words
    wratio_score = fuzz.WRatio(query, choice)  # General similarity with weights

    # Compute substring similarity using SequenceMatcher (better than 'query in choice')
    substring_match = SequenceMatcher(None, query, choice).ratio() * 100  

    # Weights (Adjust these!)
    ratio_weight = 0.1
    partial_weight = 0.4
    token_weight = 0.1
    wratio_weight = 0.2 # Slightly reduced
    first_letter_weight = 0.2 # New weight for first letter similarity

    final_score = (ratio_score * ratio_weight) + (partial_score * partial_weight) + \
                  (token_score * token_weight) + (wratio_score * wratio_weight)

    # First Letter Similarity (Improved)
    first_letter_similarity = 0
    first_letter_threshold = 66
    if query and choice:  # Check for empty strings
        min_len = min(len(query), len(choice))
        first_letters_query = query[:min_len].lower() # Extract and lowercase first letters
        first_letters_choice = choice[:min_len].lower()

        first_letter_match_ratio = SequenceMatcher(None, first_letters_query, first_letters_choice).ratio()
        first_letter_similarity = first_letter_match_ratio * 120
          # New threshold for first letter similarity

    if first_letter_similarity > first_letter_threshold: # Only add boost if above threshold
          final_score += first_letter_similarity * first_letter_weight  # Add weighted similarity

    return min(final_score, 100)

def fuzzy_search(data, column_name, query, threshold=80):
    if column_name not in data.columns:
        return []

    column_data = data[column_name].dropna()  # Remove NaN values
    if column_data.empty:
        return []

    results = []
    for name, score, index in process.extract(query, column_data, scorer=advanced_hybrid_scorer, limit=100):
        if score >= threshold:
            x, y = data['x'].iloc[index], data['y'].iloc[index]
            # Transform coordinates if they are valid (not NaN)
            if pd.notna(x) and pd.notna(y):
                lon, lat = transformer.transform(x, y)  # Convert to EPSG:4326
            else:
                lon, lat = None, None  # Keep None if no coordinates exist
            #results.append({
            result = {
                "Nimi": name,
                "Kunta": data.iloc[index]["Kunta"],  # Get corresponding municipality
                "Similarity Score": round(score,1),
                'x': lon,  # Transformed Longitude
                'y': lat   # Transformed Latitude
            }
        
            if column_name == "suomi":
                result["Language"] = "suomi"
            elif column_name == "ruotsi":
                result["Language"] = "ruotsi"
            results.append(result)
    return results


def startswith_search(data, column_name, query):
    column_data_original = data[column_name]
    column_data_lower = column_data_original.astype(str).str.lower()
    query_lower = query.lower()

    results = []

    for index, original_value in column_data_original.items():
        if original_value.lower().startswith(query_lower):
            x, y = data['x'].iloc[index], data['y'].iloc[index]
            # Transform coordinates if they are valid (not NaN)
            if pd.notna(x) and pd.notna(y):
                lon, lat = transformer.transform(x, y)  # Convert to EPSG:4326
            else:
                lon, lat = None, None  # Keep None if no coordinates exist

            results.append({
                'Nimi': original_value,
                'Kunta': data['Kunta'].iloc[index],
                'Language': "suomi" if column_name == "suomi" else "ruotsi",
                'x': lon,  # Transformed Longitude
                'y': lat   # Transformed Latitude
            })
        
    
    return results

def contains_search(data, column_name, query):
    """
    Perform a 'contains' search on the specified column.
    Returns results where the query is a substring of the column values.
    """
    # Ensure case-insensitive search
    column_data_original = data[column_name]
    column_data_lower = column_data_original.astype(str).str.lower()
    query_lower = query.lower()

    # Find matching rows
    matching_rows = data[column_data_lower.str.contains(query_lower, na=False)].copy()
    results=[]
    for index in range(len(matching_rows)):
            x, y = data['x'].iloc[index], data['y'].iloc[index]
            # Transform coordinates if they are valid (not NaN)
            if pd.notna(x) and pd.notna(y):
                lon, lat = transformer.transform(x, y)  # Convert to EPSG:4326
            else:
                lon, lat = None, None  # Keep None if no coordinates exist

            results.append({
                'Nimi': matching_rows[column_name].iloc[index],
                'Kunta': data['Kunta'].iloc[index],
                'Language': "suomi" if column_name == "suomi" else "ruotsi",
                'x': lon,  # Transformed Longitude
                'y': lat   # Transformed Latitude
            })

    return results
