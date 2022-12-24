const cohere = require('cohere-ai');
cohere.init('')


let inputs = ["mad cuz bad", "i hate sid","saydie sc=ucks"];

let examples = [
    {text: 'you are hot trash', label: 'Toxic'},
    {text: 'go to hell', label: 'Toxic'},
    {text: 'get rekt moron', label: 'Toxic'},
    {text: 'get a brain and use it', label: 'Toxic'},
    {text: 'say what you mean, you jerk.', label: 'Toxic'},
    {text: 'Are you really this stupid', label: 'Toxic'},
    {text: 'I will honestly kill you', label: 'Toxic'},
    {text: 'yo how are you', label: 'Benign'},
    {text: 'I\'m curious, how did that happen', label: 'Benign'},
    {text: 'Try that again', label: 'Benign'},
    {text: 'Hello everyone, excited to be here', label: 'Benign'},
    {text: 'I think I saw it first', label: 'Benign'},
    {text: 'That is an interesting point', label: 'Benign'},
    {text: 'I love this', label: 'Benign'},
    {text: 'We should try that sometime', label: 'Benign'},
    {text: 'You should go for it', label: 'Benign'}
  ]

async function model(){
const response = await cohere.classify({
  inputs: inputs,
  examples: examples}
);
return response;
}


////////////////////////////////////////////////////////////////
model().then((response)=>{
    console.dir(response.body, {depth: null});
});