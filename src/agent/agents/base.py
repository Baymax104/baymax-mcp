# -*- coding: UTF-8 -*-
from abc import ABC, abstractmethod

from fastmcp import Client as MCPClient
from fastmcp.client.transports import MCPConfigTransport
from icecream import ic
from langchain_core.messages import HumanMessage
from langgraph.pregel import Pregel
from pydantic import BaseModel

from config import Configuration
from llm import LLMFactory
from workflow import GraphBuilder, GraphConfig


class Agent(ABC):
    state_schema: type[BaseModel]
    input_schema: type[BaseModel] | None = None
    output_schema: type[BaseModel] | None = None

    def __init__(self, config: Configuration):
        self.config = config
        self.mcp_client = MCPClient(MCPConfigTransport(config.server.to_mcp()), timeout=10)
        self.llm = LLMFactory.create(config.model)
        self.workflow: Pregel | None = None

    async def initialize(self):
        await self.__ping_mcp_server()
        await self.__ping_llm()
        self.__build_workflow()

    @abstractmethod
    def _get_workflow(self) -> GraphConfig:
        ...

    def __build_workflow(self):
        if self.workflow is not None:
            raise RuntimeError(f"Client already initialized")
        builder = GraphBuilder(self.state_schema, self.input_schema, self.output_schema)
        graph_config = self._get_workflow()
        builder.from_config(graph_config)
        self.workflow = builder.compile()

    async def __ping_mcp_server(self):
        async with self.mcp_client:
            if not await self.mcp_client.ping():
                raise RuntimeError(f"MCP server connection failed")
            ic("ping mcp successfully")

    async def __ping_llm(self):
        response = await self.llm.generate_async([HumanMessage("Hello")])
        if not response.content:
            raise RuntimeError(f"LLM connection failed")
        ic("ping llm successfully")
