const { App } = require("@slack/bolt");
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
