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
    if (!command.text) {
      app.client.chat.postEphemeral({
        text: "I'm on it! Scanning sentiment of all channels I'm in now...",
        token: process.env.SLACK_BOT_TOKEN,
        channel: command.channel_id,
        user: command.user_id,
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

    if (isTaggedUser(command.text)) {
      const user_id = getUser(command.text);
      app.client.chat.postEphemeral({
        text: `I'm on it! Scanning sentiment of <@${user_id}> now...`,
        token: process.env.SLACK_BOT_TOKEN,
        channel: command.channel_id,
        user: command.user_id,
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
    } else {
      app.client.chat.postEphemeral({
        text: `Hmm that didn't seem to work, try to @someone`,
        token: process.env.SLACK_BOT_TOKEN,
        channel: command.channel_id,
        user: command.user_id,
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

    app.client.chat.postEphemeral({
      text: `I'm on it! Finding similar messages to '${command.text}'...`,
      token: process.env.SLACK_BOT_TOKEN,
      channel: command.channel_id,
      user: command.user_id,
    });
    const conv_meta = await findConversationMeta(command.text);
    let five_msg_arr = conv_meta[0];
    let five_msg_arr_all = conv_meta[1];
    let permalinks = [];
    for (let i = 0; i < five_msg_arr_all.length; i += 1) {
      let temp_msg = five_msg_arr_all[i];
    const perma_response =  await app.client.chat.getPermalink({
          token: process.env.SLACK_BOT_TOKEN,
          channel: temp_msg.channelID,
          message_ts: temp_msg.ts,
    })
    permalinks.push(perma_response.permalink);
    }
    blocks = [
        {
          type: "section",
          text: {
            type: "plain_text",
            emoji: true,
            text: "Here are the top 5 closes messages from the channels I'm in:",
          },
        },
        {
          type: "divider",
        }]
    let output = [];
    let index = 0;
    for (let i =0; i < 5;i++)
    {
        output.push("");
        output[i] += five_msg_arr[i]
        let link = "<"+permalinks[i]+"|Result "+ i.toString() + ": "+">"
        console.log(link);
        blocks.push({ type: "section",
        text: {
          type: "mrkdwn",
          text:  link+" "+output[i],
        }
    })
    }

    
      app.client.chat.postEphemeral({
        text: "Here's the most similar messages I've found in order: \n",
        token: process.env.SLACK_BOT_TOKEN,
        channel: command.channel_id,
        user: command.user_id,
        blocks: blocks,
      });
  } catch (error) {
    console.log("error while trying to carry out command");
    console.log(error);
  }
});

async function findPermalinks() {}

async function findConversationMeta(command_text) {
  let five_msg_arr = [];
  let five_msg_arr_all = [];
  const msg_arr_all = await findConversationTS();
  let msg_arr = [];
  for (const msg of msg_arr_all) {
    msg_arr.push(msg.text);
  }
  const search_body = {
    inputs: msg_arr,
    query: command_text,
  };
  const response = await axios.post(
    process.env.DEFAULT_ENDPOINT + process.env.SEARCH_ENDPOINT,
    search_body
  );
  const top_five_messages = response.data.slice(0, 5);
  for (const msg of top_five_messages) {
    let msg_content = msg.substring(msg.indexOf(":") + 2);
    five_msg_arr.push(msg_content);
    for (const msg_cur of msg_arr_all) {
      if (msg_cur.text === msg_content) {
        five_msg_arr_all.push(msg_cur);
        break;
      }
    }

  }
  const ret_arr = [five_msg_arr, five_msg_arr_all];
  return ret_arr;
}

function isTaggedUser(command_text) {
  const reg = /(<@)(.*)(\|.*>)/;
  return reg.test(command_text);
}

function parseDataBySentiment(sentiment_api_resp) {
  const data_dict = new Map();
  const imposed_map = new Map([
    ["anger", ["anger", "annoyance", "disapproval"]],
    ["disgust", ["disgust"]],
    ["fear", ["fear", "nervousness"]],
    [
      "joy",
      [
        "joy",
        "amusement",
        "approval",
        "excitement",
        "gratitude",
        "love",
        "optimism",
        "relief",
        "pride",
        "admiration",
        "desire",
        "caring",
      ],
    ],
    [
      "sadness",
      ["sadness", "disappointment", "embarrassment", "grief", "remorse"],
    ],
    ["suprise", ["suprise", "realization", "confusion", "curiosity"]],
  ]);

  for (const [key, value] of imposed_map) {
    data_dict.set(key, 1);
  }

  for (const resp of sentiment_api_resp) {
    for (const [key, value] of imposed_map) {
      if (value.find((val) => val === resp.prediction)) {
        data_dict.set(key, data_dict.get(key) + 1);
      }
    }
  }

  console.log(data_dict);

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
            // console.log(msg_obj);
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

async function findConversationTS(user_id = "") {
  const user_messages_ts = [];
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
            // console.log(msg_obj);
            user_messages_ts.push({...msg_obj, channelID:channel_obj.id});
          }
        }
      } catch (error) {
        console.log(error);
      }
    }
  } catch (error) {
    console.log(error);
  }

  return user_messages_ts;
}

(async () => {
  const port = 80;

  await app.start(process.env.PORT || port);
  console.log(`Slack Bolt up and running on port ${port}`);
})();
