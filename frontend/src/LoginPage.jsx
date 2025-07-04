import React, { useState } from 'react';

function LoginPage({ onLoginSuccess }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [isRegistering, setIsRegistering] = useState(false); // Toggle between login/register
  const [message, setMessage] = useState(''); // For success/error messages
  const [loading, setLoading] = useState(false); // For loading state

  const handleSubmit = async (e) => {
    e.preventDefault();
    setMessage('');
    setLoading(true);

    const endpoint = isRegistering ? 'register' : 'login';
    const url = `http://127.0.0.1:5000/${endpoint}`;

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ username, password }),
      });

      const data = await response.json();

      if (response.ok) {
        setMessage(data.message);
        if (!isRegistering) {
          // On successful login, pass the username up to App.jsx
          onLoginSuccess(data.username);
        } else {
          // After successful registration, switch to login form
          setIsRegistering(false);
          setUsername('');
          setPassword('');
        }
      } else {
        setMessage(`Error: ${data.error || 'Something went wrong.'}`);
      }
    } catch (error) {
      console.error('Authentication error:', error);
      setMessage('Network error or server unreachable.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex flex-col items-center justify-center p-4 font-inter">
      <header className="w-full max-w-md bg-white rounded-xl shadow-lg p-6 mb-8 text-center">
        <h1 className="text-4xl font-bold text-blue-700 mb-2">
          MindEase
        </h1>
        <p className="text-lg text-gray-600">
          Your AI-powered companion for mental well-being.
        </p>
      </header>

      <main className="w-full max-w-md bg-white rounded-xl shadow-lg p-8">
        <h2 className="text-3xl font-semibold text-gray-800 mb-6 text-center">
          {isRegistering ? 'Register' : 'Login'}
        </h2>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="username" className="block text-gray-700 text-sm font-bold mb-2">
              Username:
            </label>
            <input
              type="text"
              id="username"
              className="shadow appearance-none border rounded-lg w-full py-3 px-4 text-gray-700 leading-tight focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              disabled={loading}
            />
          </div>
          <div>
            <label htmlFor="password" className="block text-gray-700 text-sm font-bold mb-2">
              Password:
            </label>
            <input
              type="password"
              id="password"
              className="shadow appearance-none border rounded-lg w-full py-3 px-4 text-gray-700 leading-tight focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              disabled={loading}
            />
          </div>
          <button
            type="submit"
            className="w-full bg-blue-600 text-white py-3 px-6 rounded-lg font-semibold text-lg hover:bg-blue-700 transition duration-300 ease-in-out shadow-md hover:shadow-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-opacity-75"
            disabled={loading}
          >
            {loading ? 'Processing...' : (isRegistering ? 'Register' : 'Login')}
          </button>
        </form>

        {message && (
          <p className={`mt-4 text-center ${message.startsWith('Error') ? 'text-red-600' : 'text-green-600'}`}>
            {message}
          </p>
        )}

        <div className="mt-6 text-center">
          <button
            onClick={() => {
              setIsRegistering(prev => !prev);
              setMessage('');
              setUsername('');
              setPassword('');
            }}
            className="text-blue-600 hover:text-blue-800 text-sm font-semibold focus:outline-none"
            disabled={loading}
          >
            {isRegistering ? 'Already have an account? Login' : 'New user? Register here'}
          </button>
        </div>
      </main>

      <footer className="mt-8 text-gray-500 text-sm">
        &copy; {new Date().getFullYear()} MindEase. All rights reserved.
      </footer>
    </div>
  );
}

export default LoginPage;
