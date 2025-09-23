import json
import os
import pandas as pd
import multiprocessing
from multiprocessing import Pool
from itertools import combinations, product

# -------------------------
# Load data
# -------------------------
def load_data():
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
    
    # Check for owned characters first, fallback to available characters
    char_file = "ownedCharacters.json" if os.path.exists(os.path.join(data_dir, "ownedCharacters.json")) else "availChars.json"
    
    # Load character data
    with open(os.path.join(data_dir, char_file), 'r', encoding='utf-8') as f:
        avail_chars = json.load(f)
    
    # Load relation types and groups
    with open(os.path.join(data_dir, "relationTypes.json"), 'r', encoding='utf-8') as f:
        rel_types = json.load(f)
    
    with open(os.path.join(data_dir, "relationGroups.json"), 'r', encoding='utf-8') as f:
        rel_groups = json.load(f)
    
    # Create DataFrames
    avail_chars_df = pd.DataFrame(avail_chars)
    rel_types_df = pd.DataFrame(rel_types)
    rel_groups_df = pd.DataFrame(rel_groups)
    
    # Ensure consistent column naming
    if 'char_id' in avail_chars_df.columns and 'chara_id' not in avail_chars_df.columns:
        avail_chars_df = avail_chars_df.rename(columns={'char_id': 'chara_id'})
    
    return avail_chars_df, rel_types_df, rel_groups_df

# -------------------------
# Precompute relation type → characters
# -------------------------
def precompute_relation_type_to_chars(rel_groups_df):
    reltype_to_chars = {}
    for _, group in rel_groups_df.groupby('relation_type'):
        rel_type = group['relation_type'].iloc[0]
        char_ids = group['chara_id'].unique()
        reltype_to_chars[rel_type] = set(char_ids)
    return reltype_to_chars

# -------------------------
# Compatibility function
# -------------------------
def calculate_compatibility(rel_types_dict, reltype_to_chars, main_char, O, K, Z, J, X, Y):
    comp = 0
    for row in rel_types_dict:
        rel_type = row["relation_type"]
        points = row["relation_point"]
        group = reltype_to_chars.get(rel_type, set())

        if O in group and K in group:
            comp += points
        if O in group and main_char in group:
            comp += points
            if Z in group and Z != main_char:
                comp += points
            if J in group and J != main_char:
                comp += points
        if K in group and main_char in group:
            comp += points
            if X in group and X != main_char:
                comp += points
            if Y in group and Y != main_char:
                comp += points

    return comp

# -------------------------
# Helper function to calculate parent pair score with main_char
# -------------------------
def calculate_parent_score(rel_types_dict, reltype_to_chars, main_char, O, K):
    score = 0
    for row in rel_types_dict:
        rel_type = row["relation_type"]
        points = row["relation_point"]
        group = reltype_to_chars.get(rel_type, set())

        if O in group and K in group:
            score += points
        if O in group and main_char in group:
            score += points
        if K in group and main_char in group:
            score += points
    return score

# -------------------------
# Worker function
# -------------------------
def process_single_parent_pair(O, K, rel_types_dict, reltype_to_chars, main_char, gp_combinations):
    """Process a single parent pair and return its results."""
    results = []

    # Get grandparent combinations for this parent pair
    gp_O_combinations, gp_K_combinations = gp_combinations

    # Calculate the total combinations for this pair for progress tracking
    total_combinations = len(gp_O_combinations) * len(gp_K_combinations)

    # Combine O-side and K-side grandparents
    for (Z, J), (X, Y) in product(gp_O_combinations, gp_K_combinations):
        score = calculate_compatibility(rel_types_dict, reltype_to_chars, main_char, O, K, Z, J, X, Y)
        results.append(({"O": O, "Z": Z, "J": J, "K": K, "X": X, "Y": Y}, score))

    return results, total_combinations

# -------------------------
# Parallel brute-force
# -------------------------
def parallel_brute_force(avail_chars_df, rel_types_df, reltype_to_chars, main_char, workers=multiprocessing.cpu_count() // 2):
    """
    Perform parallel brute-force calculation using half the available CPU cores by default.
    
    Args:
        workers: Number of worker processes (defaults to half the available CPU cores)
    """
    char_ids = avail_chars_df["chara_id"].tolist()

    # Remove main character from available character IDs
    char_ids = [cid for cid in char_ids if cid != main_char]

    # All parent pairs O != K
    all_parent_pairs = list(combinations(char_ids, 2))

    # Calculate scores for all parent pairs and select top 3
    scored_pairs = []
    for pair in all_parent_pairs:
        score = calculate_parent_score(rel_types_df.to_dict('records'), reltype_to_chars, main_char, pair[0], pair[1])
        scored_pairs.append((pair, score))

    # Sort by score descending and take top 3
    scored_pairs.sort(key=lambda x: x[1], reverse=True)
    all_parent_pairs = [pair for pair, score in scored_pairs[:3]]

    # Print the top 3 parent scores for reference
    print("Top 3 parent pair scores:")
    for pair, score in scored_pairs[:3]:
        print(f"  {pair}: {score}")

    print(f"Total combinations to calculate: {len(all_parent_pairs)} parent pairs")

    # Precompute all grandparent combinations upfront and calculate total
    total_combinations = 0
    all_gp_combinations = []
    for O, K in all_parent_pairs:
        # Get all possible grandparent pairs for O (excluding O and main_char)
        gp_O_combinations = list(combinations([c for c in char_ids if c != O and c != main_char], 2))
        # Get all possible grandparent pairs for K (excluding K and main_char)
        gp_K_combinations = list(combinations([c for c in char_ids if c != K and c != main_char], 2))
        all_gp_combinations.append((gp_O_combinations, gp_K_combinations))
        total_combinations += len(gp_O_combinations) * len(gp_K_combinations)

    print(f"Total grandparent combinations to calculate: {total_combinations}")

    # Create a list of tasks with precomputed grandparent combinations
    tasks = []
    for (O, K), gp_combinations in zip(all_parent_pairs, all_gp_combinations):
        tasks.append((O, K, rel_types_df.to_dict('records'), reltype_to_chars, main_char, gp_combinations))

    # Process tasks in parallel
    with Pool(workers) as pool:
        # Process all parent pairs in parallel
        results = pool.starmap(process_single_parent_pair, tasks)

    # Combine all results
    all_results = []
    for result, count in results:
        all_results.extend(result)

    print(f"Processed {len(all_results)} grandparent combinations")

    all_results.sort(key=lambda x: x[1], reverse=True)
    return all_results[:16]

# -------------------------
# Main execution
# -------------------------
if __name__ == "__main__":
    print("Loading data...")
    avail_chars_df, rel_types_df, rel_groups_df = load_data()
    
    main_char = 1052  # Update this with your main character ID
    main_char_name = avail_chars_df[avail_chars_df['chara_id'] == main_char]['en_name'].iloc[0]
    print(f"\nUsing main character: {main_char_name}")
    
    # Precompute relation type to characters mapping
    reltype_to_chars = precompute_relation_type_to_chars(rel_groups_df)
    
    # Run the calculation
    WORKERS = multiprocessing.cpu_count() // 2
    print(f"\nUsing {WORKERS} workers for parallel processing...")
    print("\nStarting calculation...")
    top_results = parallel_brute_force(avail_chars_df, rel_types_df, reltype_to_chars, main_char, WORKERS)

    # Map IDs to names for display
    id_to_name = dict(zip(avail_chars_df["chara_id"], avail_chars_df["en_name"]))
    
    # Prepare results for display
    results = []
    for fam, score in top_results:
        try:
            results.append({
                "Parent 1 (O)": f"{id_to_name.get(fam['O'], fam['O'])} ({fam['O']})",
                "GP1 (Z)": f"{id_to_name.get(fam['Z'], fam['Z'])} ({fam['Z']})",
                "GP2 (J)": f"{id_to_name.get(fam['J'], fam['J'])} ({fam['J']})",
                "Parent 2 (K)": f"{id_to_name.get(fam['K'], fam['K'])} ({fam['K']})",
                "GP3 (X)": f"{id_to_name.get(fam['X'], fam['X'])} ({fam['X']})",
                "GP4 (Y)": f"{id_to_name.get(fam['Y'], fam['Y'])} ({fam['Y']})",
                "Score": score
            })
        except KeyError as e:
            print(f"Warning: Missing character ID in mapping: {e}")
    
    # Display results
    if results:
        top_df = pd.DataFrame(results)
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', 1000)
        pd.set_option('display.max_colwidth', 30)
        print("\nTop combinations:")
        print(top_df)
    else:
        print("\nNo valid combinations found.")
