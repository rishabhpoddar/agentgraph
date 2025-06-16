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

TODO:.. image

### Query 2: "How many users do I have?"
This query requires counting the number of rows in the `users` table. So the agent first calls the `SQLAgent` to convert the query into a SQL query, and then calls the `DatabaseAgent` to execute the query. The graph for this is:

TODO:.. image

From here, it is easy to imagine how the graph will look like for more complex scenarios, involving more tools and agents.

## How to integrate AgentGraph with your backend code?

TODO:..