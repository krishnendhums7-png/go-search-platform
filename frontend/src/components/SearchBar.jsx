function SearchBar({
  query,
  setQuery,
  onSearch,
  loading,
}) {
  const handleSubmit = (event) => {
    event.preventDefault();
    onSearch();
  };

  return (
    <form className="search-form" onSubmit={handleSubmit}>
      <input
        type="text"
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        placeholder="Search Government Orders..."
        aria-label="Search Government Orders"
      />

      <button
        type="submit"
        disabled={loading || !query.trim()}
      >
        {loading ? "Searching..." : "Search"}
      </button>
    </form>
  );
}

export default SearchBar;