import StatusBadge from "./StatusBadge";

function SearchResultCard({ result, onViewDetails }) {
  const goNumber =
    result.go_number ||
    result.matched_go_number ||
    result.source_go_number ||
    "Government Order Number Unavailable";

  const department =
    result.department || "Department not available";

  const issueDate = result.issue_date || "N/A";
  const pageNumber = result.page_number ?? "N/A";

  const semanticScore =
    typeof result.semantic_score === "number"
      ? result.semantic_score.toFixed(4)
      : "N/A";

  const retrievedText =
    result.text || "No retrieved text available.";

  return (
    <article className="result-card">
      <div className="result-card-header">
        <div>
          <h2>{goNumber}</h2>

          <p className="department">{department}</p>
        </div>

        <StatusBadge status={result.status} />
      </div>

      <div className="result-metadata">
        <div>
          <span>Issue Date</span>
          <strong>{issueDate}</strong>
        </div>

        <div>
          <span>Page</span>
          <strong>{pageNumber}</strong>
        </div>

        <div>
          <span>Relevance</span>
          <strong>{semanticScore}</strong>
        </div>
      </div>

      <div className="retrieved-text">
        <h3>Retrieved Text</h3>

        <p>{retrievedText}</p>
      </div>

      <div className="result-footer">
        <span>
          GO:{" "}
          {result.matched_go_number ||
            result.source_go_number ||
            goNumber}
        </span>

        <span>
          Chunk: {result.chunk_id || "N/A"}
        </span>
      </div>

      <button
        type="button"
        className="details-button"
        onClick={() => onViewDetails?.(result)}
        disabled={!onViewDetails}
      >
        View GO Details →
      </button>
    </article>
  );
}

export default SearchResultCard;