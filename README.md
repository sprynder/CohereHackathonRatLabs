# RatLabs - Found in Translation
Cohere Semantic Search 2022
Intelligent Slack bot for navigating mono and multi lingual messaging

## Problem
In the world of information, it can be difficult to moderate and keep up with communication. Particularly, finding relevant messages and data becomes tedious due to poor search functionalities, so finding words and phrases can be quite difficult if you forget the exact wording. It is doubly difficult if you're in a multinational team, with people speaking different languages, not only do you have to remember the exact phrase, but the exact phrase in a different language!

## Solution
To solve this, we've come up with our product: **Found in Translation** (FiT). FiT is an intelligent bot that not only provides semantic searching, but also sentiment analysis for users or servers. Semantic searching is essentially searching by meaning versus searching by strictly the words given. For example, searching for "food" with semantic search might give "here are some resturaunts near you", but with regular search, will yield something like "2005 food poisoning", quite different results.


## Flask API (venv)
Venv contains the code for the Flask API.

The actual code for the API is in the app.py file. We used Flask to develop an API that interfaces with our two cohere models. The first one is a embedding model (using the multilingual model) where we send in a list of chat messages as the embeddings. We then use Pinecone to store the vectors and use dotproduct similarity to find the most relevant messages to the user query.

The other model is a custom classification model trained using the Google GoEmotion dataset. We feed in a user's/chat's message history and get the resulting classifications, which are then processed and averaged in the slackbot. 

The clear.py file is used to manually clear the Pinecone Vector Database in case of needing a restart.
This API is dockerized and hosted on an Azure Container Instance.

## Slack Bolt API
For this project, we used the Slack Bolt API, a wrapper on Node, to host the bot. We take in data retrieved by Slack API and form POST requests to pass into the RatLabs API - or backend. 

## Sentiment Classification Models:

| Training Dataset | Co:Here Model API ID |
| ------------- | ------------- |
| Goemotions1 | 0cb7d924-400e-4be8-9403-0a90fa25af42 |
| Goemotions2 | 877d44cc-dbfa-4d50-9240-3cdb530e1394 |
| Goemotions3 | 3fdaa93a-31f9-4b79-a9e4-a4219b36765e |
| Full Set with condensed labels | e30636c1-d065-45d7-bae8-6ce61b4d4fcd |
