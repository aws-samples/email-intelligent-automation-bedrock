import chromadb
from sentence_transformers import SentenceTransformer
import pandas as pd
import os
#import openai
import numpy as np

# Set up ChromaDB with local file system persistent storage
persist_directory = './chromadb_network_logs'
if not os.path.exists(persist_directory):
    os.makedirs(persist_directory)

# Initialize ChromaDB client with persistence
client = chromadb.PersistentClient(path=persist_directory)

collection_name = "network_logs_collection"
if not client.get_or_create_collection(name=collection_name):
    collection = client.create_collection(collection_name)
else:
    collection = client.get_collection(collection_name)

# Load a pre-trained sentence transformer model for embeddings
model = SentenceTransformer('all-mpnet-base-v2')

# Load the CSV file containing network logs
csv_file_path = './network_logs.csv'  # Replace with your CSV file path
df = pd.read_csv(csv_file_path)

# Concatenate all relevant columns into a single text for each row
df['combined_text'] = df.astype(str).agg(' '.join, axis=1)

# Extract the combined text and original columns as metadata
documents = df['combined_text'].tolist()
metadata = df.drop(columns=['combined_text']).to_dict(orient='records')

# Create embeddings for the concatenated text
embeddings = model.encode(documents)

# Convert embeddings to lists
embeddings = [embedding.tolist() for embedding in embeddings]

# Prepare the data for ingestion
data_to_ingest = [
    {
        "id": str(i), 
        "embedding": embeddings[i], 
        "text": documents[i], 
        "metadata": metadata[i]
    } 
    for i in range(len(documents))
]

# Ingest the data into the collection
for item in data_to_ingest:
    collection.add(
        embeddings=[item['embedding']],
        documents=[item['text']],
        metadatas=[item['metadata']],
        ids=[item['id']]
    )

print(f"Ingested {len(documents)} rows from the CSV file into the collection '{collection_name}'")

