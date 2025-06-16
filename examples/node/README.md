# Example of using AgentGraph in Node.js

This is a simple example of using AgentGraph in Node.js. It shows how to use the `callLLMWithToolHandling` function to call an LLM with tool handling.

## Running the example

1. Clone the repository

```bash
git clone https://github.com/rishabhpoddar/agentgraph.git
```

2. Install the dependencies

```bash
cd examples/node
npm install
```

3. Create a `.env` file in `examples/node` with the following:

```bash
OPENAI_API_KEY=<your-openai-api-key>
AGENT_GRAPH_SAVE_OUTPUT=true
```

4. Run the example

```bash
npm run start
```

5. Enter a query and see the output JSON that can be visualised in the the `examples/node/agentgraph_output` directory. There are already some example queries in there for you to see.
