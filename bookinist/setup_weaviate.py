import weaviate
import weaviate.classes.config as wvc
import pandas as pd
import os
from dotenv import load_dotenv

load_dotenv()

def setup_weaviate():
    client = weaviate.connect_to_local(
        headers={
            "X-OpenAI-Api-Key": os.getenv("OPENAI_API_KEY"),
            "X-Nvidia-Api-Key": os.getenv("NVIDIA_API_KEY")
        }
    )

    collection_name = "Restaurant"

    # Delete if exists to start fresh
    if client.collections.exists(collection_name):
        client.collections.delete(collection_name)

    # Create collection
    client.collections.create(
        name=collection_name,
        vectorizer_config=wvc.Configure.Vectorizer.text2vec_openai(
            model="text-embedding-3-small"
        ),
        properties=[
            wvc.Property(name="name", data_type=wvc.DataType.TEXT),
            wvc.Property(name="gault_millau_review", data_type=wvc.DataType.TEXT),
            wvc.Property(name="phone", data_type=wvc.DataType.TEXT, skip_vectorization=True),
            wvc.Property(name="address", data_type=wvc.DataType.TEXT, skip_vectorization=True),
            wvc.Property(name="website", data_type=wvc.DataType.TEXT, skip_vectorization=True),
            wvc.Property(name="original_url", data_type=wvc.DataType.TEXT, skip_vectorization=True),
            wvc.Property(name="original_description", data_type=wvc.DataType.TEXT, skip_vectorization=True),
        ]
    )
    
    # Load data
    df = pd.read_pickle("restaurants_data.pkl")
    # Replace NaN with empty strings to avoid errors
    df = df.fillna("")
    
    collection = client.collections.get(collection_name)
    
    with collection.batch.dynamic() as batch:
        for _, row in df.iterrows():
            batch.add_object(
                properties={
                    "name": row["name"],
                    "gault_millau_review": row["gault_millau_review"],
                    "phone": row["phone"],
                    "address": row["address"],
                    "website": row["website"],
                    "original_url": row["original_url"],
                    "original_description": row["original_description"]
                }
            )
    
    if collection.batch.failed_objects:
        print(f"Failed to load {len(collection.batch.failed_objects)} objects")

    client.close()
    print(f"Collection {collection_name} created and populated with {len(df)} records.")

if __name__ == "__main__":
    setup_weaviate()
