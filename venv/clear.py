import pinecone
pinecone.init("", environment='us-west1-gcp')
index_name = 'cohere-pinecone-search'
index = pinecone.Index(index_name)
index.delete(deleteAll=True)