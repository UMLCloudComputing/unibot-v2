import logging
from typing import List, Optional, Dict, Any, Annotated
from typing_extensions import TypedDict

# Core integrations
from pymilvus import connections
from langchain_milvus import Milvus
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_mcp_adapters.client import MultiServerMCPClient

# LangGraph Core
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langchain_core.tools import tool
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage

# Set up logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)


# Agent State Schema
class AgentState(TypedDict):
    """
    Tracks the continuous lifecycle state parameters of the Graph.
    """

    messages: Annotated[list, add_messages]


# Autonomous Orchestrator Stack
class AutonomousStack:
    def __init__(
        self,
        milvus_uri: str,
        milvus_collection: str,
        ollama_model: str,
        ollama_base_url: str,
        mcp_server_url: str,  # Point to your remote FastMCP server
        mcp_api_key: Optional[str] = None,
    ):
        logger.info(f"Initializing AutonomousStack with model: {ollama_model}")
        self.model_name = ollama_model
        self.ollama_base_url = ollama_base_url

        # 1. Local Embeddings Configuration
        logger.debug("Setting up Ollama embeddings with nomic-embed-text")
        self.embeddings = OllamaEmbeddings(
            model="nomic-embed-text", base_url=ollama_base_url
        )

        # 2. Setup Vector Store Connection
        logger.debug(
            f"Connecting to Milvus at {milvus_uri}, collection: {milvus_collection}"
        )

        # Override underlying registry lookup method to return this active connection handler
        if "default" not in connections.list_connections():
            connections.connect(alias="default", uri=milvus_uri)
        active_conn = connections._fetch_handler(alias="default")
        original_fetch = connections._fetch_handler
        connections._fetch_handler = lambda using="default": (
            original_fetch(using=using)
            if using in connections.list_connections()
            else active_conn
        )

        self.vector_store = Milvus(
            embedding_function=self.embeddings,
            connection_args={"uri": milvus_uri},
            collection_name=milvus_collection,
            drop_old=False,
        )
        self.retriever = self.vector_store.as_retriever(search_kwargs={"k": 3})
        logger.debug("Vector store retriever initialized")

        # 3. Setup mcp client credentials
        self.mcp_api_key = mcp_api_key
        self.mcp_server_url = mcp_server_url

        self.graph = None
        self.mcp_client = None
        logger.info("AutonomousStack-core initialized successfully")

    async def _initialize_graph_if_needed(self):
        """
        Asynchronously boots teh client connections and compiles the
        LangGraph instance
        """

        if self.graph is not None:
            return

        headers = {}
        if self.mcp_api_key is not None:
            headers["Authorization"] = f"Bearer {self.mcp_api_key}"

        # 1. Setup MCP client
        logger.debug(f"Setting up MCP client for server: {self.mcp_server_url}")
        self.mcp_client = MultiServerMCPClient(
            {
                "uml-now-mcp": {
                    "url": self.mcp_server_url,
                    "transport": "streamable_http",
                    "headers": headers,
                }
            }
        )
        logger.debug("Obtaining tools from MCP server...")
        # 1. Pull the remote MCP tools
        all_tools = await self.mcp_client.get_tools()

        # 2. Convert the Milvus Retriever into a LangChain tool definition
        @tool
        def query_knowledge_base(query: str) -> str:
            """
            Queries the internal database to retrieve context information
            sourced from the University website Use this whenever the user asks
            about information that is possibly documented on the University sitemap
            across the sitemap.
            """
            docs = self.retriever.invoke(query)
            return "\n\n".join(doc.page_content for doc in docs)

        # Append the new RAG tool to the tool roster
        all_tools.append(query_knowledge_base)

        logger.debug(
            f"Binding MCP tools + Milvus tool to model, total {len(all_tools)} tools..."
        )
        # 3. Instantiate the model and bind all tools
        llm = ChatOllama(
            model=self.model_name, base_url=self.ollama_base_url, temperature=0.2
        )
        self.llm_with_tools = llm.bind_tools(all_tools) if all_tools else llm

        # --- Define graph nodes ---
        def call_model(state: AgentState) -> Dict[str, Any]:
            """
            Genreates model predictions.
            LLM autonomously picks the RAG or MCP tool calls based on content.
            """

            system_prompt = SystemMessage(
                content="You are a helpful and professional assistant specialized in information "
                "about the University of UMass Lowell. Your name is unibot-v2."
                "Refrain from answering questions that involve academic work like homework, class assignments, quizzes, or exams."
                "If you do not know the answer to a question, clearly state so."
            )
            response = self.llm_with_tools.invoke([system_prompt] + state["messages"])
            return {"messages": [response]}

        # --- Define routing conditions ---
        def should_continue(state: AgentState) -> str:
            """
            Routes control to tool nodes if requested, otherwise ends the loop.
            """
            last_message = state["messages"][-1]
            if hasattr(last_message, "tool_calls") and last_message.tool_calls:
                return "tools"
            return END

        # --- Define Graph Topology ---
        graph = StateGraph(AgentState)

        # Add Nodes
        graph.add_node("call_model", call_model)
        graph.add_node("tools", ToolNode(all_tools))

        # Define fixed routing edges
        graph.add_edge(START, "call_model")
        graph.add_edge("tools", "call_model")

        # Define conditional routing logic
        graph.add_conditional_edges(
            "call_model", should_continue, {"tools": "tools", END: END}
        )

        self.graph = graph.compile()

    async def chat(
        self, user_message: str, chat_history: List[BaseMessage] | None = None
    ) -> str:
        """
        Executes the autonomous graph workflow asynchronously
        """
        if chat_history is None:
            chat_history = []

        # Required since mcp client tool schema extraction is async
        # Hence, the schema must be obtained in an async function
        # Schema is necessary for tool binding to the model
        await self._initialize_graph_if_needed()  # Runs on first request

        initial_state = {
            "messages": chat_history + [HumanMessage(content=user_message)]
        }
        logger.info("Processing chat request")

        final_state = await self.graph.ainvoke(initial_state)
        return final_state["messages"][-1]
