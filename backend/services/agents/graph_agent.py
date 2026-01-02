"""
Graph Agent - Analyzes property networks using Graph Neural Networks
Part of VALORA-DMPE+ Enhanced Architecture
"""

import logging
import numpy as np
from typing import Dict, Any, List, Optional, Tuple, Set
from datetime import datetime, timedelta
import asyncio
import json
from dataclasses import dataclass
from collections import defaultdict
import networkx as nx

# ML imports
try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    from torch_geometric.nn import GCNConv, GraphConv, SAGEConv, global_mean_pool
    from torch_geometric.data import Data, Batch
    TORCH_GEOMETRIC_AVAILABLE = True
except ImportError:
    TORCH_GEOMETRIC_AVAILABLE = False

# Database imports
try:
    from sqlalchemy import text
    import pandas as pd
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False

logger = logging.getLogger(__name__)

@dataclass
class PropertyNode:
    """Represents a property in the graph"""
    property_id: str
    latitude: float
    longitude: float
    price: float
    size: float
    bedrooms: int
    property_type: str
    features: Dict[str, Any]
    embedding: Optional[np.ndarray] = None

@dataclass
class TransactionEdge:
    """Represents a relationship between properties"""
    source_id: str
    target_id: str
    edge_type: str  # similarity, transaction_flow, spatial_proximity
    weight: float
    attributes: Dict[str, Any]

class PropertyGraphSAGE(nn.Module):
    """GraphSAGE model for property embeddings"""
    
    def __init__(self, input_dim: int, hidden_dim: int = 128, output_dim: int = 64, num_layers: int = 3):
        super(PropertyGraphSAGE, self).__init__()
        
        self.num_layers = num_layers
        self.convs = nn.ModuleList()
        self.bns = nn.ModuleList()
        
        # First layer
        self.convs.append(SAGEConv(input_dim, hidden_dim))
        self.bns.append(nn.BatchNorm1d(hidden_dim))
        
        # Hidden layers
        for _ in range(num_layers - 2):
            self.convs.append(SAGEConv(hidden_dim, hidden_dim))
            self.bns.append(nn.BatchNorm1d(hidden_dim))
        
        # Output layer
        self.convs.append(SAGEConv(hidden_dim, output_dim))
        
        self.dropout = nn.Dropout(0.2)
        
    def forward(self, x, edge_index, batch=None):
        # Message passing
        for i, conv in enumerate(self.convs[:-1]):
            x = conv(x, edge_index)
            x = self.bns[i](x)
            x = F.relu(x)
            x = self.dropout(x)
        
        # Final layer
        x = self.convs[-1](x, edge_index)
        
        # Global pooling if batch is provided
        if batch is not None:
            x = global_mean_pool(x, batch)
        
        return x
    
    def get_embedding(self, x, edge_index):
        """Get node embeddings without pooling"""
        with torch.no_grad():
            return self.forward(x, edge_index)

class GraphAgent:
    """
    Agent responsible for analyzing property networks and relationships
    using Graph Neural Networks and network analysis techniques
    """
    
    def __init__(self, db_connection=None):
        self.db_connection = db_connection
        
        # Initialize graph
        self.property_graph = nx.Graph()
        self.directed_graph = nx.DiGraph()  # For transaction flows
        
        # Initialize GNN model
        self.gnn_model = None
        if TORCH_GEOMETRIC_AVAILABLE:
            self.gnn_model = PropertyGraphSAGE(
                input_dim=64,  # Will be determined by feature engineering
                hidden_dim=128,
                output_dim=64
            )
        
        # Cache for embeddings
        self.embedding_cache = {}
        
        # Community detection results
        self.communities = {}
        
        logger.info("GraphAgent initialized")
    
    async def execute(self, action: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute graph analysis action
        
        Actions:
        - analyze_network: Comprehensive network analysis
        - find_similar: Find similar properties using embeddings
        - detect_communities: Identify property market communities
        - analyze_transaction_flow: Analyze transaction patterns
        - predict_links: Predict future property relationships
        - calculate_influence: Calculate property influence radius
        """
        
        if action == "analyze_network":
            return await self.analyze_property_network(parameters)
        elif action == "find_similar":
            return await self.find_similar_properties(parameters)
        elif action == "detect_communities":
            return await self.detect_communities(parameters)
        elif action == "analyze_transaction_flow":
            return await self.analyze_transaction_flow(parameters)
        elif action == "predict_links":
            return await self.predict_property_links(parameters)
        elif action == "calculate_influence":
            return await self.calculate_influence_radius(parameters)
        else:
            raise ValueError(f"Unknown action: {action}")
    
    async def analyze_property_network(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Comprehensive network analysis for a property
        """
        property_id = parameters.get("property_id")
        radius_km = parameters.get("radius_km", 2.0)
        
        try:
            # Build local subgraph
            subgraph = await self._build_local_graph(property_id, radius_km)
            
            # Calculate network metrics
            metrics = self._calculate_network_metrics(subgraph, property_id)
            
            # Get node embedding
            embedding = await self._get_node_embedding(property_id, subgraph)
            
            # Find communities
            communities = self._detect_local_communities(subgraph)
            
            # Analyze transaction patterns
            transaction_patterns = await self._analyze_local_transactions(subgraph)
            
            # Calculate influence
            influence = self._calculate_property_influence(subgraph, property_id)
            
            return {
                "status": "success",
                "property_id": property_id,
                "network_metrics": {
                    "degree_centrality": metrics.get("degree_centrality", 0),
                    "betweenness_centrality": metrics.get("betweenness", 0),
                    "closeness_centrality": metrics.get("closeness", 0),
                    "pagerank": metrics.get("pagerank", 0),
                    "clustering_coefficient": metrics.get("clustering", 0),
                    "eigenvector_centrality": metrics.get("eigenvector", 0)
                },
                "embedding": embedding.tolist() if embedding is not None else None,
                "community": {
                    "id": communities.get(property_id, 0),
                    "size": len([n for n, c in communities.items() if c == communities.get(property_id, 0)]),
                    "avg_price": self._calculate_community_avg_price(subgraph, communities, property_id),
                    "growth_rate": self._calculate_community_growth(subgraph, communities, property_id)
                },
                "transaction_patterns": transaction_patterns,
                "influence": {
                    "radius_meters": influence.get("radius", 0),
                    "affected_properties": influence.get("count", 0),
                    "price_impact": influence.get("price_impact", 0)
                },
                "investment_signals": self._generate_investment_signals(metrics, influence, transaction_patterns)
            }
            
        except Exception as e:
            logger.error(f"Network analysis failed: {e}")
            return {"status": "failed", "error": str(e)}
    
    async def find_similar_properties(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Find similar properties using graph embeddings
        """
        property_id = parameters.get("property_id")
        k = parameters.get("k", 10)  # Number of similar properties
        
        try:
            # Get embedding for target property
            target_embedding = await self._get_node_embedding(property_id)
            
            if target_embedding is None:
                return {"status": "failed", "error": "Could not generate embedding"}
            
            # Find k nearest neighbors
            similar_properties = await self._find_nearest_neighbors(target_embedding, k, exclude_id=property_id)
            
            # Calculate similarity scores
            results = []
            for prop_id, similarity_score in similar_properties:
                prop_details = await self._get_property_details(prop_id)
                results.append({
                    "property_id": prop_id,
                    "similarity_score": float(similarity_score),
                    "price": prop_details.get("price"),
                    "location": prop_details.get("location"),
                    "features": prop_details.get("features"),
                    "price_difference": prop_details.get("price", 0) - parameters.get("target_price", 0)
                })
            
            return {
                "status": "success",
                "property_id": property_id,
                "similar_properties": results,
                "recommendation": self._generate_similarity_recommendation(results)
            }
            
        except Exception as e:
            logger.error(f"Similar property search failed: {e}")
            return {"status": "failed", "error": str(e)}
    
    async def detect_communities(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Detect communities in property network
        """
        location = parameters.get("location", {})
        radius_km = parameters.get("radius_km", 5.0)
        
        try:
            # Build area graph
            area_graph = await self._build_area_graph(location, radius_km)
            
            # Apply community detection algorithms
            communities_louvain = nx.community.louvain_communities(area_graph)
            communities_girvan = nx.community.girvan_newman(area_graph)
            
            # Convert to property assignments
            community_assignments = {}
            for i, community in enumerate(communities_louvain):
                for node in community:
                    community_assignments[node] = i
            
            # Analyze each community
            community_analysis = []
            for community_id in set(community_assignments.values()):
                members = [n for n, c in community_assignments.items() if c == community_id]
                
                analysis = {
                    "community_id": community_id,
                    "size": len(members),
                    "avg_price": self._calculate_avg_price(area_graph, members),
                    "price_range": self._calculate_price_range(area_graph, members),
                    "dominant_type": self._get_dominant_property_type(area_graph, members),
                    "connectivity": self._calculate_internal_connectivity(area_graph, members),
                    "market_activity": self._calculate_market_activity(area_graph, members)
                }
                community_analysis.append(analysis)
            
            # Sort by size
            community_analysis.sort(key=lambda x: x["size"], reverse=True)
            
            return {
                "status": "success",
                "num_communities": len(community_analysis),
                "communities": community_analysis,
                "modularity": nx.community.modularity(area_graph, communities_louvain),
                "insights": self._generate_community_insights(community_analysis)
            }
            
        except Exception as e:
            logger.error(f"Community detection failed: {e}")
            return {"status": "failed", "error": str(e)}
    
    async def analyze_transaction_flow(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze transaction flow patterns in the network
        """
        start_date = parameters.get("start_date", datetime.now() - timedelta(days=365))
        end_date = parameters.get("end_date", datetime.now())
        location = parameters.get("location", {})
        
        try:
            # Build transaction flow graph
            flow_graph = await self._build_transaction_flow_graph(start_date, end_date, location)
            
            # Analyze flow patterns
            flow_analysis = {
                "total_transactions": flow_graph.number_of_edges(),
                "unique_properties": flow_graph.number_of_nodes(),
                "avg_transactions_per_property": flow_graph.number_of_edges() / max(1, flow_graph.number_of_nodes()),
                "max_flow_path": self._find_max_flow_path(flow_graph),
                "bottlenecks": self._identify_bottlenecks(flow_graph),
                "hot_zones": self._identify_hot_zones(flow_graph),
                "velocity_score": self._calculate_velocity_score(flow_graph),
                "investor_patterns": self._detect_investor_patterns(flow_graph)
            }
            
            # Predict future flows
            flow_predictions = await self._predict_transaction_flows(flow_graph)
            
            return {
                "status": "success",
                "period": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat()
                },
                "flow_analysis": flow_analysis,
                "predictions": flow_predictions,
                "recommendations": self._generate_flow_recommendations(flow_analysis, flow_predictions)
            }
            
        except Exception as e:
            logger.error(f"Transaction flow analysis failed: {e}")
            return {"status": "failed", "error": str(e)}
    
    async def predict_property_links(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Predict future property relationships/transactions
        """
        property_id = parameters.get("property_id")
        prediction_horizon = parameters.get("horizon_days", 90)
        
        try:
            # Get property subgraph
            subgraph = await self._build_local_graph(property_id, radius_km=2.0)
            
            # Extract features for link prediction
            node_features = self._extract_node_features(subgraph)
            edge_features = self._extract_edge_features(subgraph)
            
            # Generate candidate links
            candidates = self._generate_candidate_links(subgraph, property_id)
            
            # Score candidates
            predictions = []
            for source, target in candidates:
                score = self._score_link_probability(subgraph, source, target, node_features, edge_features)
                predictions.append({
                    "source": source,
                    "target": target,
                    "probability": float(score),
                    "expected_days": int(prediction_horizon * (1 - score)),
                    "link_type": self._predict_link_type(subgraph, source, target)
                })
            
            # Sort by probability
            predictions.sort(key=lambda x: x["probability"], reverse=True)
            
            return {
                "status": "success",
                "property_id": property_id,
                "predictions": predictions[:20],  # Top 20 predictions
                "investment_opportunities": self._identify_opportunities(predictions),
                "risk_factors": self._identify_link_risks(predictions)
            }
            
        except Exception as e:
            logger.error(f"Link prediction failed: {e}")
            return {"status": "failed", "error": str(e)}
    
    async def calculate_influence_radius(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate how property changes influence surrounding market
        """
        property_id = parameters.get("property_id")
        price_change = parameters.get("price_change", 0)  # Percentage
        
        try:
            # Build influence propagation model
            influence_graph = await self._build_influence_graph(property_id)
            
            # Simulate price propagation
            propagation_results = self._simulate_price_propagation(
                influence_graph, property_id, price_change
            )
            
            # Calculate influence metrics
            influence_metrics = {
                "direct_influence_radius": self._calculate_direct_radius(propagation_results),
                "indirect_influence_radius": self._calculate_indirect_radius(propagation_results),
                "affected_properties": len(propagation_results),
                "avg_impact": np.mean([r["impact"] for r in propagation_results.values()]),
                "max_impact": np.max([r["impact"] for r in propagation_results.values()]),
                "decay_rate": self._calculate_decay_rate(propagation_results),
                "influence_score": self._calculate_influence_score(propagation_results)
            }
            
            # Identify most affected properties
            most_affected = sorted(
                propagation_results.items(),
                key=lambda x: abs(x[1]["impact"]),
                reverse=True
            )[:10]
            
            return {
                "status": "success",
                "property_id": property_id,
                "price_change": price_change,
                "influence_metrics": influence_metrics,
                "most_affected_properties": [
                    {
                        "property_id": pid,
                        "expected_impact": data["impact"],
                        "distance_meters": data["distance"],
                        "lag_days": data["lag"]
                    }
                    for pid, data in most_affected
                ],
                "market_implications": self._analyze_market_implications(influence_metrics, price_change)
            }
            
        except Exception as e:
            logger.error(f"Influence calculation failed: {e}")
            return {"status": "failed", "error": str(e)}
    
    # Helper methods for graph construction
    async def _build_local_graph(self, property_id: str, radius_km: float) -> nx.Graph:
        """Build subgraph around a property"""
        G = nx.Graph()
        
        if self.db_connection and DB_AVAILABLE:
            # Query nearby properties
            query = text("""
                SELECT p1.property_id, p1.latitude, p1.longitude, p1.price, p1.size,
                       p2.property_id as neighbor_id, p2.price as neighbor_price,
                       ST_Distance(p1.geom, p2.geom) as distance
                FROM properties p1
                JOIN properties p2 ON ST_DWithin(p1.geom, p2.geom, :radius)
                WHERE p1.property_id = :property_id
                  AND p1.property_id != p2.property_id
            """)
            
            result = self.db_connection.execute(query, {
                "property_id": property_id,
                "radius": radius_km * 1000
            })
            
            for row in result:
                # Add nodes
                G.add_node(row.property_id, 
                          price=row.price,
                          size=row.size,
                          lat=row.latitude,
                          lon=row.longitude)
                G.add_node(row.neighbor_id, price=row.neighbor_price)
                
                # Add edge with distance weight
                G.add_edge(row.property_id, row.neighbor_id,
                          weight=1/(1 + row.distance),  # Inverse distance weight
                          distance=row.distance)
        else:
            # Generate synthetic graph for demo
            G = self._generate_synthetic_graph(property_id, 20)
        
        return G
    
    def _generate_synthetic_graph(self, center_id: str, num_nodes: int) -> nx.Graph:
        """Generate synthetic property graph for testing"""
        G = nx.Graph()
        
        # Add center node
        G.add_node(center_id, 
                  price=np.random.uniform(100000, 1000000),
                  size=np.random.uniform(500, 3000))
        
        # Add neighboring nodes
        for i in range(num_nodes):
            node_id = f"prop_{i}"
            G.add_node(node_id,
                      price=np.random.uniform(100000, 1000000),
                      size=np.random.uniform(500, 3000))
            
            # Connect with probability based on synthetic distance
            if np.random.random() > 0.3:
                distance = np.random.uniform(100, 2000)
                G.add_edge(center_id, node_id,
                          weight=1/(1 + distance),
                          distance=distance)
        
        # Add some edges between neighbors
        nodes = list(G.nodes())
        for i in range(num_nodes // 2):
            n1, n2 = np.random.choice(nodes, 2, replace=False)
            if not G.has_edge(n1, n2):
                G.add_edge(n1, n2, weight=np.random.random())
        
        return G
    
    def _calculate_network_metrics(self, G: nx.Graph, node: str) -> Dict[str, float]:
        """Calculate various network centrality metrics"""
        metrics = {}
        
        try:
            metrics["degree_centrality"] = nx.degree_centrality(G).get(node, 0)
            metrics["betweenness"] = nx.betweenness_centrality(G).get(node, 0)
            metrics["closeness"] = nx.closeness_centrality(G).get(node, 0)
            metrics["pagerank"] = nx.pagerank(G).get(node, 0)
            metrics["clustering"] = nx.clustering(G).get(node, 0)
            
            # Eigenvector centrality (may fail for disconnected graphs)
            try:
                metrics["eigenvector"] = nx.eigenvector_centrality(G).get(node, 0)
            except:
                metrics["eigenvector"] = 0
            
        except Exception as e:
            logger.warning(f"Error calculating metrics: {e}")
        
        return metrics
    
    async def _get_node_embedding(self, property_id: str, graph: Optional[nx.Graph] = None) -> Optional[np.ndarray]:
        """Get GNN embedding for a property node"""
        
        # Check cache
        if property_id in self.embedding_cache:
            return self.embedding_cache[property_id]
        
        if not TORCH_GEOMETRIC_AVAILABLE or self.gnn_model is None:
            # Fallback to simple feature vector
            return self._create_simple_embedding(property_id, graph)
        
        try:
            # Prepare graph data for GNN
            if graph is None:
                graph = await self._build_local_graph(property_id, radius_km=2.0)
            
            # Convert to PyTorch Geometric format
            edge_index = self._graph_to_edge_index(graph)
            node_features = self._extract_node_features_tensor(graph)
            
            data = Data(x=node_features, edge_index=edge_index)
            
            # Get embedding
            self.gnn_model.eval()
            with torch.no_grad():
                embeddings = self.gnn_model.get_embedding(data.x, data.edge_index)
            
            # Find index of target property
            node_list = list(graph.nodes())
            idx = node_list.index(property_id)
            embedding = embeddings[idx].numpy()
            
            # Cache result
            self.embedding_cache[property_id] = embedding
            
            return embedding
            
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            return None
    
    def _create_simple_embedding(self, property_id: str, graph: nx.Graph) -> np.ndarray:
        """Create simple embedding without GNN"""
        if graph is None or property_id not in graph:
            return np.random.randn(64)  # Random embedding
        
        # Extract basic features
        node_data = graph.nodes[property_id]
        metrics = self._calculate_network_metrics(graph, property_id)
        
        features = [
            node_data.get("price", 0) / 1e6,  # Normalize
            node_data.get("size", 0) / 1000,
            metrics.get("degree_centrality", 0),
            metrics.get("betweenness", 0),
            metrics.get("closeness", 0),
            metrics.get("pagerank", 0),
            metrics.get("clustering", 0),
            graph.degree(property_id) / graph.number_of_nodes()
        ]
        
        # Pad to desired dimension
        embedding = np.array(features)
        if len(embedding) < 64:
            embedding = np.pad(embedding, (0, 64 - len(embedding)))
        
        return embedding
    
    def _simulate_price_propagation(self, G: nx.Graph, source: str, price_change: float) -> Dict[str, Any]:
        """Simulate how price change propagates through network"""
        propagation = {}
        
        # BFS to simulate propagation
        visited = set()
        queue = [(source, price_change, 0, 0)]  # (node, impact, distance, lag)
        
        while queue:
            node, impact, distance, lag = queue.pop(0)
            
            if node in visited:
                continue
            
            visited.add(node)
            propagation[node] = {
                "impact": impact,
                "distance": distance,
                "lag": lag
            }
            
            # Propagate to neighbors with decay
            for neighbor in G.neighbors(node):
                if neighbor not in visited:
                    edge_data = G.get_edge_data(node, neighbor)
                    edge_weight = edge_data.get("weight", 0.5)
                    
                    # Calculate propagated impact
                    decay_factor = 0.8  # Impact decays with distance
                    new_impact = impact * edge_weight * decay_factor
                    
                    # Only propagate if impact is significant
                    if abs(new_impact) > 0.01:
                        new_distance = distance + edge_data.get("distance", 100)
                        new_lag = lag + int(new_distance / 100)  # Days lag based on distance
                        queue.append((neighbor, new_impact, new_distance, new_lag))
        
        return propagation
    
    def _generate_investment_signals(self, metrics: Dict, influence: Dict, patterns: Dict) -> List[str]:
        """Generate investment signals based on network analysis"""
        signals = []
        
        # High centrality signal
        if metrics.get("pagerank", 0) > 0.1:
            signals.append("high_influence_property")
        
        # Growing community signal  
        if patterns.get("velocity_score", 0) > 0.7:
            signals.append("high_transaction_activity")
        
        # Undervalued signal
        if metrics.get("degree_centrality", 0) > 0.5 and influence.get("price_impact", 0) < 0:
            signals.append("potentially_undervalued")
        
        return signals
