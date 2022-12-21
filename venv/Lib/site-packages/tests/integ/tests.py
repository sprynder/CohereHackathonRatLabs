import pinecone
def test_stuff():
    pinecone.init(api_key="7e9bf571-48f5-46c0-8a0f-7069a05ee926",environment="internal-alpha")
    pinecone.create_index("rt",768)
    index = pinecone.GRPCIndex("rt")
    index.describe_index_stats()