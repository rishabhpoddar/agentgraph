# AgentGraph

## Table of Contents
- [Overview](#overview)
- [Integrating the Node SDK](#integrating-the-node-sdk)
- [Integrating the Python SDK](#integrating-the-python-sdk)
- [Visualizing the Graph](#visualizing-the-graph)

This is a utility that manages LLM tool calls and creates a graph for your agent flows:
- Each node in the graph is one message in a conversation with an LLM (ex: system message -> user message -> assistant message)
- A node can have a sub graph if the LLM used tool calling in that turn. You can click on the node to view the list of tools called, their inputs and outputs, and visualize the tool call's sub graphs.

<img src="https://raw.githubusercontent.com/rishabhpoddar/agentgraph/refs/heads/main/images/1.jpeg" width="70%" >

<img src="https://raw.githubusercontent.com/rishabhpoddar/agentgraph/refs/heads/main/images/2.png" width="70%" >

<img src="https://raw.githubusercontent.com/rishabhpoddar/agentgraph/refs/heads/main/images/3.jpeg"  width="70%" >

## Overview
1. You need to integrate our SDK into your backend code, and wrap LLM calls with our wrapper function. This wrapper function will do tool calling, capture the LLM interactions, and store it in a folder that you specify, as a json file.
2. Each file can span just one LLM call (and its tool calls), or span across multiple LLM calls (and their tool calls). This is controlled by a `sessionId` string that you specify as part of the input to the wrapper function.
3. You can then visualize the graph for a json file by running the visualizer present in this repo.

Below are the steps on how to integrate our SDK into your code, and visualize the graph.

## Integrating the Node SDK

### Installation

Install the package using npm:
```bash
npm install --save @trythisapp/agentgraph
```

Add these environment variables to your `.env` file:

```
AGENT_GRAPH_OUTPUT_DIR=./agentgraph_output
AGENT_GRAPH_SAVE_OUTPUT=true
```

- `AGENT_GRAPH_OUTPUT_DIR`: The directory to save the output json files of the llm calls.
- `AGENT_GRAPH_SAVE_OUTPUT`: Whether to save the output json files of the llm calls or not.

**Important: We recommend that you set `AGENT_GRAPH_SAVE_OUTPUT` to `true` only in a development environment, and set it to `false` in a production environment. This is because we do not want to save output JSON files in the file system in production. We are working on storing the JSON files in a database instead, and when that is released, this can be enabled in production as well. Tool calling is not affected by this flag.**

### Use without tool calling

```ts
import { v4 } from 'uuid';
import OpenAI from "openai";
import { callLLMWithToolHandling } from "@trythisapp/agentgraph";

let openaiClient = new OpenAI({
    apiKey: process.env['OPENAI_API_KEY'],
});

const agentName = "my-agent"
const sessionId = v4(); // or it can be any other ID
let input: OpenAI.Responses.ResponseInput = [{role: "user", content: "Hello, how are you?"}];

let response = await callLLMWithToolHandling(agentName, sessionId, undefined, async (inp) => {
    return await openaiClient.responses.create({
        model: "gpt-4.1",
        input: inp,
    });
}, input, []);

console.log(response.output_text)
```

- In the above, we can see how we have wrapped a simple OpenAI call with `callLLMWithToolHandling` (the wrapper function) from our SDK.
- In this case, since there is no tool calling, the wrapper function will just capture the user message and the assistant reply, i.e. there will be only 2 nodes in the graph.
- You can also add a system message in the input, in which case, there will be 3 nodes in the graph.


## Integrating the Python SDK
Coming soon...

## Visualizing the Graph
