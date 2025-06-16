# How to Visually Debug Multi-AI Agent Flows

Multi-AI agent systems represent a significant advancement in software development, characterized by two fundamental aspects:

- **Collaborative Intelligence**: Multiple AI agents working together to achieve shared objectives, each contributing their specialized capabilities.

- **Dynamic Decision Making**: Systems that employ AI-driven tool calling to determine execution paths based on real-time context, rather than following predetermined logic flows.

The dynamic nature of these systems presents a unique challenge: understanding the flow of logic becomes increasingly complex as the system scales. A single query might trigger no tool calls, while another could initiate a cascade of nested interactions where AI agents themselves trigger additional tool calls. This complexity makes system behavior difficult to track and debug.

To address this challenge, I'm introducing [AgentGraph](https://github.com/rishabhpoddar/agentgraph), an open-source library that seamlessly integrates with Python or Node.js backends. This tool captures and visualizes LLM interactions and tool calls in real-time, presenting them as an interactive graph that provides clear visibility into system behavior.

## Visualizing Agent Interactions

Let's examine a practical example: a database query agent with access to two tools:
1. SQLAgent: Converts natural language queries into SQL
2. DatabaseAgent: Executes SQL queries and returns results

Here's how the agent graph visualizes different types of interactions:

### Query 1: "Hi there!"
A simple greeting that doesn't require database access results in no tool calls:

TODO: <Insert image 5>

### Query 2: "How many users do I have?"
This query triggers a sequence of tool calls:
1. SQLAgent converts the query to SQL
2. DatabaseAgent executes the query

The main agent's graph shows:

TODO: <Insert image 1>

The second bubble contains the user input (also indicating that the LLM used tools), followed by the final response bubble. Clicking the second bubble reveals the tool calls:

TODO: <Insert image 2>

The LLM first calls SQLAgent, then DatabaseAgent. Clicking on the SQLAgent row shows its subgraph:

TODO: <Insert image 3>

The subgraph displays the tool input (orange box), output (green box), and complete LLM chat history. While this example shows a simple tool, the visualization scales to handle complex nested tool calls. The DatabaseAgent's subgraph shows:

TODO: <Insert image 4>

Since this tool doesn't use an LLM, it simply displays the input and output.

## Integration Guide

TODO:..