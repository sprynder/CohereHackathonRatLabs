const { App } = require("@slack/bolt");
const axios = require("axios");
require("dotenv").config();

const app = new App({
  token: process.env.SLACK_BOT_TOKEN,
  signingSecret: process.env.SLACK_SIGNING_SECRET,
});

app.command("/sentiment", async ({ command, ack, say }) => {
  try {
    await ack();
    // if no user is specified, get sentiment distribution of the entire chat history
    if (!command.text) {
      app.client.chat.postEphemeral({
        token: process.env.SLACK_BOT_TOKEN,
        channel: command.channel_id,
        user: command.user_id,
        text: "I'm on it! Scanning sentiment of all channels I'm in now...",
      });

      findConversation().then((msg_arr) => {
        const body = {
          inputs: msg_arr,
        };

        axios
          .post(
            process.env.DEFAULT_ENDPOINT + process.env.SENTIMENT_ENDPOINT,
            body
          )
          .then(
            (response) => {
              const parsed_data = parseDataBySentiment(response.data);
              for (let [key, value] of parsed_data) {
                parsed_data.set(key, value / response.data.length);
              }
              let output = "";
              for (const [key, value] of parsed_data) {
                output +=
                  " - " +
                  key +
                  ": " +
                  Math.round(value * 100).toString() +
                  "%\n";
              }
              blocks = [
                {
                  type: "section",
                  text: {
                    type: "plain_text",
                    emoji: true,
                    text: "Here's the sentiment breakdown for all channels I'm in:",
                  },
                },
                {
                  type: "divider",
                },
                {
                  type: "section",
                  text: {
                    type: "plain_text",
                    emoji: true,
                    text: output,
                  },
                },
              ];
              app.client.chat.postEphemeral({
                text: "",
                token: process.env.SLACK_BOT_TOKEN,
                channel: command.channel_id,
                user: command.user_id,
                blocks: blocks,
              });
            },
            (error) => {
              console.log(error.code);
            }
          );
      });
    }

    // if the user is specified
    if (command.text) {
      const user_id = getUser(command.text);
      app.client.chat.postEphemeral({
        token: process.env.SLACK_BOT_TOKEN,
        channel: command.channel_id,
        user: command.user_id,
        text: `I'm on it! Scanning sentiment of <@${user_id}> now...`,
      });
      findConversation(user_id).then((user_msg_arr) => {
        const body = {
          inputs: user_msg_arr,
        };

        axios
          .post(
            process.env.DEFAULT_ENDPOINT + process.env.SENTIMENT_ENDPOINT,
            body
          )
          .then(
            (response) => {
              const parsed_data = parseDataBySentiment(response.data);
              console.log(response.data.length);
              for (let [key, value] of parsed_data) {
                parsed_data.set(key, value / response.data.length);
              }
              let output = "";
              for (const [key, value] of parsed_data) {
                output +=
                  " - " +
                  key +
                  ": " +
                  Math.round(value * 100).toString() +
                  "%\n";
              }

              blocks = [
                {
                  type: "section",
                  text: {
                    type: "plain_text",
                    emoji: true,
                    text: "Here's the sentiment breakdown for all channels I'm in:",
                  },
                },
                {
                  type: "divider",
                },
                {
                  type: "section",
                  text: {
                    type: "plain_text",
                    emoji: true,
                    text: output,
                  },
                },
              ];
              app.client.chat.postEphemeral({
                text: `Here's the sentiment breakdown for <@${user_id}>:\n`,
                token: process.env.SLACK_BOT_TOKEN,
                channel: command.channel_id,
                user: command.user_id,
                blocks: blocks,
              });
            },
            (error) => {
              console.log(error.code);
            }
          );
      });
    }
  } catch (error) {
    console.log("error while trying to carry out command");
    console.log(error);
  }
});

app.command("/smart-search", async ({ command, ack, say }) => {
  try {
    await ack();

    // detect if a user is mentioned
    app.client.chat.postEphemeral({
      token: process.env.SLACK_BOT_TOKEN,
      channel: command.channel_id,
      user: command.user_id,
      text: `I'm on it! Finding similar messages to '${command.text}'...`,
    });
    // say(`I'm on it! Finding similar messages to '${command.text}'...`);
    findConversation().then((msg_arr) => {
      const search_body = {
        inputs: msg_arr,
        query: command.text,
      };

      axios
        .post(
          process.env.DEFAULT_ENDPOINT + process.env.SEARCH_ENDPOINT,
          search_body
        )
        .then(
          (response) => {
            const top_five_messages = response.data.slice(0, 5);
            let output = "";
            let index = 0;
            for (const msg of top_five_messages) {
              output +=
                index.toString() +
                ": " +
                msg.substring(msg.indexOf(":") + 2) +
                "\n";
              index += 1;
            }
            blocks = [
              {
                type: "section",
                text: {
                  type: "plain_text",
                  emoji: true,
                  text: "Here's the sentiment breakdown for all channels I'm in:",
                },
              },
              {
                type: "divider",
              },
              {
                type: "section",
                text: {
                  type: "plain_text",
                  emoji: true,
                  text: output,
                },
              },
            ];
            app.client.chat.postEphemeral({
              text: "Here's the most similar messages I've found in order: \n",
              token: process.env.SLACK_BOT_TOKEN,
              channel: command.channel_id,
              user: command.user_id,
              blocks: blocks,
            });
          },
          (error) => {
            console.log(error.code);
          }
        );
    });
  } catch (error) {
    console.log("error while trying to carry out command");
    console.log(error);
  }
});

function isTaggedUser(command_text) {
  const reg = /(<@)(.*)(\|.*>)/;
  return reg.test(command_text);
}

function parseDataBySentiment(sentiment_api_resp) {
  // given as array of objects
  const data_dict = new Map();
  for (const resp of sentiment_api_resp) {
    if (data_dict.has(resp.prediction)) {
      data_dict.set(resp.prediction, data_dict.get(resp.prediction) + 1);
    } else {
      data_dict.set(resp.prediction, 1);
    }
  }
  const sorted_data_dict = new Map(
    [...data_dict.entries()].sort((a, b) => b[1] - a[1])
  );
  return sorted_data_dict;
}

function getUser(cmd_text) {
  const reg = /(<@)(.*)(\|.*>)/;
  const match = cmd_text.match(reg);
  return `${match[2]}`;
}

async function findConversation(user_id = "") {
  const user_messages = [];
  try {
    const result = await app.client.conversations.list({
      token: process.env.SLACK_BOT_TOKEN,
    });

    for (const channel_obj of result.channels) {
      try {
        const message_result_obj = await app.client.conversations.history({
          channel: channel_obj.id,
        });

        for (const msg_obj of message_result_obj.messages) {
          if (
            (msg_obj.user === user_id || !user_id) &&
            !msg_obj.bot_id &&
            msg_obj.subtype != "channel_purpose" &&
            msg_obj.subtype != "channel_join"
          ) {
            user_messages.push(msg_obj.text);
          }
        }
      } catch (error) {
        console.log(error);
      }
    }
  } catch (error) {
    console.log(error);
  }

  return user_messages;
}

(async () => {
  const port = 80;

  await app.start(process.env.PORT || port);
  console.log(`Slack Bolt up and running on port ${port}`);
})();
