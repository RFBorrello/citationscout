import { useMemo, useState } from "react";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

const statusClassMap = {
  valid: "status-valid",
  review: "status-review",
  invalid: "status-invalid",
};

function App() {
  const [file, setFile] = useState(null);
  const [loadingAction, setLoadingAction] = useState("");
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);
  const [debugResult, setDebugResult] = useState(null);

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

  const uploadToEndpoint = async (endpoint) => {
    if (!file) {
      setError("Select a .docx file before uploading.");
      return null;
    }

    const formData = new FormData();
    formData.append("file", file);

    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      method: "POST",
      body: formData,
    });

    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || "Upload failed.");
    }

    return payload;
  };

  const onSubmit = async (event) => {
    event.preventDefault();
    setError("");
    setResult(null);
    setDebugResult(null);

    setLoadingAction("upload");
    try {
      const payload = await uploadToEndpoint("/upload");
      setResult(payload);
    } catch (err) {
      setError(err.message || "Unexpected error while uploading.");
    } finally {
      setLoadingAction("");
    }
  };

  const onDebug = async () => {
    setError("");
    setResult(null);
    setDebugResult(null);

    setLoadingAction("debug");
    try {
      const payload = await uploadToEndpoint("/debug");
      setDebugResult(payload);
    } catch (err) {
      setError(err.message || "Unexpected error while uploading.");
    } finally {
      setLoadingAction("");
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
          <button type="submit" disabled={Boolean(loadingAction)}>
            {loadingAction === "upload" ? "Processing..." : "Upload & Extract"}
          </button>
          <button
            type="button"
            className="secondary"
            disabled={Boolean(loadingAction)}
            onClick={onDebug}
          >
            {loadingAction === "debug" ? "Processing..." : "Run Debug Extract"}
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

        {debugResult ? (
          <section className="results">
            <div className="meta">
              <p>
                <strong>Debug file:</strong> {debugResult.filename}
              </p>
              <p>
                <strong>Extracted characters:</strong> {debugResult.character_count}
              </p>
            </div>
            <div className="debug-panel">
              <h2>Extracted Text Preview</h2>
              <pre>{debugResult.raw_extracted_text.slice(0, 4000)}</pre>
            </div>
          </section>
        ) : null}
      </section>
    </main>
  );
}

export default App;
