import React, { useState, useEffect } from 'react';
import LoginPage from './LoginPage';
import SentimentDashboard from './SentimentDashboard';
import Modal from './Modal';
import SettingsPage from './SettingsPage';

function App() {
  const [backendStatus, setBackendStatus] = useState('Checking...');
  const [backendMessage, setBackendMessage] = useState('');
  const [dbStatus, setDbStatus] = useState('');

  const [loggedInUser, setLoggedInUser] = useState(null);

  const [journalEntry, setJournalEntry] = useState('');
  const [journalEntries, setJournalEntries] = useState([]);
  const [loadingEntries, setLoadingEntries] = useState(true);
  const [errorEntries, setErrorEntries] = useState(null);

  const [insightLoading, setInsightLoading] = useState({});
  const [insights, setInsights] = useState({});

  const [sentimentUpdateLoading, setSentimentUpdateLoading] = useState({});

  const [activeView, setActiveView] = useState('journal'); 

  // New state for generated journaling prompt
  const [generatedPrompt, setGeneratedPrompt] = useState('');
  const [promptLoading, setPromptLoading] = useState(false);

  // New state for modal (remains the same)
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

  // Function to get sentiment display styles/emoji (remains the same)
  const getSentimentDisplay = (sentiment) => {
    switch (sentiment) {
      case 'positive':
        return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">Positive 😊</span>;
      case 'neutral':
        return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">Neutral 😐</span>;
      case 'negative':
        return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">Negative 🙁</span>;
      case 'mixed':
        return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">Mixed 🤔</span>;
      default:
        return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">Unknown ❓</span>;
    }
  };

  // Effect to fetch backend status (existing)
  useEffect(() => {
    const fetchBackendStatus = async () => {
      try {
        const response = await fetch('https://mindease-nxnw.onrender.com/');
        const data = await response.json();
        setBackendStatus(data.status);
        setBackendMessage(data.message);
        setDbStatus(data.database_status);
      } catch (error) {
        console.error('Error fetching backend status:', error);
        setBackendStatus('Error');
        setBackendMessage('Could not connect to backend API.');
        setDbStatus('N/A');
      }
    };

    fetchBackendStatus();
  }, []);

  // Effect to fetch journal entries from the backend (runs only if loggedInUser changes)
  useEffect(() => {
    const fetchJournalEntries = async () => {
      if (!loggedInUser) {
        setJournalEntries([]);
        setLoadingEntries(false);
        return;
      }

      setLoadingEntries(true);
      setErrorEntries(null);
      try {
        const response = await fetch(`https://mindease-nxnw.onrender.com/journal/${loggedInUser}`);
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        setJournalEntries(data);
      } catch (error) {
        console.error('Error fetching journal entries:', error);
        setErrorEntries('Failed to load journal entries.');
      } finally {
        setLoadingEntries(false);
      }
    };

    fetchJournalEntries();
  }, [loggedInUser]);

  // Function to save a new journal entry to the backend (existing, slightly refined)
  const handleSaveEntry = async () => {
    if (!loggedInUser) {
      showModal('Login Required', 'Please log in to save journal entries.', 'info');
      return;
    }
    if (journalEntry.trim()) {
      try {
        const response = await fetch(`https://mindease-nxnw.onrender.com/journal/${loggedInUser}`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ text: journalEntry.trim() }),
        });

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
        }

        const result = await response.json();
        console.log('Backend response:', result);

        if (result.entry) {
          setJournalEntries(prevEntries => [result.entry, ...prevEntries]);
          showModal('Success', 'Journal entry saved successfully!', 'success');
        }
        
        setJournalEntry(''); // Clear input field
        setGeneratedPrompt(''); // Clear prompt after saving
      } catch (error) {
        console.error('Error saving journal entry:', error);
        showModal('Error Saving Entry', `Failed to save journal entry: ${error.message || error}. Please try again.`, 'error');
      }
    }
  };

  // Function to get insight from LLM (no change needed here for auth)
  const handleGetInsight = async (entryId, entryText) => {
    setInsightLoading(prev => ({ ...prev, [entryId]: true }));
    setInsights(prev => ({ ...prev, [entryId]: 'Generating insight...' }));

    try {
      const response = await fetch('https://mindease-nxnw.onrender.com/journal/insight', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ text: entryText }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      if (result.insight) {
        setInsights(prev => ({ ...prev, [entryId]: result.insight }));
      } else {
        setInsights(prev => ({ ...prev, [entryId]: 'No insight available.' }));
      }
    } catch (error) {
      console.error('Error getting insight:', error);
      setInsights(prev => ({ ...prev, [entryId]: `Failed to generate insight: ${error.message || error}` }));
    } finally {
      setInsightLoading(prev => ({ ...prev, [entryId]: false }));
    }
  };

  // Function to update sentiment for a specific entry
  const handleUpdateSentiment = async (entryId, entryText) => {
    if (!loggedInUser) {
      showModal('Login Required', 'Please log in to update sentiment.', 'info');
      return;
    }
    setSentimentUpdateLoading(prev => ({ ...prev, [entryId]: true }));

    try {
      const response = await fetch(`https://mindease-nxnw.onrender.com/journal/update_sentiment/${loggedInUser}/${entryId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ text: entryText }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      console.log('Sentiment update response:', result);

      if (result.new_sentiment) {
        setJournalEntries(prevEntries =>
          prevEntries.map(entry =>
            entry.id === entryId ? { ...entry, sentiment: result.new_sentiment } : entry
          )
        );
        showModal('Sentiment Updated', 'Sentiment for entry updated successfully!', 'success');
      } else {
        showModal('Sentiment Update Failed', 'Failed to update sentiment: No new sentiment received.', 'error');
      }
    } catch (error) {
      console.error('Error updating sentiment:', error);
      showModal('Sentiment Update Error', `Failed to update sentiment: ${error.message || error}. Please try again.`, 'error');
    } finally {
      setSentimentUpdateLoading(prev => ({ ...prev, [entryId]: false }));
    }
  };

  // NEW function to generate a journaling prompt
  const handleGeneratePrompt = async () => {
    if (!loggedInUser) {
      showModal('Login Required', 'Please log in to generate journaling prompts.', 'info');
      return;
    }
    setPromptLoading(true);
    setGeneratedPrompt('Generating a prompt...');

    try {
      const response = await fetch(`https://mindease-nxnw.onrender.com/journal/generate_prompt/${loggedInUser}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({}) // No specific data needed for this POST, but body is required
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      if (result.prompt) {
        setGeneratedPrompt(result.prompt);
      } else {
        setGeneratedPrompt('Could not generate a prompt. Please try again.');
      }
    } catch (error) {
      console.error('Error generating prompt:', error);
      setGeneratedPrompt(`Failed to generate prompt: ${error.message || error}`);
    } finally {
      setPromptLoading(false);
    }
  };

  const handleLogout = () => {
    setLoggedInUser(null);
    setJournalEntries([]);
    setInsights({});
    setJournalEntry('');
    setGeneratedPrompt(''); // Clear prompt on logout
    setActiveView('journal'); // Reset view on logout
    showModal('Logged Out', 'You have been successfully logged out.', 'info');
  };

  if (!loggedInUser) {
    return <LoginPage onLoginSuccess={setLoggedInUser} />;
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex flex-col items-center justify-center p-4 font-inter">
      <header className="w-full max-w-4xl bg-white rounded-xl shadow-lg p-6 mb-8 text-center flex justify-between items-center">
        <div>
          <h1 className="text-4xl font-bold text-blue-700 mb-2">
            Welcome to MindEase
          </h1>
          <p className="text-lg text-gray-600">
            Your AI-powered companion for mental well-being.
          </p>
        </div>
        {loggedInUser && (
          <div className="flex items-center space-x-4">
            <span className="text-gray-700 font-medium">Logged in as: <span className="font-bold text-blue-700">{loggedInUser}</span></span>
            <button
              onClick={handleLogout}
              className="bg-red-500 text-white py-2 px-4 rounded-lg font-semibold text-sm hover:bg-red-600 transition duration-300 ease-in-out shadow-md"
            >
              Logout
            </button>
          </div>
        )}
      </header>

      <main className="w-full max-w-4xl bg-white rounded-xl shadow-lg p-8 mb-8">
        <h2 className="text-3xl font-semibold text-gray-800 mb-6 text-center">
          Frontend Status
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
          <div className="bg-blue-50 p-6 rounded-lg shadow-inner">
            <h3 className="text-xl font-medium text-blue-800 mb-2">Backend Connection:</h3>
            <p className="text-lg text-gray-700">Status: <span className={`font-bold ${backendStatus === 'success' ? 'text-green-600' : 'text-red-600'}`}>{backendStatus}</span></p>
            <p className="text-lg text-gray-700">Message: <span className="font-semibold">{backendMessage}</span></p>
          </div>

          <div className="bg-indigo-50 p-6 rounded-lg shadow-inner">
            <h3 className="text-xl font-medium text-indigo-800 mb-2">Database Connection:</h3>
            <p className="text-lg text-gray-700">Status: <span className={`font-bold ${dbStatus === 'connected' ? 'text-green-600' : 'text-red-600'}`}>{dbStatus}</span></p>
          </div>
        </div>

        {/* Navigation for Journal/Dashboard/Settings */}
        <div className="flex justify-center space-x-4 mb-8">
          <button
            onClick={() => setActiveView('journal')}
            className={`py-2 px-6 rounded-lg font-semibold text-lg transition duration-300 ease-in-out ${
              activeView === 'journal' ? 'bg-blue-600 text-white shadow-md' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
            }`}
          >
            Journal
          </button>
          <button
            onClick={() => setActiveView('dashboard')}
            className={`py-2 px-6 rounded-lg font-semibold text-lg transition duration-300 ease-in-out ${
              activeView === 'dashboard' ? 'bg-blue-600 text-white shadow-md' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
            }`}
          >
            Dashboard
          </button>
          <button
            onClick={() => setActiveView('settings')}
            className={`py-2 px-6 rounded-lg font-semibold text-lg transition duration-300 ease-in-out ${
              activeView === 'settings' ? 'bg-blue-600 text-white shadow-md' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
            }`}
          >
            Settings
          </button>
        </div>

        {/* Conditional Rendering of Views */}
        {activeView === 'journal' && (
          <section>
            <h2 className="text-3xl font-semibold text-gray-800 mb-6 text-center">
              Your Daily Journal
            </h2>
            <div className="bg-white p-6 rounded-xl shadow-inner mb-8">
              <textarea
                className="w-full p-4 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-gray-800 resize-y min-h-[120px]"
                placeholder="What's on your mind today?"
                value={journalEntry}
                onChange={(e) => setJournalEntry(e.target.value)}
              ></textarea>
              <button
                onClick={handleSaveEntry}
                className="mt-4 w-full bg-blue-600 text-white py-3 px-6 rounded-lg font-semibold text-lg hover:bg-blue-700 transition duration-300 ease-in-out shadow-md hover:shadow-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-opacity-75"
              >
                Save Entry
              </button>

              {/* Generate Prompt Section */}
              <div className="mt-6 border-t pt-6 border-gray-200">
                <button
                  onClick={handleGeneratePrompt}
                  className="w-full bg-indigo-600 text-white py-3 px-6 rounded-lg font-semibold text-lg hover:bg-indigo-700 transition duration-300 ease-in-out shadow-md hover:shadow-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-opacity-75"
                  disabled={promptLoading}
                >
                  {promptLoading ? 'Generating Prompt...' : 'Generate Journaling Prompt'}
                </button>
                {generatedPrompt && (
                  <div className="mt-4 p-4 bg-indigo-50 rounded-lg border border-indigo-200 text-indigo-800">
                    <p className="font-semibold mb-2">Suggested Prompt:</p>
                    <p>{generatedPrompt}</p>
                  </div>
                )}
              </div>
            </div>

            <h3 className="text-2xl font-semibold text-gray-800 mb-4 text-center">
              Past Entries
            </h3>
            <div className="space-y-4">
              {loadingEntries ? (
                <p className="text-center text-gray-600">Loading journal entries...</p>
              ) : errorEntries ? (
                <p className="text-center text-red-600">{errorEntries}</p>
              ) : journalEntries.length > 0 ? (
                journalEntries.map((entry) => (
                  <div key={entry.id} className="bg-white p-5 rounded-lg shadow-md border border-gray-200">
                    <div className="flex justify-between items-center mb-2">
                      <p className="text-sm text-gray-500">{entry.date}</p>
                      {entry.sentiment && getSentimentDisplay(entry.sentiment)}
                    </div>
                    <p className="text-gray-800 leading-relaxed">{entry.text}</p>
                    <div className="flex flex-wrap gap-2 mt-3">
                      <button
                        onClick={() => handleGetInsight(entry.id, entry.text)}
                        className="bg-purple-600 text-white py-2 px-4 rounded-lg text-sm hover:bg-purple-700 transition duration-300 ease-in-out shadow-sm hover:shadow-md focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-opacity-75"
                        disabled={insightLoading[entry.id]}
                      >
                        {insightLoading[entry.id] ? 'Generating Insight...' : 'Get Insight'}
                      </button>
                      {entry.sentiment === 'unknown' && (
                        <button
                          onClick={() => handleUpdateSentiment(entry.id, entry.text)}
                          className="bg-orange-500 text-white py-2 px-4 rounded-lg text-sm hover:bg-orange-600 transition duration-300 ease-in-out shadow-sm hover:shadow-md focus:outline-none focus:ring-2 focus:ring-orange-500 focus:ring-opacity-75"
                          disabled={sentimentUpdateLoading[entry.id]}
                        >
                          {sentimentUpdateLoading[entry.id] ? 'Updating Sentiment...' : 'Recalculate Sentiment'}
                        </button>
                      )}
                    </div>
                    {insights[entry.id] && (
                      <div className="mt-3 p-3 bg-purple-50 rounded-lg border border-purple-200 text-purple-800 text-sm">
                        <p className="font-semibold mb-1">AI Insight:</p>
                        <p>{insights[entry.id]}</p>
                      </div>
                    )}
                  </div>
                ))
              ) : (
                <p className="text-center text-gray-600">No journal entries yet. Start by writing one above!</p>
              )}
            </div>
          </section>
        )}

        {activeView === 'dashboard' && (
          <section>
            <SentimentDashboard username={loggedInUser} />
          </section>
        )}

        {activeView === 'settings' && (
          <section>
            <SettingsPage username={loggedInUser} />
          </section>
        )}
      </main>

      <footer className="mt-8 text-gray-500 text-sm">
        &copy; {new Date().getFullYear()} MindEase. All rights reserved.
      </footer>

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

export default App;
