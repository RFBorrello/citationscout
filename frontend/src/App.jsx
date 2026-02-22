import { useMemo, useState } from "react";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

const statusClassMap = {
  valid: "status-valid",
  review: "status-review",
  invalid: "status-invalid",
};

function App() {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);

  const summary = useMemo(() => {
    if (!result?.citations) {
      return null;
    }

    return result.citations.reduce(
      (acc, item) => {
        acc[item.type] = (acc[item.type] ?? 0) + 1;
        return acc;
      },
      { case: 0, statute: 0, regulation: 0 }
    );
  }, [result]);

  const onSubmit = async (event) => {
    event.preventDefault();
    setError("");
    setResult(null);

    if (!file) {
      setError("Select a .docx file before uploading.");
      return;
    }

    const formData = new FormData();
    formData.append("file", file);

    setLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/upload`, {
        method: "POST",
        body: formData,
      });

      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail || "Upload failed.");
      }

      setResult(payload);
    } catch (err) {
      setError(err.message || "Unexpected error while uploading.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="page">
      <section className="card">
        <h1>Citation Scout MVP</h1>
        <p className="subtitle">
          Upload a Word document to extract legal citations (cases, statutes, and regulations).
        </p>

        <form className="upload-form" onSubmit={onSubmit}>
          <input
            type="file"
            accept=".docx"
            onChange={(event) => setFile(event.target.files?.[0] || null)}
          />
          <button type="submit" disabled={loading}>
            {loading ? "Processing..." : "Upload & Extract"}
          </button>
        </form>

        {error ? <p className="error">{error}</p> : null}

        {result ? (
          <section className="results">
            <div className="meta">
              <p>
                <strong>File:</strong> {result.filename}
              </p>
              <p>
                <strong>Total citations:</strong> {result.citation_count}
              </p>
            </div>

            {summary ? (
              <div className="summary">
                <span>Cases: {summary.case}</span>
                <span>Statutes: {summary.statute}</span>
                <span>Regulations: {summary.regulation}</span>
              </div>
            ) : null}

            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Type</th>
                    <th>Citation Text</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {result.citations.length > 0 ? (
                    result.citations.map((citation, index) => (
                      <tr key={`${citation.text}-${index}`}>
                        <td className="capitalize">{citation.type}</td>
                        <td>{citation.text}</td>
                        <td>
                          <span className={`status-pill ${statusClassMap[citation.status] || ""}`}>
                            {citation.status}
                          </span>
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan="3" className="empty">
                        No citations found in this document.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </section>
        ) : null}
      </section>
    </main>
  );
}

export default App;
