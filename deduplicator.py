import time
import threading
from sentence_transformers import SentenceTransformer, util

# Load lightweight sentence embedding model
# Uses all-MiniLM-L6-v2 which is fast and perfect for real-time deduplication
embedder = SentenceTransformer('all-MiniLM-L6-v2')

class Deduplicator:
    def __init__(self):
        # Stores tuples of (timestamp, text, embedding_tensor)
        self.recent_tickets = []
        self.lock = threading.Lock()
        self.similarity_threshold = 0.9
        self.time_window_seconds = 300  # 5 minutes
        self.storm_threshold = 10       # Suppress if > 10 similar tickets

    def check_storm(self, text: str) -> str:
        """
        Identify Ticket Storms / Flash-Floods using Semantic Deduplication.
        Returns:
            "master" if exactly storm_threshold similar tickets triggered a master incident.
            "suppress" if part of an existing storm (suppress individual alert).
            "normal" if it's a unique ticket or storm threshold not met.
        """
        current_time = time.time()
        # Compute sentence embedding for the incoming ticket
        emb = embedder.encode(text, convert_to_tensor=True)

        with self.lock:
            # 1. Clean up tickets older than the 5-minute time window
            self.recent_tickets = [
                t for t in self.recent_tickets
                if current_time - t[0] < self.time_window_seconds
            ]

            # 2. Calculate Cosine Similarity against all remaining recent tickets
            similar_count = 0
            for t in self.recent_tickets:
                # util.cos_sim returns a 2D tensor, .item() gets the float value
                sim = util.cos_sim(emb, t[2]).item()
                if sim > self.similarity_threshold:
                    similar_count += 1
                    
            # 3. Add current ticket to recent list
            self.recent_tickets.append((current_time, text, emb))

            # 4. Evaluate Thresholds
            if similar_count == self.storm_threshold:
                # Exactly at threshold: trigger the Master Incident
                return "master"
            elif similar_count > self.storm_threshold:
                # Already triggered Master Incident: suppress individual alert
                return "suppress"
            else:
                # Under threshold: business as usual
                return "normal"

# Singleton instance
deduplicator = Deduplicator()
