const { App } = require("@slack/bolt");
const axios = require("axios");
require("dotenv").config();

const app = new App({
    token: process.env.SLACK_BOT_TOKEN,
    signingSecret: process.env.SLACK_SIGNING_SECRET
});

app.command("/query", async ({ command, ack, say }) => {
    try {
        await ack();

        getUser(command.text).then(user_id => {
            findConversation(user_id).then(user_msg_arr => {
                const sentiment_body = {
                    inputs: user_msg_arr
                }

                axios.post('https://961d-2600-1700-31b1-4c00-18d3-35f9-696f-b015.ngrok.io/sentiment', 
                    sentiment_body
                )
                .then(response => {
                    console.log("FOR SENTIMENT:\n", response.data);
                }, error => {
                    console.log(error);
                });
                console.log(user_msg_arr);
                
                // search
                const search_body = {
                    inputs: user_msg_arr,
                    query: "joy"
                }

                axios.post('https://961d-2600-1700-31b1-4c00-18d3-35f9-696f-b015.ngrok.io/search', 
                    search_body
                )
                .then(response => {
                    console.log("FOR SEARCHING:\n", response.data);
                }, error => {
                    console.log(error);
                });
                console.log(user_msg_arr);
            });
        });
    } catch (error) {
        console.log("error while trying to carry out command");
        console.log(error)
    }
});

async function getUser(cmd_text) {
    const reg= /(<@)(.*)(\|.*>)/;
    const match = cmd_text.match(reg);
    return `${match[2]}`;
}

async function findConversation(user_id) {
    const user_messages = [];
    try {
        const result = await app.client.conversations.list({
            token: process.env.SLACK_BOT_TOKEN
        });

        for(const channel_obj of result.channels) {
            try {
                const message_result_obj = await app.client.conversations.history({
                    channel: channel_obj.id
                });

                for(const msg_obj of message_result_obj.messages) {
                    if(msg_obj.user === user_id) {
                        user_messages.push(msg_obj.text);
                    }
                }
            } catch(error) {
                console.log(error);
            }
        }
    } catch (error) {
        console.log(error);
    }

    return user_messages;
}

(async() => {
    const port = 3000

    await app.start(process.env.PORT || port);
    console.log(`Slack Bolt up and running on port ${port}`);
})();
