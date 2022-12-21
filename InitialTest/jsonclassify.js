const cohere = require('cohere-ai')
var json = require('./testjs2.json')

cohere.init('Y9FxEPgNOaSUnIshWdfHmtVRMNaLyX5sRawtmR5o')

async function model(){
    const response = await cohere.classify(json);
    return response;
}

////////////////////////////////////////////////////////////////
model().then((response)=>{
    console.dir(response.body, {depth: null});
});