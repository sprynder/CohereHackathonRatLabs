const { App } = require("@slack/bolt");
const axios = require("axios");
require("dotenv").config();

const app = new App({
  token: process.env.SLACK_BOT_TOKEN,
  signingSecret: process.env.SLACK_SIGNING_SECRET,
});

const CONSTANTS = {
  NUM_MSG_PER_SEARCH: 5,
  USER_REGEX: /(<@)(.*)(\|.*>)/,
};

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

      findConversation().then((msg_obj_arr) => {
        const body = {
          inputs: msg_obj_arr.map((val) => val.text),
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
              sendGenericErrorMessage(command);
              console.log(error);
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
          inputs: user_msg_arr.map((msg_obj) => msg_obj.text),
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
              sendGenericErrorMessage(command);
              console.log(error);
            }
          );
      });
    } else if (command.text && !isTaggedUser(command.text)) {
      app.client.chat.postEphemeral({
        text: `Hmm that didn't seem to work, try to @someone`,
        token: process.env.SLACK_BOT_TOKEN,
        channel: command.channel_id,
        user: command.user_id,
      });
    }
  } catch (error) {
    sendGenericErrorMessage(command);
    console.log(error);
  }
});

app.command("/smart-search", async ({ command, ack, say }) => {
  try {
    await ack();
    let num = command.text.substring(0,command.text.indexOf(" "));
    let message = command.text.substring(command.text.indexOf(" ")+1)
    let parsed_int = parseInt(num, 10);
    if(!isNaN(parsed_int)){
    app.client.chat.postEphemeral({
      text: `I'm on it! Finding similar messages to '${message}'...`,
      token: process.env.SLACK_BOT_TOKEN,
      channel: command.channel_id,
      user: command.user_id,
    });
    let permalinks = [];
    const five_msg_obj_arr = await findConversationMeta(message, num);
    for (let i = 0; i < five_msg_obj_arr.length; i += 1) {
      const permalink_response = await app.client.chat.getPermalink({
        token: process.env.SLACK_BOT_TOKEN,
        channel: five_msg_obj_arr[i].channelID,
        message_ts: five_msg_obj_arr[i].ts,
      });
      permalinks.push(permalink_response.permalink);
    }
    blocks = [
      {
        type: "section",
        text: {
          type: "plain_text",
          emoji: true,
          text: "Here are the top "+num+" closest messages from the channels I'm in:",
        },
      },
      {
        type: "divider",
      },
    ];
    for (let i = 0; i < five_msg_obj_arr.length; i++) {
      let link = "<" + permalinks[i] + "|Go to message "+(i+1).toString()+": >";
      blocks.push({
        type: "section",
        text: {
          type: "mrkdwn",
          text: link + " " + five_msg_obj_arr[i].text,
        },
      });
    }

    app.client.chat.postEphemeral({
      text: "Here's the most similar messages I've found in order: \n",
      token: process.env.SLACK_BOT_TOKEN,
      channel: command.channel_id,
      user: command.user_id,
      blocks: blocks,
    });
}
else{
    app.client.chat.postEphemeral({
        text: "Please enter a valid number of search results!\n",
        token: process.env.SLACK_BOT_TOKEN,
        channel: command.channel_id,
        user: command.user_id,
      });
}
  } catch (error) {
    sendGenericErrorMessage(command);
    console.log(error);
  }
});

async function sendGenericErrorMessage(command) {
  app.client.chat.postEphemeral({
    text: "Oops! Something's gone wrong on my end, please try again \n",
    token: process.env.SLACK_BOT_TOKEN,
    channel: command.channel_id,
    user: command.user_id,
  });
}

async function findConversationMeta(command_text, num) {
  let five_msg_obj_arr = [];
  const msg_obj_arr = await findConversation();

  const search_body = {
    inputs: msg_obj_arr.map((msg_obj) => msg_obj.text),
    query: command_text,
    number: num
  };

  const response = await axios.post(
    process.env.DEFAULT_ENDPOINT + process.env.SEARCH_ENDPOINT,
    search_body
  );

  for (const msg of response.data.slice(0, num)) {
    let msg_content = msg.substring(msg.indexOf(":") + 2);
    for (const msg_cur of msg_obj_arr) {
      if (msg_cur.text === msg_content) {
        five_msg_obj_arr.push(msg_cur);
        break;
      }
    }
  }
  const ret_arr = five_msg_obj_arr;
  return ret_arr;
}

function isTaggedUser(command_text) {
  return CONSTANTS.USER_REGEX.test(command_text);
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
    ["neutral", ["neutral"]],
  ]);

  for (const [key, value] of imposed_map) {
    data_dict.set(key, 0);
  }

  //console.log(sentiment_api_resp.length);
  for (const resp of sentiment_api_resp) {
    for (const [key, value] of imposed_map) {
      if (value.find((val) => val === resp.prediction)) {
        //console.log(resp.prediction, key);
        data_dict.set(key, data_dict.get(key) + 1);
        break;
      }
    }
  }

  const sorted_data_dict = new Map(
    [...data_dict.entries()].sort((a, b) => b[1] - a[1])
  );
  return sorted_data_dict;
}

function getUser(cmd_text) {
  const match = cmd_text.match(CONSTANTS.USER_REGEX);
  return `${match[2]}`;
}

async function findConversation(user_id = "") {
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
            user_messages_ts.push({ ...msg_obj, channelID: channel_obj.id });
          }
        }
      } catch (error) {
        sendGenericErrorMessage(command);
        console.log(error);
      }
    }
  } catch (error) {
    sendGenericErrorMessage(command);
    console.log(error);
  }

  return user_messages_ts;
}

(async () => {
  const port = 80;

  await app.start(process.env.PORT || port);
  console.log(`Slack Bolt up and running on port ${port}`);
})();
