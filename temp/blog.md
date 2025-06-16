# How to Visually Debug Multi-AI Agent Flows

Multi-AI agent flows represent a paradigm shift in software development, characterized by two key features:

- **Collaborative Intelligence**: Multiple AI agents work in concert to achieve a common objective, leveraging their individual strengths and capabilities.

- **Dynamic Decision Making**: Unlike traditional software where logic flows are predetermined, these systems employ AI-driven tool calling that dynamically determines the execution path based on real-time context and requirements.

The dynamic nature of tool calling presents a significant challenge: understanding the flow of logic becomes increasingly complex as you interact with the system. A single query might trigger no tool calls, while another could initiate a cascade of nested interactions where AI agents themselves trigger additional tool calls. This complexity makes it difficult to track and debug the system's behavior.

To address this challenge, I'm excited to introduce an open-source library, called [AgentGraph](https://github.com/rishabhpoddar/agentgraph), that seamlessly integrates with your Python or Node.js backend. This powerful tool captures and visualizes LLM interactions and tool calls in real-time, presenting them as an interactive graph that makes the flow of logic crystal clear.

## What does the graph look like?

Let's take a simple example to illustrate this: I want to build an agent that can query my database based on an input query. This agent has access to two tools:
1. SQLAgent: A tool that converts the natural language query into a SQL query
2. DatabaseAgent: A tool that executes the SQL query and returns the results

We will go into the details of how to make such a system in the next section, but before that, let's see how the agent graph looks like for various queries:

### Query 1: "Hi there!"
This query has nothing to do with extracting information from the database, so no tool calls are made. The graph for this is:

TODO: <Insert image 5>

### Query 2: "How many users do I have?"
This query requires counting the number of rows in the `users` table. So the agent first calls the `SQLAgent` to convert the query into a SQL query, and then calls the `DatabaseAgent` to execute the query. The graph for main agent is:

TODO: <Insert image 1>

As you can see, the second bubble has the user input, the LLM used tools to answer the query, whose answer is shown in the third bubble. When we click on the second bubble, we can see the tool calls made by the LLM:

TODO: <Insert image 2>

The LLM first called the `SQLAgent` tool to convert the query into a SQL query, and then called the `DatabaseAgent` tool to execute the query. We can inspect the sub graph of the `SQLAgent` tool call by clicking on the row:

TODO: <Insert image 3>

In this sub graph, we can clearly see the tool input (orange box) and the output (green box), along with the exact LLM chat history. Here the tool is simple, but it is easy to imagine many steps in this tool call, where other tools could also be used (they would also show up in their respective sub graphs). Finally, we can go back and see the other tool call (`DatabaseAgent`) made by the main agent:

TODO: <Insert image 4>

This tool did not use an LLM, so here we just see the tool input and output.

## How to integrate AgentGraph with your backend code?

TODO:..