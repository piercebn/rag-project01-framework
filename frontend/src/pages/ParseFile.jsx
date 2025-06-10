import React, { useState, useEffect } from 'react';
import RandomImage from '../components/RandomImage';
import { apiBaseUrl } from '../config/config';

const ParseFile = () => {
  const [file, setFile] = useState(null);
  const [loadingMethod, setLoadingMethod] = useState('pymupdf');
  const [parsingOption, setParsingOption] = useState('all_text');
  const [parsedContent, setParsedContent] = useState(null);
  const [status, setStatus] = useState('');
  const [docName, setDocName] = useState('');
  const [isProcessed, setIsProcessed] = useState(false);
  const [activeTab, setActiveTab] = useState('preview');
  const [parsedDocuments, setParsedDocuments] = useState([]);

  useEffect(() => {
    fetchParsedDocuments();
  }, []);

  useEffect(() => {
    if (activeTab === 'documents') {
      fetchParsedDocuments();
    }
  }, [activeTab]);

  const fetchParsedDocuments = async () => {
    try {
      const response = await fetch(`${apiBaseUrl}/documents?type=parsed`);
      const data = await response.json();
      setParsedDocuments(data.documents || []);
    } catch (error) {
      console.error('Error fetching parsed documents:', error);
      setStatus(`Error fetching documents: ${error.message}`);
    }
  };

  const handleDeleteDocument = async (docName) => {
    try {
      const response = await fetch(`${apiBaseUrl}/documents/${docName}?type=parsed`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      setStatus('Document deleted successfully');
      fetchParsedDocuments();
      if (parsedContent?.filename === docName) {
        setParsedContent(null);
      }
    } catch (error) {
      console.error('Error deleting document:', error);
      setStatus(`Error deleting document: ${error.message}`);
    }
  };

  const handleViewDocument = async (docName) => {
    try {
      const response = await fetch(`${apiBaseUrl}/documents/${docName}?type=parsed`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      setParsedContent(data);
      setActiveTab('preview');
    } catch (error) {
      console.error('Error viewing document:', error);
      setStatus(`Error viewing document: ${error.message}`);
    }
  };

  const handleProcess = async () => {
    if (!file || !loadingMethod || !parsingOption) {
      setStatus('Please select all required options');
      return;
    }

    setStatus('Processing...');
    setParsedContent(null);
    setIsProcessed(false);

    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('loading_method', loadingMethod);
      formData.append('parsing_option', parsingOption);

      const response = await fetch(`${apiBaseUrl}/parse`, {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      setParsedContent(data.parsed_content);
      setStatus('Processing completed successfully!');
      setIsProcessed(true);
    } catch (error) {
      console.error('Error:', error);
      setStatus(`Error: ${error.message}`);
    }
  };

  const handleFileSelect = (e) => {
    const file = e.target.files[0];
    if (file) {
      setFile(file);
      const baseName = file.name.replace('.pdf', '');
      setDocName(baseName);
    }
  };

  const renderRightPanel = () => {
    return (
      <div className="p-4">
        <div className="flex mb-4 border-b">
          <button
            className={`px-4 py-2 ${
              activeTab === 'preview'
                ? 'border-b-2 border-blue-500 text-blue-600'
                : 'text-gray-600'
            }`}
            onClick={() => setActiveTab('preview')}
          >
            Parsing Result
          </button>
          <button
            className={`px-4 py-2 ml-4 ${
              activeTab === 'documents'
                ? 'border-b-2 border-blue-500 text-blue-600'
                : 'text-gray-600'
            }`}
            onClick={() => setActiveTab('documents')}
          >
            Document Management
          </button>
        </div>

        {activeTab === 'preview' ? (
          parsedContent ? (
            <div className="p-4">
              <h3 className="text-xl font-semibold mb-4">Parsing Results</h3>
              <div className="mb-4 p-3 border rounded bg-gray-100">
                <h4 className="font-medium mb-2">Document Information</h4>
                <div className="text-sm text-gray-600">
                  <p>Filename: {parsedContent.filename}</p>
                  <p>Total Pages: {parsedContent.total_pages}</p>
                  <p>Total Chunks: {parsedContent.total_chunks}</p>
                  <p>Loading Method: {parsedContent.loading_method}</p>
                  <p>Parsing Method: {parsedContent.parsing_method}</p>
                  <p>Timestamp: {new Date(parsedContent.timestamp).toLocaleString()}</p>
                </div>
              </div>
              <div className="space-y-3 max-h-[calc(100vh-300px)] overflow-y-auto">
                {parsedContent.chunks.map((chunk, idx) => (
                  <div key={idx} className="p-3 border rounded bg-gray-50">
                    <div className="font-medium text-sm text-gray-500 mb-1">
                      Chunk {chunk.metadata.chunk_id} - 
                      Page {chunk.metadata.page_number} - 
                      {chunk.metadata.content_type}
                    </div>
                    {chunk.metadata.word_count && (
                      <div className="text-xs text-gray-400 mb-2">
                        Words: {chunk.metadata.word_count}
                      </div>
                    )}
                    <div className="text-sm text-gray-600">
                      {chunk.content}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <RandomImage message="Upload and parse a file to see the results here" />
          )
        ) : (
          <div>
            <h3 className="text-xl font-semibold mb-4">Document Management</h3>
            <div className="space-y-4">
              {parsedDocuments.map((doc) => (
                <div key={doc.id} className="p-4 border rounded-lg bg-gray-50">
                  <div className="flex justify-between items-start">
                    <div>
                      <h4 className="font-medium text-lg">{doc.name}</h4>
                      <div className="text-sm text-gray-600 mt-1">
                        <p>Pages: {doc.metadata?.total_pages || 'N/A'}</p>
                        <p>Chunks: {doc.metadata?.total_chunks || 'N/A'}</p>
                        <p>Parsing Method: {doc.metadata?.parsing_method || 'N/A'}</p>
                        <p>Created: {doc.metadata?.timestamp ? new Date(doc.metadata.timestamp).toLocaleString() : 'N/A'}</p>
                      </div>
                    </div>
                    <div className="flex space-x-2">
                      <button
                        onClick={() => handleViewDocument(doc.name)}
                        className="px-3 py-1 bg-blue-500 text-white rounded hover:bg-blue-600"
                      >
                        View
                      </button>
                      <button
                        onClick={() => handleDeleteDocument(doc.name)}
                        className="px-3 py-1 bg-red-500 text-white rounded hover:bg-red-600"
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                </div>
              ))}
              {parsedDocuments.length === 0 && (
                <div className="text-center text-gray-500 py-8">
                  No parsed documents available
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="p-6">
      <h2 className="text-2xl font-bold mb-6">Parse File</h2>
      
      <div className="grid grid-cols-12 gap-6">
        {/* Left Panel (3/12) */}
        <div className="col-span-3 space-y-4">
          <div className="p-4 border rounded-lg bg-white shadow-sm">
            <div>
              <label className="block text-sm font-medium mb-1">Upload PDF</label>
              <input
                type="file"
                accept=".pdf"
                onChange={handleFileSelect}
                className="block w-full border rounded px-3 py-2"
                required
              />
            </div>

            <div className="mt-4">
              <label className="block text-sm font-medium mb-1">Loading Tool</label>
              <select
                value={loadingMethod}
                onChange={(e) => setLoadingMethod(e.target.value)}
                className="block w-full p-2 border rounded"
              >
                <option value="pymupdf">PyMuPDF</option>
                <option value="pypdf">PyPDF</option>
                <option value="unstructured">Unstructured</option>
                <option value="pdfplumber">PDF Plumber</option>
                <option value="llamaparse">LlamaParse</option>
              </select>
            </div>

            <div className="mt-4">
              <label className="block text-sm font-medium mb-1">Parsing Option</label>
              <select
                value={parsingOption}
                onChange={(e) => setParsingOption(e.target.value)}
                className="block w-full p-2 border rounded"
              >
                <option value="all_text">All Text</option>
                <option value="by_pages">By Pages</option>
                <option value="by_titles">By Titles</option>
                <option value="text_and_tables">Text and Tables</option>
              </select>
            </div>

            <button 
              onClick={handleProcess}
              className="mt-4 w-full px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
              disabled={!file}
            >
              Process File
            </button>
          </div>
        </div>

        {/* Right Panel (9/12) */}
        <div className="col-span-9 border rounded-lg bg-white shadow-sm">
          {renderRightPanel()}
        </div>
      </div>
    </div>
  );
};

export default ParseFile; 