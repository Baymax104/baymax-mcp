# -*- coding: UTF-8 -*-
from collections import namedtuple
from typing import Self

from langgraph.constants import END, START
from langgraph.graph import StateGraph
from langgraph.pregel import Pregel
from pydantic import BaseModel

from workflow.nodes import EndNode, Node, RouteNode, StartNode


Edge = namedtuple("Edge", ["start", "end"])


class GraphConfig(BaseModel):
    nodes: list[Node]
    edges: list[Edge]


class GraphBuilder:

    def __init__(
        self,
        state_schema: type[BaseModel],
        input_schema: type[BaseModel] | None = None,
        output_schema: type[BaseModel] | None = None
    ):
        self.__builder = StateGraph(state_schema, input=input_schema, output=output_schema)

    def from_config(self, config: GraphConfig) -> Self:
        node_dict = {node.name: node for node in config.nodes}

        # Add nodes except RouteNode
        for node in config.nodes:
            if not isinstance(node, RouteNode):
                self.__builder.add_node(node.name, node)

        # Add start node and end node for convenience
        node_dict[START] = StartNode()
        node_dict[END] = EndNode()
        for edge in config.edges:
            if edge.start not in node_dict:
                raise RuntimeError(f"Start node {edge.start} not in graph")
            if edge.end not in node_dict:
                raise RuntimeError(f"End node {edge.end} not in graph")
            end_node = node_dict[edge.end]
            if isinstance(end_node, RouteNode):
                self.__builder.add_conditional_edges(edge.start, end_node.router)
            else:
                self.__builder.add_edge(edge.start, edge.end)

    def compile(self) -> Pregel:
        return self.__builder.compile()
