
import { useEffect, useState } from "react";
import {
  getGovernmentOrderDetails,
  getGovernmentOrderStatus,
  getGovernmentOrderRelationships,
} from "../services/api";

function GODetails({ result, onBack }) {
  const goNumber =
    result?.go_number ||
    result?.government_order_number ||
    result?.metadata?.go_number ||
    result?.metadata?.government_order_number;

  const [details, setDetails] = useState(null);
  const [status, setStatus] = useState(null);
  const [relationshipData, setRelationshipData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!goNumber) {
      setError("No Government Order number was provided.");
      setLoading(false);
      return;
    }

    let cancelled = false;

    async function loadDetails() {
      setLoading(true);
      setError("");

      const results = await Promise.allSettled([
        getGovernmentOrderDetails(goNumber),
        getGovernmentOrderStatus(goNumber),
        getGovernmentOrderRelationships(goNumber),
      ]);

      if (cancelled) return;

      const [detailsResult, statusResult, relationshipsResult] = results;

      if (detailsResult.status === "fulfilled") {
        setDetails(detailsResult.value);
      } else {
        setDetails(null);
      }

      if (statusResult.status === "fulfilled") {
        setStatus(statusResult.value);
      } else {
        setStatus(null);
      }

      if (relationshipsResult.status === "fulfilled") {
        setRelationshipData(relationshipsResult.value);
      } else {
        setRelationshipData(null);
      }

      const failures = results.filter(
        (item) => item.status === "rejected"
      );

      if (failures.length === results.length) {
        setError("Unable to load Government Order details. Please try again.");
      } else if (failures.length > 0) {
        setError(
          "Some information could not be loaded. Available information is shown below."
        );
      }

      setLoading(false);
    }

    loadDetails();

    return () => {
      cancelled = true;
    };
  }, [goNumber]);

  if (loading) {
    return (
      <section className="go-details">
        <p>Loading Government Order details...</p>
      </section>
    );
  }

  const effectiveStatus = status?.status || details?.status;
  const relationships = relationshipData?.relationships || [];

  return (
    <section className="go-details">
      <button type="button" onClick={onBack}>
        ← Back to Search
      </button>

      <h2>Government Order Details</h2>

      {error && <p role="alert">{error}</p>}

      <div className="go-details-card">
        <h3>{details?.go_number || goNumber || "Unknown GO number"}</h3>

        <p>
          <strong>Department:</strong>{" "}
          {details?.department || "Not available"}
        </p>

        <p>
          <strong>Issue Date:</strong>{" "}
          {details?.issue_date || "Not available"}
        </p>

        <p>
          <strong>Legal Status:</strong>{" "}
          {effectiveStatus || "Not available"}
        </p>

        {details?.document_id && (
          <p>
            <strong>Document ID:</strong> {details.document_id}
          </p>
        )}
      </div>

      <h3>Verified Status Details</h3>

      {status ? (
        <div className="go-details-card">
          <p>
            <strong>Relationships checked:</strong>{" "}
            {status.relationships_checked ?? "Not available"}
          </p>

          <p>
            <strong>Cycle detected:</strong>{" "}
            {status.cycle_detected === undefined
              ? "Not available"
              : status.cycle_detected
                ? "Yes"
                : "No"}
          </p>

          <p><strong>Traversal path:</strong></p>

          {status.traversed_go_numbers?.length ? (
            <ol>
              {status.traversed_go_numbers.map((number, index) => (
                <li key={`${number}-${index}`}>{number}</li>
              ))}
            </ol>
          ) : (
            <p>Traversal path not available.</p>
          )}
        </div>
      ) : (
        <p>Verified status details are unavailable.</p>
      )}

      <h3>Relationships ({relationshipData?.relationship_count ?? 0})</h3>

      {relationships.length > 0 ? (
        relationships.map((relationship, index) => (
          <article
            className="relationship-card"
            key={`${relationship.direction}-${relationship.related_go_number}-${index}`}
          >
            <p>
              <strong>Relationship:</strong>{" "}
              {relationship.relationship_type || "Not available"}
            </p>

            <p>
              <strong>Direction:</strong>{" "}
              {relationship.direction === "incoming"
                ? "This GO is acted on by another GO"
                : "This GO acts on another GO"}
            </p>

            <p>
              <strong>Related GO:</strong>{" "}
              {relationship.related_go_number || "Not available"}
            </p>

            <p>
              <strong>Department:</strong>{" "}
              {relationship.department || "Not available"}
            </p>

            <p>
              <strong>Issue Date:</strong>{" "}
              {relationship.issue_date || "Not available"}
            </p>

            <p>
              <strong>Matched Phrase:</strong>{" "}
              {relationship.matched_phrase || "Not available"}
            </p>

            <p>
              <strong>Page Number:</strong>{" "}
              {relationship.page_number ?? "Not available"}
            </p>
          </article>
        ))
      ) : (
        <p>No recorded relationships were found.</p>
      )}
    </section>
  );
}

export default GODetails;
