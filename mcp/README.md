# MCP Host
The LLama CPP server running the Model

# MCP Client
The MCP Application running on the host used to determine if a request to the Server needs to be made.
Will run as a container within the deployment. Uses code from Ramalam source code under `ramalama/mcp`

# MCP Server
The actual server that sits between the client and data or application to translate requests back and forth
This will run as a container that processes requests from the client for data into the RAG Database. Uses code from the Ramalama source code under `container-images/scripts/rag_framework`

# Diagram for dummies
![MCP Diagram](https://mcpcat.io/images/blog/mcp-architecture.png)

