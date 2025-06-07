# AgentGraph

This is a tool that creates a graph for your agent flows:
- Each node in the graph is one message in a conversation with an LLM (ex: system message -> user message -> assistant message)
- A node can have a sub graph if the LLM used tool calling in that turn. You can click on the node to view the list of tools called, their inputs and outputs, and visualize the tool call's sub graphs.

<img src="https://raw.githubusercontent.com/rishabhpoddar/agentgraph/refs/heads/main/images/1.jpeg" align="left" width="50%" >

<img src="https://raw.githubusercontent.com/rishabhpoddar/agentgraph/refs/heads/main/images/2.png" align="left" width="50%" >

<img src="https://raw.githubusercontent.com/rishabhpoddar/agentgraph/refs/heads/main/images/3.jpeg" align="left" width="50%" >
