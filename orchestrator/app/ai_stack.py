import logging
from typing import List, Optional, Dict, Any, Annotated
from typing_extensions import TypedDict
from datetime import timedelta

# Core integrations
from langchain_ollama import ChatOllama
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


class MCPServer(TypedDict):
    name: str
    url: str
    api_key: Optional[str]


# Autonomous Orchestrator Stack
class AutonomousStack:
    def __init__(
        self,
        ollama_model: str,
        ollama_base_url: str,
        mcp_servers: list[MCPServer],  # Point to your remote FastMCP servers
    ):
        logger.info(f"Initializing AutonomousStack with model: {ollama_model}")
        self.model_name = ollama_model
        self.ollama_base_url = ollama_base_url

        # 2. Setup mcp client credentials
        self.mcp_servers = mcp_servers

        self.graph = None
        self.mcp_client = None
        logger.info("AutonomousStack-core initialized successfully")

    async def _initialize_graph_if_needed(self):
        """
        Asynchronously boots the client connections and compiles the
        LangGraph instance
        """

        if self.graph is not None:
            return

        # 1. Setup MCP client
        logger.debug("Setting up MCP client for server(s)")
        self.mcp_client = MultiServerMCPClient(
            {
                server["name"]: {
                    "url": server["url"],
                    "transport": "streamable_http",
                    "timeout": timedelta(seconds=120),
                    "sse_read_timeout": timedelta(seconds=600),
                    **(
                        {"headers": {"Authorization": f"Bearer {server['api_key']}"}}
                        if server.get("api_key") and server["api_key"] != ""
                        else {}
                    ),
                }
                for server in self.mcp_servers
            }
        )
        logger.debug("Obtaining tools from MCP server...")
        # 1. Pull the remote MCP tools
        all_tools = await self.mcp_client.get_tools()

        # 2. Instantiate the model and bind all tools
        llm = ChatOllama(
            model=self.model_name,
            base_url=self.ollama_base_url,
            temperature=1.0,
            top_p=0.95,
            top_k=64,
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
                "about the University of Massachusetts Lowell (UMass Lowell). Your name is unibot-v2."
                "Refrain from answering questions that involve academic work like homework, class assignments, quizzes, or exams."
                "If you do not know the answer to a question, clearly state so."
                "Use the available MCP tools for any information you need that you either don't know about or are not confident about."
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
