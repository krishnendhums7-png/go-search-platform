
import axios from "axios";

const api = axios.create({
  baseURL: "http://127.0.0.1:8000",
  headers: {
    "Content-Type": "application/json",
  },
});

// Search Government Orders using the multi-agent system.
export const searchGovernmentOrders = async (query, limit = 5) => {
  const response = await api.post("/search/orchestrated", {
    query,
    limit,
  });

  return response.data;
};

// Retrieve Government Order metadata.
export const getGovernmentOrderDetails = async (goNumber) => {
  const response = await api.get("/government-orders/details", {
    params: {
      go_number: goNumber,
    },
  });

  return response.data;
};

// Verify legal status using the deterministic relationship graph.
export const getGovernmentOrderStatus = async (goNumber) => {
  const response = await api.get("/government-orders/status", {
    params: {
      go_number: goNumber,
    },
  });

  return response.data;
};

// Retrieve incoming and outgoing relationships.
export const getGovernmentOrderRelationships = async (goNumber) => {
  const response = await api.get("/government-orders/relationships", {
    params: {
      go_number: goNumber,
    },
  });

  return response.data;
};

export default api;
