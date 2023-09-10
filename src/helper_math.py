from Bio import pairwise2, SeqIO
from Bio.pairwise2 import format_alignment
from collections import defaultdict
import csv
import pandas as pd
import os
import re


def calculate_similarity(seq1, seq2):
    alignments = pairwise2.align.globalxx(seq1, seq2)
    best_alignment = alignments[0]
    score = best_alignment[2]
    #print(best_alignment)
    #print(format_alignment(*alignments[0]))
    max_length = max(len(seq1), len(seq2))
    return (score / max_length) * 100, best_alignment


def calculate_results(fasta_files, gene_name):

    results = defaultdict(dict)

    # Perform alignment
    print(f'Calculating results for {gene_name}...')
    for fasta_file in fasta_files:
        variant_name = fasta_file.split("_")[1]
        print("Processing file: " + variant_name + ".")
        records = list(SeqIO.parse(fasta_file, "fasta"))

        homo_sapiens_seq = None
        for record in records:
            if re.match(r'^ENS[T|P|G|E|FM|R]\d+$', record.id):  # Homo sapiens
                homo_sapiens_seq = record.seq
                break

        if homo_sapiens_seq is not None:
            for record in records:
                if not re.match(r'^ENS[T|P|G|E|FM|R]\d+$', record.id):  # Exclude Homo sapiens
                    species = record.id
                    similarity, best_alignment = calculate_similarity(homo_sapiens_seq, record.seq)
                    results[variant_name][species] = {
                        'similarity': similarity,
                        'score': best_alignment[2],
                        'start': best_alignment[3],
                        'end': best_alignment[4]
                    }
        else:
            print(f"No Homo sapiens sequence found in {fasta_file}. Skipping.")

    delete_csv_file(f'results/{gene_name}_alignment_results.csv')

    # Map animal names to species prefixes
    species_mapping = {}
    with open("data/species_prefixes.txt", "r") as f:
        next(f)  # Skip the header
        for line in f:
            prefix, name = line.strip().split("\t")
            species_mapping[prefix] = name

    # Save alignment scores to .csv
    print(f'Saving {gene_name} results to .csv..')
    with open(f"results/{gene_name}_alignment_results.csv", 'w', newline='') as csvfile:
        fieldnames = ['Variant Name', 'Species', 'Similarity', 'Score', 'Start', 'End']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for variant_name, species_data in results.items():
            for species, data in species_data.items():
                species_prefix = max((k for k in species_mapping.keys() if species.startswith(k)), key=len, default=None)
                species_name = species_mapping.get(species_prefix, species)
                writer.writerow({
                    'Variant Name': variant_name,
                    'Species': species_name,
                    'Similarity': data['similarity'],
                    'Score': data['score'],
                    'Start': data['start'],
                    'End': data['end']
                })
    print(f'Finished saving {gene_name} results to .csv!')


def perform_analysis(gene_name):
    delete_csv_file(f"results_analysis/{gene_name}_aggregated_similarity.csv")
    print(f'Performing analysis for {gene_name}..')

    df = pd.read_csv(f"results/{gene_name}_alignment_results.csv")
    grouped_by_species_df = df.groupby('Species').agg({'Similarity': 'sum'}).reset_index()
    grouped_by_species_df_sorted = grouped_by_species_df.sort_values(by='Similarity', ascending=False)
    grouped_by_species_df_sorted.to_csv(f"results_analysis/{gene_name}_aggregated_similarity", index=False)

    print(f'Finished performing analysis for {gene_name}!')


def delete_all_csv_files(directory):
    print(f'Deleting all .csv files in {directory}..')
    for filename in os.listdir(directory):
        if filename.endswith(".csv"):
            os.remove(os.path.join(directory, filename))


def delete_csv_file(filename):
    print(f'Deleting {filename} if exists..')
    if os.path.exists(filename):
        os.remove(filename)


