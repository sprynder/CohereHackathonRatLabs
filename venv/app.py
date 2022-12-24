from flask import Flask, jsonify, request
import cohere
from cohere.classify import Example
import numpy as np
import pinecone
import jsonpickle
app = Flask(__name__)

# emotion_file = open('emotions.json', encoding="utf8")
# emotion_data = json.load(emotion_file)
# examples = []
# for i in range(len(emotion_data)):
#     examples.append(Example(emotion_data[i]['text'], emotion_data[i]['label']))

co = cohere.Client("")
pinecone.init("", environment='us-west1-gcp')
co_sentiment = cohere.Client('')

@app.route("/search", methods = ['POST'])
def ss():
    
    res = request.get_json()
    inputs = res['inputs']
    
    embeds = co.embed(
        texts=inputs,
        model='small',
        truncate='LEFT'
    ).embeddings

    shape = np.array(embeds).shape
    index_name = 'cohere-pinecone-search'

    if index_name not in pinecone.list_indexes():
        pinecone.create_index(
            index_name,
            dimension=shape[1],
            metric='dotproduct'
        )

    # connect to index
    index = pinecone.Index(index_name)
    batch_size = 128

    ids = [str(i) for i in range(shape[0])]
    # create list of metadata dictionaries
    meta = [{'text': text} for text in inputs]

    # create list of (id, vector, metadata) tuples to be upserted
    to_upsert = list(zip(ids, embeds, meta))

    for i in range(0, shape[0], batch_size):
        i_end = min(i+batch_size, shape[0])
        index.upsert(vectors=to_upsert[i:i_end])

    # let's view the index statistics
    # print(index.describe_index_stats())

    query = res['query']

    # create the query embedding
    xq = co.embed(
        texts=[query],
        model='small',
        truncate='LEFT'
    ).embeddings

    # query, returning the top 5 most similar results
    res = index.query(xq, top_k=5, include_metadata=True)
    ret = []

    for match in res['matches']:
        ret.append(f"{match['score']:.2f}: {match['metadata']['text']}")
    return jsonify(ret)

@app.route("/sentiment", methods = ['POST'])
def sentiment():
    print(request)
    print(type(request))
    res = request.get_json()
    inputs = res['inputs']
    classify = co_sentiment.classify(
        model='',
        inputs = inputs
    )
    ret = classify.classifications
    return jsonpickle.encode(ret)


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=80)