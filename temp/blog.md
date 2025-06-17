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

Let's walk through implementing AgentGraph in a Node.js backend. You can find the complete example code [here](https://github.com/rishabhpoddar/agentgraph/tree/main/examples). While we'll focus on Node.js, the implementation is similar for Python backends.

To get started, install the AgentGraph package:

```bash
npm install @trythisapp/agentgraph
```

### Setting Up the Main Agent

The core of the integration involves wrapping your LLM calls with AgentGraph's `callLLMWithToolHandling` function. Here's how to set up the main agent:

```typescript
import { callLLMWithToolHandling, clearSessionId } from "@trythisapp/agentgraph";
import { v4 as uuidv4 } from 'uuid';

async function mainAgent(userInput: string, sessionId: string) {
    let input: OpenAI.Responses.ResponseInput = [{
        role: "system",
        content: `You are a helpful assistant for querying a database...`
    }, {
        role: "user",
        content: userInput
    }];

    try {
        let response = await callLLMWithToolHandling(
            "mainAgent",           // Agent name for visualization
            sessionId,             // Unique session identifier
            undefined,             // Tool ID (undefined for main agent)
            async (inp) => {       // LLM call function
                return await openaiClient.responses.create({
                    model: "gpt-4.1",
                    input: inp,
                    tools: [/* tool definitions */],
                });
            },
            input,                 // Input messages
            [/* tool implementations */]
        );
        
        console.log(response.output_text);
    } finally {
        clearSessionId(sessionId);  // Clean up session data
    }
}
```

### Session Management

Each interaction requires a unique session ID to track the conversation flow:

```typescript
let sessionId = uuidv4();
console.log(`Session ID: ${sessionId}. File is saved in ./agentgraph_output/${sessionId}.json`);
```

The session ID serves two purposes:
1. **Visualization**: Groups related interactions in the same graph
2. **File Output**: Creates a JSON file with the complete interaction trace

Always call `clearSessionId(sessionId)` when the session ends to clean up memory.

### Defining Tools

Tools are defined using OpenAI's function calling format within the LLM call:

```typescript
tools: [{
    type: "function",
    strict: true,
    name: "SQLAgent",
    description: "Use this tool when you need to convert the natural language query into a SQL query",
    parameters: {
        type: "object",
        properties: {
            query: {
                type: "string",
                description: "The natural language query to convert into a SQL query"
            }
        },
        required: ["query"],
        additionalProperties: false
    }
}, {
    type: "function",
    strict: true,
    name: "databaseAgent",
    description: "Use this tool when you need to execute the SQL query and return the results",
    parameters: {
        type: "object",
        properties: {
            query: {
                type: "string",
                description: "The SQL query to execute"
            }
        },
        required: ["query"],
        additionalProperties: false
    }
}]
```

### Implementing Tool Handlers

The final parameter of `callLLMWithToolHandling` is an array of tool implementations:

```typescript
[{
    toolName: "SQLAgent",
    impl: async ({ query }: { query: string }, toolId: string) => {
        return runSQLAgent(sessionId, toolId, query);
    }
}, {
    toolName: "databaseAgent", 
    impl: async ({ query }: { query: string }) => {
        return runDatabaseAgent(query);
    }
}]
```

Each tool implementation receives:
- **Parameters**: The arguments passed by the LLM (destructured from the first parameter)
- **Tool ID**: A unique identifier for this specific tool call (used for nested visualization)

### Creating Nested Agents

For tools that use LLMs internally (like SQLAgent), you create nested agents by calling `callLLMWithToolHandling` again:

```typescript
async function runSQLAgent(sessionId: string, toolId: string, query: string): Promise<string> {
    let input: OpenAI.Responses.ResponseInput = [{
        role: "system",
        content: `You are an expert SQLite SQL query generator...`
    }, {
        role: "user",
        content: query
    }];
    
    let response = await callLLMWithToolHandling(
        "SQLAgent",        // Nested agent name
        sessionId,         // Same session ID
        toolId,            // Tool ID from parent call
        async (inp) => {
            return await openaiClient.responses.create({
                model: "gpt-4.1",
                input: inp,
                text: {
                    format: {
                        type: "json_schema",
                        name: "sqlQuery",
                        schema: {/* JSON schema */}
                    }
                }
            });
        },
        input,
        []                 // No tools for this agent
    );

    return response.output_text;
}
```

Notice how the nested agent:
- Uses the same `sessionId` to maintain session continuity
- Receives the `toolId` from the parent to establish the parent-child relationship
- Can have its own tools or none at all

### Simple Tool Implementation

For tools that don't use LLMs (like databaseAgent), the implementation is straightforward:

```typescript
async function runDatabaseAgent(query: string): Promise<string> {
    return queryDatabase(query);  // Direct function call
}
```

### Viewing the Results

After running your agent, AgentGraph seamlessly handles the complete interaction flow:

1. **Automatic Tool Orchestration**: When the LLM decides to invoke a tool, `callLLMWithToolHandling` automatically executes the corresponding tool implementation and feeds the result back to the LLM for further processing.

2. **Complete Trace Capture**: Every interaction, tool call, and response is captured and saved to `./agentgraph_output/${sessionId}.json`, creating a comprehensive execution trace.

3. **Interactive Visualization**: The generated JSON file can be visualized using the [AgentGraph visualizer](https://github.com/rishabhpoddar/agentgraph/tree/main?tab=readme-ov-file#visualizing-the-graph), which renders your agent interactions as an interactive graph.

The visualization provides:
- **Chat Flow**: LLM interactions as conversation bubbles
- **Tool Calls**: Expandable sections showing tool inputs and outputs  
- **Nested Agents**: Subgraphs for tools that use LLMs internally
- **Execution Flow**: Clear visual representation of the decision-making process

This integration approach provides complete visibility into your multi-agent system without requiring significant changes to your existing code structure.

## Conclusion

As AI agent systems become increasingly sophisticated, the ability to understand and debug their behavior becomes crucial for reliable deployment. AgentGraph addresses this challenge by providing real-time visualization of multi-agent interactions, making complex decision flows transparent and debuggable.

Key benefits of using AgentGraph include:

- **Zero-friction Integration**: Minimal code changes required to instrument your existing agent systems
- **Complete Visibility**: Track every LLM interaction, tool call, and nested agent execution
- **Interactive Debugging**: Visual graph interface that lets you drill down into specific interactions
- **Multi-language Support**: Works seamlessly with both Python and Node.js backends
- **Session Management**: Automatic trace capture and file generation for analysis

Whether you're building simple tool-calling agents or complex multi-agent orchestration systems, AgentGraph provides the observability you need to understand, debug, and optimize your AI workflows.

Check out the [AgentGraph repository](https://github.com/rishabhpoddar/agentgraph) and give it a ⭐ if you find it useful! Your support helps me continue developing tools that make AI development more transparent and accessible.

