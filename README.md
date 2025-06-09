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

**IMPORTANT: We recommend that you set `AGENT_GRAPH_SAVE_OUTPUT` to `true` only in a development environment, and set it to `false` in a production environment. This is because we do not want to save output JSON files in the file system in production. We are working on storing the JSON files in a database instead, and when that is released, this can be enabled in production as well. Tool calling is not affected by this flag.**

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

### Use with simple tool calling

In this section, we will see how to add a simple tool call. The tool call implementation is not using an LLM.

```ts
import { v4 } from 'uuid';
import OpenAI from "openai";
import * as math from 'mathjs';
import { callLLMWithToolHandling } from "@trythisapp/agentgraph";

let openaiClient = new OpenAI({
    apiKey: process.env['OPENAI_API_KEY'],
});

const agentName = "my-agent"
const sessionId = v4(); // or it can be any other ID
let input: OpenAI.Responses.ResponseInput = [{role: "user", content: "What is 21341*42422?. Use the doMath tool if needed."}];

let response = await callLLMWithToolHandling(agentName, sessionId, undefined, async (inp) => {
    return await openaiClient.responses.create({
        model: "gpt-4.1",
        input: inp,
        tools: [{
            type: "function",
            strict: true,
            name: "doMath",
            description: "Use this tool when you need to do math (for things like calculating total or average calories etc). Example expressions: " + "'5.6 * (5 + 10.5)', '7.86 cm to inch', 'cos(80 deg) ^ 4'.",
            parameters: {
                type: 'object',
                properties: {
                    expression: {
                        type: 'string',
                        description: 'The mathematical expression to evaluate.',
                    },
                },
                required: ['expression'],
                additionalProperties: false
            },
        }]
    });
}, input, [{
    toolName: "doMath",
    impl: async ({ expression }: { expression: string }) => {
        let response = math.evaluate(expression);
        if (typeof response === "string") {
            return response;
        } else if (typeof response === "number") {
            return response.toString();
        } else {
            return JSON.stringify(response);
        }
    },
    convertErrorToString: (err: any) => {
        return err.message;
    }
}]);

console.log(response.output_text)
```

- In this case, we have added a tool for the LLM to do math:
    - We tell the LLM about the tool in the prompt.
    - We tell the OpenAI SDK about the tool in the `tools` parameter. We describe the input.
    - We pass in an implementation of the tool in the array passed to the `callLLMWithToolHandling` function (last parameter). Here, we get the expression from the LLM, as a string and use the `mathjs` library to evaluate it. We return a string as a response for the LLM to use.
- The `callLLMWithToolHandling` function will automatically handle tool calling if needed, and return the final response from the LLM. It will also capture the tool calls and store it a part of the JSON file generated for this LLM call. So here, we will have 2 nodes in the main graph (user message -> assistant message) and then when you click on the user message node, it will show a sub graph with the tool call node, which will contain just the tool input (value of `expression`) and output (return value from the `impl` function). So 2 nodes in total.


## Integrating the Python SDK
Coming soon...

## Visualizing the Graph
