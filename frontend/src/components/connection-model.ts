import type { Relationships } from "@/types/worldShift";

export function connectionEdges(relationships: Relationships, query = "") {
  const nodes = new Map(relationships.nodes.map(node => [node.id, node]));
  const search = query.trim().toLowerCase();
  return relationships.edges.filter(edge => edge.category !== "cross_shift").flatMap(edge => {
    const source = nodes.get(edge.source);
    const target = nodes.get(edge.target);
    if (!source || !target) return [];
    const label = edge.relationship.replaceAll("_", " ").toLowerCase();
    if (search && !`${source.label} ${target.label} ${label} ${edge.explanation ?? ""}`.toLowerCase().includes(search)) return [];
    // Association and generic mechanism links never imply causal direction.
    const directed = /^(regulates|supplies|operates|funds|owns|acquires|sanctions|produces|invests_in)$/i.test(edge.relationship);
    return [{ ...edge, sourceNode: source, targetNode: target, label, directed }];
  });
}
