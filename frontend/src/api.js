const BASE = "/api";

async function getJSON(path) {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) {
    throw new Error(`Request failed: ${path} (${res.status})`);
  }
  return res.json();
}

export const api = {
  health: () => getJSON("/health"),
  overview: () => getJSON("/overview"),
  equipmentList: () => getJSON("/equipment"),
  equipmentDetail: (id) => getJSON(`/equipment/${id}`),
  equipmentReport: (id) => getJSON(`/equipment/${id}/report`),
};
