import React, { useState, useEffect } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer
} from 'recharts';
import Modal from './Modal';

function SentimentDashboard({ username }) {
  const [sentimentSummary, setSentimentSummary] = useState(null);
  const [loadingSummary, setLoadingSummary] = useState(true);
  const [errorSummary, setErrorSummary] = useState(null);

  const [sentimentTrends, setSentimentTrends] = useState([]);
  const [loadingTrends, setLoadingTrends] = useState(true);
  const [errorTrends, setErrorTrends] = useState(null);

  // Period Summary
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [periodSummary, setPeriodSummary] = useState('');
  const [loadingPeriodSummary, setLoadingPeriodSummary] = useState(false);
  const [errorPeriodSummary, setErrorPeriodSummary] = useState(null);

  // Modal state
  const [modal, setModal] = useState({
    isOpen: false,
    title: '',
    message: '',
    type: 'info'
  });

  const showModal = (title, message, type = 'info') => {
    setModal({
      isOpen: true,
      title,
      message,
      type
    });
  };

  const closeModal = () => {
    setModal({
      isOpen: false,
      title: '',
      message: '',
      type: 'info'
    });
  };

  // ---------------------------------------------------------
  // Emotion colors for chart
  // ---------------------------------------------------------
  const getChartLineColor = (emotionType) => {
    switch (emotionType) {
      case 'joy':
        return '#22C55E';

      case 'sadness':
        return '#3B82F6';

      case 'anger':
        return '#EF4444';

      case 'fear':
        return '#8B5CF6';

      case 'love':
        return '#EC4899';

      case 'surprise':
        return '#F59E0B';

      case 'unknown':
        return '#6B7280';

      default:
        return '#9CA3AF';
    }
  };

  // ---------------------------------------------------------
  // Emotion card colors
  // ---------------------------------------------------------
  const getEmotionColor = (emotionType) => {
    switch (emotionType) {
      case 'joy':
        return 'text-green-700 bg-green-50';

      case 'sadness':
        return 'text-blue-700 bg-blue-50';

      case 'anger':
        return 'text-red-700 bg-red-50';

      case 'fear':
        return 'text-purple-700 bg-purple-50';

      case 'love':
        return 'text-pink-700 bg-pink-50';

      case 'surprise':
        return 'text-yellow-700 bg-yellow-50';

      case 'unknown':
        return 'text-gray-700 bg-gray-50';

      default:
        return 'text-gray-700 bg-gray-50';
    }
  };

  // ---------------------------------------------------------
  // Emotion emojis
  // ---------------------------------------------------------
  const emotionEmoji = {
    joy: '😊',
    sadness: '😢',
    anger: '😡',
    fear: '😨',
    love: '❤️',
    surprise: '😮',
    unknown: '❓'
  };

  // ---------------------------------------------------------
  // Fetch Emotion Summary
  // ---------------------------------------------------------
  useEffect(() => {
    const fetchSentimentSummary = async () => {
      if (!username) {
        setLoadingSummary(false);
        return;
      }

      setLoadingSummary(true);
      setErrorSummary(null);

      try {
        const response = await fetch(
          `http://127.0.0.1:5000/journal/sentiment_summary/${username}`
        );

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        console.log('EMOTION SUMMARY RECEIVED BY REACT:', data);

        setSentimentSummary(data);
      } catch (error) {
        console.error('Error fetching emotion summary:', error);
        setErrorSummary('Failed to load emotion summary.');
      } finally {
        setLoadingSummary(false);
      }
    };

    fetchSentimentSummary();
  }, [username]);

  // ---------------------------------------------------------
  // Fetch Emotion Trends
  // ---------------------------------------------------------
  useEffect(() => {
    const fetchSentimentTrends = async () => {
      if (!username) {
        setLoadingTrends(false);
        return;
      }

      setLoadingTrends(true);
      setErrorTrends(null);

      try {
        const response = await fetch(
          `http://127.0.0.1:5000/journal/sentiment_trends/${username}`
        );

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        console.log('EMOTION TRENDS RECEIVED BY REACT:', data);

        setSentimentTrends(data);
      } catch (error) {
        console.error('Error fetching emotion trends:', error);
        setErrorTrends('Failed to load emotion trends.');
      } finally {
        setLoadingTrends(false);
      }
    };

    fetchSentimentTrends();
  }, [username]);

  // ---------------------------------------------------------
  // Generate Period Summary
  // ---------------------------------------------------------
  const handleGeneratePeriodSummary = async () => {
    if (!username) {
      showModal(
        'Login Required',
        'Please log in to generate period summaries.',
        'info'
      );
      return;
    }

    if (!startDate || !endDate) {
      showModal(
        'Date Range Required',
        'Please select both a start and end date.',
        'error'
      );
      return;
    }

    if (new Date(startDate) > new Date(endDate)) {
      showModal(
        'Invalid Date Range',
        'Start date cannot be after end date.',
        'error'
      );
      return;
    }

    setLoadingPeriodSummary(true);
    setPeriodSummary('');
    setErrorPeriodSummary(null);

    try {
      const response = await fetch(
        `http://127.0.0.1:5000/journal/period_summary/${username}`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            start_date: startDate,
            end_date: endDate
          })
        }
      );

      if (!response.ok) {
        const errorData = await response.json();

        throw new Error(
          errorData.error || `HTTP error! status: ${response.status}`
        );
      }

      const result = await response.json();

      if (result.summary) {
        setPeriodSummary(result.summary);

        if (result.entry_count === 0) {
          showModal(
            'No Entries',
            'No journal entries found for the selected period.',
            'info'
          );
        } else {
          showModal(
            'Summary Generated',
            `Generated summary for ${result.entry_count} entries.`,
            'success'
          );
        }
      } else {
        setPeriodSummary(
          'Failed to generate summary. No summary received.'
        );

        showModal(
          'Summary Failed',
          'Failed to generate summary. No summary received.',
          'error'
        );
      }
    } catch (error) {
      console.error('Error generating period summary:', error);

      setErrorPeriodSummary(
        `Failed to generate summary: ${error.message || error}`
      );

      showModal(
        'Summary Error',
        `Failed to generate summary: ${
          error.message || error
        }. Please try again.`,
        'error'
      );
    } finally {
      setLoadingPeriodSummary(false);
    }
  };

  // ---------------------------------------------------------
  // Check data
  // ---------------------------------------------------------
  const hasData =
    sentimentSummary &&
    sentimentSummary.total > 0;

  const hasTrendData =
    sentimentTrends &&
    sentimentTrends.length > 0;

  // ---------------------------------------------------------
  // Loading state
  // ---------------------------------------------------------
  if (loadingSummary || loadingTrends) {
    return (
      <div className="text-center p-6 bg-white rounded-xl shadow-lg">
        <p className="text-gray-600">
          Loading emotion dashboard...
        </p>
      </div>
    );
  }

  // ---------------------------------------------------------
  // Error state
  // ---------------------------------------------------------
  if (errorSummary || errorTrends) {
    return (
      <div className="text-center p-6 bg-white rounded-xl shadow-lg">
        <p className="text-red-600">
          {errorSummary || errorTrends}
        </p>
      </div>
    );
  }

  // ---------------------------------------------------------
  // No data state
  // ---------------------------------------------------------
  if (!hasData && !hasTrendData) {
    return (
      <div className="text-center p-6 bg-white rounded-xl shadow-lg">
        <p className="text-gray-600">
          No journal entries with emotion data yet.
          Start journaling!
        </p>
      </div>
    );
  }

  // ---------------------------------------------------------
  // Main Dashboard
  // ---------------------------------------------------------
  return (
    <div className="p-6 bg-white rounded-xl shadow-lg">

      {/* =====================================================
          EMOTION SNAPSHOT
      ====================================================== */}
      <h3 className="text-2xl font-semibold text-gray-800 mb-4 text-center">
        Your Emotion Snapshot
      </h3>

      {hasData && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-8">

          {Object.entries(sentimentSummary).map(
            ([emotionType, count]) => {

              // Don't create a card for total
              if (emotionType === 'total') {
                return null;
              }

              return (
                <div
                  key={emotionType}
                  className={`p-4 rounded-lg shadow-sm flex flex-col items-center justify-center ${getEmotionColor(
                    emotionType
                  )}`}
                >
                  <p className="text-4xl font-bold">
                    {count}
                  </p>

                  <p className="text-lg capitalize">
                    {emotionEmoji[emotionType] || '❓'}{' '}
                    {emotionType}
                  </p>
                </div>
              );
            }
          )}

        </div>
      )}

      {/* Total Entries */}
      {hasData && (
        <p className="text-center text-gray-600 mb-8">
          Total Entries:{' '}
          <span className="font-bold">
            {sentimentSummary.total}
          </span>
        </p>
      )}

      {/* =====================================================
          EMOTION TRENDS
      ====================================================== */}
      <h3 className="text-2xl font-semibold text-gray-800 mb-4 text-center mt-8">
        Emotion Trends Over Time
      </h3>

      {hasTrendData ? (
        <ResponsiveContainer width="100%" height={300}>
          <LineChart
            data={sentimentTrends}
            margin={{
              top: 5,
              right: 30,
              left: 20,
              bottom: 5
            }}
          >

            <CartesianGrid
              strokeDasharray="3 3"
              stroke="#e0e0e0"
            />

            <XAxis
              dataKey="date"
              stroke="#6B7280"
            />

            <YAxis
              stroke="#6B7280"
              allowDecimals={false}
            />

            <Tooltip
              contentStyle={{
                backgroundColor: '#fff',
                border: '1px solid #ccc',
                borderRadius: '8px',
                padding: '10px'
              }}
              labelStyle={{
                color: '#333'
              }}
              itemStyle={{
                color: '#555'
              }}
            />

            <Legend />

            {/* Joy */}
            <Line
              type="monotone"
              dataKey="joy"
              name="Joy"
              stroke={getChartLineColor('joy')}
              strokeWidth={2}
              dot={true}
            />

            {/* Sadness */}
            <Line
              type="monotone"
              dataKey="sadness"
              name="Sadness"
              stroke={getChartLineColor('sadness')}
              strokeWidth={2}
              dot={true}
            />

            {/* Anger */}
            <Line
              type="monotone"
              dataKey="anger"
              name="Anger"
              stroke={getChartLineColor('anger')}
              strokeWidth={2}
              dot={true}
            />

            {/* Fear */}
            <Line
              type="monotone"
              dataKey="fear"
              name="Fear"
              stroke={getChartLineColor('fear')}
              strokeWidth={2}
              dot={true}
            />

            {/* Love */}
            <Line
              type="monotone"
              dataKey="love"
              name="Love"
              stroke={getChartLineColor('love')}
              strokeWidth={2}
              dot={true}
            />

            {/* Surprise */}
            <Line
              type="monotone"
              dataKey="surprise"
              name="Surprise"
              stroke={getChartLineColor('surprise')}
              strokeWidth={2}
              dot={true}
            />

            {/* Unknown */}
            <Line
              type="monotone"
              dataKey="unknown"
              name="Unknown"
              stroke={getChartLineColor('unknown')}
              strokeWidth={2}
              dot={true}
            />

          </LineChart>
        </ResponsiveContainer>
      ) : (
        <p className="text-center text-gray-600">
          No sufficient data for emotion trends.
          Keep journaling!
        </p>
      )}

      {/* =====================================================
          PERIOD SUMMARY
      ====================================================== */}
      <h3 className="text-2xl font-semibold text-gray-800 mb-4 text-center mt-8">
        Narrative Summary for a Period
      </h3>

      <div className="bg-white p-6 rounded-xl shadow-inner mb-8">

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">

          {/* Start Date */}
          <div>
            <label
              htmlFor="startDate"
              className="block text-gray-700 text-sm font-bold mb-2"
            >
              Start Date:
            </label>

            <input
              type="date"
              id="startDate"
              className="shadow appearance-none border rounded-lg w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={startDate}
              onChange={(e) =>
                setStartDate(e.target.value)
              }
              disabled={loadingPeriodSummary}
            />
          </div>

          {/* End Date */}
          <div>
            <label
              htmlFor="endDate"
              className="block text-gray-700 text-sm font-bold mb-2"
            >
              End Date:
            </label>

            <input
              type="date"
              id="endDate"
              className="shadow appearance-none border rounded-lg w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={endDate}
              onChange={(e) =>
                setEndDate(e.target.value)
              }
              disabled={loadingPeriodSummary}
            />
          </div>

        </div>

        {/* Generate Summary Button */}
        <button
          onClick={handleGeneratePeriodSummary}
          className="mt-4 w-full bg-teal-600 text-white py-3 px-6 rounded-lg font-semibold text-lg hover:bg-teal-700 transition duration-300 ease-in-out shadow-md hover:shadow-lg focus:outline-none focus:ring-2 focus:ring-teal-500 focus:ring-opacity-75"
          disabled={loadingPeriodSummary}
        >
          {loadingPeriodSummary
            ? 'Generating Summary...'
            : 'Generate Period Summary'}
        </button>

        {/* Summary Error */}
        {errorPeriodSummary && (
          <p className="text-red-600 text-center mt-4">
            {errorPeriodSummary}
          </p>
        )}

        {/* Summary Result */}
        {periodSummary && !errorPeriodSummary && (
          <div className="mt-6 p-4 bg-teal-50 rounded-lg border border-teal-200 text-teal-800 leading-relaxed">
            <p className="font-semibold mb-2">
              Summary:
            </p>

            <p>
              {periodSummary}
            </p>
          </div>
        )}

      </div>

      {/* =====================================================
          MODAL
      ====================================================== */}
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