
import { useState } from "react";

import GODetails from "./GODetails";
import SearchBar from "../components/SearchBar";
import SearchResultCard from "../components/SearchResultCard";
import { searchGovernmentOrders } from "../services/api";

function Search() {
  const [selectedResult, setSelectedResult] = useState(null);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [intent, setIntent] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [hasSearched, setHasSearched] = useState(false);

  const handleSearch = async (searchQuery = query) => {
    const trimmedQuery = searchQuery.trim();

    if (!trimmedQuery || loading) {
      return;
    }

    setQuery(trimmedQuery);
    setSelectedResult(null);
    setLoading(true);
    setError("");
    setResults([]);
    setIntent("");
    setHasSearched(true);

    try {
      const data = await searchGovernmentOrders(trimmedQuery, 5);

      // Support the different result fields returned by the API.
      const returnedResults = Array.isArray(data.final_results)
        ? data.final_results
        : Array.isArray(data.search_results)
          ? data.search_results
          : Array.isArray(data.results)
            ? data.results
            : [];

      setResults(returnedResults);
      setIntent(data.intent || "");
    } catch (requestError) {
      console.error("Search request failed:", requestError);

      setError(
        requestError.response?.data?.detail ||
          "Unable to search Government Orders. Please check that the backend is running and try again."
      );
    } finally {
      setLoading(false);
    }
  };

  // Display the selected Government Order details.
  if (selectedResult) {
    return (
      <GODetails
        result={selectedResult}
        onBack={() => setSelectedResult(null)}
      />
    );
  }

  return (
    <main className="search-page">
      <header className="hero">
        <div className="hero-content">
          <p className="eyebrow">KERALA GOVERNMENT</p>

          <h1>Government Order Search</h1>

          <p className="hero-description">
            Search Government Orders using relevant queries in
            English or Malayalam. Find documents by topic, GO
            number, department, date, and more.
          </p>

          <SearchBar
            query={query}
            setQuery={setQuery}
            onSearch={() => handleSearch()}
            loading={loading}
          />

          <p className="example-query">
            Try a query such as:{" "}

            <button
              type="button"
              disabled={loading}
              onClick={() =>
                handleSearch(
                  "Which government order discusses Public WiFi?"
                )
              }
            >
              Public WiFi
            </button>

            {" · "}

            <button
              type="button"
              disabled={loading}
              onClick={() =>
                handleSearch(
                  "Find Government Orders related to scholarships"
                )
              }
            >
              Scholarships
            </button>

            {" · "}

            <button
              type="button"
              disabled={loading}
              onClick={() =>
                handleSearch("G.O.(Rt) No. 24/2026/ITD")
              }
            >
              GO number
            </button>
          </p>
        </div>
      </header>

      <section className="results-section">
        <div className="results-container">
          {/* Loading state */}
          {loading && (
            <div className="message-card" role="status">
              <div className="loader" />

              <h2>Searching Government Orders...</h2>

              <p>
                Processing your query and retrieving relevant
                documents.
              </p>
            </div>
          )}

          {/* Error state */}
          {!loading && error && (
            <div className="message-card error-card">
              <h2>Search failed</h2>

              <p>{error}</p>

              <button
                type="button"
                onClick={() => handleSearch()}
                disabled={!query.trim()}
              >
                Try Again
              </button>
            </div>
          )}

          {/* Search type */}
          {!loading && !error && intent && (
            <div className="search-info">
              <span>Search type</span>
              <strong>{intent}</strong>
            </div>
          )}

          {/* Search results */}
          {!loading && !error && results.length > 0 && (
            <div className="results-list">
              <div className="results-heading">
                <h2>Search Results</h2>

                <span>
                  {results.length} result
                  {results.length !== 1 ? "s" : ""}
                </span>
              </div>

              <p className="results-notice">
                Results are retrieved from the currently indexed
                Government Orders. Check each document's text to
                confirm that it answers your query.
              </p>

              {results.map((result, index) => (
                <SearchResultCard
                  key={
                    result.chunk_id ||
                    `${result.document_id || result.go_number || "result"}-${index}`
                  }
                  result={result}
                  onViewDetails={() => setSelectedResult(result)}
                />
              ))}
            </div>
          )}

          {/* Empty results state */}
          {!loading &&
            !error &&
            hasSearched &&
            results.length === 0 && (
              <div className="message-card">
                <h2>No results found</h2>

                <p>
                  No Government Orders were returned for this
                  query. Try different keywords or a more
                  specific GO number.
                </p>
              </div>
            )}

          {/* Initial state */}
          {!loading && !error && !hasSearched && (
            <div className="message-card">
              <h2>
                What Government Order are you looking for?
              </h2>

              <p>
                Enter a query to get started. You can search
                by topic, department, GO number, date, or a
                question in Malayalam or English.
              </p>
            </div>
          )}
        </div>
      </section>
    </main>
  );
}

export default Search;
