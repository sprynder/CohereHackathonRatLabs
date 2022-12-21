import pinecone
pinecone.init("909a3195-602e-46c2-b603-a0f44f1183d7", environment='us-west1-gcp')
index_name = 'cohere-pinecone-search'
index = pinecone.Index(index_name)
index.delete(deleteAll=True)