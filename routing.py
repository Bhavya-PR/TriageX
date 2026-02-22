import numpy as np
from scipy.optimize import linear_sum_assignment
from queue_manager import get_queue_size

class Agent:
    def __init__(self, agent_id, name, skill_vector, capacity):
        self.agent_id = agent_id
        self.name = name
        self.skills = skill_vector      # e.g., {"Technical": 0.9, "Billing": 0.1, "Legal": 0.0}
        self.capacity = capacity        # max tickets they can handle at once
        self.assigned_tickets = []      # list of assigned ticket dicts

# Stateful Registry of Agents (skill vectors based on hackathon spec)
AGENT_REGISTRY = [
    Agent("A1", "Agent X (Tech Lead)",   {"Technical": 0.9, "Billing": 0.1, "Legal": 0.0}, capacity=2),
    Agent("A2", "Agent Y (Billing Pro)", {"Technical": 0.1, "Billing": 0.9, "Legal": 0.0}, capacity=3),
    Agent("A3", "Agent Z (Legal Eval)",  {"Technical": 0.0, "Billing": 0.2, "Legal": 0.8}, capacity=2),
    Agent("A4", "Agent W (Generalist)",  {"Technical": 0.4, "Billing": 0.4, "Legal": 0.4}, capacity=4)
]

def map_tickets_to_agents(tickets: list) -> list:
    """
    Solve a Constraint Optimization problem (Linear Sum Assignment/Bipartite Matching)
    to route 'N' tickets to the best available agent slots based on their Skill Vectors.
    """
    if not tickets:
        return []

    # 1. Expand agents into available 'slots' based on their remaining capacity
    agent_slots = []
    for agent in AGENT_REGISTRY:
        available_capacity = agent.capacity - len(agent.assigned_tickets)
        for _ in range(available_capacity):
            agent_slots.append(agent)

    if not agent_slots:
        # All agents are at max capacity, no routing possible right now
        return []

    # 2. Build the Cost Matrix
    # We want to MAXIMIZE skill match, which means MINIMIZING cost.
    # Cost = 1.0 - agent_skill_for_ticket_category
    n_tickets = len(tickets)
    n_slots = len(agent_slots)
    
    cost_matrix = np.zeros((n_tickets, n_slots))
    
    for i, ticket in enumerate(tickets):
        category = ticket.get("category", "Technical") # fallback to Technical
        for j, slot in enumerate(agent_slots):
            # Give a default low skill of 0.1 if category is completely unknown to agent
            skill_match = slot.skills.get(category, 0.1)
            cost_matrix[i, j] = 1.0 - skill_match

    # 3. Solve Constraint Optimization via Hungarian Algorithm
    ticket_indices, slot_indices = linear_sum_assignment(cost_matrix)

    # 4. Process the matching results
    routed_assignments = []
    for t_idx, s_idx in zip(ticket_indices, slot_indices):
        ticket = tickets[t_idx]
        agent = agent_slots[s_idx]
        
        # Stateful update: assign ticket to the agent
        agent.assigned_tickets.append(ticket)
        category = ticket.get("category", "Unknown")
        
        routed_assignments.append({
            "ticket_id": ticket["id"],
            "category": category,
            "agent_name": agent.name,
            "skill_match": agent.skills.get(category, 0.1),
            "text_preview": ticket["text"][:50] + "..."
        })

    return routed_assignments

def get_agent_status():
    """Return the current capacity and load of all registered agents."""
    status = []
    for a in AGENT_REGISTRY:
        status.append({
            "id": a.agent_id,
            "name": a.name,
            "skills": a.skills,
            "capacity": a.capacity,
            "current_load": len(a.assigned_tickets),
            "assigned_tickets": [t["id"] for t in a.assigned_tickets]
        })
    return status
