import logging
import json
import time
from typing import List, Optional, Dict, Any, Annotated
from typing_extensions import TypedDict
from datetime import timedelta

# Prometheus
from prometheus_client import Counter, Histogram

# Core integrations
from langchain_openai import ChatOpenAI
from langchain_mcp_adapters.client import MultiServerMCPClient

# LangGraph Core
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langchain_core.tools import tool

# LangChain Core
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage
from langchain_core.callbacks import BaseCallbackHandler

# Set up logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)


# Prometheus Metrics
TOOLS_PER_QUERY_COUNT = Histogram(
    "orchestrator_tools_per_query_total",
    "The number of tools executed during a single LangGraph workflow execution loop",
    ["query_type"],
    buckets=(0, 1, 2, 3, 4, 10, float("inf")),
)

MCP_TOOL_EXECUTION_TOTAL = Counter(
    "orchestrator_mcp_tool_executions_total",
    "Total running count of individual CMP tool executions",
    ["mcp_server", "tool_name"],
)

REQUEST_COUNT = Counter(
    "orchestrator_requests_total",
    "Total number of requests received by the orchestrator API",
    ["endpoint", "status_code"],
)

GRAPH_COMPUTE_DURATION = Histogram(
    "orchestrator_query_compute_seconds",
    "Time spent computing a single query inside the LangGraph orchestrator",
    ["query_type"],
    buckets=(0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, float("inf")),
)


# Agent State Schema
class AgentState(TypedDict):
    """
    Tracks the continuous lifecycle state parameters of the Graph.
    """

    messages: Annotated[list, add_messages]


# Prometheus Callback bridge
class PrometheusMetricsCallback(BaseCallbackHandler):
    def __init__(self, query_type: str, mcp_servers_config: list):
        self.query_type = query_type
        self.start_time = None
        self.num_tools_invoked = 0
        self.mcp_servers_config = mcp_servers_config

    def _get_server_name_for_tool(self, tool_name: str) -> str:
        """
        Helper to map a tool name back t its parent MCP server name
        """
        for server in self.mcp_servers_config:
            if tool_name.startswith(f"server['name']__"):
                return server["name"]
        return "unknown_mcp_server"

    def on_chain_start(self, serialized: dict, inputs: dict, **kwargs) -> None:
        """
        Triggers when the compiled LangGraph starts executing
        """
        if self.start_time is None:
            self.start_time = time.perf_counter()
            self.num_tools_invoked = 0  # Reset

    def on_tool_start(self, serialized: dict, input_str: str, **kwargs) -> None:
        """
        Run every single time the LLM decides to call an MCP tool
        """
        self.num_tools_invoked += 1

        tool_name = serialized.get("name", "unknown_tool")
        mcp_server = self._get_server_name_for_tool(tool_name)

        MCP_TOOL_EXECUTION_TOTAL.labels(
            mcp_server=mcp_server, tool_name=tool_name
        ).inc()

    def on_chain_end(self, outputs: dict, **kwargs) -> None:
        """
        Triggers when LangGraph reaches an END node successfully
        """
        if self.start_time:
            duration = time.perf_counter() - self.start_time
            GRAPH_COMPUTE_DURATION.labels(query_type=self.query_type).observe(duration)

            TOOLS_PER_QUERY_COUNT.labels(query_type=self.query_type).observe(
                self.num_tools_invoked
            )

            self.start_time = None

    def on_chain_error(self, error: BaseException, **kwargs) -> None:
        """
        Triggers if the graph execution fails to crashes
        """
        if self.start_time:
            duration = time.perf_counter() - self.start_time
            GRAPH_COMPUTE_DURATION.labels(query_type=self.query_type).observe(duration)

            TOOLS_PER_QUERY_COUNT.labels(query_type=self.query_type).observe(
                self.num_tools_invoked
            )

            self.start_time = None


# Autonomous Orchestrator Stack
class AutonomousStack:
    def __init__(
        self,
        model_name: str,
        model_endpoint_base_url: str,
    ):
        logger.info(f"Initializing AutonomousStack with model: {model_name}")
        self.model_name = model_name
        self.model_endpoint_base_url = model_endpoint_base_url

        # 2. Setup mcp client credentials
        try:
            with (
                open("/app/config/mcp_servers.json", "r") as f
            ):  # MCP Servers config file must be mounted into the container at /app/config/...
                self.mcp_servers = json.load(f)["mcp_servers"]
        except Exception as e:
            logging.error(f"Error parsing MCP Servers JSON config: {e}")

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
        llm = ChatOpenAI(
            model=self.model_name,
            base_url=self.model_endpoint_base_url,
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
                "Similarly, refrain from answering questions that are not about or related to the University of Massachusetts Lowell."
                "If you do not know the answer to a question, clearly state so."
                "Use the available MCP tools for any information you need that you either don't know about or are not confident about."
                "Refrain from guessing about information before having exhaustively checked via the available tools."
                "Always validate the correctness of a query and it's answer before clearly stating it."
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
        self,
        user_message: str,
        chat_history: List[BaseMessage] | None = None,
        query_type: str = "general",  # Optional label for metric slicing
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

        metrics_callback = PrometheusMetricsCallback(
            query_type=query_type, mcp_servers_config=self.mcp_servers
        )

        config = {"callbacks": [metrics_callback]}

        final_state = await self.graph.ainvoke(initial_state, config=config)
        return final_state["messages"][-1]
