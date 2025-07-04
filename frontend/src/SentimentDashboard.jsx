import React, { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import Modal from './Modal'; // Assuming Modal.jsx is in the same directory

function SentimentDashboard({ username }) {
  const [sentimentSummary, setSentimentSummary] = useState(null);
  const [loadingSummary, setLoadingSummary] = useState(true);
  const [errorSummary, setErrorSummary] = useState(null);

  const [sentimentTrends, setSentimentTrends] = useState([]);
  const [loadingTrends, setLoadingTrends] = useState(true);
  const [errorTrends, setErrorTrends] = useState(null);

  // New states for Period Summary
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [periodSummary, setPeriodSummary] = useState('');
  const [loadingPeriodSummary, setLoadingPeriodSummary] = useState(false);
  const [errorPeriodSummary, setErrorPeriodSummary] = useState(null);

  // Modal state for feedback
  const [modal, setModal] = useState({
    isOpen: false,
    title: '',
    message: '',
    type: 'info'
  });

  const showModal = (title, message, type = 'info') => {
    setModal({ isOpen: true, title, message, type });
  };

  const closeModal = () => {
    setModal({ isOpen: false, title: '', message: '', type: 'info' });
  };

  // Helper to get sentiment color for chart lines
  const getChartLineColor = (sentimentType) => {
    switch (sentimentType) {
      case 'positive': return '#22C55E'; // Green-500
      case 'neutral': return '#6B7280'; // Gray-500
      case 'negative': return '#EF4444'; // Red-500
      case 'mixed': return '#F59E0B'; // Yellow-500
      case 'unknown': return '#3B82F6'; // Blue-500
      default: return '#9CA3AF'; // Default gray
    }
  };

  // Existing effect to fetch sentiment summary (total counts)
  useEffect(() => {
    const fetchSentimentSummary = async () => {
      if (!username) {
        setLoadingSummary(false);
        return;
      }

      setLoadingSummary(true);
      setErrorSummary(null);
      try {
        const response = await fetch(`https://mindease-nxnw.onrender.com/journal/sentiment_summary/${username}`);
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        setSentimentSummary(data);
      } catch (error) {
        console.error('Error fetching sentiment summary:', error);
        setErrorSummary('Failed to load sentiment summary.');
      } finally {
        setLoadingSummary(false);
      }
    };

    fetchSentimentSummary();
  }, [username]);

  // Existing effect to fetch sentiment trends
  useEffect(() => {
    const fetchSentimentTrends = async () => {
      if (!username) {
        setLoadingTrends(false);
        return;
      }

      setLoadingTrends(true);
      setErrorTrends(null);
      try {
        const response = await fetch(`https://mindease-nxnw.onrender.com/journal/sentiment_trends/${username}`);
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        setSentimentTrends(data);
      } catch (error) {
        console.error('Error fetching sentiment trends:', error);
        setErrorTrends('Failed to load sentiment trends.');
      } finally {
        setLoadingTrends(false);
      }
    };

    fetchSentimentTrends();
  }, [username]);

  const getSentimentColor = (sentimentType) => {
    switch (sentimentType) {
      case 'positive': return 'text-green-700 bg-green-50';
      case 'neutral': return 'text-gray-700 bg-gray-50';
      case 'negative': return 'text-red-700 bg-red-50';
      case 'mixed': return 'text-yellow-700 bg-yellow-50';
      case 'unknown': return 'text-blue-700 bg-blue-50';
      default: return 'text-gray-700 bg-gray-50';
    }
  };

  // NEW function to generate period summary
  const handleGeneratePeriodSummary = async () => {
    if (!username) {
      showModal('Login Required', 'Please log in to generate period summaries.', 'info');
      return;
    }
    if (!startDate || !endDate) {
      showModal('Date Range Required', 'Please select both a start and end date.', 'error');
      return;
    }
    if (new Date(startDate) > new Date(endDate)) {
      showModal('Invalid Date Range', 'Start date cannot be after end date.', 'error');
      return;
    }

    setLoadingPeriodSummary(true);
    setPeriodSummary(''); // Clear previous summary
    setErrorPeriodSummary(null);

    try {
      const response = await fetch(`https://mindease-nxnw.onrender.com/journal/period_summary/${username}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ start_date: startDate, end_date: endDate }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      if (result.summary) {
        setPeriodSummary(result.summary);
        if (result.entry_count === 0) {
            showModal('No Entries', 'No journal entries found for the selected period.', 'info');
        } else {
            showModal('Summary Generated', `Generated summary for ${result.entry_count} entries.`, 'success');
        }
      } else {
        setPeriodSummary('Failed to generate summary. No summary received.');
        showModal('Summary Failed', 'Failed to generate summary. No summary received.', 'error');
      }
    } catch (error) {
      console.error('Error generating period summary:', error);
      setErrorPeriodSummary(`Failed to generate summary: ${error.message || error}`);
      showModal('Summary Error', `Failed to generate summary: ${error.message || error}. Please try again.`, 'error');
    } finally {
      setLoadingPeriodSummary(false);
    }
  };

  // Check if there's any data at all for initial loading state
  const hasData = sentimentSummary && sentimentSummary.total > 0;
  const hasTrendData = sentimentTrends && sentimentTrends.length > 0;

  if (loadingSummary || loadingTrends) {
    return (
      <div className="text-center p-6 bg-white rounded-xl shadow-lg">
        <p className="text-gray-600">Loading sentiment dashboard...</p>
      </div>
    );
  }

  if (errorSummary || errorTrends) {
    return (
      <div className="text-center p-6 bg-white rounded-xl shadow-lg">
        <p className="text-red-600">{errorSummary || errorTrends}</p>
      </div>
    );
  }

  if (!hasData && !hasTrendData) {
    return (
      <div className="text-center p-6 bg-white rounded-xl shadow-lg">
        <p className="text-gray-600">No journal entries with sentiment data yet. Start journaling!</p>
      </div>
    );
  }

  return (
    <div className="p-6 bg-white rounded-xl shadow-lg">
      <h3 className="text-2xl font-semibold text-gray-800 mb-4 text-center">
        Your Sentiment Snapshot
      </h3>
      {hasData && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-8">
          {Object.entries(sentimentSummary).map(([sentimentType, count]) => {
            if (sentimentType === 'total') return null;
            return (
              <div 
                key={sentimentType} 
                className={`p-4 rounded-lg shadow-sm flex flex-col items-center justify-center ${getSentimentColor(sentimentType)}`}
              >
                <p className="text-4xl font-bold">{count}</p>
                <p className="text-lg capitalize">{sentimentType}</p>
              </div>
            );
          })}
        </div>
      )}
      {hasData && <p className="text-center text-gray-600 mb-8">Total Entries: <span className="font-bold">{sentimentSummary.total}</span></p>}

      <h3 className="text-2xl font-semibold text-gray-800 mb-4 text-center mt-8">
        Sentiment Trends Over Time
      </h3>
      {hasTrendData ? (
        <ResponsiveContainer width="100%" height={300}>
          <LineChart
            data={sentimentTrends}
            margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
            <XAxis dataKey="date" stroke="#6B7280" />
            <YAxis stroke="#6B7280" />
            <Tooltip 
                contentStyle={{ backgroundColor: '#fff', border: '1px solid #ccc', borderRadius: '8px', padding: '10px' }}
                labelStyle={{ color: '#333' }}
                itemStyle={{ color: '#555' }}
            />
            <Legend />
            <Line type="monotone" dataKey="positive" stroke={getChartLineColor('positive')} strokeWidth={2} dot={false} />
            <Line type="monotone" dataKey="neutral" stroke={getChartLineColor('neutral')} strokeWidth={2} dot={false} />
            <Line type="monotone" dataKey="negative" stroke={getChartLineColor('negative')} strokeWidth={2} dot={false} />
            <Line type="monotone" dataKey="mixed" stroke={getChartLineColor('mixed')} strokeWidth={2} dot={false} />
            <Line type="monotone" dataKey="unknown" stroke={getChartLineColor('unknown')} strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      ) : (
        <p className="text-center text-gray-600">No sufficient data for sentiment trends. Keep journaling!</p>
      )}

      {/* NEW: Period Summary Section */}
      <h3 className="text-2xl font-semibold text-gray-800 mb-4 text-center mt-8">
        Narrative Summary for a Period
      </h3>
      <div className="bg-white p-6 rounded-xl shadow-inner mb-8">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
          <div>
            <label htmlFor="startDate" className="block text-gray-700 text-sm font-bold mb-2">
              Start Date:
            </label>
            <input
              type="date"
              id="startDate"
              className="shadow appearance-none border rounded-lg w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              disabled={loadingPeriodSummary}
            />
          </div>
          <div>
            <label htmlFor="endDate" className="block text-gray-700 text-sm font-bold mb-2">
              End Date:
            </label>
            <input
              type="date"
              id="endDate"
              className="shadow appearance-none border rounded-lg w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              disabled={loadingPeriodSummary}
            />
          </div>
        </div>
        <button
          onClick={handleGeneratePeriodSummary}
          className="mt-4 w-full bg-teal-600 text-white py-3 px-6 rounded-lg font-semibold text-lg hover:bg-teal-700 transition duration-300 ease-in-out shadow-md hover:shadow-lg focus:outline-none focus:ring-2 focus:ring-teal-500 focus:ring-opacity-75"
          disabled={loadingPeriodSummary}
        >
          {loadingPeriodSummary ? 'Generating Summary...' : 'Generate Period Summary'}
        </button>

        {errorPeriodSummary && (
          <p className="text-red-600 text-center mt-4">{errorPeriodSummary}</p>
        )}

        {periodSummary && !errorPeriodSummary && (
          <div className="mt-6 p-4 bg-teal-50 rounded-lg border border-teal-200 text-teal-800 leading-relaxed">
            <p className="font-semibold mb-2">Summary:</p>
            <p>{periodSummary}</p>
          </div>
        )}
      </div>

      {/* Modal Component */}
      {modal.isOpen && (
        <Modal
          title={modal.title}
          message={modal.message}
          type={modal.type}
          onClose={closeModal}
        />
      )}
    </div>
  );
}

export default SentimentDashboard;
